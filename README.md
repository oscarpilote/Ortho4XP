# Ortho4XP_FSX_P3D

Note: Use airport_auto_patch branch to get functioning masks. This branch can only build unmasked bgls for ESP, due to the way Ortho4XP downloads tiles in the master branch. Mask support will not be added to this branch. V130 (ie the version in airport_auto_patch) creates masks in a way much more compatible with resample.exe, and support for building masks into bgl's will be added to this branch.

A scenery generator for the X-Plane flight simulator  
Work in progress at adding FSX/P3D (ESP support)  
For now, only Ortho4XP_v120b.py runs (binaries haven't been built with ESP support)  
To install, follow the install guide for Ortho4XP, making sure to install all python libraries, and run Ortho4XP_v120b.py from the command line  
TODO:  
implement water masks  
remove extra steps not needed for ESP scenery creation  
build binaries  
