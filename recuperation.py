from datetime import datetime
import re

from dateparser import DateDataParser
import pandas as pd

from gestion_erreurs import ajout_erreur


# on crée un analyseur de dates pour le français
DDP = DateDataParser(languages=["fr"])
# on stocke la date du jour d'exécution pour filtrer les dates mal reconnues
# (eg. si la date de signature extraite est postérieure à la date du jour)
_TODAY = datetime.now()


def recup_id(texte):
    with open(texte, "r", encoding="utf-8") as fichier:
        res = str(fichier.read()).partition("ID : ")[2].partition("\n")[0]
    return res


def recup_adresse(texte):
    with open(texte, "r", encoding="utf-8") as fichier:
        res = (
            str(fichier.read())
            .partition("immeuble sis ")[2]
            .partition("-")[0]
            .partition("")[0]
            .partition("â")[0]
            .partition("—")[0]
        )
    return res


def recup_pathologie(texte, db_csv, p_list_txt, i):
    fichier = open(texte, "r", encoding="utf-8")
    if "pathologies suivantes" in fichier.read():
        fichier.seek(0)
        res = (
            str(fichier.read())
            .partition("pathologies suivantes")[2]
            .partition("Considérant")[0]
        )
        fichier.close()
        return res
    else:
        fichier.close()
        ajout_erreur(db_csv, p_list_txt, i, "Problème pathologies")
        return None


PROG_ENVOI_PREF = re.compile(
    "Envoyé en préfecture le (?P<date_envoi>\d\d/\d\d/\d\d\d\d)[ ]*\n"
)
PROG_DATE_SIGN = re.compile("Signé[ ]?le[ ]?:[ ]?(?P<date_sign>.*)\n")


def recup_date(p_txt):
    with open(p_txt, "r", encoding="utf-8") as f_txt:
        doc_txt = str(f_txt.read())
    # heuristique 1: extraire la date du tampon de transmission à la préfecture
    m_pref = PROG_ENVOI_PREF.search(doc_txt)
    # heuristique 2: extraite la date de la signature en fin d'acte
    m_sign = PROG_DATE_SIGN.search(doc_txt)
    if m_pref is not None:
        # ex: "Envoyé en préfecture le 23/10/2019"
        res = m_pref.group("date_envoi")
        # print("date: pref", repr(res))
        res_old = datetime.strptime(res, "%d/%m/%Y").strftime("%d/%m/%Y")
        res_new = DDP.get_date_data(res)["date_obj"].strftime("%d/%m/%Y")
        assert res_old == res_new
        return res_new
    elif m_sign is not None:
        # ex: "Signé le : 23 décembre 2018"
        res = m_sign.group("date_sign")
        # print("date: sign (raw)", repr(res))
        res = DDP.get_date_data(res)["date_obj"]
        # erreurs d'OCR: dates non ou mal lues, car manuscrites ou partiellement effacées
        if res is None:
            # la date n'a pu être lue
            print("ERR date non lue", p_txt)
            raise ValueError("Problème date")
        elif res > _TODAY:
            # la date a été mal lue
            print("ERR date future: ", res, p_txt)
            raise ValueError("Problème date")
        res = res.strftime("%d/%m/%Y")
        # print("date: sign (pro)", repr(res))
        return res
    elif p_txt in (
        # date manuscrite ou pb OCR
        "./Datas/TXT/ml_30-rue-du-bon-pasteur-13002_2019_04445.txt",
        "./Datas/TXT/pi_2020_57-rue-felix-pyat-13003_01751_vdm.txt",
        "./Datas/TXT/ml_43-rue-francois-barbini-13003_2020_02677_vdm.txt",
        "./Datas/TXT/ml_11-rue-kleber-13011_2020_02228_vdm.txt",
        "./Datas/TXT/pi_22-rue-sery-13003_2020_02824_vdm.txt",
        "./Datas/TXT/ml_2-rue-lucien-rolmer-13003_2020_03037_vdm.txt",
        "./Datas/TXT/10-rue-de-marathon-13003_abrogation_perimetre_2020_00022.txt",
        "./Datas/TXT/8-impasse-croix-de-regnier_13004_ms_2021_00426_1.txt",
        "./Datas/TXT/pi_60_rue_roouebrune-13004_n2020_02529_.txt",
        "./Datas/TXT/ml-6a-imp-croix-de-regnier-13004-2021-00774-160321.txt",
        "./Datas/TXT/po_162-rue-saint-pierre-13005_2020_02036_vdm.txt",
        "./Datas/TXT/po_7-rue-de-bruys-13005_2020_02037_vdm.txt",
        "./Datas/TXT/po_58-rue-saint-pierre-13005_2020_02594_vdm.txt",
        "./Datas/TXT/4-rue-de-lolivier-13005_ms_2021_00133.txt",
        "./Datas/TXT/ml_29-rue-saint-suffren-13006_2020_00787_vdm.txt",
        "./Datas/TXT/83-rue-marengo-13006_2020_02405.txt",
        "./Datas/TXT/5-rue-de-village-13006_2021_00790.txt",
        "./Datas/TXT/po_27-rue-nau-13006_2020_02800_vdm.txt",
        "./Datas/TXT/pi_99-rue-de-tilsit-13006_modif_2020_02038_vdm.txt",
        "./Datas/TXT/ml_41-rue-des-bons-enfants-13006_2020_02245_vdm.txt",
        "./Datas/TXT/28-rue-des-trois-rois-13006_po-2020_02738.txt",
        "./Datas/TXT/ml_7-boulevard-louis-salvator-13006_2020_02039_vdm.txt",
        "./Datas/TXT/po_10-12-14-boulevard-alexandre-delabre-13008_2020_01858_vdm.txt",
        "./Datas/TXT/pi_n2020-01691_vdm-45-che-valbarelle-a-saintmarcel-13010.txt",
        "./Datas/TXT/16-rue-d-alby-13010_2021_00137.txt",
        "./Datas/TXT/535-rue-saint-pierre_13012_pi_2020_02524.txt",
        "./Datas/TXT/535-rue-saint-pierre_13012_modif-deconstruction-2020_02525.txt",
        "./Datas/TXT/4-impasse-montcault_13013_po_ndeg2020_02902.txt",
        "./Datas/TXT/4_rue-saint-andre_13014_ml_2021_00380.txt",
        "./Datas/TXT/57-rue-merlino-13014_msu_2021_00494.txt",
        "./Datas/TXT/234-avenue-salengro_msu_2021_00667_du-01-03-2021.txt",
        "./Datas/TXT/18-rue-le-chatelier-13015_ml_2021_00670_du-01-mars-2021.txt",
        "./Datas/TXT/4-chemin-de-la-martine-13015_2021_00370.txt",
        "./Datas/TXT/ppm_61-rue-francis-davso-13001_2020_02290_vdm.txt",
        "./Datas/TXT/abrogation-ppm_119-boulevard-national-13003_2020_01999_vdm.txt",
        "./Datas/TXT/ppm_64-traverse-du-moulin-de-la-vilette-13003_2020_02801_vdm.txt",
        "./Datas/TXT/ppm_14-rue-auphan_13003_2020_03030_vdm.txt",
        "./Datas/TXT/11-rue-jean-cristofol-13003_ppm_ndeg2020_00024.txt",
        "./Datas/TXT/161-av-camille-pelletan-2021_00530.txt",
        "./Datas/TXT/28-rue-albe-13004_ppm-2020_03139.txt",
        "./Datas/TXT/mise_en_securite_2020_02385_vdm.txt",
        "./Datas/TXT/ppm-39-rue-de-la-petite-mallette.txt",
        "./Datas/TXT/parking-puces-oddo_ppm_2020_02314.txt",
        "./Datas/TXT/rue-curiol-place-jean-jaures_13001_perimete-de-securite_2020_02808.txt",
        "./Datas/TXT/ppm-rues-aubagne-jean-roque-cours-lieutaud_2020_02537.txt",
        "./Datas/TXT/perimetre_ppm_41-43-rue-de-la-palud-13001_2020_02183_vdm.txt",
        "./Datas/TXT/perimetre-securite-33-av-de-montoliver-13004_2020_02310.txt",
        "./Datas/TXT/arrete_deconstruction_rue-d-aubagne-03042020.txt",
        "./Datas/TXT/deconstruction_535-rue-saint-pierre-13012_2020_02407_vdm.txt",
        # ordonnance du TA
        "./Datas/TXT/ordonnance_37-boulevard-gilly-13010.txt",
    ):
        # TMP remise manuelle pour balayer tous les PDF et valider que le motif de
        # date est suffisant (la clause suivante avec l'Exception qui sera supprimée)
        # "Signé le — 3 janvier 2020" (bad OCR ":" => "—")
        raise ValueError("Problème date")
    else:
        if "Signé" in doc_txt:
            dbg_beg, dbg, dbg_end = doc_txt.partition("Signé")
            print(
                repr(dbg_beg[-60:]) + "\n" + repr("Signé") + "\n" + repr(dbg_end[:30])
            )
        raise Exception("Motif de date non trouvé", p_txt)


def ajout_class(string1, string2, classification, pathologie):
    if string1 in pathologie:
        if string2 not in classification:
            classification.append(string2)
    return None


def classification_pathologie(pathologie):
    classification = []
    ajout_class("ffais", "affaissement", classification, pathologie)
    ajout_class("ltér", "altération", classification, pathologie)
    ajout_class("hute", "chutes", classification, pathologie)
    ajout_class("tomber", "chutes", classification, pathologie)
    ajout_class("porte à faux", "chutes", classification, pathologie)
    ajout_class("orro", "corrosion", classification, pathologie)
    ajout_class("ouill", "corrosion", classification, pathologie)
    ajout_class("lectr", "danger électrique", classification, pathologie)
    ajout_class("ébris", "débris", classification, pathologie)
    ajout_class("éform", "déformation", classification, pathologie)
    ajout_class("égrad", "dégradation", classification, pathologie)
    ajout_class("ésord", "désordre", classification, pathologie)
    ajout_class("éstructu", "déstructuration", classification, pathologie)
    ajout_class("estructi", "déstruction", classification, pathologie)
    ajout_class("étérior", "détérioration", classification, pathologie)
    ajout_class("ffondr", "effondrement", classification, pathologie)
    ajout_class("stabl", "effondrement", classification, pathologie)
    ajout_class("tanch", "étanchéité", classification, pathologie)
    ajout_class("coulement", "étanchéité", classification, pathologie)
    ajout_class("issu", "fissures", classification, pathologie)
    ajout_class("ézarde", "fissures", classification, pathologie)
    ajout_class("ragil", "fragilité", classification, pathologie)
    ajout_class("aible", "fragilité", classification, pathologie)
    ajout_class("umid", "humidité", classification, pathologie)
    ajout_class("nstab", "instabilité", classification, pathologie)
    ajout_class("oisi", "moisissures", classification, pathologie)
    ajout_class("ruine", "risque de ruine", classification, pathologie)
    return classification


def classification_lieu(pathologie):
    classification = []
    ajout_class("alcon", "balcon", classification, pathologie)
    ajout_class("errass", "balcon", classification, pathologie)
    ajout_class("harpente", "charpente", classification, pathologie)
    ajout_class("loison", "cloison", classification, pathologie)
    ajout_class("orniche", "corniche", classification, pathologie)
    ajout_class("onstruction", "constructions", classification, pathologie)
    ajout_class("arche", "escalier", classification, pathologie)
    ajout_class("scalier", "escalier", classification, pathologie)
    ajout_class("agade", "façade", classification, pathologie)
    ajout_class("açade", "façade", classification, pathologie)
    ajout_class("acade", "façade", classification, pathologie)
    ajout_class("enêtre", "fenêtre", classification, pathologie)
    ajout_class("enetre", "fenêtre", classification, pathologie)
    ajout_class("mur", "mur", classification, pathologie)
    ajout_class("lafond", "plafond", classification, pathologie)
    ajout_class("lafond", "plafond", classification, pathologie)
    ajout_class("sol", "plancher", classification, pathologie)
    ajout_class("lancher", "plancher", classification, pathologie)
    ajout_class("arrelage", "plancher", classification, pathologie)
    ajout_class("outre", "poutre", classification, pathologie)
    ajout_class("oiture", "toiture", classification, pathologie)
    return classification
