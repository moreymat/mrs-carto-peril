# -*- coding: utf-8 -*-

from datetime import datetime
import re

from branca.element import Template, MacroElement
import folium
from folium.plugins import MarkerCluster

import database
from gestion_erreurs import ajout_erreur

# keep
LAT_MARSEILLE = 43.2969500
LON_MARSEILLE = 5.3810700

# pour les clusters (markers)
icon_create_function = """ 
function(cluster) {
var childCount = cluster.getChildCount(); 
var c = ' marker-cluster-medium';
return new L.DivIcon({ html: '<link rel="stylesheet" href="./cluster.css"/><div><span> ' + childCount + '</span></div>', className: 'marker-cluster' + c, iconSize: new L.Point(40, 40) });
}
"""


def creation_carte(marker_type="marker"):
    """Crée la carte.

    Parameters
    ----------
    marker_type : one of {"marker", "point"}
        Type de marqueur

    Returns
    -------
    c : ?
        Carte folium
    mcg : MarkerCluster or None
        Cluster pour ajouter les marqueurs le cas échéant
    """
    # initialisation
    fmap = folium.Map(
        location=[LAT_MARSEILLE, LON_MARSEILLE], min_zoom=11, max_zoom=19, zoom_start=12
    )
    # ajout de la légende
    legend = ajout_legend()
    fmap.get_root().add_child(legend)
    # ajout du cluster de marqueurs
    if marker_type == "marker":
        mcg = folium.plugins.MarkerCluster(
            control=False, icon_create_function=icon_create_function
        )
        fmap.add_child(mcg)
    else:
        # "point"
        mcg = None
    #
    return fmap, mcg


palette = dict()
palette["Arrêtés de déconstruction"] = "black"
palette["Arrêtés d'interdiction d'occuper"] = "darkred"
palette["Arrêtés de péril"] = "red"
palette["Arrêtés de péril modificatif"] = "red"
palette["Arrêtés d'insécurité imminente des équipements communs"] = "lightred"
palette["Arrêtés d'évacuation et de réintégration"] = "orange"
##########
### Pour des markers:
palette["Arrêtés de périmètres de sécurité sur voie publique"] = "beige"
palette["Arrêtés de police générale"] = "beige"
### Pour des points:
# palette["Arrêtés de périmètres de sécurité sur voie publique"] = "#FFDAB9"
# palette["Arrêtés de police générale"] = "#FFDAB9"
#########
palette["Arrêtés de main levée partielle"] = "lightgreen"
palette["Arrêtés de main levée"] = "green"
palette["Diagnostics d'ouvrages"] = "purple"


def creation_marker(parent, x, y, message, marker_type="marker"):
    """
    Parameters
    ----------
    parent : Union[Map, MarkerCluster]

    marker_type : one of {"marker", "point"}
    """
    popup = folium.Popup(message[0], max_width=600, min_width=600)
    if marker_type == "marker":
        # marker
        res = folium.Marker(
            [x, y],
            popup=popup,
            icon=folium.Icon(
                icon="home", icon_color="white", color=palette[message[1]]
            ),
        )
    else:
        # point
        res = folium.vector_layers.Circle(
            [x, y],
            radius=4,
            fill=True,
            fill_opacity=0.5,
            popup=popup,
            color=palette[message[1]],
        )
    res.add_to(parent)


def create_markers(fmap, mcg, liste_messages, liste_latlons, marker_type="marker"):
    """Ajoute les marqueurs

    Parameters
    ----------
    fmap : ?
        Carte Folium
    mcg : MarkerCluster or None
        Cluster de marqueurs si marker_type == "marker"
    liste_messages : List[str]
        Liste de messages pour les infobulles
    liste_latlons : List[(str, str)]
        Liste de coordonnées des marqueurs (latitude et longitude)
    marker_type : one of {"marker", "point"}
        Type de marqueur à afficher
    """
    if marker_type == "marker":
        parent = mcg
    else:
        parent = fmap
    nb_messages = len(liste_messages)
    for i, (msg_i, (lat, lon)) in enumerate(
        zip(liste_messages, liste_latlons), start=1
    ):
        if lat is None or lon is None:
            # FIXME gérer en amont
            continue
        print(f"{i} / {nb_messages}")
        creation_marker(parent, lat, lon, msg_i, marker_type=marker_type)


def adresses(db):
    liste = []
    for key, value in db.items():
        adresse = value[0]["adresse"]
        if adresse is None:
            # FIXME gérer en amont
            continue
        if adresse not in liste:
            liste.append(adresse)
    return liste


def adrlatlons(db):
    result = []
    for key, value in db.items():
        if value[0]["adresse"] is None:
            # FIXME gérer en amont
            continue
        adrlatlon = (value[0]["adresse"], value[0]["latitude"], value[0]["longitude"])
        if adrlatlon not in result:
            result.append(adrlatlon)
    return result


#  FIXME appliquer en amont? + redondant avec recuperation.RE_DOC_ID
RE_DOC_ID = re.compile(
    r"(?P<doc_id_year>\d{4})[ ]?[-_]?[ ]?(?P<doc_id_idx>\d{4,5}[B]?)[ ]?[-_.]?[ ]?(?P<doc_id_suf>VDM[A]?)"
)


def sort_docs(list_k_date, reverse_chronological=True):
    """Trie des documents.

    Parameters
    ----------
    list_k_date : List[Tuple[str, str]]
        Couple clé et date de chaque document.

    Returns
    -------
    sorted_list : List[str]
        Liste triée de couples clé et date.
    """
    m_norm_keys = [RE_DOC_ID.search(k) for k, date in list_k_date]
    if any(m is None for m in m_norm_keys):
        raise ValueError(f"Key set : {repr(list_k_date)}")
    norm_keys = [
        m.group("doc_id_year", "doc_id_idx", "doc_id_suf") for m in m_norm_keys
    ]
    norm_k_date = list(
        sorted(
            [(norm_k, k, date) for norm_k, (k, date) in zip(norm_keys, list_k_date)],
            key=lambda x: x[0],
            reverse=True,
        )
    )
    sorted_k_date = [(x[1], x[2]) for x in norm_k_date]  # new result ?
    # sort dates?
    if False:
        # alt 1 ; parsing ensures it is indeed a date (surprise: sometimes it isn't)
        liste_dateD = [
            datetime.strptime(x, "%d/%m/%Y") if x is not None else x for x in liste_date
        ]
        liste_dateD_s = sorted(liste_dateD, reverse=True)
        liste_dateD_f = [x.strftime("%d/%m/%Y") for x in liste_dateD_s]
        # alt 2
        liste_date2_f = sorted(
            liste_date, key=lambda x: tuple(reversed(x.split("/"))), reverse=True
        )
    #
    return sorted_k_date


def message(db, liste_adresse, db_csv, p_list_txt):
    liste = []
    for adresse in liste_adresse:
        if adresse is None:
            # FIXME gérer en amont
            continue
        char = '<font size="+1"><B>' + adresse + "</B><br><br>"
        # begin sort docs (reverse chronological order)
        sel_docs = [
            (k, v[0]["date"]) for k, v in db.items() if v[0]["adresse"] == adresse
        ]
        sorted_list = sort_docs(sel_docs)
        # end sort docs (reverse chronological order)
        cat_last = db[sorted_list[0][0]][0]["categorie"]
        for couple in sorted_list:
            elt = db[couple[0]][0]
            # TODO handle in a better way
            if elt["date"] is None:
                if not db_csv.loc[db_csv["url"] == elt["url"], "err_date"].values[0]:
                    indice = db_csv.loc[db_csv["url"] == elt["url"]].index.tolist()[0]
                    ajout_erreur(db_csv, p_list_txt, indice, "Problème date")
            # end TODO
            cat = elt["categorie"]
            char += "<U>" + cat + "</U><br>"
            char += (
                "<i>"
                + "<a href="
                + elt["url"]
                + ' Target="_blank">'
                + elt["nom_doc"]
                + "</a>"
                + "</i> "
                + (elt["date"] if elt["date"] is not None else "??/??/????")
                + "<br>"
            )
            #
            if cat == "Arrêtés de péril":
                try:
                    char += (
                        "- "
                        + (
                            ", ".join(elt["classification_pathologies"])
                            if elt["classification_pathologies"] is not None
                            else "(manquant)"
                        )
                        + "<br> "
                        + "- "
                        + (
                            ", ".join(elt["classification_lieux"])
                            if elt["classification_lieux"] is not None
                            else "(manquant)"
                        )
                        + "<br>"
                    )
                except:
                    print(adresse, "problème de pathologie manquante")
                    raise
            char += "<br>"
        char += "</font>"
        liste.append([char, cat_last])

    return liste


def ajout_legend():
    template = """
    {% macro html(this, kwargs) %}

    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Carte des Arrêtés de Marseille</title>
      <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">

      <script src="https://code.jquery.com/jquery-1.12.4.js"></script>
      <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>

      <script>
      $( function() {
        $( "#maplegend" ).draggable({
                        start: function (event, ui) {
                            $(this).css({
                                right: "auto",
                                top: "auto",
                                bottom: "auto"
                            });
                        }
                    });
    });

      </script>
    </head>
    <body>


    <div id='maplegend' class='maplegend' 
        style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.8);
         border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px;'>

    <div class='legend-title'>Type d'arrêtés (cliquez pour déplacer)</div>
    <div class='legend-scale'>
      <ul class='legend-labels'>
        <li><span style='background:black;opacity:0.7;'></span>Arrêtés de déconstruction</li>
        <li><span style='background:darkred;opacity:0.7;'></span>Arrêtés d'interdiction d'occuper</li>
        <li><span style='background:red;opacity:0.7;'></span>Arrêtés de péril</li>
        <li><span style='background:red;opacity:0.7;'></span>Arrêtés de péril modificatif</li>
        <li><span style='background:salmon;opacity:0.7;'></span>Arrêtés d'insécurité imminente des équipements communs</li>
        <li><span style='background:orange;opacity:0.7;'></span>Arrêtés d'évacuation et de réintégration</li>
        <li><span style='background:#FFDAB9;opacity:0.7;'></span>Arrêtés de périmètres de sécurité sur voie publique</li>
        <li><span style='background:#FFDAB9;opacity:0.7;'></span>Arrêtés de police générale </li>
        <li><span style='background:lightgreen;opacity:0.7;'></span>Arrêtés de main levée partielle </li>
        <li><span style='background:green;opacity:0.7;'></span>Arrêtés de main levée </li>
        <li><span style='background:purple;opacity:0.7;'></span>Diagnostics d'ouvrages </li>
      </ul>
    </div>
    </div>

    </body>
    </html>

    <style type='text/css'>
      .maplegend .legend-title {
        text-align: left;
        margin-bottom: 5px;
        font-weight: bold;
        font-size: 90%;
        }
      .maplegend .legend-scale ul {
        margin: 0;
        margin-bottom: 5px;
        padding: 0;
        float: left;
        list-style: none;
        }
      .maplegend .legend-scale ul li {
        font-size: 80%;
        list-style: none;
        margin-left: 0;
        line-height: 18px;
        margin-bottom: 2px;
        }
      .maplegend ul.legend-labels li span {
        display: block;
        float: left;
        height: 16px;
        width: 30px;
        margin-right: 5px;
        margin-left: 0;
        border: 1px solid #999;
        }
      .maplegend .legend-source {
        font-size: 80%;
        color: #777;
        clear: both;
        }
      .maplegend a {
        color: #777;
        }
    </style>
    {% endmacro %}"""
    macro = MacroElement()
    macro._template = Template(template)
    return macro
