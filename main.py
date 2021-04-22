"""

TODO
- [ ] extraire le numéro (identifiant) de l'arrêté (ex: 2021_00380_VDM)
- [ ] utiliser le numéro de l'arrêté pour classer (puis afficher) les actes sans date
- [ ] extraire l'identifiant de la parcelle cadastrale
- [ ] utiliser l'identifiant de la parcelle cadastrale pour améliorer la localisation
- [ ] extraire les arrêtés précédents (péril, main-levée etc) rappelés en préambule
- [ ] utiliser les arrêtés précédents pour compléter ou vérifier les données et leur affichage
- [ ] ajouter source RAA (ex: 2019_03696_VDM 1-bd-eugene-pierre-13005_2019_03696.pdf dans raa 585 du 1er novembre 2019)
- [ ] calculer la couverture des scripts (2021-04-09: 889 entrées dans data.json (=889 arrêtés cartographiés?),
      609 adresses (items dans les listes sur la page des arrêtés)
- [ ] regrouper les arrêtés par "id" de géolocalisation, pour regrouper "35 rue Montolieu" et "35 rue Montolieu - 13002"
"""
# nb arrêtés : jq 'keys[]' data.json |wc -l
# 2021-04-10: 1082 (cartographiés, ou incluant les adresses non reconnues?)
# nb adresses : jq 'values[][0].adresse' data.json |sort |uniq |wc -l
# 2021-04-10: 674 (dont des None)

from datetime import datetime
import json
from pathlib import Path
import re
import webbrowser

import pandas as pd

from corpus_pdf import check_or_get_corpus_pdf, changement_url
from csv_adr_geo import load_csv_adr_geo, summarize_adr_geo
from csv_raw_format import load_csv_raw
from geocode import geocode_batch
import carte
import database
import convert_pdf_to_txt as conv
import recuperation as rec


# raw :
# liste de documents PDF et métadonnées de la page du site de la ville
# P_LIST_PDF = Path("data", "raw", "mrs-arretes-de-peril-2021-03-25.csv")
P_LIST_PDF = Path("data", "raw", "mrs-arretes-de-peril-2021-03-25_new.csv")
# documents PDF
CORPUS_DIR = Path("data", "raw", "marseille-fr_arretes-de-peril_pdf")

# interim :
# documents TXT produits par OCR
TXT_DIR = Path("data", "interim", "marseille-fr_arretes-de-peril_txt")
# liste d'adresses uniques
P_ADR = Path("data", "interim", P_LIST_PDF.stem + "_adr" + P_LIST_PDF.suffix)
# interim : liste des adresses géocodées
P_ADR_GEO = Path("data", "interim", P_ADR.stem + "_geo" + P_ADR.suffix)
# interim : same as raw + cols ["erreurs", "nom_txt"]
P_LIST_TXT = Path("data", "interim", P_LIST_PDF.stem + "_txt" + P_LIST_PDF.suffix)
# FIXME errors : grmpf
P_LIST_ERR = Path("Datas", "erreurs.csv")

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


def init_list_txt(df_raw):
    """Initialiser la liste des textes extraits des PDF des arrêtés."""
    # 0. copy original (raw) listing to working copy with additional columns
    df_raw["erreurs"] = False
    df_raw["nom_txt"] = ""
    #
    df_raw.to_csv(P_LIST_TXT, index=False, encoding="utf-8")


RE_DATE_NOMDOC = re.compile(r"(?P<date_link>\d{2}/\d{2}/\d{4})")


def process_arretes(db_csv, txt_dir, dict_arretes, p_json):
    """Traite les arrêtés: catégorise et extrait les pathologies.

    Pour les adresses, on utilise en première approximation celles récupérées de
    la liste sur le site de la ville (TODO extraire du contenu des documents).

    Parameters
    ----------
    db_csv : pandas.DataFrame
        DataFrame des arrêtés
    txt_dir : Path
        Dossier contenant les TXT
    dict_arretes : dict
        Dict JSON
    p_json : Path
        Fichier JSON résultat, où seront stockées les données.
    """
    idc_err_date = []  # échec sur l'extraction de date
    # TODO détecter ou marquer les erreurs d'extraction d'adresse
    idc_err_adr = []  # échec sur l'extraction de l'adresse
    idc_err_pathologies = []  # échec sur l'extraction de pathologies
    for row_idx, row in db_csv.to_dict(orient="index").items():
        if not row["nom_txt"]:
            # FIXME essayer d'extraire les infos qu'on peut à partir du texte du lien etc?
            continue
        # charger le texte du doc
        p_txt = txt_dir.joinpath(row["nom_txt"])
        with open(p_txt, "r", encoding="utf-8") as f_txt:
            doc_txt = f_txt.read()
        # extraire l'identifiant du doc
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
        if True:  # doc_id not in dict_arretes:  # FIXME optionally enable this cache
            # définir la catégorie de l'arrêté
            cat = database.calcul_categorie(row_idx, db_csv)

            # date
            try:
                # date extraite depuis le corps de texte
                date_txt = rec.recup_date(doc_txt)
            except ValueError:
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
                    print(
                        f"W: Pas de date pour {p_txt} (main: {row_idx} / {len(db_csv)})"
                    )
            elif date_txt is not None and date_nomdoc is not None:
                d_nomdoc = datetime.strptime(date_nomdoc, "%d/%m/%Y")
                d_txt = datetime.strptime(date_txt, "%d/%m/%Y")
                date = min(d_nomdoc, d_txt).strftime("%d/%m/%Y")
                if date_nomdoc != date_txt:
                    # idc_err_date.append(row_idx)
                    print(
                        f"W: Dates différentes: txt={date_txt}, nomdoc={date_nomdoc} ({p_txt}) (main: {row_idx} / {len(db_csv)})"
                    )
            elif date_txt is not None:
                date = date_txt
            else:
                date = date_nomdoc

            # stockage des résultats
            if cat == "Arrêtés de péril":
                pathologies = rec.recup_pathologie(doc_txt, db_csv, P_LIST_TXT, row_idx)
                if pathologies is None:
                    idc_err_pathologies.append(row_idx)
                # TODO keep ?
                changement_url(row_idx, row["url"], db_csv)
                # ?
                database.ajout_ligne_peril(
                    dict_arretes,
                    doc_id,
                    row["url"],
                    row["nom_doc"],
                    row["adresse"],  # adresse sur la page
                    # geocodage
                    row["result_label"],  # adresse trouvée par le géocodeur
                    row["result_id"],  # identifiant unique adresse géocodeur
                    row["longitude"],
                    row["latitude"],
                    # pathologies
                    pathologies,
                    date,
                )
            else:
                database.ajout_ligne_autre(
                    dict_arretes,
                    cat,
                    doc_id,
                    row["url"],
                    row["nom_doc"],
                    row["adresse"],  # adresse sur la page
                    # geocodage
                    row["result_label"],  # adresse trouvée par le géocodeur
                    row["result_id"],  # identifiant unique adresse géocodeur
                    row["longitude"],
                    row["latitude"],
                    date,
                )
    # erreurs
    db_csv["err_date"] = False
    db_csv.loc[idc_err_date, "err_date"] = True
    db_csv["err_adresse"] = False
    db_csv.loc[idc_err_adr, "err_adresse"] = True
    db_csv["err_pathologies"] = False
    db_csv.loc[idc_err_pathologies, "err_pathologies"] = True
    # dump
    print("Dump CSV")
    db_csv.to_csv(P_LIST_TXT, index=False, encoding="utf-8")
    # dump JSON
    with open(p_json, "w", encoding="utf-8") as f:
        json.dump(dict_arretes, f, ensure_ascii=False, indent=4)
    # return dict (JSON)
    return dict_arretes


# 0. géocodage des adresses des arrêtés
# charger la liste de documents
df_raw = load_csv_raw(P_LIST_PDF)
# géocoder les adresses raw
do_geoloc = True
mode_geoloc = "new"  # "old", "new"
if do_geoloc:
    print("Géocodage des adresses (raw)")
    df_adr = df_raw[["adresse", "code_postal", "ville"]].drop_duplicates()
    # Préparation du fichier CSV d'adresses
    # si un immeuble a plusieurs adresses, on en garde une seule pour le géocodage
    # TODO utiliser les autres adresses en fallback lorsque le géocodage renvoie un résultat
    # de faible score, ou une rue plutôt qu'un bâtiment ?
    # TODO valider avec les utilisateurs qu'on veut bien un seul point pour la carto
    if mode_geoloc == "new":
        df_adr = df_adr.assign(
            adrs=df_adr.adresse.str.split(
                r"(?<=[a-zA-Zé])[ ]?/[ ]?(?=\d)", expand=False
            )
        ).explode("adrs")
        # TODO gérer les arrêtés portant sur deux immeubles ou plus, à deux adresses ou plus
        geocode_cols = ["adrs", "code_postal", "ville"]
    else:
        # DEBUG
        geocode_cols = ["adresse", "code_postal", "ville"]
    df_adr_geo = geocode_batch(df_adr, geocode_cols, P_ADR, P_ADR_GEO)
    # Candidats au sauvetage :
    # - si le résultat est de type "street" alors que l'adresse comporte un numéro
else:
    df_adr_geo = load_csv_adr_geo(P_ADR_GEO)
# ne retenir que le meilleur résultat pour chaque adresse
# https://stackoverflow.com/a/63485139/14201886
# FIXME certains matchs "street" ont des scores supérieurs à "housenumber" ;
# mais en dépliant encore plus les adresses, on devrait éviter ces régressions (espérons-le)
# sinon utiliser groupby.filter(lambda x: fn(x['col']) )
if mode_geoloc == "new":
    df_adr_geo = (
        df_adr_geo.groupby(
            ["adresse", "code_postal", "ville"], sort=False, dropna=False
        )
        .apply(lambda group: group.nlargest(1, columns="result_score"))
        .reset_index(drop=True)
    )
# DEBUG df_adr_geo.to_csv(f"dbg_geoloc_{mode_geoloc}", encoding="utf-8", index=False)
# assembler les adresses géocodées et le fichier raw
print("------------")
summarize_adr_geo(df_adr_geo)
# faire la jointure de la liste des documents et du géocodage de leurs adresses
df_raw_adr_geo = pd.merge(
    df_raw, df_adr_geo, how="inner", on=["adresse", "code_postal", "ville"]
).drop(
    columns=[
        "result_context",
        "result_oldcitycode",
        "result_oldcity",
    ]
)
#  TODO renommer les colonnes ? : 'result_*' -> 'raw_result_*' ?

# 0. init list txt
do_init_list_txt = True  # FIXME argparse?
if do_init_list_txt:
    init_list_txt(df_raw_adr_geo)

# 1. on ouvre le corpus PDF
dl_pdf = "none"  # "missing", "none"
if not CORPUS_DIR.is_dir():
    CORPUS_DIR.mkdir()
df_corpus = check_or_get_corpus_pdf(P_LIST_TXT, CORPUS_DIR, dl_pdf=dl_pdf)

# 2. on extrait le texte par OCR
extract_text = "missing"  # "missing", "none"
df_corpus = conv.pdf_to_txt(df_corpus, CORPUS_DIR, TXT_DIR, extract_text=extract_text)
# dump current state
df_corpus.to_csv(P_LIST_TXT, index=False, encoding="utf-8")

# 3. on extrait les données des arrêtés (pour export json)
DB_PATH = Path("data", "processed", "arretes-de-peril.json")

if not DB_PATH.is_file():
    # FIXME init json file if missing: make it cleaner
    dict_arretes = {}
    with open(DB_PATH, mode="w", encoding="utf-8") as f_db:
        json.dump(dict_arretes, f_db, ensure_ascii=False, indent=4)
    # end FIXME

# FIXME on charge le fichier actuel des données sur les arrêtés
with open(DB_PATH, encoding="utf-8") as f_json:
    dict_arretes = json.load(f_json)

# FIXME ajouter une option pour simplement lire le contenu du json (sans ré-extraire le contenu des arrêtés)
print("Analyse des arrêtés")
dict_arretes = process_arretes(df_corpus, TXT_DIR, dict_arretes, DB_PATH)

# 3. create map
print("Création de la carte")
marker_type = "point"  # "marker", "point"
# si marker_type != "marker", mcg is None
c, mcg = carte.creation_carte(marker_type=marker_type)

print("Compilation de la liste d'adresses")
liste_adresses = carte.adresses(dict_arretes)
print("Préparation des messages pour les infobulles")
liste_messages = carte.message(dict_arretes, liste_adresses, df_corpus, P_LIST_TXT)
# TODO cleanup
print("(TEST) Extraction des latlons déjà extraites")
liste_adrlatlons_old = carte.adrlatlons(dict_arretes)
# TODO géocoder les adresses extraites du texte, plus fines que celles du raw
do_geocode_txt = False
if do_geocode_txt:
    print("Géocodage des adresses (txt) (TODO)")
    pass
liste_latlons = [(lat, lon) for _, lat, lon in liste_adrlatlons_old]
# end TODO cleanup

print("Ajout des points sur la carte")
carte.create_markers(c, mcg, liste_messages, liste_latlons, marker_type=marker_type)
# sauvegarde de la carte HTML
p_carte = Path("reports", f"carte_{marker_type}.html")
c.save(str(p_carte))
# ouverture dans le navigateur
webbrowser.open(p_carte.resolve().as_uri())
