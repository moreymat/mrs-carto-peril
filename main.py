"""

TODO
- [ ] extraire le numéro (identifiant) de l'arrêté (ex: 2021_00380_VDM)
- [ ] utiliser le numéro de l'arrêté pour classer (puis afficher) les actes sans date
- [ ] extraire l'identifiant de la parcelle cadastrale
- [ ] utiliser l'identifiant de la parcelle cadastrale pour améliorer la localisation
- [ ] extraire les arrêtés précédents (péril, main-levée etc) rappelés en préambule
- [ ] utiliser les arrêtés précédents pour compléter ou vérifier les données et leur affichage
- [ ] ajouter source RAA (ex: 2019_03696_VDM 1-bd-eugene-pierre-13005_2019_03696.pdf dans raa 585 du 1er novembre 2019)
"""

from datetime import datetime
import os
from pathlib import Path
import re
import webbrowser

import folium
from folium.plugins import MarkerCluster
import pandas as pd

import geocode as geo
import carte
import database
import convert_pdf_to_txt as conv
import recuperation as rec
from gestion_erreurs import ajout_erreur


# raw : list of PDF files and metadata from landing page
P_LIST_PDF = Path("data", "raw", "mrs-arretes-de-peril-2021-03-25.csv")
# interim : same as raw + cols ["erreurs", "nom_txt"]
P_LIST_TXT = Path("data", "interim", P_LIST_PDF.stem + "_txt" + P_LIST_PDF.suffix)
# errors : grmpf
P_LIST_ERR = Path("Datas", "erreurs.csv")


MAP_NEW_CLASSES = {
    "CONSULTEZ LES DERNIERS ARRÊTÉS DE DÉCONSTRUCTION": "Arrêtés de déconstruction",
    "CONSULTEZ LES DERNIERS ARRÊTÉS DE PÉRIL IMMINENT, DE MAIN LEVÉE ET DE RÉINTÉGRATION PARTIELLE DE LA VILLE DE MARSEILLE PAR ARRONDISSEMENT (ORDRE CHRONOLOGIQUE)": "Arrêtés de péril imminent, de Main Levée et de Réintégration partielle de la ville de Marseille",
    "CONSULTEZ LES DERNIERS ARRÊTÉS DE PÉRIMÈTRES DE SÉCURITÉ SUR VOIE PUBLIQUE": "Arrêtés de périmètres de sécurité sur voie publique",
    "CONSULTEZ LES DERNIERS ARRÊTÉS DE POLICE GÉNÉRALE": "Arrêtés de police générale",
    "CONSULTEZ LES DERNIERS ARRÊTÉS D'ÉVACUATION ET DE RÉINTÉGRATION": "Arrêtés d'évacuation et de réintégration",
    "CONSULTEZ LES DERNIERS ARRÊTÉS D'INSÉCURITÉ IMMINENTE DES ÉQUIPEMENTS COMMUNS": "Arrêtés d'insécurité imminente des équipements communs",
    "CONSULTEZ LES DERNIERS ARRÊTÉS D'INTERDICTION D'OCCUPER PAR ARRONDISSEMENT (ORDRE CHRONOLOGIQUE)": "Arrêtés d'interdiction d'occuper",
    "CONSULTEZ LES DERNIERS DIAGNOSTICS D'OUVRAGES": "Diagnostics d'ouvrages",
}


# textes dans lesquels le motif de date est introuvable (absent ou qualité de l'OCR)
PB_DATE_TXT = [
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
]


def init_list_txt():
    """Initialiser la liste des textes extraits des PDF des arrêtés."""
    # 0. copy original (raw) listing to working copy with additional columns
    df_raw = pd.read_csv(P_LIST_PDF, encoding="utf-8")
    df_raw["erreurs"] = False
    df_raw["nom_txt"] = ""
    # fix URLs when we know the correct ones
    # TODO improve this kind of error handling?
    df_raw.at[
        153, "url"
    ] = "https://www.marseille.fr/sites/default/files/contenu/logement/Mains_Levees/ml_8-rue-de-jemmapes-13001_2019_03216_vdm.pdf"
    # messed up URL infixed in another
    df_raw.at[
        284, "url"
    ] = "https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/6-rue-de-la-butte-13002_2019_01932.pdf"
    # here our best guess URL does not work but we want to avoid downloading
    # an HTML page instead of a PDF, so a 404 is better
    df_raw.at[
        781, "url"
    ] = "https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/PI_53-rue-roger-renzo-13008_2020_02689_VDM.pdf"
    # TODO mark erreurs=True and keep it (currently it would be erased later, I think)
    # pretend to fix another URL, just so it gets a proper 404 instead of an HTML page
    # that is stored as a PDF then will be ill-parsed
    #
    # FIXME corriger les classes en amont, au scraping, car le site a changé
    # en attendant, un correctif quick'n'dirty...
    df_raw["classe"] = df_raw["classe"].apply(lambda x: MAP_NEW_CLASSES.get(x, x))
    #
    df_raw.to_csv(P_LIST_TXT, index=False)


RE_DATE_NOMDOC = re.compile(r"(?P<date_link>\d{2}/\d{2}/\d{4})")


def process_arretes(db_csv, json2):
    """Traite les arrêtés: catégorise, extrait les pathologies, les adresses.

    Parameters
    ----------
    db_csv : pandas.DataFrame
        DataFrame des arrêtés
    json2 : Path
        Export JSON
    """
    idc_err_date = []  # échec sur l'extraction de date
    idc_err_adr = []  # échec sur l'extraction de l'adresse
    idc_err_pathologies = []  # échec sur l'extraction de pathologies
    for row_idx, row in db_csv.to_dict(orient="index").items():
        print(f"main: {row_idx} / {len(db_csv)}")
        if not row["nom_txt"]:
            # FIXME essayer d'extraire les infos qu'on peut à partir du texte du lien etc?
            continue
        #
        p_txt = Path("./Datas/TXT/", row["nom_txt"])
        with open(p_txt, "r", encoding="utf-8") as f_txt:
            doc_txt = f_txt.read()
        try:
            doc_id = rec.extract_doc_id(doc_txt)
        except ValueError:
            if p_txt.name in (
                # FIXME filtrer ces documents en amont, car ce ne sont pas des arrêtés
                # ordonnance du TA
                "ordonnance_37-boulevard-gilly-13010.txt",
                # diagnostic d'ouvrage
                "gs_cours_julien_rapport_du_20_novembre_18.txt",
                # FIXME bad OCR
                "arrete_deconstruction_rue-d-aubagne-03042020.txt",
            ):
                # ordonnance du TA
                continue
            print(p_txt)
            raise
        if True:  # doc_id not in json2:  # FIXME optionally enable this cache
            # catégorie d'arrêté
            cat = database.calcul_categorie(row_idx, db_csv)
            # date
            try:
                # date extraite depuis le corps de texte
                date_txt = rec.recup_date(doc_txt)
            except ValueError as e:
                date_txt = None
            # date extraite du texte du lien (site ville)
            m_date_nomdoc = RE_DATE_NOMDOC.search(row["nom_doc"])
            if m_date_nomdoc is not None:
                date_nomdoc = m_date_nomdoc.group("date_link")
            else:
                date_nomdoc = None
            # s'il y a 2 dates, elles doivent correspondre ;
            # s'il n'y en a aucune, c'est une erreur ;
            # sinon on garde celle qu'on a
            if date_txt is None and date_nomdoc is None:
                date = None
                idc_err_date.append(row_idx)
                if p_txt.name not in (
                    # date nulle part
                    "10-place-jean-jaures-13001_arrete_modificatif_de_pi-2020_03143_vdm_1.txt",
                    # date longue dans le lien (ex: 16 février 2021)
                    "16_rue_guibal_13001_m.txt",
                    "29_allee_leon_gambetta_13001_ppm_2021_00524.txt",
                    "8_rue_de_recolettes_13001_ppm_2021_00525.txt",
                    # date courte (ex: 25/02/21, 03/03/21)
                    "39-rue-tapis-vert-13001_2021_00674.txt",
                    # FIXME etc. (cf. liste recuperation.recup_date())
                ):
                    print(f"W: Pas de date pour {p_txt}")
            elif date_txt is not None and date_nomdoc is not None:
                d_nomdoc = datetime.strptime(date_nomdoc, "%d/%m/%Y")
                d_txt = datetime.strptime(date_txt, "%d/%m/%Y")
                date = min(d_nomdoc, d_txt).strftime("%d/%m/%Y")
                if date_nomdoc != date_txt:
                    # idc_err_date.append(row_idx)
                    print(
                        f"W: Dates différentes: txt={date_txt}, nomdoc={date_nomdoc} ({p_txt})"
                    )
            elif date_txt is not None:
                date = date_txt
            else:
                date = date_nomdoc
            #
            if cat == "Arrêtés de péril":
                pathologies = rec.recup_pathologie(doc_txt, db_csv, P_LIST_TXT, row_idx)
                if pathologies is None:
                    idc_err_pathologies.append(row_idx)
                # TODO keep ?
                conv.changement_url(row_idx, row["url"], db_csv)
                # ?
                try:
                    database.ajout_ligne_peril(
                        doc_id,
                        row["url"],
                        row["adresse"] + ", Marseille",
                        pathologies,
                        date,
                    )
                except:
                    idc_err_adr.append(row_idx)
            else:
                try:
                    database.ajout_ligne_autre(
                        cat,
                        doc_id,
                        row["url"],
                        row["adresse"] + ", Marseille",
                        date,
                    )
                except:
                    idc_err_adr.append(row_idx)
    # erreurs
    db_csv["err_date"] = False
    db_csv.loc[idc_err_date, "err_date"] = True
    db_csv["err_adresse"] = False
    db_csv.loc[idc_err_adr, "err_adresse"] = True
    # dump
    print("Dump CSV")
    db_csv.to_csv(P_LIST_TXT, index=False, encoding="utf-8")


# 0. init list txt
do_init_list_txt = True  # FIXME argparse?
if do_init_list_txt:
    init_list_txt()

# 1. convert PDF to txt
redo_dl_extract = True  # FIXME argparse?
if redo_dl_extract:
    db_csv = conv.pdf_to_txt(P_LIST_TXT, dl_pdf="none")
else:
    db_csv = pd.read_csv(
        P_LIST_TXT,
        encoding="utf-8",
    )

# 2. create json
# FIXME init json file if missing: make it cleaner
DB_PATH = Path("data.json")
if not DB_PATH.is_file():
    with open(DB_PATH, mode="w", encoding="utf-8") as f_db:
        f_db.write("{}\n")
# end FIXME
do_process_arretes = True  # FIXME argparse?
if do_process_arretes:
    print("Analyse des arrêtés")
    json2 = database.ouverture_bdd()
    process_arretes(db_csv, json2)

# 3. create map
print("Création de la carte")
c = carte.creation_carte()


icon_create_function = """ 
    function(cluster) {
    var childCount = cluster.getChildCount(); 
    var c = ' marker-cluster-medium';
    return new L.DivIcon({ html: '<link rel="stylesheet" href="./cluster.css"/><div><span> ' + childCount + '</span></div>', className: 'marker-cluster' + c, iconSize: new L.Point(40, 40) });
    }
    """

# marker type : "marker" or "point"
marker_type = "marker"
if marker_type == "marker":
    mcg = folium.plugins.MarkerCluster(
        control=False, icon_create_function=icon_create_function
    )
    c.add_child(mcg)

print("Compilation de la liste d'adresses")
liste_adresses = carte.adresses()
print("Préparation des messages pour les infobulles")
liste_messages = carte.message(liste_adresses, db_csv, P_LIST_TXT)
# TODO cleanup
print("(TEST) Extraction des latlons déjà extraites")
liste_adrlatlons_old = carte.adrlatlons()
print("Géocodage des adresses")
liste_lonlats = [geo.geocode(x) for x in liste_adresses]
# le géocodeur renvoie (lon, lat) mais folium attend (lat, lon)
liste_adrlatlons = [(adr, x[1], x[0]) for adr, x in zip(liste_adresses, liste_lonlats)]
try:
    assert liste_adrlatlons == liste_adrlatlons_old
except AssertionError:
    for i, (old, new) in enumerate(zip(liste_adrlatlons_old, liste_adrlatlons)):
        if old != new:
            print(i, repr(old), repr(new))
            break
    raise
print("Humpf.........")
liste_latlons = [(lat, lon) for _, lat, lon in liste_adrlatlons]
# end TODO cleanup

print("Ajout des points sur la carte")
nb_adresses = len(liste_adresses)
for i, (adr_i, msg_i, (lat, lon)) in enumerate(
    zip(liste_adresses, liste_messages, liste_latlons)
):
    print(f"{i} / {nb_adresses}")
    if marker_type == "marker":
        parent = mcg
    else:
        parent = c
    carte.creation_marker(parent, lat, lon, msg_i, marker_type=marker_type)

legend = carte.ajout_legend()

c.get_root().add_child(legend)


c.save("carte.html")


webbrowser.open("file://" + os.getcwd() + "/carte.html")
