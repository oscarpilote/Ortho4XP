<<<<<<< HEAD
# Ortho4XP

A scenery generator for the X-Plane flight simulator by Oscar Pilote and co-workers.


NOTICE 1. Windows users: Only use Notepad++ or an equivalent decent editor to read or modify Ortho4XP related files. Notepad doesn't understand linux line-ends and will create a mess. 

NOTICE 2 : Windows users: You do not need to read further than this notice if you have installed the binary windows version!
In your case, the executable file is Binary/Ortho4XP_v130.exe, and the only advisable action is to make a short-cut to it somewhere, e.g. in the main Ortho4XP directory (but the executable needs to stay where it is). 
If you end-up installing the python modules some day (to get more frequent updates or bugs fixed), the Binary directory won't be necessary anymore. 

The following instructions are for the script install :

## Linux (Debian derived, names might slightly differ for other distros)

sudo apt-get install python3 python3-pip python3-requests python3-numpy python3-pyproj python3-gdal python3-shapely python3-rtree python3-pil python3-pil.imagetk p7zip-full libnvtt-bin

(if some of them were note packaged for your distro you can use pip instead, like say, pip install pyproj)


## Windows

1) Download and install Python 3 from www.python.org 

Just select one for your Windows OS, there is no benefit in our case to download the pretty lastest version of Python, since you might get difficulties further down to find modules already built for it. As of 10/2018, I would recommend using 3.7.    
Make sure during the process that "pip" (package management system for Python) is installed along and made accessible from your PATH [there is a checkbox for this during the Python install process wich by default ISN'T checked].  

2) Download the following packages from https://www.lfd.uci.edu/~gohlke/pythonlibs/

Pyproj, Numpy, Gdal, Shapely, Rtree, Pillow (or alternatively Pillow-SIMD)

Pay attention to take the ones that correspond to the Python version which you picked at Step 1) and to your OS nbr of bits (32 or 64, I guess 64 in all but a few cases).
As an example, if Python 3.7.*  was selected at Step 1) above and you have a 64bit windows, then you would choose these files that have -cp37- and _amd64 within their filename.   

In order to use the build geotiff feature of the custom_zl map, you will need to add the directory containing gdal_translate and gdalwarp (***/python**/lib/site-packages/osgeo/) into your PATH variable.

Finally, if you do not already have them : download and install the build tools for visual studio (2017):
https://visualstudio.microsoft.com/fr/downloads/  

3) From a command window launch successively 

pip install --upgrade pip  [if this goes wrong you probably missed the last point in 1)]
pip install requests
pip install *******.whl [replacing ******** successively by each of the files downloaded at Step 2]

You should be done. Open a command window in the Ortho4XP directory (freshly downloaded from Github) and launch "python Ortho4XP_v130.py".

## OS X

1) In a Terminal window, install Homebrew (brew.sh), a package manager 
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

2) Go to the Ortho4XP folder
cd /path/to/Ortho4XP

3) Execute the install script (you may have to run "chmod +x ./install_mac.sh" first)
./install_mac.sh

4) Launch Ortho4XP
python3 Ortho4XP_v130.py
=======
# Unofficial Flykido's Ortho4XP
Ortho4XP is a scenery generator for the X-Plane flight simulator, written by _**Oscar Pilote**_

It is a really amazing tool and just like many others, I got addicted to it :)

**Please be aware that THIS IS NOT THE OFFICIAL Ortho4XP**.

This repository contains my own modifications to his tool, which I hope will one day be included in the official one.

**It may or may not work** for you, as this is all a work in progress for now.

A few resources for the original Ortho4XP :
- Forum : http://forums.x-plane.org/index.php?/forums/forum/322-ortho4xp/
- Discord Community : https://discord.gg/78nD2
- Original Ortho4XP git repository : https://github.com/oscarpilote/Ortho4XP
- Original Ortho4XP dropbox : https://www.dropbox.com/sh/cjjwu92mausoh04/AACt-QzgMRwKDL392K_Ux3cPa?dl=0

If you want to talk with me about that, I often lurk on the forum and the discord community.

I will of course add an history file to document my changes along the way : also have a look in the wiki and in the issues page.

My first intentions with this repository :
- minor code cleanup / refactoring
  - first based on pycharm buitin analyzer (pep8 checker, etc.)
  - then on external tools analysis : starting with quantifiedcode, but I'm not settled on a particular tool yet
    => see the first results here : https://www.quantifiedcode.com/app/project/gh:Flykido:Ortho4XP
  - finally, maybe I'll refactor a bit more as I see fit.
    - config files and logging : use a more standard lib for that

- add some tests along the way

- implement a few evolutions :
  - multiple layers of ZL around airports (already have a dirty patch for this, will make a cleaner one)
    => next step, even better : I know someone has implemented something to have different ZL in the corridors along the runways, I should get in touch with him
  - integration with xplane apt.dat to show them on the map
    - also use this to find the set of tiles needed along a given flight plan (or simply a given airport)
  - push the idea of simlinking from the HMI a bit further
    - also, have a "tile manager" to manage the storage location of the tiles and overlays

- maybe later, have my own go at an HMI revamp
>>>>>>> cc806cbf49a716de8028786bae5e8b9028978b2f
