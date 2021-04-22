import recuperation as rec


# TODO
# - [ ] déplacer vers un module regroupant les fonctions qui s'appliquent aux données brutes extraites de la page du site ;
# - [ ] réimplanter ? avec pandas.str.*
# - [ ] implanter (dans un autre module) une variante plus fiable, qui utilise le texte de l'arrêté
def calcul_categorie(i, db):
    """Catégorie d'acte.

    Si absente du CSV de départ, la catégorie est déduite de son URL.

    Parameters
    ----------
    """
    row = db.loc[i]
    if (
        row["classe"]
        != "Arrêtés de péril imminent, de Main Levée et de Réintégration partielle"
    ):
        categorie = row["classe"]
    else:
        url_split = row["url"].split("/")
        cat_partielle = url_split[-2]
        if cat_partielle == "Arretes-peril":
            if "odificatif" in row["nom_doc"]:
                categorie = "Arrêtés de péril modificatif"
            else:
                categorie = "Arrêtés de péril"
        else:
            if "artiel" in row["nom_doc"]:
                categorie = "Arrêtés de main levée partielle"
            else:
                categorie = "Arrêtés de main levée"
    return categorie


def ajout_ligne_peril(
    db,
    id,
    url,
    nom_doc,
    adresse_orig,
    adresse_geoc,
    adr_id,
    lon,
    lat,
    pathologies,
    date,
):
    db[id] = [
        {
            "categorie": "Arrêtés de péril",
            "adresse_orig": adresse_orig,
            "adresse_geoc": adresse_geoc,
            "adr_id": adr_id,
            "longitude": lon,
            "latitude": lat,
            "pathologies": pathologies,
            "classification_pathologies": rec.classification_pathologie(pathologies),
            "classification_lieux": rec.classification_lieu(pathologies),
            "url": url,
            "nom_doc": nom_doc,
            "date": date,
        }
    ]


def ajout_ligne_autre(
    db, categorie, id, url, nom_doc, adresse_orig, adresse_geoc, adr_id, lon, lat, date
):
    db[id] = [
        {
            "categorie": categorie,
            "adresse_orig": adresse_orig,
            "adresse_geoc": adresse_geoc,
            "adr_id": adr_id,
            "longitude": lon,
            "latitude": lat,
            "url": url,
            "nom_doc": nom_doc,
            "date": date,
        }
    ]
