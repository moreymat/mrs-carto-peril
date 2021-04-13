"""Charger et écrire une liste de documents au format CSV brut (nouveau).

"""

import pandas as pd


def load_csv_raw(p_csv):
    """Charge la liste des documents au format CSV brut (nouveau).

    Les champs sont supposés être textuels, sauf certains.

    Parameters
    ----------
    p_csv : Path
        Chemin vers le fichier CSV.
    Returns
    -------
    df_csv : pandas.DataFrame
        Tableau des documents.
    """
    converters = {"doc_grp_idx": int, "doc_grp_rel_idx": int}
    df_csv = pd.read_csv(p_csv, encoding="utf-8", dtype="string", converters=converters)
    return df_csv


def dump_csv_raw(df_csv, p_csv):
    """Écrit la liste des documents au format CSV.

    Parameters
    ----------
    df_csv : pandas.DataFrame
        Liste de documents.
    p_csv : Path
        Chemin vers le fichier CSV.
    """
    df_csv.to_csv(p_csv, encoding="utf-8", index=False)
