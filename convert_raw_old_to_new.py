"""Convertit une liste de documents de l'ancien format CSV brut vers le nouveau.

TODO
- [ ] déplacer le code vers le scraper
- [ ] déplier les adresses avec séparateur ?
"""

from pathlib import Path
import re

import pandas as pd


MAP_NEW_CLASSES = {
    "ARRÊTÉS DE DÉCONSTRUCTION": "Arrêtés de déconstruction",
    "ARRÊTÉS DE PÉRIL IMMINENT, DE MAIN LEVÉE ET DE RÉINTÉGRATION PARTIELLE DE LA VILLE DE MARSEILLE PAR ARRONDISSEMENT (ORDRE CHRONOLOGIQUE)": "Arrêtés de péril imminent, de Main Levée et de Réintégration partielle",
    "ARRÊTÉS DE PÉRIMÈTRES DE SÉCURITÉ SUR VOIE PUBLIQUE": "Arrêtés de périmètres de sécurité sur voie publique",
    "ARRÊTÉS DE POLICE GÉNÉRALE": "Arrêtés de police générale",
    "ARRÊTÉS D'ÉVACUATION ET DE RÉINTÉGRATION": "Arrêtés d'évacuation et de réintégration",
    "ARRÊTÉS D'INSÉCURITÉ IMMINENTE DES ÉQUIPEMENTS COMMUNS": "Arrêtés d'insécurité imminente des équipements communs",
    "ARRÊTÉS D'INTERDICTION D'OCCUPER PAR ARRONDISSEMENT (ORDRE CHRONOLOGIQUE)": "Arrêtés d'interdiction d'occuper",
    "DIAGNOSTICS D'OUVRAGES": "Diagnostics d'ouvrages",
}


def load_csv(p_csv, version="raw_old"):
    """Charge la liste des documents au format CSV.

    Les champs sont supposés être textuels, sauf certains selon la version.

    Parameters
    ----------
    p_csv : Path
        Chemin vers le fichier CSV.
    version : one of {"raw_old", "raw_new"}
        Version du fichier : "raw_old", "raw_new".
    Returns
    -------
    df_csv : pandas.DataFrame
        Tableau des documents.
    """
    if version == "raw_old":
        converters = None
    elif version == "raw_new":
        converters = {"doc_grp_idx": int, "doc_grp_rel_idx": int}
    else:
        # ?
        converters = None
    #
    df_csv = pd.read_csv(p_csv, encoding="utf-8", dtype="string", converters=converters)
    return df_csv


def dump_csv(df_csv, p_csv):
    """Écrit la liste des documents au format CSV.

    Parameters
    ----------
    df_csv : pandas.DataFrame
        Liste de documents.
    p_csv : Path
        Chemin vers le fichier CSV.
    """
    df_csv.to_csv(p_csv, encoding="utf-8", index=False)


def check_csv_raw(df_raw):
    """Vérifie la cohérence de la liste CSV.

    FIXME déplacer dans le scraper pour contrôler le fichier produit
    """
    # deux classes d'arrêtés sont structurées par arrondissement sur la page
    classe_arr = df_raw["classe"].str.contains(
        "PAR ARRONDISSEMENT \(ORDRE CHRONOLOGIQUE\)"
    )
    assert df_raw.loc[classe_arr, "arrondissement"].isna().sum() == 0
    assert df_raw.loc[~classe_arr, "arrondissement"].notna().sum() == 0
    assert (
        df_raw.loc[classe_arr, "arrondissement"].notna().sum()
        + df_raw.loc[~classe_arr, "arrondissement"].isna().sum()
        == df_raw.shape[0]
    )
    # dépendance fonctionnelle : s'il y a un arrondissement, alors il y a un code_postal
    sel_arr = df_raw["arrondissement"].notna()
    assert df_raw.loc[sel_arr, "code_postal"].isna().sum() == 0
    # on a autant d'arrondissements que de codes postaux, et les deux ensembles sont
    # en bijection
    assert (
        df_raw.value_counts(subset=["arrondissement"]).shape[0]
        == df_raw.value_counts(subset=["arrondissement", "code_postal"]).shape[0]
        == df_raw.value_counts(subset=["code_postal"]).shape[0]
    )
    # pour les autres types de documents, la page ne donne pas de structure par arrondissement
    # mais on a pu extraire certains codes postaux depuis les adresses


# corrections, à essayer d'automatiser au maximum en amont
RE_TIRET_CP = r"-[ ]?(?P<cp>\d{5})"


def auto_fix(df_raw):
    """Correction automatique, devrait être effectuée en amont."""
    # code postal manquant
    missing_cp = df_raw["code_postal"].isna()
    # le code postal aurait pu être extrait de l'item
    df_raw.loc[missing_cp, "code_postal"] = df_raw["item"].str.extract(
        RE_TIRET_CP, expand=True
    )["cp"]
    return df_raw


# dictionnaire de corrections manuelles
# TODO
# - [ ] déplier les listes d'adresses et produire un format tidy où 1 doc peut donner n entrées
MANUAL_ITEM_TO_ADRESSE = {
    "Arrêté modificatif de péril ordinaire - 20 rue du Jet d'eau": "20 rue du Jet d'eau",
    "Arrêté portant mise en place d'un périmètre de sécurité sur la rue d'Aubagne et la rue Jean Roque": "rue d'Aubagne et rue Jean Roque",
    "Arrêté portant sur la modification du périmètre de sécurité sur la rue d'Aubagne": "rue d'Aubagne",
    "Arrêté modifiant le périmètre de sécurité de la rue d'Aubagne et de la rue Jean Roque - 13001 2019_01380_VDM du 25/04/19": "rue d'Aubagne et rue Jean Roque",
    "Arrêté portant sur la mise en place d'un périmètre de sécurité pour l'immeuble CG13 situé rue Saint-Cassien et Bouleverd Louis de Grasse - 13002": "rue Saint-Cassien et Boulevard Louis de Grasse",
    "Arrêté de police 20 rue de l'Académie - 13001 - abrogation du 08/10/2020": "20 rue de l'Académie",  # x2
    "Arrêté de police générale du Maire portant  sur le 54 rue d'Italie - 13006": "54 rue d'Italie",
    "Arrêté portant sur la mise en place d'un périmètre de sécurité sur la rue Curiol (N°79, 81, 85, 92, 94, 96, 98 et 100) et la place Jean Jaurès (n°24 et 26)": "rue Curiol (N°79, 81, 85, 92, 94, 96, 98 et 100) et place Jean Jaurès (n°24 et 26)",
}

MANUAL_FIX_URL = {
    # j'ai réussi à retrouver la bonne URL
    "https://www.marseille.fr/logement-urbanisme/am%C3%A9lioration-de-lhabitat/sites/default/files/contenu/logement/Mains_Levees/ml_8-rue-de-jemmapes-13001_2019_03216_vdm.pdf": "https://www.marseille.fr/sites/default/files/contenu/logement/Mains_Levees/ml_8-rue-de-jemmapes-13001_2019_03216_vdm.pdf",
    # idem, la bonne URL était enchassée dans une autre
    "https://www.marseille.fr/https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/6-rue-de-la-butte-13002_2019_01932.pdf/default/files/contenu/logement/Arretes-deconstruction/deconstruction_8-rue-de-la-butte-13002_2019_03064_vdm.pdf": "https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/6-rue-de-la-butte-13002_2019_01932.pdf",
    # je n'ai pas la bonne URL mais l'actuelle bien que mauvaise ne renvoie pas une erreur 404
    # je remplace donc par une URL qui, elle, renvoie bien un 404 et évite de télécharger un mauvais HTML
    # et de le prendre pour un PDF
    "https://www.marseille.fr/logement-urbanisme/am%C3%A9lioration-de-lhabitat/PI_53-rue-roger-renzo-13008_2020_02689_VDM.pdf": "https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/PI_53-rue-roger-renzo-13008_2020_02689_VDM.pdf",
}


def manual_fix(df_raw):
    """Corrige manuellement certaines entrées.

    Idéalement, certaines corrections devraient être réalisées en amont.
    """
    for e_item, e_adrs in MANUAL_ITEM_TO_ADRESSE.items():
        df_raw.loc[df_raw["item"] == e_item, "adresse"] = e_adrs
    for url_bad, url_fix in MANUAL_FIX_URL.items():
        df_raw.loc[df_raw["url"] == url_bad, "url"] = url_fix
    return df_raw


def clean_enrich_raw_csv(df_raw):
    """Nettoie et enrichit la liste CSV brute.

    FIXME déplacer dans le scraper pour nettoyer le fichier produit

    Parameters
    ----------
    df_raw : pandas.DataFrame
        Liste de documents de départ

    Returns
    -------
    df_raw : pandas.DataFrame
        Liste de documents nettoyée
    """
    # on ajoute la ville
    df_raw["ville"] = "Marseille"
    # on supprime le code postal de l'adresse
    df_raw["adresse"] = df_raw["adresse"].str.replace(RE_TIRET_CP, "", regex=True)
    # on nettoie les intitulés de classe
    df_raw["classe"] = df_raw["classe"].str.replace(
        "CONSULTEZ LES DERNIERS ", "", regex=True
    )
    # deux classes d'arrêtés sont structurées par arrondissement sur la page
    classe_arr = df_raw["classe"].str.contains(
        " PAR ARRONDISSEMENT \(ORDRE CHRONOLOGIQUE\)", regex=True
    )
    # et, par adresse, par ordre chronologique : on marque les groupes d'arrêtés de même
    # type à la même adresse (d'après la page du site) ainsi que leur ordre relatif dans
    # chaque groupe, qui pourra être utilisé pour classer les arrêtés
    df_raw["doc_grp_idx"] = df_raw.groupby(
        by=["classe", "adresse"], sort=False
    ).ngroup()
    df_raw["doc_grp_rel_idx"] = df_raw.groupby(
        by=["classe", "adresse"], sort=False
    ).cumcount()
    # maintenant on peut réécrire les classes
    for classe_old, classe_new in MAP_NEW_CLASSES.items():
        df_raw["classe"] = df_raw["classe"].replace(classe_old, classe_new, regex=False)
    return df_raw


def summarize_data(df_new):
    """Résume l'état actuel des données"""
    print(f"Nombre de documents : {df_new.shape[0]}")
    # sanity check + stats adresse
    nb_sans_adr = df_new["adresse"].isna().sum()
    print(f"dont sans adresse : {nb_sans_adr}")
    if nb_sans_adr:
        print("  détail sans adresse :")
        print(f"    {df_new[df_new['adresse'].isna()][['item']].values}")
    # sanity check + stats code postal
    nb_sans_cp = df_new["code_postal"].isna().sum()
    print(f"dont sans code postal : {nb_sans_cp}")
    try:
        assert nb_sans_cp == 7  # 2021-03-25
    except AssertionError:
        if nb_sans_cp:
            print("  détail sans code postal :")
            print(f"    {df_new[df_new['code_postal'].isna()][['item']].values}")
    # adresses
    df_adr_uniq = df_new[["adresse"]].drop_duplicates()
    print(f"adresses uniques (WIP) : {df_adr_uniq.shape[0]}")
    # adresses à déplier
    # combien d'adresses contenaient des "&", "et", "-", ",", "/"
    df_with_sep = df_adr_uniq[
        df_adr_uniq["adresse"].str.contains(
            r"[&,/]| et |[^a-zA-Z]-[^a-zA-Z]|[0-9] au [0-9]", regex=True
        )
    ]
    print(
        f"  dont potentiellement à déplier (avec séparateur : '&', ',', '/', 'et', 'au', '-') : {df_with_sep.shape[0]}"
    )
    print(df_with_sep["adresse"].values)


if __name__ == "__main__":
    # in: raw old
    p_raw_old = Path("data", "raw", "mrs-arretes-de-peril-2021-03-25.csv")
    p_raw_dir = p_raw_old.parent
    # out: raw new
    p_raw_new = p_raw_dir.joinpath(p_raw_old.stem + "_new" + p_raw_old.suffix)
    # load
    df_raw = load_csv(p_raw_old)
    # check
    check_csv_raw(df_raw)
    # fix ; should be done upstream
    df_raw = auto_fix(df_raw)
    df_raw = manual_fix(df_raw)
    # enrich
    df_new = clean_enrich_raw_csv(df_raw)
    # dump
    dump_csv(df_new, p_raw_new)
    # summarize
    summarize_data(df_new)