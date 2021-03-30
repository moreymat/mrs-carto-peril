import json

import geocode as geo
import recuperation as rec


def ouverture_bdd():
    with open("data.json", encoding="utf-8") as json_data:
        data_dict = json.load(json_data)
    return data_dict


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


def calcul_categorie(i, db):
    """Catégorie d'acte.

    Si absente du CSV de départ, la catégorie est déduite de son URL.

    Parameters
    ----------
    """
    row = db.loc[i]
    # FIXME corriger les classes en amont, au scraping, car le site a changé
    # en attendant, un correctif quick'n'dirty...
    row["classe"] = MAP_NEW_CLASSES.get(row["classe"], row["classe"])
    # traitement normal
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
            "lattitude": lat,
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
            "lattitude": lat,
            "url": url,
            "date": date,
        }
    ]
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    return None
