"""Liste d'adresses géolocalisées au format CSV.


"""

import pandas as pd


def load_csv_adr_geo(p_csv):
    """Charge un fichier d'adresses géolocalisées.

    Parameters
    ----------
    p_csv : Path
        Fichier d'adresses géolocalisées.
    Returns
    -------
    df_adr : pandas.DataFrame
        Tableau d'adresses géolocalisées.
    """
    # tout est lu comme string, sauf result_score ;
    # latitude et longitude devraient être des Decimal mais ce type n'existe ni dans
    # numpy ni dans pandas
    converters = {"result_score": float}
    # converters = None
    df_adr = pd.read_csv(p_csv, dtype="string", converters=converters, encoding="utf-8")
    return df_adr


def summarize_adr_geo(df_adr):
    """Produit une vue synthétique du tableau d'adresses géolocalisées.

    Parameters
    ----------
    df_adr : pandas.DataFrame
        Tableau d'adresses géolocalisées
    """
    print(f"Adresses : {df_adr.shape[0]}")
    # adresses à déplier
    # combien d'adresses contenaient des "&", "et", "-", ",", "/"
    df_with_sep = df_adr[
        df_adr["adresse"].str.contains(
            r"[&,/]| et |[^a-zA-Z]-[^a-zA-Z]|[0-9] au [0-9]", regex=True
        )
    ]
    print(
        f"  dont potentiellement à déplier (avec séparateur : '&', ',', '/', 'et', 'au', '-') : {df_with_sep.shape[0]}"
    )
    # combien d'adresses géolocalisées comme des "street" ?
    df_street = df_adr[df_adr["result_type"] == "street"]
    print(f"  dont géolocalisées 'street' : {df_street.shape[0]}")
