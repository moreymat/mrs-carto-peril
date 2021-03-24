# Cartographie des arrêtés de péril à Marseille

## Installation

### Installer `tesseract-ocr`

Suivre les instructions d'installation générale de <https://tesseract-ocr.github.io/tessdoc/Installation.html>.

Pour Ubuntu :

```console
# tesseract et ses bibliothèques
sudo apt install tesseract-ocr
sudo apt install libtesseract-dev
# modèle pour le français
sudo apt install tesseract-ocr-fra
```

#### ? Tesseract 3

Installer tesseract 3 puis ajouter le modèle pour le français `fra.traineddata` dans le répertoire *`tessdata`*. On peut le trouver ici : <https://github.com/tesseract-ocr/tessdata/raw/3.04.00/fra.traineddata> .

#### Windows et Mac

- Ajouter tesseract aux variables d'environnement.
- Modifier `convert_pdf_to_txt.py`:
  - ajouter les dépendances relatives à l'installation tesseract aux lignes 12 à 18. Les lignes sont différentes suivant le système d'exploitation:
    - **Windows**: `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`suffit pour l'utilisation de la langue française ;
    - **Mac**: il faut donner le lien vers le fichier de langues : `tessdata_dir_config = r'--tessdata-dir "/Users/nomdutilisateur/Downloads/tesseract-ocr-setup-3.05.01/tessdata/"'` ;

### Installer `poppler`

- Ajouter poppler aux variables d'environnement.

### Installer les dépendances python

```console
pip install -r requirements.txt
```

## Configuration de la représentation des objets

### Changement de représentation des données : marqueurs ou points

Deux représentations, marqueurs ou points, sont possibles pour les différentes addresses présentant des arrêtés.
Actuellement il faut commenter et décommenter les lignes adaptées à la représentation choisie.

Dans `carte.py`:

- fonction *`creation_carte`*, lignes 27 à 34
- fonction *`creation_marker`*, lignes 42 à 47

Dans `main.py`:

- dans la boucle, lignes 69 à 74
- lignes 57 à 61 (décommenté = marqueurs, commenté=points)

### Personnalisation des marqueurs

Avec la représentation par des marqueurs, il est possible de personnaliser les icones (type et couleur). Par défaut, ce sont des maisons blanches.

Dans `carte.py`:

- fonction *`creation_marker`*, ligne 44 :

  - Pour le type d'icone, il faut changer `icon='home'` en remplaçant "home" par un des icones présent sur <https://glyphicons.com/sets/basic/> ;
  - Pour la couleur de l'icone, il faut changer `icon_color='white'` en remplaçant "white" par une des couleurs listées dans la documentation  : `'red', 'darkred',  'lightred', 'orange', 'beige', 'green', 'darkgreen', 'lightgreen', 'blue', 'darkblue', 'cadetblue', 'lightblue', 'purple', 'darkpurple', 'pink', 'white', 'gray', 'lightgray', 'black'`.

## Gestion manuelle des erreurs

Lorsqu'une erreur est détectée par le programme (problème d'URL, d'adresse, de date ou d'annonce de pathologies), elle est ajoutée au fichier `erreurs.csv`. Certaines peuvent être traitées manuellement.

### Problème de date

1- Aller dans le fichier `.txt` correspondant à l'adresse que l'on souhaite traiter
2- Ajouter au début du fichier : `Envoyé en préfecture le <dd/mm/yyyy>`
3- Supprimer toutes les lignes de `erreurs.csv` sauf la première
4- Supprimer le contenu du fichier `data.json` et ne laisser que `{}` comme contenu
5- Dans le fichier `arretes.csv` placer la colonne `erreurs` de l'arrêté traité sur `False`
6- Faire `run` sur le fichier `main.py`
7- Vérifier que l'arrêté n'apparaît plus dans `erreurs.csv` et que l'erreur a été correctement traitée

### Problème d'adresse

1- Aller dans le fichier `arretes.csv`
2- Ajouter l'adresse dans la colonne `adresse`
3- Placer la colonne `erreurs` de l'arrêté traité sur `False`
4- Supprimer toutes les lignes de `erreurs.csv` sauf la première
5- Supprimer le contenu du fichier `data.json` et ne laisser que `{}` comme contenu
6- Faire `run` sur le fichier `main.py`
7- Vérifier que l'arrêté n'apparaît plus dans `erreurs.csv` et que l'erreur a été correctement traitée

### Problème d'URL

Si c'est cette catégorie de problème qui est listée dans le fichier `erreurs.csv`, il faut vérifier que le lien vers le PDF de l'arrêté est fonctionnel. Si c'est le cas et que l'arrêté n'avait pas pu être traité à cause d'un problème de connexion, relancer le programme suffira à traiter l'erreur. Sinon, il est possible que le PDF ne soit plus disponible sur le site de la mairie.
