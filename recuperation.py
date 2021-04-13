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


RE_DOC_ID = re.compile(
    r"N°[ ]*(?P<doc_id>\d{4}[ ]?[-_]?[ ]?\d{4,5}[B]?[ ]?[-_.]?[ ]?VDM[A]?)"
)


def extract_doc_id(doc_txt):
    """Extrait l'identifiant de l'arrêté: année_num_VDM

    année sur 4 chiffres, num sur 5 chiffres, VDM pour Ville De Marseille ?

    Parameters
    ----------
    doc_txt : string
        Texte du document

    Returns
    -------
    doc_id : string or None
        Idenfitiant du document
    """
    m = RE_DOC_ID.search(doc_txt)
    if m is None:
        raise ValueError("doc_id not found")
        # return None
    return m.group("doc_id")


def recup_adresse(doc_txt):
    res = (
        doc_txt.partition("immeuble sis ")[2]
        .partition("-")[0]
        .partition("")[0]
        .partition("â")[0]
        .partition("—")[0]
    )
    return res


def recup_pathologie(doc_txt, db_csv, p_list_txt, i):
    if "pathologies suivantes" not in doc_txt:
        return None
    res = doc_txt.partition("pathologies suivantes")[2].partition("Considérant")[0]
    return res


PROG_ID = re.compile(
    r"ID : \d{3}-\d{9}-(?P<date_id>\d{8})-(?P<doc_id>\d{4}_\d{5}_VDM)-AR"
)
PROG_ENVOI_PREF = re.compile(
    r"Envoyé en préfecture le (?P<date_envoi>\d{2}/\d{2}/\d{4})[ ]*\n"
)
PROG_DATE_SIGN = re.compile(r"Signé[ ]?le[ ]?:[ ]?(?P<date_sign>.*)\n")


def recup_date(doc_txt):
    """Extrait la date du texte.

    Extrait la date de l'ID du tampon de transmission à la préfecture,
    sinon la date d'envoi du tampon de transmission à la préfecture,
    sinon la date de signature.
    Si aucune de ces heuristiques ne fonctionne, lève une erreur.
    """
    # heuristique 1: extraire la date de l'ID du tampon de transmission à la préfecture
    # (parfois tampon absent ou sans ID)
    m_id = PROG_ID.search(doc_txt)
    # heuristique 2: extraire la date de la signature en fin d'acte
    # (parfois manuscrite)
    m_sign = PROG_DATE_SIGN.search(doc_txt)
    # heuristique 3: extraire la date d'envoi du tampon de transmission à la préfecture
    # (parfois envoi daté du lendemain de l'arrêté)
    m_pref = PROG_ENVOI_PREF.search(doc_txt)
    if m_id is not None:
        # ex: "ID : "
        res = m_id.group("date_id")
        # print("date: pref", repr(res))
        res_old = datetime.strptime(res, "%Y%m%d").strftime("%d/%m/%Y")
        return res_old
    elif m_sign is not None:
        # ex: "Signé le : 23 décembre 2018"
        res = m_sign.group("date_sign")
        # print("date: sign (raw)", repr(res))
        res = DDP.get_date_data(res)["date_obj"]
        # erreurs d'OCR: dates non ou mal lues, car manuscrites ou partiellement effacées
        if res is None:
            # la date n'a pu être lue
            raise ValueError("Problème date")
        elif res > _TODAY:
            # la date a été mal lue
            print("ERR date future: ", res)
            raise ValueError("Problème date")
        res = res.strftime("%d/%m/%Y")
        # print("date: sign (pro)", repr(res))
        return res
    elif m_pref is not None:
        # ex: "Envoyé en préfecture le 23/10/2019"
        res = m_pref.group("date_envoi")
        # print("date: pref", repr(res))
        res_old = datetime.strptime(res, "%d/%m/%Y").strftime("%d/%m/%Y")
        res_new = DDP.get_date_data(res)["date_obj"].strftime("%d/%m/%Y")
        assert res_old == res_new
        return res_new
    else:
        raise ValueError("Problème date")


def ajout_class(string1, string2, classification, pathologie):
    if string1 in pathologie:
        if string2 not in classification:
            classification.append(string2)
    return None


def classification_pathologie(pathologie):
    if pathologie is None:
        return None
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
    if pathologie is None:
        return None
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
