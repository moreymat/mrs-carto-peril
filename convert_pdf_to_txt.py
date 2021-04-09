# Modifier ligne 14 à 18 pour tesseract

import os
from pathlib import Path
import time

import pandas as pd
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError
import pytesseract
import requests

from gestion_erreurs import enlever_erreur, ajout_erreur

F_ERREURS_CSV = Path("Datas", "erreurs.csv")

new_errors = True

# À adapter en fonction de l'ordinateur utilisé
# Linux/Windows
tessdata_dir_config = ""
# - Windows : (?)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# - Mac : (?)
# tessdata_dir_config = r'--tessdata-dir "/Users/maelle/Downloads/tesseract-ocr-setup-3.05.01/tessdata/"'


def pdf_to_string(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for i, image in enumerate(images):
        text = text + pytesseract.image_to_string(
            image, lang="fra", config=tessdata_dir_config
        )
    return text


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


def pdf_to_txt(
    f_list_txt: Path, dl_pdf="missing", extract_text="missing", convert_urls=False
):
    """Convert PDF files, listed in a CSV, to texts.

    New PDF files are downloaded then optionally removed (see `delete_pdfs`).

    Parameters
    ----------
    f_list_txt : Path
        CSV file describing a list of links to PDF files, the path to their
        local TXT extract and a flag if there is an error (scraping, OCR or
        other).
    dl_pdf : one of {"missing", "none"}
        If "missing", download missing PDFs ; if "none", don't.
    extract_text : one of {"all", "missing", "none"}
        Extract text via OCR for "all" PDF files, "missing" text files (PDF
        but no TXT) only, or "none".
    convert_urls : boolean, defaults to False
        If True, convert legacy URLs.

    Returns
    -------
    db_csv : pandas.DataFrame
        DataFrame of updated list of PDFs, the CSV file is updated as well.
    """
    db_csv = pd.read_csv(f_list_txt, encoding="utf-8", dtype={"url": "string"})
    # extraction des noms de fichiers
    s_pdf = db_csv["url"].str.rsplit(pat="/", n=1, expand=True)[1]
    s_stem = s_pdf.str.split(pat=".", n=1, expand=True)[0]  # or Path(...).stem ?
    s_txt = s_stem + ".txt"
    # on stocke les noms de fichiers
    db_csv["nom_pdf"] = s_pdf
    db_csv["nom_txt"] = s_txt
    # on calcule les chemins locaux
    s_txt_path = s_txt.apply(lambda x: Path("./Datas/TXT", x))
    s_pdf_path = s_pdf.apply(lambda x: Path("./Datas/PDF", x))
    db_csv["err_missing_pdf"] = s_pdf_path.apply(lambda x: not x.is_file())
    db_csv["err_missing_txt"] = s_txt_path.apply(lambda x: not x.is_file())
    # vérification de situation incohérente : pas de PDF mais un TXT
    assert not (db_csv["err_missing_pdf"] & ~db_csv["err_missing_txt"]).any()

    idc_new_pdf = []  # indices des lignes avec nouveau PDF
    idc_err_url = []  # indices des lignes avec erreur d'URL
    if dl_pdf == "none":
        # les PDF manquants le resteront, et leur TXT aussi
        db_csv.loc[db_csv["err_missing_pdf"], "nom_pdf"] = ""
        db_csv.loc[db_csv["err_missing_pdf"], "nom_txt"] = ""
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
            p_pdf = Path("./Datas/PDF", row["nom_pdf"])
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
    # for all bad URLs, set flag to True, erase nom_pdf and nom_txt
    db_csv["err_bad_url"] = False
    if idc_err_url:
        db_csv.loc[idc_err_url, "err_bad_url"] = True
        db_csv.loc[idc_err_url, "nom_pdf"] = ""
        db_csv.loc[idc_err_url, "nom_txt"] = ""

    # 2. (if sel) extraction des TXT par OCR
    idc_new_txt = []
    idc_bad_pdf = []
    if extract_text != "none":
        if extract_text == "all":
            df_extr_txt = db_csv[~db_csv["err_missing_pdf"]]
        elif extract_text == "missing":
            # tentative de téléchargement des PDF manquants
            df_extr_txt = db_csv[~db_csv["err_missing_pdf"] & db_csv["err_missing_txt"]]
        else:
            raise ValueError(f"Unknown value for extract_text: {extract_text}")
        #
        for row_idx, row in df_extr_txt.to_dict(orient="index").items():
            p_pdf = Path("./Datas/PDF", row["nom_pdf"])
            p_txt = Path("./Datas/TXT", row["nom_txt"])
            print(f"Extract text from {p_pdf.name} to {p_txt.name}")
            try:
                texte = pdf_to_string(p_pdf)
            except PDFPageCountError as err:
                # le fichier PDF était incorrect
                print(f"ERR: {err}")
                idc_bad_pdf.append(row_idx)
                raise
            else:
                # write OCR'd text
                with open(p_txt, "w", encoding="utf-8") as f_txt:
                    f_txt.write(texte)
                # mark new text
                idc_new_txt.append(row_idx)
        # for all newly extracted TXTs, set err_missing_txt to False
        db_csv.loc[idc_new_txt, "err_missing_txt"] = False
        # for all bad PDFs, set flag to True and erase nom_pdf
        db_csv["err_bad_pdf"] = False
        db_csv.loc[idc_bad_pdf, "err_bad_pdf"] = True
        db_csv.loc[idc_bad_pdf, "nom_pdf"] = ""
        db_csv.loc[idc_bad_pdf, "nom_txt"] = ""

    # dump current state
    db_csv.to_csv(f_list_txt, index=False, encoding="utf-8")
    return db_csv


def changement_url(i, url, db):
    print(f"changement_url: {i}")
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
