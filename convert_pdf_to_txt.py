# Modifier ligne 14 à 18 pour tesseract

import os
from pathlib import Path

import pandas as pd
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError
import pytesseract
import requests

from gestion_erreurs import enlever_erreur, ajout_erreur

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


def pdf_to_txt(f_list_txt: Path, delete_pdfs=False, convert_urls=False):
    """Convert PDF files, listed in a CSV, to texts.

    New PDF files are downloaded then optionally removed (see `delete_pdfs`).

    Parameters
    ----------
    f_list_txt : Path
        CSV file describing a list of links to PDF files, the path to their
        local TXT extract and a flag if there is an error (scraping, OCR or
        other).
    delete_pdfs : boolean, defaults to False
        If True, delete PDF files after download.

    Returns
    -------
    db_csv : pandas.DataFrame
        DataFrame of updated list of PDFs, the CSV file is updated as well.
    """
    db_csv = pd.read_csv(f_list_txt, encoding="utf-8")
    for i in range(len(db_csv)):
        print(f"pdf_to_txt: {i} / {len(db_csv)}")
        url = db_csv.loc[i].url
        url_split = url.split("/")
        nom = url_split[-1].split(".")[0]
        p_txt = Path("./Datas/TXT", nom + ".txt")
        if p_txt.is_file():
            # all good, we assume the txt is correct ;
            # we still rewrite the field in p_list_txt for safety
            # TODO is it really necessary?
            db_csv.loc[i, "nom_txt"] = p_txt.name
            continue
        # else extract text from PDF
        print(f"TXT manquant: {p_txt.name}")
        p_pdf = Path("./Datas/PDF", nom + ".pdf")
        is_new_pdf = False  # if delete_pdfs is True, we'll need to delete the new PDF
        if not p_pdf.is_file():
            # missing PDF: try to download
            try:
                if convert_urls:
                    # process urls from 2020-02, after 2020-03
                    # TODO check if still useful
                    changement_url(i, url, db_csv)
                # download PDF
                print(f"Tentative de téléchargement du PDF: {url}")
                myfile = requests.get(url)
                myfile.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(f"ERR: {err}")
                ajout_erreur(db_csv, f_list_txt, i, "Problème URL")
                # we still have no PDF, skip this entry
                continue
            else:
                # write PDF
                with open(p_pdf, "wb") as f_pdf:
                    f_pdf.write(myfile.content)
                is_new_pdf = True
        # extract text from PDF via OCR
        try:
            texte = pdf_to_string(p_pdf)
        except PDFPageCountError as err:
            # le fichier PDF était incorrect
            print(f"ERR: {err}")
            ajout_erreur(db_csv, f_list_txt, i, "Problème URL")
            raise
        else:
            # write OCR'd text
            with open(p_txt, "w", encoding="utf-8") as f_txt:
                f_txt.write(texte)
            # store path to txt file
            db_csv.loc[i, "nom_txt"] = p_txt.name
            # remove error in status file
            if db_csv.loc[i].erreurs:
                enlever_erreur(db_csv, i, url)
        # clean up (if necessary)
        if delete_pdfs and is_new_pdf:
            try:
                os.remove(p_pdf)
            except:
                raise ValueError(f"Cannot delete new PDF: {p_pdf}")
                # pass
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
