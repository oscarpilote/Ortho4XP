#!/usr/bin/env python3
import sys
import os
Ortho4XP_dir = os.pardir if getattr(sys, 'frozen', False) else os.curdir
sys.path.extend([os.path.join(Ortho4XP_dir, 'src'),
                 os.path.join(Ortho4XP_dir, 'Providers')])

import O4_Airport_Data_Source as APT_SRC
import O4_File_Names as FNAMES
sys.path.append(FNAMES.Provider_dir)
import O4_Imagery_Utils as IMG
import O4_Vector_Map as VMAP
import O4_Mesh_Utils as MESH
import O4_Mask_Utils as MASK
import O4_Tile_Utils as TILE
import O4_GUI_Utils as GUI
import O4_Config_Utils as CFG  # CFG imported last because it can modify other modules variables


cmd_line="USAGE: Ortho4XP.py lat lon imagery zl (won't read a tile config)\n   OR:  Ortho4XP.py lat lon (with existing tile config file)"

if __name__ == '__main__':
    if not os.path.isdir(FNAMES.Utils_dir):
        print("Missing ",FNAMES.Utils_dir,"directory, check your install. Exiting.")
        sys.exit()
    for directory in (FNAMES.Preview_dir, FNAMES.Provider_dir, FNAMES.Extent_dir, FNAMES.Filter_dir, FNAMES.OSM_dir,
                      FNAMES.Mask_dir,FNAMES.Imagery_dir,FNAMES.Elevation_dir,FNAMES.Geotiff_dir,FNAMES.Patch_dir,
                      FNAMES.Tile_dir,FNAMES.Tmp_dir,FNAMES.Airport_dir):
        if not os.path.isdir(directory):
            try:
                os.makedirs(directory)
                print("Creating missing directory",directory)
            except:
                print("Could not create required directory",directory,". Exit.")
                sys.exit()
    IMG.initialize_extents_dict()
    IMG.initialize_color_filters_dict()
    IMG.initialize_providers_dict()
    IMG.initialize_combined_providers_dict()
    APT_SRC.AirportDataSource.update_cache()

    if len(sys.argv)==1: # switch to the graphical interface
        Ortho4XP = GUI.Ortho4XP_GUI()
        Ortho4XP.mainloop()
        print("Bon vol!")

    else: # sequel is only concerned with command line
        if len(sys.argv)<3:
            print(cmd_line); sys.exit()
        try:
            lat=int(sys.argv[1])
            lon=int(sys.argv[2])
        except:
            print(cmd_line); sys.exit()
        if len(sys.argv)==3:
            try:
                tile=CFG.Tile(lat,lon,'')
            except Exception as e:
                print(e)
                print("ERROR: could not read tile config file."); sys.exit()
        else:
            try:
                provider_code=sys.argv[3]
                zoomlevel=int(sys.argv[4])
                tile=CFG.Tile(lat,lon,'')
                tile.default_website=provider_code
                tile.default_zl=zoomlevel
            except:
                print(cmd_line); sys.exit()
        try:
            VMAP.build_poly_file(tile)
            MESH.build_mesh(tile)
            MASK.build_masks(tile)
            TILE.build_tile(tile)
            print("Bon vol!")
        except:
            print("Crash!")

    if False:
        import json
        import O4_Geo_Utils
        print("04_airport_Data_Source.GTile :")
        print(json.dumps(APT_SRC.GTile.cache_info(), indent=True))
        print(json.dumps(APT_SRC.AirportCollection.cache_info(), indent=True))
        for f in [O4_Geo_Utils.gtile_to_wgs84]:
            print("{} : {}".format(f.__qualname__, f.cache_info()))
