import requests

url_geocode = "http://api-adresse.data.gouv.fr/search/"

# FIXME dirty, temporary fix
CACHE_GEOCODE = {}  # cache geocoding


def geocode(adresse):
    """Géocode une adresse avec l'API adresse et renvoie les coordonnées (lon, lat).

    TODO
    - [ ] ajouter une méthode batch pour faire une unique requête sur un lot d'adresses.
    - [ ] récupérer et valoriser les autres champs de la réponse : https://github.com/geocoders/geocodejson-spec/tree/master/draft
    """
    # return (1, 1)  # DEBUG bypass request
    # print(repr(adresse))
    if adresse in CACHE_GEOCODE:
        print(f"CACHE geocode: {adresse}")  # DEBUG
        return CACHE_GEOCODE[adresse]
    reponse = requests.get(url_geocode, params={"q": adresse})
    lon, lat = reponse.json().get("features")[0].get("geometry").get("coordinates")
    CACHE_GEOCODE[adresse] = (lon, lat)
    # print(f"geocode: {adresse}")  # DEBUG
    return lon, lat
