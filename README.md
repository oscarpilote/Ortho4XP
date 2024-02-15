# Ortho4XP
A scenery generator for the X-Plane flight simulator.

NOTE 15/02/2024 : In transition to version 1.40.

Version 1.40 is mostly a compatibility update for XP 12 water requirements.
Some newer code related to 3D waterbed rendering is included, but one will have
to wait for XP 12.1 to potentially revise it. The default setting is XP11 (i.e. 
overlay based ) water rendering + bathymetry for 3D water and physics plane interaction. 
The new Ortho4XP tiles also automatically bring the seasons, sounds, etc raster from the
corresponding Global Scenery tiles.

The code as been updated to work with recent versions of the python modules it
depends on (you may have experienced some deprecation warnings or even some
code break due to Numpy, Pyproj and Shapely, these should be fixed with this
update). The only new python module used is skfmm (Fast Marching Method) and is only needed when using 
the distance_masks_too option, the program will run even without it.


TODO :
- Update install instructions (after user first tests). The ones included have
  not been updated at all, but the same list of decently recent python modules should 
  work out of the box.
- Check and update providers status.
- Compile nvcompress for OSX ARM64 (the included version is the old one renamed without the
  .app). A Linux version of nvcompress is included now because some distros are apparently 
  no longer shipping it. Triangle4XP has been updated for all OS, including ARM based Mac.
  I have not tested anything but Linux software.
- Incorporate some code changes that were in the old "devel" version (the
  present is an update from the v130 master branch only).
- Do something about the 3rd party initiatives to provide some Docker or other 
  Plug and Play versions.
