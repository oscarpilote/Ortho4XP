import os
from math import ceil
import tkinter as tk
import tkinter.ttk as ttk
from   tkinter import RIDGE,N,S,E,W,filedialog
import O4_File_Names as FNAMES
import O4_UI_Utils as UI
import O4_DEM_Utils as DEM
import O4_OSM_Utils as OSM
import O4_Vector_Map as VMAP
import O4_Imagery_Utils as IMG
import O4_Tile_Utils as TILE
import O4_Overlay_Utils as OVL


cfg_vars={
    # App
    'verbosity':             {'module':'UI','type':int,'default':1,'values':(0,1,2,3),'hint':'Verbosity determines the amount of information about the whole process which is printed on screen.  Critical errors, if any, are reported in all states as well as in the Log. Values above 1 are probably only useful for for debug purposes.'},  
    'cleaning_level':        {'module':'UI','type':int,'default':1,'values':(0,1,2,3),'hint':'Determines which temporary files are removed. Level 3 erases everything except the config and what is needed for X-Plane; Level 2 erases everything except what is needed to redo the current step only; Level 1 allows you to redo any prior step; Level 0 keeps every single file.'}, 
    'overpass_server_choice':{'module':'OSM','type':str,'default':'random','values':['random']+sorted(OSM.overpass_servers.keys()),'hint':'The (country) of the Overpass OSM server used to grab vector data. It can be modified on the fly (as all _Application_ variables) in case of problem with a particular server.'},
    'skip_downloads':        {'module':'TILE','type':bool,'default':False,'hint':'Will only build the DSF and TER files but not the textures (neither download nor convert). This could be useful in cases where imagery cannot be shared.'},
    'skip_converts':         {'module':'TILE','type':bool,'default':False,'hint':'Imagery will be downloaded but not converted from jpg to dds. Some user prefer to postprocess imagery with third party softwares prior to the dds conversion. In that case Step 3 needs to be run a second time after the retouch work.'}, 
    'max_convert_slots':     {'module':'TILE','type':int,'default':4,'values':(1,2,3,4,5,6,7,8),'hint':'Number of parallel threads for dds conversion. Should be mainly dictated by the number of cores in your CPU.'},
    'check_tms_response':    {'module':'IMG','type':bool,'default':True,'hint':'When set, internal server errors (HTTP [500] and the likes) yields new requests, if not a white texture is used in place.'},
    'http_timeout':          {'module':'IMG','type':float,'default':10,'hint':'Delay before we decide that a http request is timed out.'},
    'max_connect_retries':   {'module':'IMG','type':int,'default':5,'hint':'How much times do we try again after a failed connection for imagery request. Only used if check_tms_response is set to True.'},
    'max_baddata_retries':   {'module':'IMG','type':int,'default':5,'hint':'How much times do we try again after an internal server error for an imagery request. Only used if check_tms_response is set to True.'},
    'ovl_exclude_pol'    :   {'module':'OVL','type':list,'default':[0],'hint':'Indices of polygon types which one would like to left aside in the extraction of overlays. The list of these indices in front of their name can be obtained by running the "extract overlay" process with verbosity = 2 (skip facades that can be numerous) or 3. Index 0 corresponds to beaches in Global and HD sceneries. Strings can be used in places of indices, in that case any polygon_def that contains that string is excluded, and the string can begin with a ! to invert the matching. As an exmaple, ["!.for"] would exclude everything but forests.'},
    'ovl_exclude_net'    :   {'module':'OVL','type':list,'default':[],'hint':'Indices of road types which one would like to left aside in the extraction of overlays. The list of these indices is can be in the roads.net file within X-Plane Resources, but some sceneries use their own corresponding net definition file. Powerlines have index 22001 in XP11 roads.net default file.'},
    'custom_scenery_dir':    {'type':str,'default':'','hint':'Your X-Plane Custom Scenery. Used only for "1-click" creation (or deletion) of symbolic links from Ortho4XP tiles to there.'},
    'custom_overlay_src':    {'module':'OVL','type':str,'default':'','hint':'The directory containing the sceneries with the overlays you would like to extract. You need to select the level of directory just _ABOVE_ Earth nav data.'},
    # Vector
    'apt_smoothing_pix':   {'type':int,  'default':8,'hint':"How much gaussian blur is applied to the elevation raster for the look up of altitude over airports. Unit is the evelation raster pixel size."},
    'road_level':          {'type':int,'default':1,'values':(0,1,2,3,4,5),'hint':'Allows to level the mesh along roads and railways. Zero means nothing such is included; "1" looks for banking ways among motorways, primary and secondary roads and railway tracks; "2" adds tertiary roads; "3" brings residential and unclassified roads; "4" takes service roads, and 5 finishes with tracks. Purge the small_roads.osm cached data if you change your mind in between the levels 2-5.'},
    'road_banking_limit':  {'type':float,'default':0.5,'hint':"How much sloped does a roads need to be to be in order to be included in the mesh levelling process. The value is in meters, measuring the height difference between a point in the center of a road node and its closest point on the side of the road."}, 
    'lane_width':          {'type':float,'default':5,'hint':"With (in meters) to be used for buffering that part of the road network that requires levelling."},
    'max_levelled_segs':   {'type':int,'default':100000,'hint':"This limits the total number of roads segments included for mesh levelling, in order to keep triangle count under control in case of abundant OSM data."},
    'water_simplification':{'type':float,'default':0,'hint':"In case the OSM data for water areas would become too large, this parameter (in meter) can be used for node simplification."},
    'min_area':            {'type':float,'default':0.001,'hint':"Minimum area (in km^2) a water patch needs to be in order to be included in the mesh as such. Contiguous water patches are merged before area computation."}, 
    'max_area':            {'type':float,'default':200,'hint':"Any water patch larger than this quantity (in km^2) will be masked like the sea."},
    'clean_bad_geometries':{'type':bool,'default':True,'hint':"When set, all OSM geometries are checked for self-intersection and merged between themselves in case of overlapping, allowing (hopefully!) to go around most OSM errors. This is computationally expensive, especially in places where OSM road/water data is detailed, and this is the reason for this switch, but if you are not in a hurry it is probably wise leaving it always activated."},
    'mesh_zl':             {'type':int,'default':19,'values':(16,17,18,19,20),'hint':"The mesh will be preprocessed to accept later any combination of imageries up to and including a zoomlevel equal to mesh_zl. Lower value could save a few tens of thousands triangles, but put a limitation on the maximum allowed imagery zoomlevel."},
    # Mesh
    'curvature_tol':       {'type':float,'default':2,'hint':"This parameter is intrinsically linked the mesh final density. Mesh refinement is mostly based on curvature computations on the elevation data (the exact decision rule can be found in _ triunsuitable() _ in Utils/Triangle4XP.c). A higher curvature tolerance yields fewer triangles."},
    'apt_curv_tol':        {'type':float,'default':0.5,'hint':"If smaller, it supersedes curvature_tol over airports neighbourhoods."},
    'apt_curv_ext':        {'type':float,'default':0.5,'hint':"Extent (in km) around the airports where apt_curv_tol applies."},
    'coast_curv_tol':      {'type':float,'default':1,'hint':"If smaller, it supersedes curvature_tol along the coastline."},
    'coast_curv_ext':      {'type':float,'default':0.5,'hint':"Extent (in km) around the coastline where coast_curv_tol applies."},
    'limit_tris'    :      {'type':int,  'default':0,'hint':"If non zero, upper bound on the number of final triangles in the mesh."},
    'hmin':                {'type':float,'default':0,'hint':"The mesh algorithm will not try to subdivide triangles whose shortest edge is already smaller than hmin (in meters). If hmin is smaller than half of the levation data step size, it will default to it anyhow (its default zero value thus means : as good as the DEM can do)."}, 
    'min_angle':           {'type':float,'default':10,'hint':"The mesh algorithm will try to not have mesh triangles with second smallest angle less than the value (in deg) of min_angle (prior to v1.3 it was the smallest, not second smallest) The goal behind this is to avoid potential artifacts when a triangle vertex is very close the the middle of its facing edge."},
    'sea_smoothing_mode':  {'type':str,  'default':'zero','values':['zero','mean','none'],'hint':"Zero means that all nodes of sea triangles are set to zero elevation. With mean, some kind of smoothing occurs (triangles are levelled one at a time to their mean elevation), None (a value mostly appropriate for DEM resolution of 10m and less), positive altitudes of sea nodes are kept intact, only negative ones are brought back to zero, this avoids to create unrealistic vertical cliffs if the coastline vector data was lower res."},
    'water_smoothing':     {'type':int,  'default':10,'hint':"Number of smoothing passes over all inland water triangles (sequentially set to their mean elevation)."},
    'iterate':             {'type':int,  'default':0,'hint':"Allows to refine a mesh using higher resolution elevation data of local scope only (requires Gdal), typically LIDAR data. Having an iterate number is handy to go backward one step when some choice of parameters needs to be revised. REQUIRES cleaning_level=0."},     
    # Masks
    'mask_zl':             {'type':int,'default':14,'values':(14,15,16),'hint':'The zoomlevel at which the (sea) water masks are built. Masks are used for alpha channel, and this channel usually requires less resolution than the RGB ones, the reason for this (VRAM saving) parameter. If the coastline and elevation data are very detailed, it might be interesting to lift this parameter up so that the masks can reproduce this complexity.'},
    'masks_width':         {'type':list,'default':100,'hint':'Maximum extent of the masks perpendicularly to the coastline (rough definition). NOTE: The value is now in meters, it used to be in ZL14 pixel size in earlier verions, the scale is roughly one to ten between both.'},
    'masking_mode':        {'type':str,'default':'sand','values':['sand','rocks','3steps'],'hint':'A selection of three tentative masking algorithms (still looking for the Holy Grail...). The first two (sand and rocks) requires masks_width to be a single value; the third one (3steps) requires a list of the form [a,b,c] for masks width: "a" is the length in meters of a first transition from plain imagery at the shoreline towards ratio_water transparency, "b" is the second extent zone where transparency level is kept constant equal to ratio_water, and "c" is the last extent where the masks eventually fade to nothing. The transition with rocks is more abrupt than with sand.'},
    'use_masks_for_inland':{'type':bool,'default':False,'hint':'Will use masks for the inland water (lakes, rivers, etc) too, instead of the default constant transparency level determined by ratio_water. This is VRAM expensive and presumably not really worth the price.'},
    'imprint_masks_to_dds':{'type':bool,'default':False,'hint':'Will apply masking directly to dds textures (at the Build Imagery/DSF step) rather than using external png files. This doubles the file size of masked textures (dxt5 vs dxt1) but reduce the overall VRAM footprint (a matter of choice!)'},  
    'masks_use_DEM_too':   {'type':bool,'default':False,'hint':'If you have acces to high resolutions DEMs (really shines with 5m or lower), you can use the elevation in addition to the vector data in order to draw masks with higher precision. If the DEM is not high res, this option will yield unpleasant pixellisation.'},
    'masks_custom_extent': {'type':str,'default':'','hint':'Yet another tentative to draw masks with maximizing the use of the good imagery part. Requires to draw (JOSM) the "good imagery" threshold first, but it could be one order of magnitude faster to do compared to hand tweaking the masks and the imageries one by one.'},
    # DSF/Imagery
    'default_website':     {'type':str,'default':'','hint':''},
    'default_zl':          {'type':int,'default':16,'hint':''},
    'zone_list':           {'type':list,'default':[],'hint':''},
    'cover_airports_with_highres':{'type':str,'default':'False','values':('False','True','ICAO','Existing'),'hint':'When set, textures above airports will be upgraded to a higher zoomlevel, the imagery being the same as the one they would otherwise receive. Can be limited to airports with an ICAO code for tiles with so many airports. Exceptional: use "Existing" to (try to) derive custom zl zones from the textures directory of an existing tile.','short_name':'high_zl_airports'},
    'cover_extent':        {'type':float,'default':1,'hint':'The extent (in km) past the airport boundary taken into account for higher ZL. Note that for VRAM efficiency higher ZL textures are fully used on their whole extent as soon as part of them are needed.'},
    'cover_zl':            {'type':int,'default':18,'hint':'The zoomlevel with which to cover the airports zone when high_zl_airports is set. Note that if the cover_zl is lower than the zoomlevel which would otherwise be applied on a specific zone, the latter is used.'},
    'sea_texture_blur':    {'type':float,'default':0,'hint':'For layers of type "mask" in combined providers imageries, determines the extent (in meters) of the blur radius applied. This allows to smoothen some sea imageries where the wave or reflection pattern was too much present.'},
    'add_low_res_sea_ovl': {'type':bool,'default':False,'hint':'Will add an extra texture layer over the sea (with constant alpha channel given by ratio_water as for inland water), based on a low resolution imagery with global coverage. Masks with their full resolution imagery are still being used when present, the final render is a composite of both. The default imagery with code SEA can be changed as any other imagery defined in the Providers directory, it needs to have a max_zl defined and is used at its max_zl.'},
    'experimental_water':  {'type':int,'default':0,'values':(0,1,2,3),'hint':'If non zero, replaces X-Plane water by a custom normal map over low res ortho-imagery (requires XP11 but turns water rendering more XP10 alike). The value 0 corresponds to legacy X-Plane water, 1 replaces it for inland water only, 2 over sea water only, and 3 over both. Values 2 and 3 should always be used in combination with "imprint_masks_to_dds".\n\nThis experimental feature has two strong downsides: 1) the waves are static rather dynamical (would require a plugin to update the normal_map as X-Plane does) and 2) the wave height is no longer weather dependent. On the other hand, waves might have less repetitive patterns and some blinking in water reflections might be improved too; users are welcome to improve the provided water_normal_map.dds (Gimp can be used to edit the mipmaps individually).'},
    'ratio_water':         {'type':float,'default':0.25,'hint':'Inland water rendering is made of two layers : one bottom layer of "X-Plane water" and one overlay layer of orthophoto with constant level of transparency applied. The parameter ratio_water (values between 0 and 1) determines how much transparency is applied to the orthophoto. At zero, the orthophoto is fully opaque and X-Plane water cannot be seen ; at 1 the orthophoto is fully transparent and only the X-Plane water is seen.'},
    'normal_map_strength': {'type':float,'default':1,'hint':'Orthophotos by essence already contain the part of the shading burned in (here by shading we mean the amount of reflected light in the camera direction as a function of the terrain slope, not the shadows). This option allows to tweak the normal coordinates of the mesh in the DSF to avoid "overshading", but it has side effects on the way X-Plane computes scenery shadows. Used to be 0.3 by default in earlier versions, the default is now 1 which means exact normals.},      '},
    'terrain_casts_shadows':{'type':bool,'default':True,'hint':'If unset, the terrain itself will not cast (but still receive!) shadows. This option is only meaningful if scenery shadows are opted for in the X-Plane graphics settings.','short_name':'terrain_casts_shadow'},
    'overlay_lod':         {'type':float,'default':25000,'hint':'Distance until which overlay imageries (that is orthophotos over water) are drawn. Lower distances have a positive impact on frame rate and VRAM usage, and IFR flyers will probably need a higher value than VFR ones.'},
    'use_decal_on_terrain':{'type':bool,'default':False,'hint':'Terrain files for all but water triangles will contain the maquify_1_green_key.dcl decal directive. The effect is noticeable at very low altitude and helps to overcome the orthophoto blur at such levels. Can be slightly distracting at higher altitude.'},
    # Other
    'custom_dem':          {'type':str,'default':'','hint':'Path to an elevation data file to be used instead of the default Viewfinderpanoramas.org ones (J. de Ferranti). The raster must be in geopgraphical coordinates (EPSG:4326) but the extent need not match the tile boundary (requires Gdal). Regions of the tile that are not covered by the raster are mapped to zero altitude (can be useful for high resolution data over islands in particular).     '},
    'fill_nodata':         {'type':bool,'default':True,'hint':'When set, the no_data values in the raster will be filled by a nearest neighbour algorithm. If unset, they are turned into zero (can be useful for rasters with no_data over the whole oceanic part or partial LIDAR data).'}
}

list_app_vars=['verbosity','cleaning_level','overpass_server_choice',
               'skip_downloads','skip_converts','max_convert_slots','check_tms_response',
               'http_timeout','max_connect_retries','max_baddata_retries','ovl_exclude_pol','ovl_exclude_net','custom_scenery_dir','custom_overlay_src']
gui_app_vars_short=list_app_vars[:-2]
gui_app_vars_long=list_app_vars[-2:]

list_vector_vars=['apt_smoothing_pix','road_level','road_banking_limit','lane_width','max_levelled_segs','water_simplification','min_area','max_area','clean_bad_geometries','mesh_zl']
list_mesh_vars=['curvature_tol','apt_curv_tol','apt_curv_ext','coast_curv_tol','coast_curv_ext','limit_tris','hmin','min_angle','sea_smoothing_mode','water_smoothing','iterate']
list_mask_vars=['mask_zl','masks_width','masking_mode','use_masks_for_inland','imprint_masks_to_dds','masks_use_DEM_too','masks_custom_extent']
list_dsf_vars=['cover_airports_with_highres','cover_extent','cover_zl','ratio_water','overlay_lod','sea_texture_blur','add_low_res_sea_ovl','experimental_water','normal_map_strength','terrain_casts_shadows','use_decal_on_terrain']
list_other_vars=['custom_dem','fill_nodata']
list_tile_vars=list_vector_vars+list_mesh_vars+list_mask_vars+list_dsf_vars+list_other_vars+['default_website','default_zl','zone_list']

list_global_cfg=list_app_vars+list_vector_vars+list_mesh_vars+list_mask_vars+list_dsf_vars

############################################################################################
# Initialization to default values
for var in cfg_vars:
    target=cfg_vars[var]['module']+"."+var if 'module' in cfg_vars[var] else var
    exec(target+"=cfg_vars['"+var+"']['default']")
############################################################################################
# Update from Global Ortho4XP.cfg
try:
    f=open(os.path.join(FNAMES.Ortho4XP_dir,'Ortho4XP.cfg'),'r')
    for line in f.readlines():
        line=line.strip()
        if not line: continue
        if line[0]=='#': continue
        try:
            (var,value)=line.split("=")
            # compatibility with config files from version <= 1.20
            if value and value[0] in ('"',"'"): value=value[1:]
            if value and value[-1] in ('"',"'"): value=value[:-1]
            target=cfg_vars[var]['module']+"."+var if 'module' in cfg_vars[var] else var
            if cfg_vars[var]['type'] in (bool,list):
                cmd=target+"="+value
            else:
                cmd=target+"=cfg_vars['"+var+"']['type'](value)"
            exec(cmd)
        except:
            UI.lvprint(1,"Global config file contains an invalide line:",line)
            pass
    f.close()
except: 
    print("No global config file found. Reverting to default values.") 


############################################################################################
class Tile():

    def __init__(self,lat,lon,custom_build_dir):
        
        self.lat=lat
        self.lon=lon
        self.custom_build_dir=custom_build_dir
        self.grouped=True if (custom_build_dir and custom_build_dir[-1]!='/') else False
        self.build_dir=FNAMES.build_dir(lat,lon,custom_build_dir)
        self.dem=None
        for var in list_tile_vars:
            exec("self."+var+"="+var)
    
    def make_dirs(self):
        if os.path.isdir(self.build_dir):
            if not os.access(self.build_dir,os.W_OK): 
                UI.vprint(0,"OS error: Tile directory",self.build_dir," is write protected.")
                raise Exception 
        else: 
            try: os.makedirs(self.build_dir)
            except:
                UI.vprint(0,"OS error: Cannot create tile directory",self.build_dir," check file permissions.")
                raise Exception

    def read_from_config(self,config_file=None):
        if not config_file: 
            config_file=os.path.join(self.build_dir,"Ortho4XP_"+FNAMES.short_latlon(self.lat,self.lon)+".cfg")
            if not os.path.isfile(config_file):
                config_file=os.path.join(self.build_dir,"Ortho4XP.cfg")
                if not os.path.isfile(config_file):
                    UI.lvprint(0,"CFG error: No config file found for tile",FNAMES.short_latlon(self.lat,self.lon))
                    return 0
        try:
            f=open(config_file,'r')
            for line in f.readlines():
                line=line.strip()
                if not line: continue
                if line[0]=='#': continue
                try:
                    (var,value)=line.split("=")
                    # compatibility with config files from version <= 1.20
                    if value and value[0] in ('"',"'"): value=value[1:]
                    if value and value[-1] in ('"',"'"): value=value[:-1]
                    if cfg_vars[var]['type'] in (bool,list):
                        cmd="self."+var+"="+value
                    else:
                        cmd="self."+var+"=cfg_vars['"+var+"']['type'](value)"
                    exec(cmd)
                except Exception as e:
                    # compatibility with zone_list config files from version <= 1.20
                    if "zone_list.append" in line:
                        try:
                            exec("self."+line)
                        except:
                            pass
                    else:
                        UI.vprint(2,e)
                        pass
            f.close()
            return 1
        except:
            UI.lvprint(0,"CFG error: Could not read config file for tile",FNAMES.short_latlon(self.lat,self.lon))
            return 0


    def write_to_config(self,config_file=None):
        if not config_file: 
            config_file=os.path.join(self.build_dir,"Ortho4XP_"+FNAMES.short_latlon(self.lat,self.lon)+".cfg")
            config_file_bak=config_file+".bak"
        try:
            os.replace(config_file,config_file_bak)
        except:
            pass
        try:
            f=open(config_file,'w')
            for var in list_tile_vars:
                f.write(var+"="+str(eval("self."+var))+"\n")
            f.close()
            return 1
        except Exception as e:
            UI.vprint(2,e)
            UI.lvprint(0,"CFG error: Could not write config file for tile",FNAMES.short_latlon(self.lat,self.lon))
            return 0
        
############################################################################################

############################################################################################
class Ortho4XP_Config(tk.Toplevel):

    def __init__(self,parent):
        
        tk.Toplevel.__init__(self)
        self.option_add("*Font", "TkFixedFont")
        self.title('Ortho4XP Config')
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        if self.winfo_screenheight()>=1024:
            self.pady=5
        else:
            self.pady=1
 

        # Ortho4XP main window reference
        self.parent=parent
                 
        # Frames
        self.main_frame       =  tk.Frame(self, border=4,\
                                 relief=RIDGE,bg='light green')
        self.frame_cfg        = tk.Frame(self.main_frame,border=0,padx=5,pady=self.pady,bg="light green")
        self.frame_dem        = tk.Frame(self.frame_cfg,border=0,padx=0,pady=self.pady,bg="light green")
        self.frame_lastbtn    = tk.Frame(self.main_frame,border=0,padx=5,pady=self.pady,bg="light green")
        # Frames properties
        for j in range(8): self.frame_cfg.columnconfigure(j,weight=1)
        self.frame_cfg.rowconfigure(0,weight=1)
        for j in range(6): self.frame_lastbtn.columnconfigure(j,weight=1)
        self.frame_lastbtn.rowconfigure(0,weight=1)

        # Frames placement
        self.main_frame.grid(row=0,column=0,sticky=N+S+W+E)
        self.frame_cfg.grid(row=0,column=0,pady=10,sticky=N+S+E+W)
        self.frame_lastbtn.grid(row=1,column=0,pady=10,sticky=N+S+E+W)
        
        # Variables and widgets and their placement
        self.v_={}
        for item in cfg_vars: self.v_[item]=tk.StringVar()
        self.entry_={}
        self.folder_icon=tk.PhotoImage(file=os.path.join(FNAMES.Utils_dir,'Folder.gif'))

        col=0
        next_row=0
        for (title,sub_list) in (("Vector data",list_vector_vars),("Mesh",list_mesh_vars),("Masks",list_mask_vars),("DSF/Imagery",list_dsf_vars)):
            tk.Label(self.frame_cfg,text=title,bg='light green',anchor=W,font="TKFixedFont 14").grid(row=0,column=col,columnspan=2,pady=(0,10),sticky=N+S+E+W)
            row=1
            for item in sub_list:
                text=item if 'short_name' not in cfg_vars[item] else cfg_vars[item]['short_name'] 
                ttk.Button(self.frame_cfg,text=text,takefocus=False,command=lambda item=item: self.popup(item,cfg_vars[item]['hint'])).grid(row=row,column=col,padx=2,pady=2,sticky=E+W+N+S)
                if cfg_vars[item]['type']==bool or 'values' in cfg_vars[item]:
                    values=[True,False] if cfg_vars[item]['type']==bool else [str(x) for x in cfg_vars[item]['values']]
                    self.entry_[item]=ttk.Combobox(self.frame_cfg,values=values,textvariable=self.v_[item],width=6,state='readonly',style='O4.TCombobox')
                else:
                    self.entry_[item]=ttk.Entry(self.frame_cfg,textvariable=self.v_[item],width=7) 
                self.entry_[item].grid(row=row,column=col+1,padx=(0,20),pady=2,sticky=N+S+W)
                row+=1
            next_row=max(next_row,row)
            col+=2
        row=next_row
        
        self.frame_dem.grid(row=row,column=0,columnspan=6,sticky=N+S+W+E)
        item='custom_dem'
        ttk.Button(self.frame_dem,text=item,takefocus=False,command=lambda item=item: self.popup(item,cfg_vars[item]['hint'])).grid(row=0,column=0,padx=2,pady=2,sticky=E+W)
        #self.entry_[item]=tk.Entry(self.frame_dem,textvariable=self.v_[item],bg='white',fg='blue',width=80) 
        values=DEM.available_sources[1::2] 
        self.entry_[item]=ttk.Combobox(self.frame_dem,values=values,textvariable=self.v_[item],width=80,style='O4.TCombobox')
        self.entry_[item].grid(row=0,column=1,padx=(2,0),pady=8,sticky=N+S+W+E)
        dem_button=ttk.Button(self.frame_dem,image=self.folder_icon,command=self.choose_dem,style='Flat.TButton')
        dem_button.grid(row=0,column=2, padx=2, pady=0,sticky=W)
        dem_button.bind("<Shift-ButtonPress-1>", self.add_dem)
        item='fill_nodata'
        ttk.Button(self.frame_cfg,text=item,takefocus=False,command=lambda item=item: self.popup(item,cfg_vars[item]['hint'])).grid(row=row,column=6,padx=2,pady=2,sticky=E+W)
        values=[True,False] 
        self.entry_[item]=ttk.Combobox(self.frame_cfg,values=values,textvariable=self.v_[item],width=6,state='readonly',style='O4.TCombobox')
        self.entry_[item].grid(row=row,column=7,padx=2,pady=2,sticky=W)
        row+=1
        
        ttk.Separator(self.frame_cfg,orient=tk.HORIZONTAL).grid(row=row,column=0,columnspan=8,sticky=N+S+E+W); row+=1
        tk.Label(self.frame_cfg,text="Application ",bg='light green',anchor=W,font="TKFixedFont 14").grid(row=row,column=0,columnspan=4,pady=10,sticky=N+S+E+W); row+=1
        
        l=ceil((len(gui_app_vars_short))/4)
        this_row=row
        j=0
        for item in gui_app_vars_short:
            col=2*(j//l)
            row=this_row+j%l
            text=item if 'short_name' not in cfg_vars[item] else cfg_vars[item]['short_name'] 
            ttk.Button(self.frame_cfg,text=text,takefocus=False,command=lambda item=item: self.popup(item,cfg_vars[item]['hint'])).grid(row=row,column=col,padx=2,pady=2,sticky=E+W+N+S)  
            if cfg_vars[item]['type']==bool or 'values' in cfg_vars[item]:
                values=['True','False'] if cfg_vars[item]['type']==bool else [str(x) for x in cfg_vars[item]['values']]
                self.entry_[item]=ttk.Combobox(self.frame_cfg,values=values,textvariable=self.v_[item],width=6,state='readonly',style='O4.TCombobox')
            else:
                self.entry_[item]=tk.Entry(self.frame_cfg,textvariable=self.v_[item],width=7,bg='white',fg='blue') 
            self.entry_[item].grid(row=row,column=col+1,padx=(0,20),pady=2,sticky=N+S+W)
            j+=1
        
        row=this_row+l

        for item in gui_app_vars_long:
            ttk.Button(self.frame_cfg,text=item,takefocus=False,command=lambda item=item: self.popup(item,cfg_vars[item]['hint'])).grid(row=row,column=0,padx=2,pady=2,sticky=E+W+N+S)  
            self.entry_[item]=tk.Entry(self.frame_cfg,textvariable=self.v_[item],bg='white',fg='blue') 
            self.entry_[item].grid(row=row,column=1,columnspan=5,padx=(2,0),pady=2,sticky=N+S+E+W)
            ttk.Button(self.frame_cfg,image=self.folder_icon,command=lambda item=item: self.choose_dir(item),style='Flat.TButton').grid(row=row,column=6, padx=2, pady=0,sticky=N+S+W)
            row+=1


        self.button1= ttk.Button(self.frame_lastbtn, text='Load Tile Cfg ',command= self.load_tile_cfg)
        self.button1.grid(row=0,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button2= ttk.Button(self.frame_lastbtn, text='Write Tile Cfg',command= self.write_tile_cfg)
        self.button2.grid(row=0,column=1,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button3= ttk.Button(self.frame_lastbtn, text='Reload App Cfg',command= self.load_global_cfg)
        self.button3.grid(row=0,column=2,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button4= ttk.Button(self.frame_lastbtn, text='Write App Cfg ',command= self.write_global_cfg)
        self.button4.grid(row=0,column=3,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button5= ttk.Button(self.frame_lastbtn, text='    Apply     ',command= self.apply_changes)
        self.button5.grid(row=0,column=4,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button6= ttk.Button(self.frame_lastbtn, text='     Exit     ',command= self.destroy)
        self.button6.grid(row=0,column=5,padx=5,pady=self.pady,sticky=N+S+E+W)

        # Initialize fields and variables
        self.v_['default_website']=parent.default_website
        self.v_['default_zl']=parent.default_zl
        self.load_interface_from_variables()

         

    def load_interface_from_variables(self):
        for var in cfg_vars:
            target=cfg_vars[var]['module']+"."+var if 'module' in cfg_vars[var] else var
            self.v_[var].set(str(eval(target)))

    def choose_dem(self):
        tmp=filedialog.askopenfilename(parent=self,title='Choose DEM file',filetypes=[('DEM files',('.tif','.hgt','.raw','.img')),('all files','.*')])
        if tmp: self.v_['custom_dem'].set(str(tmp))
    
    def add_dem(self,event):
        tmp=filedialog.askopenfilename(parent=self,title='Choose DEM file',filetypes=[('DEM files',('.tif','.hgt','.raw','.img')),('all files','.*')])
        if tmp: 
            if not  self.v_['custom_dem'].get():
                self.v_['custom_dem'].set(str(tmp))
            else:
                self.v_['custom_dem'].set(self.v_['custom_dem'].get()+";"+str(tmp))
            
    def choose_dir(self,item):
        tmp=filedialog.askdirectory(parent=self)
        if tmp: self.v_[item].set(str(tmp))
    
    def load_tile_cfg(self):
        zone_list=[]
        try: (lat,lon)=self.parent.get_lat_lon()
        except: return 0
        custom_build_dir=self.parent.custom_build_dir_entry.get()
        build_dir=FNAMES.build_dir(lat,lon,custom_build_dir)
        try: 
            f=open(os.path.join(build_dir,'Ortho4XP_'+FNAMES.short_latlon(lat,lon)+'.cfg'),'r')
        except:
            try:
                f=open(os.path.join(build_dir,'Ortho4XP.cfg'),'r')
            except:
                self.popup("ERROR","No config file found in "+str(build_dir))
                return 0
        for line in f.readlines():
            line=line.strip()
            if not line: continue
            if line[0]=='#': continue
            try:
                (var,value)=line.split("=")
                # compatibility with config files from version <= 1.20
                if value and value[0] in ('"',"'"): value=value[1:]
                if value and value[-1] in ('"',"'"): value=value[:-1]
                self.v_[var].set(value)
            except Exception as e:
                # compatibility with zone_list config files from version <= 1.20
                    if "zone_list.append" in line:
                        try:
                            exec(line)
                        except Exception as e:
                            print(e) 
                            pass
                    else:
                        UI.vprint(2,e)
                        pass
        if not self.v_['zone_list'].get(): self.v_['zone_list'].set(str(zone_list))        
        f.close()

    def write_tile_cfg(self):
        try: (lat,lon)=self.parent.get_lat_lon()
        except: return 0
        custom_build_dir=self.parent.custom_build_dir_entry.get()
        build_dir=FNAMES.build_dir(lat,lon,custom_build_dir)
        try:
            if not os.path.isdir(build_dir): os.makedirs(build_dir)
            f=open(os.path.join(build_dir,'Ortho4XP_'+FNAMES.short_latlon(lat,lon)+'.cfg'),'w')
        except:
            self.popup("ERROR","Cannot write into "+str(build_dir))
            return 0
        self.v_['zone_list'].set(str(eval('zone_list')))    
        for var in list_tile_vars:
            f.write(var+"="+self.v_[var].get()+'\n')
        f.close()
        return
      
    def load_global_cfg(self):
        try: f=open(os.path.join(FNAMES.Ortho4XP_dir,'Ortho4XP.cfg'),'r')
        except: return 0
        for line in f.readlines():
            line=line.strip()
            if not line: continue
            if line[0]=='#': continue
            try:
                (var,value)=line.split("=")
                # compatibility with config files from version <= 1.20
                if value and value[0] in ('"',"'"): value=value[1:]
                if value and value[-1] in ('"',"'"): value=value[:-1]
                self.v_[var].set(value)
            except:
                pass
        f.close()
        return
    
    def write_global_cfg(self):
        old_cfg=os.path.join(FNAMES.Ortho4XP_dir,'Ortho4XP.cfg.bak')
        new_cfg=os.path.join(FNAMES.Ortho4XP_dir,'Ortho4XP.cfg')
        if os.path.isfile(old_cfg):
            try: os.remove(old_cfg) 
            except: pass
        try: os.rename(new_cfg,old_cfg)
        except: pass
        try: f=open(new_cfg,'w')
        except: return 0
        for var in list_global_cfg:
            f.write(var+"="+self.v_[var].get()+'\n')
        f.close()
        return

    def apply_changes(self):
        errors=[]
        for var in list_tile_vars+list_app_vars:
            try:
                target=cfg_vars[var]['module']+"."+var if 'module' in cfg_vars[var] else "globals()['"+var+"']"
                if cfg_vars[var]['type'] in (bool,list):
                    cmd=target+"="+self.v_[var].get()
                else:
                    cmd=target+"=cfg_vars['"+var+"']['type'](self.v_['"+var+"'].get())"
                exec(cmd)
            except:
                target=cfg_vars[var]['module']+"."+var if 'module' in cfg_vars[var] else "globals()['"+var+"']"
                self.v_[var].set(str(cfg_vars[var]['default']))
                exec(target+"=cfg_vars['"+var+"']['type'](cfg_vars['"+var+"']['default'])")
                errors.append(var)
        if errors:
            error_text="The following variables had wrong type\nand were reset to their default value!\n\n* "+'\n* '.join(errors) 
            self.popup("ERROR",error_text)

    def popup(self,header,input_text):
        self.popupwindow = tk.Toplevel()
        self.popupwindow.wm_title("Hint!")
        ttk.Label(self.popupwindow, text=header+" :",anchor=W,font="TkBoldFont").pack(side="top", fill="x", padx=5,pady=3)
        ttk.Label(self.popupwindow, text=input_text,wraplength=600,anchor=W).pack(side="top", fill="x", padx=5,pady=0)
        ttk.Button(self.popupwindow, text="Ok", command = self.popupwindow.destroy).pack(pady=5)
        return
    
    


