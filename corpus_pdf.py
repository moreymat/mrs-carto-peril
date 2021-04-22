"""Corpus de documents PDF
"""

from pathlib import Path

import pandas as pd
import requests


def changement_url(i, url, db):
    # TODO vérifier si ça sert à quelque chose...
    # print(f"changement_url: {i}")
    url_split = url.split("/")
    if url_split[2] == "logement-urbanisme.marseille.fr":
        url_split[2] = "marseille.fr"
        url = "/".join(url_split)
        db.loc[i, "url"] = url
    elif url_split[4] == "logement-urbanisme":
        url_split.pop(3)
        url = "/".join(url_split)
        db.loc[i, "url"] = url
    return None


def download_pdf(url, p_pdf):
    """Download a PDF file from a URL.

    Raise an error if the request fails, or the downloaded file is not an (image-based) PDF.

    Parameters
    ----------
    url : str
        URL for the PDF
    p_pdf : Path
        Local path to store the PDF file
    """
    try:
        # download PDF
        myfile = requests.get(url)
        myfile.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"ERR: {err}")
        raise
    else:
        # write PDF
        with open(p_pdf, "wb") as f_pdf:
            f_pdf.write(myfile.content)
        print(f"PDF téléchargé: {url}")


def check_or_get_corpus_pdf(
    f_list_txt, corpus_dir, dl_pdf="missing", convert_urls=False
):
    """Vérifie que les documents sont accessibles.

    Parameters
    ----------
    f_list_txt : Path
        Chemin du fichier CSV contenant une liste de liens vers des documents PDF.
    corpus_dir : Path
        Dossier contenant le corpus de documents.
    dl_pdf : one of {"missing", "none"}
        If "missing", download missing PDFs ; if "none", don't.
    convert_urls : boolean, defaults to False
        If True, convert legacy URLs.

    Returns
    -------
    db_csv : pandas.DataFrame
        DataFrame
    """
    db_csv = pd.read_csv(f_list_txt, encoding="utf-8", dtype={"url": "string"})
    # extraction et stockage des noms de fichiers
    s_pdf = db_csv["url"].str.rsplit(pat="/", n=1, expand=True)[1]
    db_csv["nom_pdf"] = s_pdf
    # calcul des chemins locaux
    s_pdf_path = s_pdf.apply(lambda x: Path(corpus_dir, x))
    db_csv["err_missing_pdf"] = s_pdf_path.apply(lambda x: not x.is_file())
    #
    idc_new_pdf = []  # indices des lignes avec nouveau PDF
    idc_err_url = []  # indices des lignes avec erreur d'URL
    if dl_pdf == "none":
        # les PDF manquants le resteront
        db_csv.loc[db_csv["err_missing_pdf"], "nom_pdf"] = ""
    elif dl_pdf == "missing":
        # tentative de téléchargement des PDF manquants
        df_missing_pdf = db_csv[db_csv["err_missing_pdf"]]
        for row_idx, row in df_missing_pdf.to_dict(orient="index").items():
            url = row["url"]
            if convert_urls:
                # process urls from 2020-02, after 2020-03
                # TODO check if still useful
                changement_url(i, url, db_csv)
            #
            p_pdf = Path(corpus_dir, row["nom_pdf"])
            try:
                download_pdf(url, p_pdf)
            except requests.exceptions.HTTPError as err:
                idc_err_url.append(row_idx)
                # we still have no PDF, skip this entry
                continue
            else:
                idc_new_pdf.append(row_idx)
        # for all new PDFs, set err_missing_pdf to False
        db_csv.loc[idc_new_pdf, "err_missing_pdf"] = False
    # for all bad URLs, set flag to True, erase nom_pdf
    db_csv["err_bad_url"] = False
    if idc_err_url:
        db_csv.loc[idc_err_url, "err_bad_url"] = True
        db_csv.loc[idc_err_url, "nom_pdf"] = ""
    return db_csv
