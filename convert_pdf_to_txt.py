"""

TODO
- [ ] remplacer pytesseract par tesserocr ? (2021-04-18 pas de gain !?)
- [ ] tester différents réglages pour la conversion PDF -> image ?
- [ ] utiliser la sortie ALTO XML de tesseract pour avoir les blocs ?
"""
# Modifier ligne 14 à 18 pour tesseract

from pathlib import Path
import time

import pandas as pd
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError
import pytesseract
import requests


# À adapter en fonction de l'ordinateur utilisé
# Linux/Windows
tessdata_dir_config = ""
# - Windows : (?)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# - Mac : (?)
# tessdata_dir_config = r'--tessdata-dir "/Users/maelle/Downloads/tesseract-ocr-setup-3.05.01/tessdata/"'


def pdf_to_string(pdf_path, dpi=200, thread_count=1):
    """
    Parameters
    ----------
    pdf_path : Path
        Chemin vers le fichier PDF qu'on veut convertir
    dpi : int
        Qualité de l'image en DPI (pdf2image)
    thread_count : int
        Nombre de threads autorisés (pdf2image)
    Returns
    -------
    text : str
        Texte extrait
    """
    images = convert_from_path(pdf_path, dpi=dpi, thread_count=thread_count)
    text = ""
    for img in images:
        text = text + pytesseract.image_to_string(
            img, lang="fra", config=tessdata_dir_config
        )
    return text


def pdf_to_txt(
    db_csv,
    corpus_dir,
    out_dir,
    extract_text="missing",
    dpi=200,
    thread_count=1,
):
    """Convert PDF files, listed in a DataFrame, to texts.

    New PDF files are downloaded then optionally removed (see `delete_pdfs`).

    Parameters
    ----------
    db_csv : pandas.DataFrame
        DataFrame décrivant le corpus, après vérification de la présence des PDFs.
    corpus_dir : Path
        Dossier contenant le corpus PDF
    out_dir : Path
        Dossier pour écrire les fichiers TXT
    extract_text : one of {"all", "missing", "none"}
        Extract text via OCR for "all" PDF files, "missing" text files (PDF
        but no TXT) only, or "none".
    dpi : int
        Qualité de l'image en DPI (pdf2image)
    thread_count : int
        Nombre de threads autorisés (pdf2image)

    Returns
    -------
    db_csv : pandas.DataFrame
        DataFrame of updated list of PDFs, the CSV file is updated as well.
    """
    # lecture des noms de fichiers PDF et construction des chemins
    s_pdf = db_csv["nom_pdf"]
    s_pdf_path = s_pdf.apply(lambda x: corpus_dir.joinpath(x))
    # calcul et stockage des noms de fichiers TXT
    s_stem = s_pdf.str.rsplit(pat=".", n=1, expand=True)[0]  # or Path(...).stem ?
    s_txt = s_stem + ".txt"
    db_csv["nom_txt"] = s_txt

    # 1. on vérifie quels TXT existent vraiment
    s_txt_path = s_txt.apply(lambda x: out_dir.joinpath(x))
    db_csv["err_missing_txt"] = s_txt_path.apply(lambda x: not x.is_file())
    # si on n'a pas de PDF, on ne doit pas avoir de TXT
    assert not (db_csv["err_missing_pdf"] & ~db_csv["err_missing_txt"]).any()
    db_csv.loc[db_csv["err_missing_pdf"], "nom_txt"] = ""

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
            p_pdf = corpus_dir.joinpath(row["nom_pdf"])
            p_txt = out_dir.joinpath(row["nom_txt"])
            print(f"{row_idx:04} Extract text from {p_pdf.name} to {p_txt.name}")
            try:
                texte = pdf_to_string(p_pdf, dpi=dpi, thread_count=thread_count)
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
    return db_csv
