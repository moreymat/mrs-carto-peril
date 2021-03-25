import pandas as pd


def ajout_erreur(db_csv, p_list_txt, i, erreur):
    """
    p_list_txt : Path
        Interim CSV file.
    """
    if not db_csv.loc[i, "erreurs"]:
        db_csv.loc[i, "erreurs"] = True
        error = pd.read_csv("Datas/erreurs.csv")
        error.loc[len(error)] = [erreur] + list(db_csv.loc[i])
        error.to_csv("Datas/erreurs.csv", encoding="utf-8", index=False)
        db_csv.to_csv(p_list_txt, encoding="utf-8", index=False)
    return None


def enlever_erreur(db_csv, i, url):
    db_csv.loc[i, "erreurs"] = False
    error = pd.read_csv("Datas/erreurs.csv")
    indice = error.loc[error["url"] == url].index.tolist()[0]
    error.drop(indice, 0, inplace=True)
    error.to_csv("Datas/erreurs.csv", encoding="utf-8", index=False)
    return None