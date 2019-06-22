# Ortho4XP_FSX_P3D
A scenery generator for the X-Plane flight simulator

Work in progress at adding FSX/P3D (ESP support)

# Use at your own risk

# Prerequisites

Please install ImageMagick before attempting to run, otherwise the night/season creation won't work. An installer has been provided inside the dist/ directory. Run the installer with the default settings.
The same installer can also be found here: https://www.imagemagick.org/download/binaries/ImageMagick-7.0.8-10-Q8-x64-dll.exe

NOTE: Need to provide the location of your resample.exe from the P3D or FSX SDK in Ortho4XP.cfg, like this:

`ESP_resample_loc=C:\\LOCATION\\TO\\resample.exe`

Notice the double backslashes `\\` instead of single `\`. This key is only supported by this fork and will be deleted from the Ortho4XP.cfg file each time you change and save the settings via the settings screen in the GUI, so be sure to add it again using a text editor if it gets removed.

You can obtain the P3D resample.exe by installing the P3D SDK provided by Lockheed Martin on their site where you download P3D.
For FSX, resample.exe can be found by installing the FSX SDK found in the FSX Deluxe Disc 1 or in FSX Acceleration Pack (or FSX Gold which includes the Acceleration pack). The Steam edition of FSX does have an SDK but doesn't include the resample.exe executable, so you will have to install the regular SDK from any of these other sources (the FSX SDK has its own installer and can be installed separately without having to install the full game). 

# Running from exe
An executable (.exe) file has been provided in the dist/ directory, if you don't want to build the binary yourself. Simply double click on it, and it'll run. It cannot run without the parent folders though.

# Running with Python
To install, follow the install guide for Ortho4XP, making sure to install all python libraries, and run Ortho4XP_v130.py from the command line.

# To create autogen with ScenProc
*NOTE* -> the included default ScenProc script needs improvement. I will improve it as time permits. There is also the possibility to improve it yourself, or simply add new scripts which ScenProc can use (see below steps on how to do this)
1) Download ScenProc from here: https://www.scenerydesign.org/development-releases/
Either the x86 or x64 version, depending on whether your operating system is 32 bit (x86) or 64 bit (x64)
2) Extract ScenProc to the location of your choice
3) Make sure to run scenProc.exe at least once, and set the path to your sim. Do this by running scenProc.exe, accepting the message box which appears, and then selecting the sim you are using along with the path to the sim in the window which shows up
4) Set the path to scenProc.exe in Ortho4XP.cfg, like this:
`ESP_scenproc_loc=C:\\path\\to\\ScenProc\\scenProc.exe`
5) OPTIONAL: You can create more scripts to guide ScenProc in creating autogen. They *MUST* be placed inside the `ScenProc_configs` folder. You can select which script for ScenProc to utilize, by changing the following line in Ortho4XP.cfg:
`ESP_scenproc_script=default.spc`, where `default.spc` is the name of the script you wish to use inside the `ScenProc_configs` folder
*IMPORTANT*: *MAKE SURE* to include the `@0@` and `@1@` in the same locations in your custom ScenProc scripts as are found in the default ScenProc script. Namely, the first and last lines:
`IMPORTOGR|@0@|*|building;landuse;natural;leisure|NOREPROJ` and
`EXPORTAGN|FSX|@1@`
Everything else can be changed, just not `@0@` and `@1@`, as ScenProc needs these so Ortho4XP can tell it where to load the OSM data from and where to output the autogen files to, respectively

# Example run from exe
https://www.youtube.com/watch?v=fkvmlbJXAq4

# Building binary (only tested on windows 10 64 bit):
Use pyinstaller like this:

`pyinstaller --clean -F -p src Ortho4XP_v130.py`

Then, copy spatialindex-64.dll and spatialindex_c.dll (from rtree python module) into the dist folder where the new executable is:

`cp /cygdrive/c/Users/fery2/AppData/Local/Programs/Python/Python36/lib/site-packages/rtree/spatialindex*.dll dist/`

To build the imagemagick based c++ dll, use the Visual Studio Native Tools Command Prompt, and do something like:

`"F:\ExtraPrograms\Microsoft Visual Studio\2017\Community\VC\Tools\MSVC\14.14.26428\bin\Hostx64\x64\cl.exe" /LD /I "C:\Program Files\ImageMagick-7.0.8-Q8\include" /I C:/Users/fery2/AppData/Local/Programs/Python/Python36/include src\cpp\fast_image_mask.cpp src\cpp\FSET_ports.cpp  C:\Users\fery2\AppData\Local\Programs\Python\Python36\libs\python36.lib "C:\Program Files\ImageMagick-7.0.8-Q8\lib\CORE_RL_Magick++_.lib" "C:\Program Files\ImageMagick-7.0.8-Q8\lib\CORE_RL_MagickCore_.lib" "C:\Program Files\ImageMagick-7.0.8-Q8\lib\CORE_RL_MagickWand_.lib"`

Make sure the visual ++ environment is set to the correct bit of your python (32 vs 64 bit), and rename the .dll to .pyd

Note:
Imagemagick is required, specifically the q8 quantum depth version. To build it on UNIX from source code, configure like this:

`./configure --with-tiff=yes --with-quantum-depth=8`

# WHERE TO FIND the .bgl FILES FOR FSX
Ortho4XP generates a bunch of .bgl files for each tile inside the `Orthophotos` directory (for instance: `Ortho4XP_FSX_P3D-master\Orthophotos\+30+000\+39+002\BI_16\ADDON_SCENERY`). Rename the `ADDON_SCENERY` folder to whatever you wish, and move it wherever you wish (recommended is inside the `Addons Scenery` folder inside FSX/P3D). Then, add the scenery using the add/remove scenery option inside of the sim

# FINISHED:
base satellite imagery creation for FSX and P3D
water masks for FSX and P3D
build binary
night/seasonal texture creation options

# TODO:
remove extra steps not needed for ESP scenery creation
improve default scenProc spc file so it looks good in as many areas of the world as possible

# BUGS:
Certain tiles don't appear when their BGL is too large in size (like when creating tiles at ZL 12 and enabling all the seasons which creates 2+ gig BGLs). Not sure if limitation of the sim, or some other issue.
