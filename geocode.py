"""Geocode

TODO
- [ ] ajouter une méthode batch pour faire une unique requête sur un lot d'adresses avec /search/csv/
- [ ] valoriser les autres champs de la réponse : https://geo.api.gouv.fr/adresse
    https://github.com/geocoders/geocodejson-spec/tree/master/draft
"""

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


def geocode_batch(p_adr, p_adr_geo):
    """Géocode un fichier CSV d'adresses.

    Parameters
    ----------
    p_adr : Path
        Fichier d'adresses
    p_adr_geo : Path
        Fichier d'adresses géolocalisées résultat.
    """
    files = {"data": open(p_adr, mode="rb")}
    # faire la requête POST avec le contenu
    reponse = requests.post(ENDPOINT_SEARCH_CSV, files=files)
    # récupérer et écrire la réponse
    result = reponse.text
    with open(p_adr_geo, mode="w", encoding="utf-8") as f_adr_geo:
        f_adr_geo.write(result)
