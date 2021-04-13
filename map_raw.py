"""Géocode et cartographie les documents sans examiner leur contenu.

Avantages:
* rapide à calculer et afficher ;
* exhaustive: représente tous les documents, même ceux qui ne sont pas accessibles ;

Inconvénients:
* partiellement structurée : les documents à la même adresse mais de classes différentes ne sont pas triés ;
* peu détaillée : pas de pathologie ni de lieux ;
"""

from pathlib import Path
import webbrowser

import pandas as pd

from carte import creation_carte, ajout_legend, create_markers
from csv_adr_geo import load_csv_adr_geo, summarize_adr_geo
from csv_raw_format import load_csv_raw
from geocode import geocode_batch


if __name__ == "__main__":
    # in : liste des documents
    p_raw = Path("data", "raw", "mrs-arretes-de-peril-2021-03-25_new.csv")
    # out : liste des adresses
    p_adr = Path("data", "interim", p_raw.stem + "_adr" + p_raw.suffix)
    # out : liste des adresses géocodées
    p_adr_geo = Path("data", "interim", p_adr.stem + "_geo" + p_adr.suffix)
    # out : carte
    p_map = Path("data", "processed", p_raw.stem + "_map" + ".html")

    # charger la liste de documents
    df_raw = load_csv_raw(p_raw)
    # géocoder les adresses
    do_geoloc = False
    if do_geoloc:
        df_adr = df_raw[["adresse", "code_postal", "ville"]].drop_duplicates()
        df_adr.to_csv(p_adr, index=False)
        geocode_batch(p_adr, p_adr_geo)
    # assembler les adresses géocodées et le fichier raw
    df_adr_geo = load_csv_adr_geo(p_adr_geo)
    print("------------")
    summarize_adr_geo(df_adr_geo)
    # faire la jointure de la liste des documents et du géocodage de leurs adresses
    df_raw_adr_geo = pd.merge(
        df_raw, df_adr_geo, how="inner", on=["adresse", "code_postal", "ville"]
    )
    # dump ?
    # créer la carte
    marker_type = "marker"
    fmap, mcg = creation_carte(marker_type=marker_type)
    # ajouter un point par adresse
    df_gby_adr = df_raw_adr_geo.groupby(
        by=["adresse", "code_postal", "ville", "latitude", "longitude"]
    )
    messages = [
        ("[TODO] " + adresse, entries.tail(1)["classe"].values[0])
        for (adresse, cp, ville, lat, lon), entries in df_gby_adr
    ]
    # FIXME en 1re approximation on considère tous les arrêtés de classe 1
    # comme des périls
    messages = [
        (
            x,
            "Arrêtés de péril"
            if y
            == "Arrêtés de péril imminent, de Main Levée et de Réintégration partielle"
            else y,
        )
        for x, y in messages
    ]
    latlons = [(lat, lon) for (_, _, _, lat, lon), v in df_gby_adr]
    create_markers(fmap, mcg, messages, latlons, marker_type="marker")
    # sauvegarder la carte en fichier HTML
    fmap.save(str(p_map))
    # ouvrir le navigateur et afficher la carte
    webbrowser.open(p_map.resolve().as_uri())
