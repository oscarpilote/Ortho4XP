# Ortho4XP_FSX_P3D

# Use at your own risk

A scenery generator for the X-Plane flight simulator  
Work in progress at adding FSX/P3D (ESP support)  
For now, only Ortho4XP_v130.py runs (binaries haven't been built with ESP support)  

To install, follow the install guide for Ortho4XP, making sure to install all python libraries, and run Ortho4XP_v130.py from the command line  
NOTE: Need to provide the location of your resample.exe from the P3D or FSX SDK in Ortho4XP.cfg, like this:  
ESP_resample_loc=C:\LOCATION\TO\resample.exe  
You can obtain the P3D resample.exe by installing the P3D SDK provided by Lockheed Martin on their site where you download P3D.  
The FSX resample.exe can be found by installing the FSX SDK found in the FSX Deluxe Disc 2 or in FSX Acceleration Pack (or FSX Gold which includes the Acceleration pack)  

Building binary:
Use pyinstaller like this:  
pyinstaller -F -p src Ortho4XP_v130.py
Then, copy spatialindex-64.dll and spatialindex_c.dll (from rtree python module) into the dist folder where the new executable is:  
cp /cygdrive/c/Users/fery2/AppData/Local/Programs/Python/Python36/lib/site-packages/rtree/spatialindex*.dll dist/  
  
FINISHED:
base satellite imagery creation for FSX and P3D  
water masks for FSX and P3D  
build binary  
  
TODO:  
remove extra steps not needed for ESP scenery creation  
add integration with sceneproc to allow for adding of custom autogen from OpenStreetMap data
