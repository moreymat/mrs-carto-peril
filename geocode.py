import requests

url_geocode = "http://api-adresse.data.gouv.fr/search/"


def geocode(adresse):
    """Géocode une adresse avec l'API adresse et renvoie les coordonnées (lat, lon).

    Permute les coordonnées car API adresse renvoie du GeoJSON qui utilise l'ordre lonlat,
    alors que folium attend du latlon.

    TODO
    - [ ] ajouter une méthode batch pour faire une unique requête sur un lot d'adresses.
    - [ ] récupérer et valoriser les autres champs de la réponse : https://github.com/geocoders/geocodejson-spec/tree/master/draft
    """
    reponse = requests.get(url_geocode, params={"q": adresse})
    lon = reponse.json().get("features")[0].get("geometry").get("coordinates")[0]
    lat = reponse.json().get("features")[0].get("geometry").get("coordinates")[1]
    return lat, lon
