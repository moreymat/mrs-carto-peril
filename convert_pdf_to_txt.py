import os
import pytesseract
from pdf2image import convert_from_path
import pandas
import requests

# À adapter en fonction de l'ordinateur utilisé
#pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
tessdata_dir_config = r'--tessdata-dir "/Users/maelle/Downloads/tesseract-ocr-setup-3.05.01/tessdata/"'


def pdf_to_image(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for i, image in enumerate(images):
        # text = text + pytesseract.image_to_string(image, lang='fra') #jeremy
        text = text + pytesseract.image_to_string(image, lang='fra', config=tessdata_dir_config) #maelle
    return text


def pdf_to_txt():
    db_csv = pandas.read_csv("arretes.csv", encoding='utf-8')
    for i in range(len(db_csv)):
    # for i in range(580):
        url = db_csv.loc[i].url
        url_split = url.split("/")
        nom = url_split[-1].split(".")[0]
        if nom + ".txt" not in os.listdir("./Datas/TXT"):
            try:
                changement_url(i, url, db_csv)
                myfile = requests.get(url)
                open('./Datas/PDF/' + nom+".pdf", 'wb').write(myfile.content)
                texte = pdf_to_image("./Datas/PDF/"+nom+".pdf")
                fichier = open("./Datas/TXT/" + nom + ".txt", "w", encoding="utf-8")
                fichier.write(texte)
                fichier.close()
                if db_csv.loc[i].erreurs:
                    db_csv.loc[i, 'erreurs'] = False
                    error = pandas.read_csv("Datas/erreurs.csv")
                    indice = error.loc[error['url'] == url].index.tolist()[0]
                    error.drop(indice, 0, inplace=True)
                    error.to_csv("Datas/erreurs.csv", encoding='utf-8', index=False)
            except:
                if db_csv.loc[i, 'erreurs'] == False:
                    db_csv.loc[i, 'erreurs'] = True
                    error = pandas.read_csv("Datas/erreurs.csv")
                    error.loc[len(error)] = ["Problème URL"] + list(db_csv.loc[i])
                    error.to_csv("Datas/erreurs.csv", encoding='utf-8', index=False)

            try:
                os.remove("./Datas/PDF/" + nom + ".pdf")
            except:
                pass
        db_csv.loc[i, "nom_txt"] = nom + ".txt"
    db_csv.to_csv("arretes.csv", index=False, encoding='utf-8')
    return db_csv


def changement_url(i, url, db):
    url_split = url.split("/")
    if url_split[2] == 'logement-urbanisme.marseille.fr':
        url_split[2] = "marseille.fr"
        url = "/".join(url_split)
        db.loc[i, "url"] = url
    elif url_split[4] == 'logement-urbanisme':
        url_split.pop(3)
        url = "/".join(url_split)
        db.loc[i, "url"] = url
    return None
