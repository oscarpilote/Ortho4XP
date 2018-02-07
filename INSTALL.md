# Ortho4XP

A scenery generator for the X-Plane flight simulator
=======

*Note: These instructions are currently* ***OUT OF DATE***

### I. In English (top)
*don't forget to read the Manual for instructions of use!*

### II. En Français (plus loin ci-dessous)
*ne pas oublier de lire le Manuel pour les instructions d'utilisation!*


## I. Installation instructions for Ortho4XP.
November 3rd 2015

### Installation instructions under Windows 64 bits 
*July 2016 !!! Look instead on youtube for updates !!!*


1. Download the archive containing Ortho4XP and extract it to the place of your choice. If you read these instructions you probably already did so! 
Choose preferably a partition with some comfortable free space, and it is probably also best to avoid directories with spaces in their name (although it should work too).

1. Open the Explorer of Windows and within the sub-directory `Install/Win64` open the text file `Win64_download_list.txt` containing the list of files needed for the installation of third parties. Download and save all of them (in the following I assume they are save in `Install/Win64`).

1. In `Install/Win64` click on the Python 3.5 installer (and follow its instructions). Pay attention to indicate it to add its directory to the `PATH` of Windows (this is an option with a checkbox at the bottom of some drop-down menu). 

1. Same as Step 2 but for Imagemagick, accept all default choice, except for the install dir which you can choose freely. 

1. Same as Step 2 but for the Visual C++ redistribuables. You may already have (a close version of) it on your system, in that case the installer will propose you to "repair" it, you are free to decide whether you wish to do so or keep yours.

1. Still in the directory `Install/Win64` of Ortho4XP, hold the <kbd>SHIFT</kbd> key pressed and perform a right-click, and then select the option "Open a terminal here".

1. In the terminal window type:
```
pip install requests [press Enter key]
pip install overpy [press Enter key]
pip install "numpy-1.9.3+mkl-cp35-none-win_amd64.whl" [press Enter key] 
```  
*you can type on the TAB key to automatically complete the long numpy-1.9... name, and the same for the next two lines*
```
pip install "GDAL-1.11.3-cp35-none-win_amd64.whl"[press the Enter key]     
pip install "Pillow-3.0.0-cp35-none-win_amd64.whl"[press the Enter key]
```

1. (Optional but recommended if you wish to build automatic water masks)
  1. Download Gimp 2.8 from the address: http://download.gimp.org/pub/gimp/v2.8/windows/gimp-2.8.14-setup-1.exe
  1. Adapt the line corresponding to gimp_cmd in the file `Ortho4XP.cfg`
  1. Copy the script-fu blurX.scm (initially contained in the Utils dir of Ortho4XP) in your Gimp scripts directory (presumably `.gimp-2.8/scripts` within your home directory).

1. (Optional if you wish to use certain providers) install the pyproj module for Python 3 trough the command
```
pip install "pyproj-1.9.4-cp35-none-win_amd64.whl"[press the Enter key]
```

### Installation instructions for Mac Os X 64 bits 

*A more detailed installation manual was written by a french user Milan 
(xplanefr.com), it is available (in French) in the Install/MAC64 directory*

1. Download the archive containing Ortho4XP and extract it to the place of your choice. If you read these instructions you probably already did so! 
Choose preferably a partition with some comfortable free space, and it is probably also best to avoid directories with spaces in their name (although it should work too).

1. In the Finder, navigate up to the directory `Install/Mac64` in Ortho4XP. Right-click on the file `Install_script.sh` and select "Open with" and then select the "Terminal" app. Confirm with "OK" and then double click on the file `Install_script.sh`, which should fire itself within a terminal. Follow the instructions on screen. NOTE THAT a number of users that have tried this prefer to execute the script by themselves (by recopying each of the lines starting with exec, but omitting the exec). 

1. (Optional but recommended for automatic water masks)
  1. Download and install Gimp 2.8 from the address: http://gimp.lisanet.de/Website/Download.html
  1. Adapt (if necessary) the line corresponding to gimp_cmd in the file `Ortho4XP.cfg`
  1. Open Gimp, select Preferences/Folders/Scripts, select in the Folders window the one starting with /Users (a green button should show up) and validate
  1. Copy the script-fu blurX.scm file (initially contained in the `Utils` dir of Ortho4XP) in your Gimp scripts directory (presumably Your Name / Library / Application Support / GIMP / 2.8 / scripts)

1. Do not forget to make the files `Ortho4XP.py` and `Triangle4XP.app` executable. From within a terminal in the main Ortho4XP dir:
```
chmod a+x ./Ortho4XP.py ./Utils/Triangle4XP.app
```

### Installation instructions under Linux 64 bits 

With a Linux distro using the apt package tool :

*The names of packages may slightly vary depending on your distribution, the ones below are those in Debian 8 (and presumably Ubuntu 15.10 or Mint 17)*

```
sudo apt-get install python3
sudo apt-get install imagemagick  (!!! Important : version >= 6.8 needed !!!) 
sudo apt-get install python3-pip
pip3 install requests
pip3 install overpy
pip3 install numpy
pip3 install gdal  (or apt-get install python3-gdal if the previous fails) 
sudo apt-get install python3-pil
sudo apt-get install python3-pil.imagetk 
sudo apt-get install gimp
sudo apt-get install python3-pyproj
sudo apt-get install libnvtt.bin
```

Copy the script-fu blurX.scm (initially contained in the Utils dir of Ortho4XP) in your Gimp scripts directory (`$HOME/.gimp-2.8/scripts`). 
   
Do not forget to make the files `Ortho4XP.py` and `Triangle4XP` executable from within a terminal in the main Ortho4XP dir:
```
chmod a+x ./Ortho4XP.py ./Utils/Triangle4XP
```

## II. Notes d'installation du logiciel Ortho4XP.
Le 03 novembre 2015.

### Instructions d'installation sous Windows 64 bits 

(Juillet 2016 : voir plutôt la vidéo youtube que j'ai rapidement réalisée)


1. Télécharger l'archive contenant Ortho4XP et l'extraire tel quel à 
   l'endroit de votre choix.
   Si vous lisez ceci vous l'avez vraisemblablement déjà fait!
   Choisir un disque avec de la place, et éviter dans la mesure du possible 
   les noms de répertoires avec des espaces (devrait fonctionner toutefois).

1. Ouvrir l'Explorateur de Windows et dans le sous-répertoire 
   "Install/Win64" d'Ortho4XP ouvrir le fichier texte Win64_download_list.txt
   et télécharger tous les éléments qu'il indique (dans la suite je suppose 
   qu'ils sont téléchargés dans le répertoire Install/Win64. 
   
1. Cliquer sur l'installateur de Python 3.5 et suivre ses instructions. 
   Faire attention à bien lui indiquer d'ajouter son répertoire au PATH de 
   Windows (c'est une option d'installation à cocher en bas d'un menu 
   déroulant). Si vous disposez déjà d'une version de Python 3 vous n'êtes 
   pas obligé d'installer la version proposée. 

1. Faire de même avec Imagemagick, en laissant les choix par défaut 
   (sauf le dossier d'installation que vous pouvez modifier à votre guise).

1. Faire de même avec la libraire C++ Microsoft Visual Studio 
   Il est possible/vraisemblable que vous disposiez déjà 
   de cette librairie, auquel cas l'installateur vous proposera de "réparer" 
   l'ancienne avec la nouvelle, vous êtes libre de votre choix.

1. Toujours dans le répertoire Install/Win64 de Ortho4XP, maintenir la 
   touche SHIFT enfoncée et cliquer sur le bouton droit pour faire apparaitre 
   l'option "Ouvrir un terminal dans ce répertoire" que l'on sélectionne.

1. Une fois dans le terminal taper au clavier :
```
pip install requests[appuyer sur Entrée]
pip install overpy[appuyer sur Entrée]
pip install "numpy-1.9.3+mkl-cp35-none-win_amd64.whl"[appuyer sur Entrée] 
```
[on peut appuyer sur TAB en cours de route pour qu'il complète seul ce nom 
de fichier compliqué, idem pour les lignes suivantes]
```
pip install "GDAL-1.11.3-cp35-none-win_amd64.whl"[appuyer sur Entrée]     
pip install "Pillow-3.0.0-cp35-none-win_amd64.whl"[appuyer sur Entrée]
```
1. (Optionnel mais recommandé pour pouvoir créer des masques automatiquement) 
   Télécharger puis installer Gimp 2.8 depuis l'adresse :
   http://download.gimp.org/pub/gimp/v2.8/windows/gimp-2.8.14-setup-1.exe,
   adapter (si besoin) la ligne correspondant à gimp_cmd dans le fichier 
   Ortho4XP.cfg, et copier le script-fu blurX.scm (initialement situé dans le 
   répertoire Utils) dans le répertoire scripts de Gimp (vraisemblablement 
   .gimp-2.8/scripts à l'intérieur de votre répertoire personnel). 

1. (Optionnel pour utiliser certains fournisseurs) Installer le module
   pyproj pour Python 3 par la commande
```
pip install "pyproj-1.9.4-cp35-none-win_amd64.whl"[appuyer sur Entrée]
```

### Instructions d'installation sous Mac Os X 64 bits 

(En complément des instructions qui suivent, une notice très détaillée avec
images réalisée par Milan (xplanefr.com) est mise à disposition dans le 
répertoire Install/Mac64)

1) Télécharger le dossier Ortho4XP sur Dropbox (cfr. ma signature sur 
   x-plane.fr) et le copier tel quel à l'endroit de votre choix.
   Si vous lisez ceci vous l'avez vraisemblablement déjà fait!
   Choisir un disque avec de la place, et éviter dans la mesure du possible 
   les noms de répertoires avec des espaces (devrait fonctionner toutefois).

2) Dans le Finder, se rendre dans le répertoire Install/Mac64 d'Ortho4XP.
   Cliquer avec le bouton droit de la souris sur le fichier Install_script.sh
   et choisir "Ouvrir avec" puis sélectionner l'application Terminal (dans
   les utilitaires). Appuyer sur OK puis double cliquer sur le fichier
   Install_script.sh, qui devrait se lancer dans un terminal. Suivre les
   instructions qui apparaitront à l'écran (plusieurs installations).
   Plusieurs utilisateurs ont préféré lancer les commandes du script 
   manuellement l'une après l'autre (ouvrir le fichier dans un éditeur de texte
   et recopier suivi par Entrée une à une toutes les lignes commençant par
   exec, en omettant le exec).

3) Optionnel mais recommandé pour la création automatique des masques).
   Télécharger et installer Gimp 2.8 depuis l'adresse :
   http://gimp.lisanet.de/Website/Download.html 
   Adapter si nécessaire la ligne correspondant à gimp_cmd dans le fichier
   Ortho4XP.cfg.
   Ouvrir Gimp et naviguer dans les menus Préférences/Dossiers/Scripts, 
   sélectionner dans la fenêtre Dossiers celui commençant par /Users (un bouton
   vert apparaitra) et valider. 
   Copier le script-fu blurX.scm (initialement situé dans le 
   répertoire Utils) dans le répertoire scripts de Gimp (vraisemblablement 
   Nom d'utilisateur / Bibliothèque / Application Support / GIMP / 2.8 / scripts).  


### Instructions d'installation sous Linux 64 bits 

Avec une distribution basée sur le gestionnaire de paquet apt :

(les noms de paquets peuvent légèrement varier suivant votre distribution)

```
sudo apt-get install python3
sudo apt-get install imagemagick  (!!! Important : version >= 6.8 nécessaire !!!) 
sudo apt-get install python3-pip
pip3 install requests
pip3 install overpy
pip3 install numpy
pip3 install gdal  (ou apt-get install python3-gdal si problème il y a) 
sudo apt-get install python3-pil
sudo apt-get install python3-pil.imagetk 
sudo apt-get install gimp
sudo apt-get install python3-pyproj
sudo apt-get install libnvtt.bin
```

Copier le script-fu blurX.scm (initialement situé dans le répertoire Utils) dans le répertoire scripts de Gimp 
($HOME/.gimp-2.8/scripts).

