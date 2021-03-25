# Modifier ligne 14 à 18 pour tesseract

import os

import pandas
from pdf2image import convert_from_path
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


def pdf_to_txt(delete_pdfs=False):
    db_csv = pandas.read_csv("arretes.csv", encoding="utf-8")
    for i in range(len(db_csv)):
        print(f"pdf_to_txt: {i} / {len(db_csv)}")
        url = db_csv.loc[i].url
        url_split = url.split("/")
        nom = url_split[-1].split(".")[0]
        if nom + ".txt" not in os.listdir("./Datas/TXT"):
            try:
                changement_url(i, url, db_csv)
                myfile = requests.get(url)
                myfile.raise_for_status()
                with open("./Datas/PDF/" + nom + ".pdf", "wb") as f_pdf:
                    f_pdf.write(myfile.content)
                texte = pdf_to_string("./Datas/PDF/" + nom + ".pdf")
                with open(
                    "./Datas/TXT/" + nom + ".txt", "w", encoding="utf-8"
                ) as f_txt:
                    f_txt.write(texte)
                if db_csv.loc[i].erreurs:
                    enlever_erreur(db_csv, i, url)
            except:
                # la requête HTTP a échoué (requests.exceptions.HTTPError) ou
                # le fichier PDF était incorrect (pdf2image.exceptions.PDFPageCountError)
                ajout_erreur(db_csv, i, "Problème URL")

            if delete_pdfs:
                try:
                    os.remove("./Datas/PDF/" + nom + ".pdf")
                except:
                    pass
        db_csv.loc[i, "nom_txt"] = nom + ".txt"
    db_csv.to_csv("arretes.csv", index=False, encoding="utf-8")
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
