"""Geocode

TODO
- [ ] ajouter une méthode batch pour faire une unique requête sur un lot d'adresses avec /search/csv/
- [ ] valoriser les autres champs de la réponse : https://geo.api.gouv.fr/adresse
    https://github.com/geocoders/geocodejson-spec/tree/master/draft
"""

from io import StringIO

import pandas as pd
import requests

ENDPOINT_SEARCH = "https://api-adresse.data.gouv.fr/search/"
ENDPOINT_SEARCH_CSV = "https://api-adresse.data.gouv.fr/search/csv/"

# FIXME dirty, temporary fix
CACHE_GEOCODE = {}  # cache geocoding


def geocode(adresse):
    """Géocode une adresse avec l'API adresse et renvoie des infos de géolocalisation.

    Returns
    -------
    adr_geoloc : Dict[str, Any]
        Éléments de géolocalisation de l'adresse
    """
    # return (1, 1)  # DEBUG bypass request
    # print(repr(adresse))
    if adresse in CACHE_GEOCODE:
        print(f"CACHE geocode: {adresse}")  # DEBUG
        return CACHE_GEOCODE[adresse]
    # raises HTTP error
    reponse = requests.get(ENDPOINT_SEARCH, params={"q": adresse})
    try:
        result = reponse.json().get("features")[0]
    except IndexError:
        # adresse non reconnue, ex: '10 boulevard de la Liberté / 20 rue Lafayette'
        raise ValueError("adresse non reconnue")
    else:
        lon, lat = result.get("geometry").get("coordinates")
        props = result.get("properties")
        adr_geoloc = {
            "lon": lon,
            "lat": lat,
            "label": props["label"],
            "housenumber": props["housenumber"] if "housenumber" in props else None,
            "id": props["id"],
            "name": props["name"],
            "postcode": props["postcode"],
            "citycode": props["citycode"],
            "city": props["city"],
            "street": props["street"] if "street" in props else None,
        }
    CACHE_GEOCODE[adresse] = adr_geoloc
    # print(f"geocode: {adresse}")  # DEBUG
    return adr_geoloc


def geocode_batch(df_adr, columns, p_adr, p_adr_geo):
    """Géocode un ensemble d'adresses, par l'envoi d'un fichier CSV à l'API adresse.

    Parameters
    ----------
    df_adr : pandas.DataFrame
        Tableau d'adresses
    columns : List[str]
        Liste des colonnes à envoyer à l'API
    p_adr : Path
        Fichier d'adresses
    p_adr_geo : Path
        Fichier d'adresses géolocalisées résultat.

    Returns
    -------
    df_adr_geo : pandas.DataFrame
        Adresses géolocalisées
    """
    print("Appel au géocodeur d'adresses")
    # écrire les données dans un fichier CSV
    df_adr.to_csv(p_adr, encoding="utf-8", index=False)
    # appeler l'API
    query_params = {"columns": columns}
    files = {"data": open(p_adr, mode="rb")}
    reponse = requests.post(ENDPOINT_SEARCH_CSV, files=files, data=query_params)
    # récupérer la réponse en CSV et l'écrire dans un fichier (CSV)
    result = reponse.text
    # with open(p_adr_geo, mode="w", encoding="utf-8") as f_adr_geo:
    #     f_adr_geo.write(result)
    f_result = StringIO(result)
    df_adr_geo = pd.read_csv(f_result, dtype="string")
    df_adr_geo["result_score"] = df_adr_geo["result_score"].astype("float")
    df_adr_geo.to_csv(p_adr_geo, encoding="utf-8", index=False)
    # renvoyer le tableau d'adresses géolocalisées
    return df_adr_geo
