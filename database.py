import json

import geocode as geo
import recuperation as rec


def ouverture_bdd():
    with open("data.json", encoding="utf-8") as json_data:
        data_dict = json.load(json_data)
    return data_dict


def calcul_categorie(i, db):
    """Catégorie d'acte.

    Si absente du CSV de départ, la catégorie est déduite de son URL.

    Parameters
    ----------
    """
    row = db.loc[i]
    if (
        row["classe"]
        != "Arrêtés de péril imminent, de Main Levée et de Réintégration partielle de la ville de Marseille"
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


def ajout_ligne_peril(id, url, adresse, pathologies, date):
    db = ouverture_bdd()
    lon, lat = geo.geocode(adresse)
    db[id] = [
        {
            "categorie": "Arrêtés de péril",
            "adresse": adresse,
            "longitude": lon,
            "latitude": lat,
            "pathologies": pathologies,
            "classification_pathologies": rec.classification_pathologie(pathologies),
            "classification_lieux": rec.classification_lieu(pathologies),
            "url": url,
            "date": date,
        }
    ]
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    return None


def ajout_ligne_autre(categorie, id, url, adresse, date):
    db = ouverture_bdd()
    lon, lat = geo.geocode(adresse)
    db[id] = [
        {
            "categorie": categorie,
            "adresse": adresse,
            "longitude": lon,
            "latitude": lat,
            "url": url,
            "date": date,
        }
    ]
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    return None
