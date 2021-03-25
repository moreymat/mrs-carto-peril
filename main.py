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

# 1. convert PDF to txt
db_csv = conv.pdf_to_txt(P_LIST_TXT)
# 2. create json
json2 = database.ouverture_bdd()

for i in range(len(db_csv)):
    print(f"main: {i} / {len(db_csv)}")
    if not db_csv.loc[i].erreurs:
        path = "./Datas/TXT/" + db_csv.loc[i]["nom_txt"]
        id = rec.recup_id(path)
        if id not in json2:
            cat = database.calcul_categorie(i, db_csv)
            date = rec.recup_date(path, db_csv, P_LIST_TXT, i)
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

print("Création de la carte")
c = carte.creation_carte()


icon_create_function = """ 
    function(cluster) {
    var childCount = cluster.getChildCount(); 
    var c = ' marker-cluster-medium';
    return new L.DivIcon({ html: '<link rel="stylesheet" href="./cluster.css"/><div><span> ' + childCount + '</span></div>', className: 'marker-cluster' + c, iconSize: new L.Point(40, 40) });
    }
    """

#########
###Il faut que ce soit décommenté pour Markers et commenté pour Points
mcg = folium.plugins.MarkerCluster(
    control=False, icon_create_function=icon_create_function
)
c.add_child(mcg)
########

liste_adresses = carte.adresses()

liste_messages = carte.message(liste_adresses, db_csv, P_LIST_TXT)

print("Géocodage des adresses")
for i in range(len(liste_adresses)):
    ##########
    ### Pour Marker:
    carte.creation_marker(
        mcg,
        geo.geocode(liste_adresses[i])[0],
        geo.geocode(liste_adresses[i])[1],
        liste_messages[i],
    )
    ### Pour Points:
    # carte.creation_marker(c, geo.geocode(liste_adresses[i])[0], geo.geocode(liste_adresses[i])[1], liste_messages[i])
    #########

legend = carte.ajout_legend()

c.get_root().add_child(legend)


c.save("carte.html")


webbrowser.open("file://" + os.getcwd() + "/carte.html")
