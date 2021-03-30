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

#######
### 2 endroits à modifier en fonction de MARKER ou POINT
######

import os
from pathlib import Path
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
    # here our best guess URL does not work but we want to avoid downloading
    # an HTML page instead of a PDF, so a 404 is better
    df_raw.at[
        781, "url"
    ] = "https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/PI_53-rue-roger-renzo-13008_2020_02689_VDM.pdf"
    # TODO mark erreurs=True and keep it (currently it would be erased later, I think)
    # pretend to fix another URL, just so it gets a proper 404 instead of an HTML page
    # that is stored as a PDF then will be ill-parsed
    df_raw.to_csv(P_LIST_TXT, index=False)


def process_arretes(db_csv, json2):
    """Traite les arrêtés: catégorise, extrait les pathologies, les adresses."""
    for i in range(len(db_csv)):
        print(f"main: {i} / {len(db_csv)}")
        if not db_csv.loc[i].erreurs:
            path = "./Datas/TXT/" + db_csv.loc[i]["nom_txt"]
            id = rec.recup_id(path)
            if True:  # id not in json2:  # FIXME optionally enable this cache
                cat = database.calcul_categorie(i, db_csv)
                try:
                    date = rec.recup_date(path)
                except ValueError as e:
                    ajout_erreur(db_csv, P_LIST_TXT, i, "Problème date")
                if cat == "Arrêtés de péril":
                    pathologies = rec.recup_pathologie(path, db_csv, P_LIST_TXT, i)

                    if not db_csv.loc[i].erreurs:
                        conv.changement_url(i, db_csv.loc[i].url, db_csv)
                        try:
                            database.ajout_ligne_peril(
                                id,
                                db_csv.loc[i].url,
                                db_csv.loc[i].adresse + ", Marseille",
                                pathologies,
                                date,
                            )
                        except:
                            ajout_erreur(db_csv, P_LIST_TXT, i, "Problème adresse")
                else:
                    try:
                        database.ajout_ligne_autre(
                            cat,
                            id,
                            db_csv.loc[i].url,
                            db_csv.loc[i].adresse + ", Marseille",
                            date,
                        )
                    except:
                        ajout_erreur(db_csv, P_LIST_TXT, i, "Problème adresse")
    print("Dump CSV")
    db_csv.to_csv(P_LIST_TXT, index=False, encoding="utf-8")


# 0. init list txt
do_init_list_txt = True  # FIXME argparse?
if do_init_list_txt:
    init_list_txt()

# 1. convert PDF to txt
redo_dl_extract = True  # FIXME argparse?
if redo_dl_extract:
    db_csv = conv.pdf_to_txt(P_LIST_TXT)
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
print("Géocodage des adresses")
liste_latlons = [geo.geocode(x) for x in liste_adresses]

print("Ajout des points sur la carte")
nb_adresses = len(liste_adresses)
for i, (adr_i, msg_i, (lat, lon)) in enumerate(
    zip(liste_adresses, liste_messages, liste_latlons)
):
    print(f"{i} / {nb_adresses}")
    ### Pour Marker:
    carte.creation_marker(mcg, lat, lon, msg_i)
    ### Pour Points:
    # carte.creation_marker(c, lat, lon, msg_i)
    #########

legend = carte.ajout_legend()

c.get_root().add_child(legend)


c.save("carte.html")


webbrowser.open("file://" + os.getcwd() + "/carte.html")
