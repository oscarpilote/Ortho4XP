# Ortho4XP
![example](https://github.com/shred86/Ortho4XP/assets/32663154/f06ebfe5-ba1d-4f05-9439-8e569bd99ef5)

Ortho4XP is a scenery generation tool for [X-Plane](https://www.x-plane.com). It creates the scenery base mesh and texture layer using external data and orthophoto sources.

This is a forked version of [Ortho4XP](https://github.com/oscarpilote/Ortho4XP) developed by [@oscarpilote](https://github.com/oscarpilote) which includes some updates, fixes and documentation. The official version is infrequently updated which is the reason I created this forked version to provide quicker updates and documentation.

The specific changes in this forked version:

#### General
* Tile configurations are automatically loaded when the active tile is changed using the Tiles Collection and Management window. If a tile configuration doesn't exist, the global tile configuration settings are used. The tile configuration is not loaded if you manually type in coordinates to change the active tile.
* Code changes to enable using [PyInstaller](https://pyinstaller.org/en/stable/) to bundle Ortho4XP and its dependencies into a single package.

#### Tiles Collection and Management
* Batch building process modified in regards to configuration files. If a tile configuration exists, it will be used. If a tile configuration does not exist, the global configuration will be used.
* "Read per tile cfg" removed and a "Override tile cfg" option added. This override setting allows you to force using the global configuration setting on all tiles, overriding any existing tile configurations.
* Erased cached data feature works like batch building tiles now, meaning Shift-Click (red rectangle) to select tiles, choose deletion options, and click "Batch Delete". The batch delete has no effect on the active tile selection (yellow rectangle).
* Display asterisk next to each tile zoom level number in the Tiles and configuration window if custom zoom levels have been specified.
* Added ability to create a symlink to the yOrtho4XP_Overlays folder by pressing the "O" key in the Tiles Collection and Management window.

#### Config
* Ortho4XP Config window is now separated into three tabs: Tile Config, Global Config, and Application Config. 
* When a tile configuration doesn't exist, the Tile Tab fields will become read-only. Clicking "Save Tile Cfg" in this case will make the fields become editable again since a tile configuration now exists.
* Text added at the top of the Tile Tab window which provides information on whether a tile configuration was loaded, or global defaults are being used.
* "Apply" buttons removed since this occurs automatically when a tile is changed, and the configuration is loaded. It also occurs when you click "Save".
* A "Reset to Global" button was added to the Tile Config tab which will reset the tile settings to the global tile config settings. If custom zones exist, a prompt asserts asking to save the zones. You still must select "Save Tile Config" if you want to save the changes. 
* A "Reset to Defaults" button was added as a part of the Global Config and Application Config tabs which will reset the tile and application settings to the application defaults. You still must select "Save Tile Config" if you want to save the changes. These buttons are independent of each other so if you're on the Global Config tab, it will reset just the tile settings in your global config and if you're on the Application Config tab, it will reset just the application settings in your global config.
* "Load Backup Cfg" buttons added to the Tile, Global, and Application Config tabs which loads settings from a backup config file (if available).
* Added ability to set an alternate `custom_overlay_src` directory to resolve an issue for some users. The default X-Plane scenery files are split up between `/X-Plane 12/Global Scenery/X-Plane Global Scenery` and `/X-Plane 12/Global Scenery/X-Plane Demo Areas`. So if you set `custom_overlay_src` to the first directory and try to batch build a bunch of tiles, you might get an error that the .dsf file can't be found if it's a location where the .dsf files are located in the second directory.
* The `custom_dem` and `fill_nodata` settings are now saved to the global configuration.
* Prompt user if attempting to close the application or config window with unsaved changes.
* Prompt user if attempting to change the active tile with unsaved changes on the Tile Tab in the config window.
* Prompt user if attempting to build tiles with unsaved changes in the config window.
* Backup of the tile configuration is created when using the "Save Tile Config" button (previously was only during a tile build process).
* Default `imprint_mask_to_dds` to `False` to prevent issues with `water_tech=XP12`.
* Added a new setting `max_download_slots` to support a new feature allowing users to specify number of parallel threads for imagery download. @tlinkin
* Setting `max_convert_slots` can now be manually specified by the user.

#### Miscellaneous
* Automatically saves the same data (active tile, default provider, default zoom level and base folder) that the power button icon does when you close the application using the operating system close button.
* Additional console messages addeded to provide more feedback. These are categorized with a verbosity setting of 1 (default).
* Attempt to redownload images (only once) that were not properly downloaded (white squares) if using "All in one" or batch build.
* "Part of image could not be obtained" error will now show a summary message at the end of a batch build or "All in one" if redownload was unsuccessful.
* Minor visual tweaks which included moving the "Refresh" and "Exit" buttons to the bottom of the left side in the Tiles collection and management window to better illustrate the "Refresh" button is not tied to Batch Build only.
* Includes Windows Python dependency wheel files for gdal and scikit-fmm.
* Updated Python and pin requirements to latest working versions.
* Adds a bash script to automate the setup process for those that prefer not to use the packaged version.
* Removed Maxar and Mapbox image providers which are no longer publically available.
* Update overpass servers.
* Include 7-zip executable for Mac.
* Update EOX url template and deleted the broken EOX2.lay file. @A346fan
* Updated Windows & Linux nvcompress to latest version. @tlinkin
* Use DDSTool instead of nvcompress for Mac.
* Update DFSTool to latest version 24-5.
* Removed unused tools.
* Update numpy to 2.3.4 and included specific .whl file for Python 3.13 to avoid an issue on Mac.

#### Bug Fixes
* If one-click symlink feature is used, added removal of symlink when "Erase cached data" "Tile (whole)" option is used.
* Fixed zones being saved to tile configuration that were outside of the tile location.
* Fixed a bug where symlinks weren't automatically deleted if you used the Erased cached data - Tile (whole) option.
* Fixed a bug if you created zones on a tile then clicked "Apply" (which no longer exists as a button) before saving the tile config, it would delete your zones.
* Fixed Viewfinderpanorama elevation source for certain regions of the world.
* Fixed Here (https://wego.here.com/) image provider API key.
* Fixed issue in certain coastal regions where .dds files were being deleted with cleaning_level set to 2 or higher.
* Corrected a few typos in setting descriptions.
* Default `imprint_mask_to_dds` to `False` to prevent issues when using `water_tech=XP12`.
* Fixed a bug with random OSM server selection not working correctly.
* Include recompiled version of Triangle4XP.exe with MinGW-GCC for Windows users to resolve an [issue](https://github.com/oscarpilote/Ortho4XP/issues/282).
* Fixed a bug when using manually installed dem files were not being used on certain tiles.
* Fixed a bug and improved handling of complex meshes (e.g., +30-085) that would cause the build process to get stuck.
* Fixed and improved automatically trying a lower `min_angle` value when the current value fails.
* Reverted to previous triangle.exe to fix issues with creation of extent masks and certain providers.
* Fixed issue with latest version of shapely.
* Fixed OSM.lay provider to resolve 403 error with "Preview / Custom Zoom levels" window. @d41k4n
* Fixed issue in Triangle4XP.c with `scaly2` and rebuilt Triangle4XP executables for Windows, Mac (Universal) and Linux.
* Fixed redundant output supression with `subprocess.call`.
* Fixed temporary tif not being removed in `convert_texture` function.
* Update deprecated pillow method `BICUBIC` with `Resampling.BICUBIC`.

## Installation

For installation instructions, refer to the [Installation page](https://github.com/shred86/Ortho4XP/wiki/Installation) in the [Wiki](https://github.com/shred86/Ortho4XP/wiki).

## Support

Troubleshooting steps for some issues are provided in the [Wiki FAQ](https://github.com/shred86/Ortho4XP/wiki/FAQ). For additional support or questions, refer to the [Ortho4XP forum](https://forums.x-plane.org/index.php?/forums/forum/322-ortho4xp/) at [X-Plane.org](https://forums.x-plane.org).
