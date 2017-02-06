#!/usr/bin/env python3                                                       
##############################################################################
# Ortho4XP : A base mesh creation tool for the X-Plane 10 flight simulator.  #
# Version  : 1.15 released July 9th 2016                                     #
# Copyright 2016 Oscar Pilote                                                #
# Thanks to all that have contributed to improvement of the code.            #
##############################################################################
#                                                                            #
#   LEGAL NOTICE :                                                           #
#                                                                            #
#   This program is free software: you can redistribute it and/or modify     #
#   it under the terms of the GNU General Public License as published by     #
#   the Free Software Foundation, either version 3 of the License, or        #
#   (at your option) any later version.                                      #
#                                                                            #
#   This program is distributed in the hope that it will be useful,          #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of           #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
#   GNU General Public License for more details.                             #
#                                                                            #
#   You should have received a copy of the GNU General Public License        #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.    #
#                                                                            #
##############################################################################

from math import *
import array,numpy
import os,sys,threading,subprocess,time,gc
import overpy
import requests
import random
import pickle
import collections
import struct
import hashlib
from tkinter import *               # GUI
from tkinter import filedialog
import tkinter.ttk as ttk           # Themed Widgets
from PIL import Image, ImageDraw, ImageFilter, ImageTk
Image.MAX_IMAGE_PIXELS = 1000000000 # Not a decompression bomb attack!   
import subprocess 
import shlex

try:
    import gdal
    gdal_loaded = True
except:
    gdal_loaded = False

try:
    exec(open('Carnet_d_adresses.py').read())
except:
    print("The file Carnet_d_adresses.py does not follow the syntactic rules.")
    sys.exit()

# The following parameters are put here rather than in the config file 
# because most of users will never modify them.

Ortho4XP_dir        = '.'
meshzl              = 19    # The maximum ZL which the mesh will support
hmin                = 20    # Smallest triangle side-length
hmax                = 2000  # Largest triangle side-length
smallest_angle      = 5     # called min_angle in the graphical interface
water_smoothing     = 2     # increase if you find the rivers are not smooth enough
tile_has_water_airport=False# Put to True if an airport with a water boundary does not turn flat correctly
do_not_flatten_these_list=[]# Those airport won't be flattened, icao code needed, like = ['LFPG','LFMN'] 
masks_width         = 16    # default one
sea_texture_params  = []    # e.g. ['GO2',16] will use this provider and ZL for the triangles over the sea
keep_old_pre_mask   = False
complex_masks       = False # is set to True the build_masks process will be longer (because mesh from all nearby tiles will be used), but will not "suffer" from boundary effects
use_masks_for_inland= False # if you want inland water to be treated like sea water (transparency based on a mask rather than fixed)
use_additional_water_shader = False # remainder of a test, which was not that succesful
use_decal_on_terrain = False # if you want to use decal on top of the orthophoto, they can look good at small altitude
dds_or_png          = 'dds'
full_color_correction={}
contrast_adjust={}
brightness_adjust={}
saturation_adjust={}
check_tms_response  = False # Available as a checkbox in the interface, with it set to True some providers will lead to a dead loop of missed requests if data is not available. On the other hand with it set to False you may end up some times with a few corrupted textures with some white squares.
use_bing_for_non_existent_data = False # when using providers with local coverage only, if you ask for a zone not covered then Bing will be used there instead
tricky_provider_hack= 70000 # The minimum size a wms2048 image should be to be accepted (trying to avoid missed cached with white squares) 
wms_timeout         = 60
max_convert_slots   = 4     # Trying to use multi_core to convert jpegs into dds, adapt to your cpu capabilities
max_montage_slots   = 4     # Same for montage
pools_max_points    = 65536 # do not change this !
normal_map_strength = 0.3   # shading due to slope is normally already present in an orthophoto, so 0 is orthophoto shade only and 1 is full additional shade
verbose_output      = True
shutdown_timer      = 60    # Time in seconds to close program / shutdown computer after completition
shutd_msg_interval  = 15    # Shutdown message display interval

# Will be used as global variables
download_to_do_list=[]
montage_to_do_list=[]
convert_to_do_list=[]
busy_slots_mont=0
busy_slots_conv=0

if 'dar' in sys.platform:
    dir_sep         = '/'
    Triangle4XP_cmd = Ortho4XP_dir+"/Utils/Triangle4XP.app "
    copy_cmd        = "cp "
    delete_cmd      = "rm "
    rename_cmd      = "mv "
    unzip_cmd       = "7z "
    montage_cmd     = "montage "  
    convert_cmd     = "convert " 
    convert_cmd_bis = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"nvcompress"+dir_sep+"nvcompress-mac-nocuda.app -bc1 " 
    gimp_cmd        = "gimp "
    showme_cmd      = Ortho4XP_dir+"/Utils/showme.app "
    devnull_rdir    = " >/dev/null 2>&1"
    use_gimp        = True
    # --> mth
    shutdown_cmd    = 'sudo shutdown -h now'
    # <-- mth
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/DSFTool.app')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/Triangle4XP.app')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/nvcompress/nvcompress-mac-nocuda.app')


elif 'win' in sys.platform: 
    dir_sep         = '\\'
    Triangle4XP_cmd = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"Triangle4XP.exe "
    copy_cmd        = "copy "
    delete_cmd      = "del "	
    rename_cmd      = "move "
    unzip_cmd       = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"7z.exe "
    montage_cmd     = "montage "  
    convert_cmd     = "convert " 
    convert_cmd_bis = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"nvcompress"+dir_sep+"nvcompress.exe -bc1 " 
    gimp_cmd        = "c:\\Program Files\\GIMP 2\\bin\\gimp-console-2.8.exe "
    showme_cmd      = Ortho4XP_dir+"/Utils/showme.exe "
    devnull_rdir    = " > nul  2>&1"
    use_gimp        = True
     # --> mth
    shutdown_cmd    = 'shutdown /s /f /t 0'
    # <-- mth

else:
    dir_sep         = '/'
    Triangle4XP_cmd = Ortho4XP_dir+"/Utils/Triangle4XP "
    delete_cmd      = "rm "
    copy_cmd        = "cp "
    rename_cmd      = "mv "
    unzip_cmd       = "7z "
    montage_cmd     = "montage "  
    convert_cmd     = "convert " 
    convert_cmd_bis     = "nvcompress -fast -bc1a " 
    gimp_cmd        = "gimp "
    showme_cmd      = Ortho4XP_dir+"/Utils/showme "
    devnull_rdir    = " >/dev/null 2>&1 "
    use_gimp        = True
    # --> mth
    shutdown_cmd    = 'sudo shutdown -h now'
    # <-- mth
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/DSFTool')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/Triangle4XP')

##############################################################################

dico_edge_markers   = {'outer':'1','inner':'1','coastline':'2',\
                       'tileboundary':'3','orthogrid':'3',\
                       'airport':'4','runway':'5','patch':'6'}
dico_tri_markers    = {'water':'1','sea':'2','sea_equiv':'3'}  

##############################################################################
# Minimalist error messages.                                                 #
##############################################################################
##############################################################################
def usage(reason,do_i_quit=True):
    if reason=='config':
        print("The file Ortho4XP.cfg was not found or does not follow the "+\
              "syntactic rules.")
    elif reason=='command_line':
        print("The command line does not follow the syntactic rules.")
    elif reason=='osm_tags':
        print("I had a problem downloadings data from Openstreetmap.\n"+\
              "Your connection may be unavailable or the Overpass server\n"+\
              "may be unreachable.") 
    elif reason=='dem_files':
        print("I could not fin the elevation data file, or it was broken.") 
    elif reason=='adresses':
        print("The file Carnet_d_adresses.py does not follow the syntactic"+\
              " rules.")
    elif reason=='crash':
        print("The mesh algorithm Triangle4XP has encountered a problem and"+\
              " had to stop.")
    elif reason=='inprogress':
        print("This functionality is not yet supported.")
    if do_i_quit==True:
            sys.exit()
    return
##############################################################################

##############################################################################
# Téléchargement de tags Openstreetmap via l'api Overpass.
##############################################################################
def get_osm_data(lat0,lat1,lon0,lon1,tag):                                   
    api=overpy.Overpass()
    succeeded = False 
    while succeeded == False:
        try:
            result=api.query('('+tag+'('+str(lat0)+','+str(lon0)+','+\
                 str(lat1)+','+str(lon1)+');>>;);out;')
            succeeded = True
        except:
            print("Server overloaded or network not available, "
                  "will try again in 3 sec.") 
            time.sleep(3)
    return result
##############################################################################

##############################################################################
# Construction du fichier .poly décrivant toutes les données vectorielles
# a intégrer au maillage (frontières sol/eau et aéroports).
##############################################################################
def build_poly_file(lat0,lon0,option,build_dir): 
    t1=time.time()
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
    strlat='{:+.0f}'.format(lat0).zfill(3)
    strlon='{:+.0f}'.format(lon0).zfill(4)
    poly_file     =  build_dir+dir_sep+'Data'+strlat+strlon+'.poly'
    airport_file  =  build_dir+dir_sep+'Data'+strlat+strlon+'.apt'
    patch_dir     =  Ortho4XP_dir+dir_sep+'Patches'+dir_sep+strlat+strlon
    dico_nodes={}
    dico_edges={}
    # seeds will serve to populate corresponding regions with the appropriate 
    # marker 
    water_seeds=[]
    sea_seeds=[]
    sea_equiv_seeds=[]
    flat_airport_seeds=[]
    flat_patch_seeds=[]
    sloped_patch_seeds=[]
    init_nodes=0
    tags=[]
    if option==4:    # Testing airports
        orthogrid=False
        print("-> Downloading airport data from OpenstreetMap.")
        tags.append('node["aeroway"="aerodrome"]')                                         
        tags.append('way["aeroway"="aerodrome"]')                                         
        tags.append('rel["aeroway"="aerodrome"]')                                         
        tags.append('way["aeroway"="heliport"]')                                         
    elif option==2:  # Orthophoto only for inland water
        orthogrid=True
        print("-> Downloading airport and water/ground boundary data on Openstreetmap")
        tags.append('way["aeroway"="aerodrome"]')                                         
        tags.append('rel["aeroway"="aerodrome"]')                                         
        tags.append('way["aeroway"="heliport"]')                                         
        tags.append('way["natural"="coastline"]')
    else:  # Mixed
        orthogrid=True
        print("-> Downloading airport and water/ground boundary data on Openstreetmap")
        tags.append('way["aeroway"="aerodrome"]')                                         
        tags.append('rel["aeroway"="aerodrome"]')                                         
        tags.append('way["aeroway"="heliport"]')                                         
        tags.append('way["natural"="water"]')                                         
        tags.append('rel["natural"="water"]')                                         
        tags.append('way["waterway"="riverbank"]')                                    
        tags.append('rel["waterway"="riverbank"]')                                    
        tags.append('way["natural"="coastline"]')
        tags.append('way["waterway"="dock"]')
    try:
        application.red_flag.set(0)
    except:
        pass
    for tag in tags:
        try:
            if application.red_flag.get()==1:
                print("\nOSM download process interrupted.")
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
        except:
            pass
        subtags=tag.split('"')
        osmfilename=build_dir+dir_sep+"OSM_"+subtags[0][0:-1]+'_'+\
                subtags[1]+'_'+subtags[3]
        if os.path.isfile(osmfilename):
            osmfile=open(osmfilename,'rb')
            result=pickle.load(osmfile)
            nbr_nodes=len(result.nodes)
            if nbr_nodes>0:
                strtmp=str(nbr_nodes)+" nodes."
            else:
                strtmp="no node."
            print("     -> "+tag+" recycled from previous data : "\
                    +strtmp)
        else:
            result=get_osm_data(lat0,lat0+1,lon0,lon0+1,tag)
            osmfile=open(osmfilename,'wb')
            pickle.dump(result,osmfile)
            nbr_nodes=len(result.nodes)
            if nbr_nodes>0:
                strtmp=str(nbr_nodes)+" nodes."
            else:
                strtmp="no node."
            print('     -> '+tag+ ' downloaded without error : '+strtmp)
        osmfile.close()
        # we shall treat osm data differently depending on tag :
        # coastline data are non closed ways, and relations (multipolygons)
        # are sometimes splitted (see below)
        if tag=='node["aeroway"="aerodrome"]':
            for node in result.nodes:
                if ('icao' in node.tags) and ('name' in node.tags):
                    try:
                        print("       * "+node.tags['icao']+" "+node.tags['name'])
                    except:
                        print("       * "+node.tags['icao'])
                elif ('name' in node.tags):
                    try:
                        print("       *       "+node.tags['name'])
                    except:
                        pass
                elif ('icao' in node.tags):
                    print("       * "+node.tags['icao'])
        elif tag=='way["aeroway"="aerodrome"]' or tag=='way["aeroway"="heliport"]':
            sloped_airports_list=[]
            if os.path.exists(patch_dir):
                for pfilename in os.listdir(patch_dir):
                    if pfilename[-10:] == '.patch.osm':
                        sloped_airports_list.append(pfilename[:4])
            for way in result.ways:
                # we only treat closed ways, non closed should not exist in 
                # osm ways (but a few sometimes do!)
                if strcode(way.nodes[0]) == strcode(way.nodes[-1]):
                    signed_area=area(way)
                    # Keep only sufficiently large water pieces. 1 deg^2 is
                    # very roughly equal to 10000 km^2
                    if signed_area<0:
                        side='left'
                    else:
                        side='right'
                    keep_that_one=True
                    if ('icao' in way.tags):
                        if (way.tags['icao'] in sloped_airports_list) or (way.tags['icao'] in do_not_flatten_these_list):
                            print("          I will not flatten "+way.tags['icao']+ " airport.")	
                            keep_that_one=False
                    if ('icao' in way.tags) and ('name' in way.tags):
                        print("       * "+way.tags['icao']+" "+way.tags['name'])
                    elif ('icao' in way.tags):
                        print("       * "+way.tags['icao'])
                    elif 'name' in way.tags:
                        print("       *      "+way.tags['name'])
                    else:
                        print("       * lat="+str(way.nodes[0].lat)+" lon="+str(way.nodes[0].lon))
                    if ('ele' in way.tags):
                        altitude=way.tags['ele']
                    else:
                        altitude='unknown'
                    if keep_that_one==True:
                        keep_way(way,lat0,lon0,1,'airport',dico_nodes,\
                                dico_edges)
                        flat_airport_seeds.append([way,\
                                pick_point(way,side,lat0,lon0),altitude])
                else:
                    print("One or the airports within the tile is not correctly closed \n"+\
                          "on Openstreetmap !")
        elif tag=='rel["aeroway"="aerodrome"]':
            sloped_airports_list=[]
            if os.path.exists(patch_dir):
                for pfilename in os.listdir(patch_dir):
                    if pfilename[-10:] == '.patch.osm':
                        sloped_airports_list.append(pfilename[:4])
            for rel in result.relations:
                keep_that_one=True
                if ('icao' in rel.tags):
                    if rel.tags['icao'] in sloped_airports_list or (rel.tags['icao'] in do_not_flatten_these_list):
                        keep_that_one=False
                if ('icao' in rel.tags) and ('name' in rel.tags):
                    print("       * "+rel.tags['icao']+" "+rel.tags['name'])
                elif ('icao' in rel.tags):
                    print("       * "+rel.tags['icao'])
                elif 'name' in rel.tags:
                        print("       *      "+rel.tags['name'])
                if ('ele' in rel.tags):
                    altitude=rel.tags['ele']
                else:
                    altitude='unknown'
                if keep_that_one==False:
                    continue
                index=0
                while index < len(rel.members):
                    role=rel.members[index].role
                    if role not in ['outer','inner']:
                        #print("strange role :"+str(role))
                        index+=1
                        break
                    loop_structure=find_next_loop(rel,index,result)
                    if loop_structure=='None':
                        # This relation of OSM data was too poor, 
                        index+=1
                        break
                    if role=='inner':
                        new_index=index
                        for data in loop_structure:
                            new_index=max(new_index,data[0])
                        index=new_index+1
                        continue
                    total_area=0
                    for data in loop_structure:
                        way=member_to_way(rel.members[data[0]],result)
                        sign=data[1]
                        total_area+=area(way)*sign 
                    for data in loop_structure:
                        way=member_to_way(rel.members[data[0]],result)
                        sign=data[1]
                        keep_way(way,lat0,lon0,sign,'airport',dico_nodes,\
                                        dico_edges)
                    data=loop_structure[0]
                    way=member_to_way(rel.members[data[0]],result)
                    sign=data[1]
                    if total_area*sign>0:
                        side='right'
                    else:
                        side='left'
                    flat_airport_seeds.append([way,\
                                pick_point(way,side,lat0,lon0),altitude])
                    new_index=index
                    for data in loop_structure:
                        new_index=max(new_index,data[0])
                    index=new_index+1
        elif 'way["natural"="coastline"]' in tag:
            #continue
            total_sea_seeds=0
            for way in result.ways:
                # Openstreetmap ask that sea is to the right of oriented
                # coastline. We trust OSM contributors...
                if strcode(way.nodes[0])!=strcode(way.nodes[-1]):
                    if (lat0>=40 and lat0<=49 and lon0>=-93 and lon0<=-76):
                        sea_equiv_seeds+=pick_points_safe(way,'right',lat0,lon0)
                    else:
                        sea_seeds+=pick_points_safe(way,'right',lat0,lon0)
                    total_sea_seeds+=1
                keep_way(way,lat0,lon0,1,'coastline',dico_nodes,dico_edges)
            if total_sea_seeds<=3:
                for way in result.ways:
                    if strcode(way.nodes[0])==strcode(way.nodes[-1]):
                        if (lat0>=40 and lat0<=49 and lon0>=-93 and lon0<=-76):
                            sea_equiv_seeds+=pick_points_safe(way,'right',lat0,lon0)
                        else:
                            sea_seeds+=pick_points_safe(way,'right',lat0,lon0)
        elif tag in ['way["natural"="water"]',\
                   'way["waterway"="riverbank"]',\
                   'way["waterway"="dock"]']:
            #continue
            for way in result.ways:
                # we only treat closed ways, non closed should not exist in 
                # osm ways (but a few sometimes do!)
                try:
                    check_server=strcode(way.nodes[0])
                    check_server=strcode(way.nodes[-1])
                except:
                    print("\nThe overpass OSM server did not fulfilled our request, it is probably down.")
                    print("\nFailure.")        
                    print('_____________________________________________________________'+\
                            '____________________________________')
                    return
                if strcode(way.nodes[0]) == strcode(way.nodes[-1]) and \
                        touches_region(way,lat0,lat0+1,lon0,lon0+1)==True:
                    signed_area=area(way)
                    # Keep only sufficiently large water pieces. 1 deg^2 is
                    # very roughly equal to 10000 km^2
                    if abs(signed_area) >= min_area/10000.0: 
                    #if abs(signed_area) >= 0.04/10000.0 and abs(signed_area)<=0.06/10000.0: 
                        if signed_area<0:
                            side='left'
                        else:
                            side='right'
                        keep_way(way,lat0,lon0,1,'outer',dico_nodes,\
                                dico_edges)
                        point=pick_point(way,side,lat0,lon0)
                        polygon=[]
                        for node in way.nodes:
                            polygon+=[float(node.lon),float(node.lat)]
                        if point_in_polygon(point,polygon):
                            sea_way=False
                            try:
                                if way.tags['name'] in sea_equiv:
                                    sea_way=True
                            except:
                                pass    
                            if sea_way!=True:
                                water_seeds.append(point)
                            else:
                                sea_seeds.append(point)
                        else:
                            pass
                            #print("Point outside : "+str(point))
        elif 'rel[' in tag:
            for rel in result.relations:
                # Members of rel may not be closed and the 
                # corresponding polygon is split across (hopefully) 
                # consecutive members. For that reason
                # we need an extra bit of work to guess how to
                # rebuild closed loops of water.
                sea_rel=False
                try:
                    if rel.tags['name'] in sea_equiv:
                        print("sea_equiv found :",rel.tags['name'])
                        sea_rel=True
                except:
                    pass
                index=0
                while index < len(rel.members):
                    role=rel.members[index].role
                    if role not in ['outer','inner']:
                        #print("strange role :"+str(role))
                        index+=1
                        break
                    loop_structure=find_next_loop(rel,index,result)
                    if loop_structure=='None':
                        # This relation of OSM data was too poor, 
                        # (occurs, but rarely). 
                        # print("Aie...")
                        index+=1
                        break
                    total_area=0
                    keep_loop=False
                    for data in loop_structure:
                        way=member_to_way(rel.members[data[0]],result)
                        if touches_region(way,lat0,lat0+1,lon0,lon0+1)==True:
                            keep_loop=True
                        sign=data[1]
                        total_area+=area(way)*sign 
                    if ((role=='inner') or \
                            (abs(total_area) >= min_area/10000.0)) \
                            and (keep_loop==True):
                    #if (abs(total_area) >= 0.058/10000.0) and  (abs(total_area) <= 0.059/10000.0) and \
                    #        (keep_loop==True):
                        for data in loop_structure:
                            way=member_to_way(rel.members[data[0]],result)
                            sign=data[1]
                            if touches_region(way,lat0,lat0+1,lon0,lon0+1)\
                                    ==True:
                                keep_way(way,lat0,lon0,sign,role,dico_nodes,\
                                        dico_edges)
                                if role=='outer':
                                    #if abs(total_area)*10000>0.001 and abs(total_area)*10000<0.01:
                                    #    print(way.nodes[0].lat,way.nodes[0].lon)
                                    if total_area*sign>0:
                                        side='right'
                                    else:
                                        side='left'
                                    if sea_rel == True:
                                        #pass
                                        sea_equiv_seeds.append(pick_point(\
                                                way,side,lat0,lon0))
                                    else:
                                        #pass
                                        #print(pick_point(way,side,lat0,lon0))
                                        water_seeds.append(pick_point(\
                                                way,side,lat0,lon0))
                    new_index=index
                    for data in loop_structure:
                        new_index=max(new_index,data[0])
                    index=new_index+1
    treated_nodes=len(dico_nodes)-init_nodes
    init_nodes=len(dico_nodes)
    if treated_nodes>0:
        strtmp=str(treated_nodes)+" new nodes."
    else:
        strtmp="no new node."
    print("   -> process of the associated data completed : "+strtmp)
    print("-> Cutting off of too long edges,")
    dico_edges_tmp={}
    for edge in dico_edges:
        [initpt,endpt]=edge.split('|')
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        length=sqrt((xi-xf)*(xi-xf)+(yi-yf)*(yi-yf))
        pieces=ceil(length*1000)
        if pieces == 1:
            dico_edges_tmp[edge]=dico_edges[edge]
        else:
            coordlist=[]
            for k in range(1,pieces):
                xk=((pieces-k)/pieces)*xi+(k/pieces)*xf
                yk=((pieces-k)/pieces)*yi+(k/pieces)*yf
                coordlist.append([xk,yk])
                keep_node_xy(xk,yk,lat0,lon0,dico_nodes)
            keep_edge_str_tmp(initpt,strxy(coordlist[0][0],coordlist[0][1],\
                    lat0,lon0),dico_edges[edge],dico_edges_tmp)
            for k in range(1,pieces-1):
                keep_edge_str_tmp(strxy(coordlist[k-1][0],coordlist[k-1][1],\
                        lat0,lon0),strxy(coordlist[k][0],coordlist[k][1],\
                        lat0,lon0),dico_edges[edge],dico_edges_tmp)
            keep_edge_str_tmp(strxy(coordlist[pieces-2][0],\
                    coordlist[pieces-2][1],lat0,lon0),endpt,dico_edges[edge],\
                        dico_edges_tmp)
    dico_edges=dico_edges_tmp
    print("-> Adding patch data for the mesh, ")
    if os.path.exists(patch_dir):
        patchlist=os.listdir(patch_dir)
    else:
        patchlist=[]
    for pfilename in patchlist:
        if pfilename[-10:] != '.patch.osm':
            continue
        pfile=open(patch_dir+dir_sep+pfilename,"r")
        secondline=pfile.readline()
        secondline=pfile.readline()
        print("     "+pfilename)
        finished_with_nodes=False
        started_with_nodes=False
        nodes_codes={}
        while not finished_with_nodes==True:
            items=pfile.readline().split()
            if '<node' in items:
                started_with_nodes=True
                for item in items:
                    if 'id=' in item:
                        id=item[3:]
                    elif 'lat=' in item:
                        slat=item[5:-1]
                    elif 'lon=' in item:
                        slon=item[5:-1]
                dico_nodes[slat+'_'+slon]=[float(slon)-lon0,float(slat)-lat0]
                nodes_codes[id]=slat+'_'+slon
            elif started_with_nodes==True:
                finished_with_nodes=True
        finished_with_ways=False
        while finished_with_ways != True:
            newwaycodes=[]
            finished_with_newway=False
            flat_patch=False
            sloped_patch=False
            way_profile='atanh'
            way_steepness='3.5'
            way_cell_size='5'
            while finished_with_newway!=True:
                line=pfile.readline().split()
                if '<nd' in line:
                    newnodeid=line[1][4:]
                    newwaycodes.append(nodes_codes[newnodeid])
                else:
                    if "k='altitude'" in line:
                        flat_patch=True
                        if line[2][3:-1]=='mean':
                            way_altitude='mean'
                        else:
                            way_altitude=float(line[2][3:-1])
                    elif "k='altitude_high'" in line:
                        sloped_patch=True
                        way_altitude_high=float(line[2][3:-1]) 
                    elif "k='altitude_low'" in line:
                        way_altitude_low=float(line[2][3:-1])
                    elif "k='profile'" in line:
                        way_profile=line[2][3:-1]
                    elif "k='steepness'" in line:
                        way_steepness=line[2][3:-1]
                    elif "k='cell_size'" in line:
                        way_cell_size=line[2][3:-1]
                    elif '</way>' in line:
                        finished_with_newway=True
                    else:
                        pass
            if flat_patch==True:
                seed=keep_patch(newwaycodes,dico_nodes,dico_edges)
                flat_patch_seeds.append([seed,way_altitude,newwaycodes])
            elif sloped_patch==True:
                [seed,xi,yi,xf,yf]=keep_sloped_patch(newwaycodes,\
                        float(way_cell_size)/100000,dico_nodes,\
                        dico_edges,lat0,lon0)
                sloped_patch_seeds.append([seed,xi,yi,xf,yf,\
                        way_altitude_high,way_altitude_low,\
                        way_profile,way_steepness,way_cell_size])
            else:
                seed=keep_patch(newwaycodes,dico_nodes,dico_edges)
            line=pfile.readline().split()
            if '</osm>' in line:
                finished_with_ways=True
        # Now we need to sanitize edges because the cuts which we made
        # on the short sides of sloped patches may be encroached with
        # sides of flat patches.
        pfile.seek(0)
        finished_with_nodes=False
        started_with_nodes=False
        while not finished_with_nodes==True:
            items=pfile.readline().split()
            if '<node' in items:
                started_with_nodes=True
            elif started_with_nodes==True:
                finished_with_nodes=True
        finished_with_ways=False
        while finished_with_ways != True:
            newwaycodes=[]
            finished_with_newway=False
            sloped_patch=False
            while finished_with_newway!=True:
                line=pfile.readline().split()
                if '<nd' in line:
                    newnodeid=line[1][4:]
                    newwaycodes.append(nodes_codes[newnodeid])
                else:
                    if "k='altitude_high'" in line:
                        sloped_patch=True
                    elif '</way>' in line:
                        finished_with_newway=True
                    else:
                        pass
            if sloped_patch==True:
                dico_edges.pop(newwaycodes[0]+'|'+newwaycodes[3],None)
                dico_edges.pop(newwaycodes[3]+'|'+newwaycodes[0],None)
                dico_edges.pop(newwaycodes[1]+'|'+newwaycodes[2],None)
                dico_edges.pop(newwaycodes[2]+'|'+newwaycodes[1],None)
            line=pfile.readline().split()
            if '</osm>' in line:
                finished_with_ways=True
        pfile.close()
    print("-> Adding of edges related to the orthophoto grid and computation of\n"
          "     their intersections with OSM edges,")
    dico_edges=cut_edges_with_grid(lat0,lon0,dico_nodes,dico_edges,orthogrid)
    print("     Removal of obsolete edges,")
    dico_edges_tmp={}
    for edge in dico_edges:
        [initpt,endpt]=edge.split('|')
        if initpt != endpt:
            dico_edges_tmp[edge]=dico_edges[edge]
        #else:
        #    print("one removed edge : "+str(initpt))
    dico_edges=dico_edges_tmp
    print("     Removal of obsolete nodes,")
    final_nodes={}
    for edge in dico_edges:
        #print(edge)
        [initpt,endpt]=edge.split('|')
        final_nodes[initpt]=dico_nodes[initpt]
        final_nodes[endpt]=dico_nodes[endpt]
    dico_nodes=final_nodes
    print("-> Transcription of the updated data to the file "+poly_file)
    total_nodes=len(dico_nodes)
    f=open(poly_file,'w')
    f.write(str(total_nodes)+' 2 0 0\n')
    dico_node_pos={}
    idx=1
    for key in dico_nodes:
        dico_node_pos[key]=idx
        f.write(str(idx)+' '+str(dico_nodes[key][0])+' '+\
          str(dico_nodes[key][1])+'\n')        
        idx+=1
    f.write('\n')
    idx=1
    total_edges=len(dico_edges)
    f.write(str(total_edges)+' 1\n')
    for edge in dico_edges:
        [code1,code2]=edge.split('|')
        idx1=dico_node_pos[code1]
        idx2=dico_node_pos[code2]
        f.write(str(idx)+' '+str(idx1)+' '+str(idx2)+' '+\
                dico_edge_markers[dico_edges[edge]]+'\n')
        idx+=1
    f.write('\n0\n')
    total_seeds=len(water_seeds)+len(sea_seeds)+len(sea_equiv_seeds)+\
                len(flat_airport_seeds)+len(flat_patch_seeds)+\
                len(sloped_patch_seeds)
    if total_seeds==0:
        water_seeds.append([1000,1000])
        total_seeds=1
    f.write('\n'+str(total_seeds)+' 1\n')
    idx=1
    for seed in water_seeds:
        f.write(str(idx)+' '+str(seed[0]-lon0)+' '+str(seed[1]-lat0)+' '+\
          dico_tri_markers['water']+'\n')
        idx+=1
    for seed in sea_seeds:
        f.write(str(idx)+' '+str(seed[0]-lon0)+' '+str(seed[1]-lat0)+' '+\
          dico_tri_markers['sea']+'\n')
        idx+=1
    for seed in sea_equiv_seeds:
        f.write(str(idx)+' '+str(seed[0]-lon0)+' '+str(seed[1]-lat0)+' '+\
          dico_tri_markers['sea_equiv']+'\n')
        idx+=1
    apt_idx=100 
    for seed in flat_airport_seeds:
        f.write(str(idx)+' '+str(seed[1][0]-lon0)+' '+\
          str(seed[1][1]-lat0)+' '+str(apt_idx)+'\n')
        apt_idx+=1        
        idx+=1
    fp_idx=1000
    for seed in flat_patch_seeds:
        f.write(str(idx)+' '+str(seed[0][0])+' '+\
          str(seed[0][1])+' '+str(fp_idx)+'\n')
        fp_idx+=1
        idx+=1
    sp_idx=10000
    for seed in sloped_patch_seeds:
        f.write(str(idx)+' '+str(seed[0][0])+' '+str(seed[0][1])+' '+\
                str(sp_idx)+'\n')
        sp_idx+=1
    print("   Remain " + str(len(dico_edges))+\
          " edges in total.") 
    f.close()
    f=open(airport_file,"w")
    apt_idx =   100
    fp_idx  =  1000
    sp_idx  = 10000
    for seed in flat_airport_seeds:
        f.write("Airport "+str(apt_idx)+" : "+str(len(seed[0].nodes))+\
                " nodes.\n")
        f.write("Elevation "+str(seed[2])+'\n')
        for node in seed[0].nodes:
            f.write(str(float(node.lat))+" "+str(float(node.lon))+"\n")
        f.write("\n")
        apt_idx+=1
    f.write('\n')
    for seed in flat_patch_seeds:
        f.write("Flat_patch "+str(fp_idx)+" : "+str(len(seed[2]))+"\n") 
        f.write("Elevation "+str(seed[1])+'\n')
        for node in seed[2]:
            [slat,slon]=node.split('_')
            f.write(slat+" "+slon+"\n")
        f.write("\n")
        fp_idx+=1
    f.write('\n')
    for seed in sloped_patch_seeds:
        f.write("Sloped_patch "+str(sp_idx)+" : "+str(seed[1])+" "+\
                str(seed[2])+" "+str(seed[3])+" "+str(seed[4])+" "+\
                str(seed[5])+" "+str(seed[6])+" "+str(seed[7])+" "+\
                str(seed[8])+" "+str(seed[9])+"\n") 
        sp_idx+=1
    f.close()
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t1))+\
                'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    return 
#############################################################################
#############################################################################
# Puzzle consistant à trouver toutes les boucles fermées de berges parmi
# une mer de boucles ouvertes...
#############################################################################
def find_next_loop(rel,index,result):
   way=member_to_way(rel.members[index],result)
   if way is None:
       return 'None'
   initpoint = strcode(way.nodes[0])
   endpoint  = strcode(way.nodes[-1])
   loop_structure=[[index,1]]
   list_already_in_loop=[index]
   while initpoint != endpoint:
       new_idx=index
       while new_idx < len(rel.members): 
           if new_idx not in list_already_in_loop:
               [start,stop]=end_pt_codes(new_idx,rel,result)
               if endpoint == start:
                   loop_structure.append([new_idx,1])
                   endpoint=stop
                   list_already_in_loop.append(new_idx)
                   break
               elif endpoint == stop:
                   loop_structure.append([new_idx,-1])
                   endpoint=start
                   list_already_in_loop.append(new_idx)
                   break
               else:
                   new_idx+=1
           else:
               new_idx+=1
       if new_idx==len(rel.members):
           #print("Je n'ai pas pu fermer une des relations OpenStreetMap.")
           return 'None'
   return loop_structure 
#############################################################################

#############################################################################
def strcode(node):
   return str(node.lat)+'_'+str(node.lon)
#############################################################################

#############################################################################
def member_to_way(member,result):
   for way in result.ways:
       if way.id==member.ref:
           return way
#############################################################################

#############################################################################
def end_pt_codes(index,rel,result):
   start = strcode(member_to_way(rel.members[index],result).nodes[0])
   stop  = strcode(member_to_way(rel.members[index],result).nodes[-1])
   return [start,stop]
#############################################################################

#############################################################################
def keep_node(node,lat0,lon0,dico_nodes):
   dico_nodes[strcode(node)]=[node.lon-lon0,node.lat-lat0]
   return
#############################################################################
   
#############################################################################
def keep_edge(node0,node,marker,dico_edges):
   if strcode(node0) != strcode(node):
       dico_edges[strcode(node0)+'|'+strcode(node)]=marker
   return
#############################################################################

#############################################################################
def keep_way(way,lat0,lon0,sign,marker,dico_nodes,dico_edges):
   if sign==1:
       node0=way.nodes[0]
       keep_node(node0,lat0,lon0,dico_nodes)
       for node in way.nodes[1:]:
           keep_node(node,lat0,lon0,dico_nodes)
           keep_edge(node0,node,marker,dico_edges)
           node0=node
   elif sign==-1:
       node0=way.nodes[-1]
       keep_node(node0,lat0,lon0,dico_nodes)
       for node in way.nodes[-1:-len(way.nodes)-1:-1]:
           keep_node(node,lat0,lon0,dico_nodes)
           keep_edge(node0,node,marker,dico_edges)
           node0=node
   return
#############################################################################
   
#############################################################################
def strxy(x,y,lat0,lon0):
    return str(y+lat0)+'_'+str(x+lon0)
#############################################################################

#############################################################################
def keep_node_xy(x,y,lat0,lon0,dico_nodes):
   dico_nodes[strxy(x,y,lat0,lon0)]=[x,y]
   return
#############################################################################

#############################################################################
def xcoord(strcode,dico_nodes):
    return float(dico_nodes[strcode][0])
#############################################################################

#############################################################################
def ycoord(strcode,dico_nodes):
    return float(dico_nodes[strcode][1])
#############################################################################
   
#############################################################################
def keep_edge_str_tmp(strcode1,strcode2,marker,dico_edges_tmp):
   dico_edges_tmp[strcode1+'|'+strcode2]=marker
   return
#############################################################################


#############################################################################
def keep_patch(newwaycodes,dico_nodes,dico_edges):
    for i in range(0,len(newwaycodes)-1):
        dico_edges[newwaycodes[i]+'|'+newwaycodes[i+1]]='patch'
    eps=0.01
    newway=[]
    for node_code in newwaycodes:
        newway+=dico_nodes[node_code]
    testpt1=[(newway[0]+newway[2])/2.0+eps*(newway[3]-newway[1]),\
             (newway[1]+newway[3])/2.0-eps*(newway[2]-newway[0])]
    testpt2=[(newway[0]+newway[2])/2.0-eps*(newway[3]-newway[1]),\
             (newway[1]+newway[3])/2.0+eps*(newway[2]-newway[0])]
    if point_in_polygon(testpt1,newway)==True:
        return testpt1
    else:
        return testpt2
#############################################################################


#############################################################################
def keep_sloped_patch(waycodes,cell_size,dico_nodes,dico_edges,lat0,lon0):
    way=[]
    sdn={}
    for node_code in waycodes:
        way+=dico_nodes[node_code]
    approx_length=sqrt((way[0]-way[2])**2*cos(lat0*pi/180)**2+\
            (way[1]-way[3])**2)
    approx_width =sqrt((way[0]-way[6])**2*cos(lat0*pi/180)**2+\
            (way[1]-way[7])**2)
    Nx=ceil(approx_width/cell_size)
    Ny=ceil(approx_length/cell_size)
    for ny in range(0,Ny+1):
        for nx in range(0,Nx+1):
            xcoord=way[0]+ny/Ny*(way[2]-way[0])+nx/Nx*\
                    (way[6]-way[0]+ny/Ny*(way[0]+way[4]-way[2]-way[6]))
            ycoord=way[1]+ny/Ny*(way[3]-way[1])+nx/Nx*\
                    (way[7]-way[1]+ny/Ny*(way[1]+way[5]-way[3]-way[7]))
            nlat=ycoord+lat0
            nlon=xcoord+lon0
            if (nx!=0 or ny!=0) and (nx!=0 or ny!=Ny) and \
                    (nx!=Nx or ny!=0) and (nx!=Nx or ny!=Ny):
                dico_nodes[str(nlat)+'_'+str(nlon)]=[xcoord,ycoord]
                sdn[(nx,ny)]=str(nlat)+'_'+str(nlon) 
    sdn[(0,0)]=waycodes[0]
    sdn[(0,Ny)]=waycodes[1]
    sdn[(Nx,Ny)]=waycodes[2]
    sdn[(Nx,0)]=waycodes[3]
    dico_edges.pop(waycodes[0]+'|'+waycodes[3],None)
    dico_edges.pop(waycodes[3]+'|'+waycodes[0],None)
    dico_edges.pop(waycodes[1]+'|'+waycodes[2],None)
    dico_edges.pop(waycodes[2]+'|'+waycodes[1],None)
    for ny in range(0,Ny+1):
        for nx in range(0,Nx):
            if ny==0 or ny==Ny:
                dico_edges[sdn[(nx,ny)]+'|'+sdn[(nx+1,ny)]]='patch'
            else:
                # fake but we want those to be traversed by the plague 
                # regional algo of Triangle4XP
                dico_edges[sdn[(nx,ny)]+'|'+sdn[(nx+1,ny)]]='orthogrid' 
    for ny in range(0,Ny):
        for nx in range(0,Nx+1):
            if nx==0 or nx==Nx:
                dico_edges[sdn[(nx,ny)]+'|'+sdn[(nx,ny+1)]]='patch'
            else:
                dico_edges[sdn[(nx,ny)]+'|'+sdn[(nx,ny+1)]]='orthogrid'
    eps=0.01
    testpt1=[(way[0]+way[2])/2.0+eps*(way[3]-way[1]),\
             (way[1]+way[3])/2.0-eps*(way[2]-way[0])]
    testpt2=[(way[0]+way[2])/2.0-eps*(way[3]-way[1]),\
             (way[1]+way[3])/2.0+eps*(way[2]-way[0])]
    if point_in_polygon(testpt1,way)==True:
        return [testpt1,(way[0]+way[6])/2.0,(way[1]+way[7])/2.0,\
                (way[2]+way[4])/2.0,(way[3]+way[5])/2.0]
    else:
        return [testpt2,(way[0]+way[6])/2.0,(way[1]+way[7])/2.0,\
                (way[2]+way[4])/2.0,(way[3]+way[5])/2.0]
#############################################################################

#############################################################################
def cut_edges_with_grid(lat0,lon0,dico_nodes,dico_edges,orthogrid=True):
    dico_edges_tmp={}
    xgrid=[]  # x coordinates of vertical grid lines
    ygrid=[]  # y coordinates of horizontal grid lines
    xcuts={}  # xcuts[y] will contain the x coordinates of the cut points on
              # the horiz line at y  
    ycuts={}  # ycuts[x] will contain the y coordinates of the cut points on
              # the vertical line at x
    
    # computation of the coordinates of the grid lines
    til_xul=ceil((lon0/180+1)*(2**(meshzl-1)))
    til_yul=ceil((1-log(tan((90+lat0+1)*pi/360))/pi)*(2**(meshzl-1)))
    til_xlr=floor(((lon0+1)/180+1)*(2**(meshzl-1)))
    til_ylr=floor((1-log(tan((90+lat0)*pi/360))/pi)*(2**(meshzl-1)))
    til_xul=ceil(til_xul/16)*16
    til_yul=ceil(til_yul/16)*16
    til_xlr=(til_xlr//16)*16
    til_ylr=(til_ylr//16)*16
    for til_x in range(int(til_xul),int(til_xlr+1),16):
        pos_x=(til_x/(2**(meshzl-1))-1)
        xgrid.append(pos_x*180-lon0+0.0)
    for til_y in range(int(til_yul),int(til_ylr+1),16):
        pos_y=(1-(til_y)/(2**(meshzl-1)))
        ygrid=[360/pi*atan(exp(pi*pos_y))-90-lat0+0.0]+ygrid
    if 0.0 not in xgrid:
        xgrid=[0.0]+xgrid
    if 1.0 not in xgrid:
        xgrid=xgrid+[1.0]
    if 0.0 not in ygrid:
        ygrid=[0.0]+ygrid
    if 1.0 not in ygrid:
        ygrid=ygrid+[1.0]
    # encoding nodes corresponding to grid points
    for x in xgrid:
        for y in ygrid:
            keep_node_xy(x,y,lat0,lon0,dico_nodes)
    # keeping track of the intersections of the vertical and horizontal lines
    # between themselves.
    for x in xgrid:
        ycuts[x]=ygrid
    for y in ygrid:
        xcuts[y]=xgrid
    # adding boundary points every 25m (roughly) to prevent tear between tiles
    for k in range(1,4000):
        keep_node_xy(0.0,k/4000.0,lat0,lon0,dico_nodes)
        keep_node_xy(1.0,k/4000.0,lat0,lon0,dico_nodes)
        keep_node_xy(k/4000.0,0.0,lat0,lon0,dico_nodes)
        keep_node_xy(k/4000.0,1.0,lat0,lon0,dico_nodes)
        xcuts[0.0]=xcuts[0.0]+[k/4000.0]
        xcuts[1.0]=xcuts[1.0]+[k/4000.0]
        ycuts[0.0]=ycuts[0.0]+[k/4000.0]
        ycuts[1.0]=ycuts[1.0]+[k/4000.0]
    # we compute the intersection of osm edges with horizontal tile boundaries 
    for edge in dico_edges:
        initpt=edge.split('|')[0]
        endpt=edge.split('|')[1]
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        if ((yi<0 and 0<yf) or (yi>0 and 0>yf)):
            xcross= (0-yf)/(yi-yf)*xi+(yi-0)/(yi-yf)*xf
            if xcross>0 and xcross<1:
                xcuts[0.0]=xcuts[0.0]+[xcross]
            keep_node_xy(xcross,0.0,lat0,lon0,dico_nodes)
            if yi>0:
                keep_edge_str_tmp(initpt,strxy(xcross,0.0,lat0,lon0),\
                       dico_edges[edge],dico_edges_tmp)
            elif yf>0:
                keep_edge_str_tmp(strxy(xcross,0.0,lat0,lon0),\
                       endpt,dico_edges[edge],dico_edges_tmp)
        elif ((yi<1 and 1<yf) or (yi>1 and 1>yf)):
            xcross= (1-yf)/(yi-yf)*xi+(yi-1)/(yi-yf)*xf
            if xcross>0 and xcross<1:
                xcuts[1.0]=xcuts[1.0]+[xcross]
            keep_node_xy(xcross,1.0,lat0,lon0,dico_nodes)
            if yi<1:
                keep_edge_str_tmp(initpt,strxy(xcross,1.0,lat0,lon0),\
                       dico_edges[edge],dico_edges_tmp)
            elif yf<1:
                keep_edge_str_tmp(strxy(xcross,1.0,lat0,lon0),\
                       endpt,dico_edges[edge],dico_edges_tmp)
        elif ((yi==0) and (yf>0)):
            xcross=xi
            keep_node_xy(xcross,0.0,lat0,lon0,dico_nodes)
            xcuts[0.0]=xcuts[0.0]+[xcross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((yf==0) and (yi>0)):
            xcross=xf
            keep_node_xy(xcross,0.0,lat0,lon0,dico_nodes)
            xcuts[0.0]=xcuts[0.0]+[xcross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((yi==1) and (yf<1)):
            xcross=xi
            keep_node_xy(xcross,1.0,lat0,lon0,dico_nodes)
            xcuts[1.0]=xcuts[1.0]+[xcross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((yf==1) and (yi<1)):
            xcross=xf
            keep_node_xy(xcross,1.0,lat0,lon0,dico_nodes)
            xcuts[1.0]=xcuts[1.0]+[xcross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((yi==0) and (yf==0)):
            xcuts[0.0]=xcuts[0.0]+[xi,xf]
            keep_node_xy(xi,0.0,lat0,lon0,dico_nodes)
            keep_node_xy(xf,0.0,lat0,lon0,dico_nodes)
        elif ((yi==1) and (yf==1)):
            xcuts[1.0]=xcuts[1.0]+[xi,xf]
            keep_node_xy(xi,1.0,lat0,lon0,dico_nodes)
            keep_node_xy(xf,1.0,lat0,lon0,dico_nodes)
        elif (yi>0 and yi<1) and (yf>0 and yf<1): 
            dico_edges_tmp[edge]=dico_edges[edge]
    dico_edges=dico_edges_tmp
    dico_edges_tmp={}

    # we compute the intersection of (v-splitted) osm edges with vertical tile boundaries 
    for edge in dico_edges:
        initpt=edge.split('|')[0]
        endpt=edge.split('|')[1]
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        if ((xi<0 and 0<xf) or (xi>0 and 0>xf)):
            ycross= (0-xf)/(xi-xf)*yi+(xi-0)/(xi-xf)*yf
            if ycross>0 and ycross<1:
                ycuts[0.0]=ycuts[0.0]+[ycross]
            keep_node_xy(0.0,ycross,lat0,lon0,dico_nodes)
            if xi>0:
                keep_edge_str_tmp(initpt,strxy(0.0,ycross,lat0,lon0),dico_edges[edge],\
                   dico_edges_tmp)
            elif xf>0:
                keep_edge_str_tmp(strxy(0.0,ycross,lat0,lon0),endpt,dico_edges[edge],\
                   dico_edges_tmp)
        elif ((xi<1 and 1<xf) or (xi>1 and 1>xf)):
            ycross= (1-xf)/(xi-xf)*yi+(xi-1)/(xi-xf)*yf
            if ycross>0 and ycross<1:
                ycuts[1.0]=ycuts[1.0]+[ycross]
            keep_node_xy(1.0,ycross,lat0,lon0,dico_nodes)
            if xi<1:
                keep_edge_str_tmp(initpt,strxy(1.0,ycross,lat0,lon0),dico_edges[edge],\
                   dico_edges_tmp)
            elif xf<1:
                keep_edge_str_tmp(strxy(1.0,ycross,lat0,lon0),endpt,dico_edges[edge],\
                   dico_edges_tmp)
        elif ((xi==0) and (xf>0)):
            ycross=yi
            keep_node_xy(0.0,ycross,lat0,lon0,dico_nodes)
            ycuts[0.0]=ycuts[0.0]+[ycross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((xf==0) and (xi>0)):
            ycross=yf
            keep_node_xy(0.0,ycross,lat0,lon0,dico_nodes)
            ycuts[0.0]=ycuts[0.0]+[ycross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((xi==1) and (xf<1)):
            ycross=yi
            keep_node_xy(1.0,ycross,lat0,lon0,dico_nodes)
            ycuts[1.0]=ycuts[1.0]+[ycross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((xf==1) and (xi<1)):
            ycross=yf
            keep_node_xy(1.0,ycross,lat0,lon0,dico_nodes)
            ycuts[1.0]=ycuts[1.0]+[ycross]
            dico_edges_tmp[edge]=dico_edges[edge]
        elif ((xi==0) and (xf==0)):
            ycuts[0.0]=ycuts[0.0]+[yi,yf]
            keep_node_xy(0.0,yi,lat0,lon0,dico_nodes)
            keep_node_xy(0.0,yf,lat0,lon0,dico_nodes)
        elif ((xi==1) and (xf==1)):
            ycuts[1.0]=ycuts[1.0]+[yi,yf]
            keep_node_xy(1.0,yi,lat0,lon0,dico_nodes)
            keep_node_xy(1.0,yf,lat0,lon0,dico_nodes)
        elif (xi>0 and xi<1) and (xf>0 and xf<1): 
            dico_edges_tmp[edge]=dico_edges[edge]
    dico_edges=dico_edges_tmp
    dico_edges_tmp={}
    
    
    # we compute the intersection of osm edges with inner horizontal grid lines 
    for edge in dico_edges:
        initpt=edge.split('|')[0]
        endpt=edge.split('|')[1]
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        til_yi=floor((1-log(tan((90+lat0+yi)*pi/360))/pi)*(2**(meshzl-1)))
        til_yf=floor((1-log(tan((90+lat0+yf)*pi/360))/pi)*(2**(meshzl-1)))
        til_yi=(til_yi//16)*16
        til_yf=(til_yf//16)*16
        if til_yi != til_yf:
            #if abs(til_yi-til_yf) != 16:
               #print("arête coupant plusieurs lignes horizontales de la grilles : \n")
               #print(str(abs(til_yi-til_yf))+"\n")
            til_y0=max(til_yi,til_yf)
            y0=360/pi*atan(exp(pi*(1-(til_y0)/(2**(meshzl-1)))))-90-lat0
            xcross= (y0-yf)/(yi-yf)*xi+(yi-y0)/(yi-yf)*xf
            xcuts[y0]=xcuts[y0]+[xcross]
            keep_node_xy(xcross,y0,lat0,lon0,dico_nodes)
            keep_edge_str_tmp(initpt,strxy(xcross,y0,lat0,lon0),\
                   dico_edges[edge],dico_edges_tmp)
            keep_edge_str_tmp(strxy(xcross,y0,lat0,lon0),\
                   endpt,dico_edges[edge],dico_edges_tmp)
        else:
            dico_edges_tmp[edge]=dico_edges[edge]
      
    dico_edges=dico_edges_tmp
    dico_edges_tmp={}

    # then the intersection of osm edges with inner vertical grid lines 
    for edge in dico_edges:
        initpt=edge.split('|')[0]
        endpt=edge.split('|')[1]
        xi=xcoord(initpt,dico_nodes)
        yi=ycoord(initpt,dico_nodes)
        xf= xcoord(endpt,dico_nodes)
        yf= ycoord(endpt,dico_nodes)
        til_xi=floor(((lon0+xi)/180+1)*(2**(meshzl-1)))
        til_xf=floor(((lon0+xf)/180+1)*(2**(meshzl-1)))
        til_xi=(til_xi//16)*16
        til_xf=(til_xf//16)*16
        if til_xi != til_xf:
            #if abs(til_xi-til_xf) != 16:
                #print("arête coupant plusieurs lignes verticales de la grilles\n")
                #print(str(xi)+' '+str(yi)+' '+str(xf)+' '+str(yf)+"\n")
            til_x0=max(til_xi,til_xf)
            x0=(til_x0/(2**(meshzl-1))-1)*180-lon0
            ycross= (x0-xf)/(xi-xf)*yi+(xi-x0)/(xi-xf)*yf
            ycuts[x0]=ycuts[x0]+[ycross]
            keep_node_xy(x0,ycross,lat0,lon0,dico_nodes)
            keep_edge_str_tmp(initpt,strxy(x0,ycross,lat0,lon0),dico_edges[edge],\
                   dico_edges_tmp)
            keep_edge_str_tmp(strxy(x0,ycross,lat0,lon0),endpt,dico_edges[edge],\
                   dico_edges_tmp)
        else:
            dico_edges_tmp[edge]=dico_edges[edge]
    
    # finally we include edges that are formed by cutted grid lines        
    for y in xcuts:
        xcuts[y].sort()
        for k in range(0,len(xcuts[y])-1):
            dico_edges_tmp[strxy(xcuts[y][k],y,lat0,lon0)+'|'+\
                      strxy(xcuts[y][k+1],y,lat0,lon0)]='orthogrid'
    for x in ycuts:
        ycuts[x].sort()
        for k in range(0,len(ycuts[x])-1):
            dico_edges_tmp[strxy(x,ycuts[x][k],lat0,lon0)+'|'+\
                      strxy(x,ycuts[x][k+1],lat0,lon0)]='orthogrid'
    return dico_edges_tmp
#############################################################################



#############################################################################
# Petite routine bien utile : comment calculer rapidement l'aire d'un 
# polygone dont on dispose de la liste des sommets.  Le signe donne le sens
# de parcours horaire ou anti-horaire.
#############################################################################
def area(way):
   area=0
   x1=float(way.nodes[0].lon)
   y1=float(way.nodes[0].lat)
   for node in way.nodes[1:]:
       x2=float(node.lon)
       y2=float(node.lat)
       area+=(x2-x1)*(y2+y1)
       x1=x2
       y1=y2
   return area/2 
#############################################################################

#############################################################################
# Openstreetmap donne tous les objets qui intersectent la tuile, pour les
# objets de type 'rel' on peut virer les boucles fermées qui sont entièrement
# hors tuile (sinon par exemple pour lat=45 lon=5 on récupère le Rhônes 
# jusqu'à son embouchure !
#############################################################################
def touches_region(way,lat0,lat1,lon0,lon1):
    for node in way.nodes:
       if float(node.lat)>=lat0 and float(node.lat)<=lat1\
         and float(node.lon)>=lon0 and float(node.lon)<=lon1:
           return True
    return False
#############################################################################

#############################################################################
# Comment planter une petite graine qui de proche en proche découvrira tous
# les triangles en eau (en se baladant sans pouvoir traverser les arêtes du
# fichier .poly).
#############################################################################
def pick_point(way,side,lat0,lon0):
   if side=='left':
       sign=1
   elif side=='right':
       sign=-1
   dmin =0.00001 
   l=0
   ptin=False
   i=0
   while (l<dmin) or (ptin==False):
       if len(way.nodes)==i+1:
           break
       x1=float(way.nodes[i].lon)
       y1=float(way.nodes[i].lat)
       x2=float(way.nodes[i+1].lon)
       y2=float(way.nodes[i+1].lat)
       l=sqrt((x2-x1)**2+(y2-y1)**2)
       ptin=False
       if ((x2>lon0) and (x2<lon0+1) and (y2>lat0) and (y2<lat0+1)) and\
          ((x1>lon0) and (x1<lon0+1) and (y1>lat0) and (y1<lat0+1)):
           ptin=True
       i+=1
   if ptin==True:
       dperp=0.000001
       x=0.5*x1+0.5*x2+(y1-y2)/l*dperp*sign
       y=0.5*y1+0.5*y2+(x2-x1)/l*dperp*sign
       return [x,y]
   i=0
   while (l<dmin) or (ptin==False):
       if len(way.nodes)==i+1:
           # This should never happen, we send it to hell
           return [1000,1000]
       x1=float(way.nodes[i].lon)
       y1=float(way.nodes[i].lat)
       x2=float(way.nodes[i+1].lon)
       y2=float(way.nodes[i+1].lat)
       l=sqrt((x2-x1)**2+(y2-y1)**2)
       ptin=False
       if ((x2>lon0) and (x2<lon0+1) and (y2>lat0) and (y2<lat0+1)):
           ptin=True
           ptend=2
       if ((x1>lon0) and (x1<lon0+1) and (y1>lat0) and (y1<lat0+1)):
           ptin=True
           ptend=1
       i+=1
   dperp=0.0000001
   if ptend==1:
       x=0.99*x1+0.01*x2+(y1-y2)/l*dperp*sign
       y=0.99*y1+0.01*y2+(x2-x1)/l*dperp*sign
   else:
       x=0.99*x2+0.01*x1+(y1-y2)/l*dperp*sign
       y=0.99*y2+0.01*y1+(x2-x1)/l*dperp*sign
   return [x,y]
#############################################################################

#############################################################################
def pick_points_safe(way,side,lat0,lon0):
   if side=='left':
       sign=1
   elif side=='right':
       sign=-1
   dmin =0.00001 
   return_list=[]
   not_yet_edge_fully_in=True
   for i in range(0,len(way.nodes)-1):
       x1=float(way.nodes[i].lon)
       y1=float(way.nodes[i].lat)
       x2=float(way.nodes[i+1].lon)
       y2=float(way.nodes[i+1].lat)
       l=sqrt((x2-x1)**2+(y2-y1)**2)
       if l<dmin:
          continue    
       x2in= (x2>lon0) and (x2<lon0+1) and (y2>lat0) and (y2<lat0+1) 
       x1in= (x1>lon0) and (x1<lon0+1) and (y1>lat0) and (y1<lat0+1)
       if x1in and x2in and  not_yet_edge_fully_in:
          not_yet_edge_fully_in=False
          dperp=0.000001
          x=0.5*x1+0.5*x2+(y1-y2)/l*dperp*sign
          y=0.5*y1+0.5*y2+(x2-x1)/l*dperp*sign   
          return_list.append([x,y])
       elif x1in and not x2in:
          dperp=0.0000001
          x=0.99*x1+0.01*x2+(y1-y2)/l*dperp*sign
          y=0.99*y1+0.01*y2+(x2-x1)/l*dperp*sign
          return_list.append([x,y])
       elif x2in and not x1in:
          dperp=0.0000001
          x=0.99*x2+0.01*x1+(y1-y2)/l*dperp*sign
          y=0.99*y2+0.01*y1+(x2-x1)/l*dperp*sign
          return_list.append([x,y])	   
   return return_list
#############################################################################





##############################################################################
# La construction des noms des fichiers d'altitudes, sera amené à changer 
# si de meilleures sources libres de DEM voient le jour. 
##############################################################################
def downloaded_dem_filename(lat,lon,source):
    if source=='SRTMv3_1(void filled)':
        if (lat >= 0):
            hemisphere='N'
        else:
            hemisphere='S'
        if (lon >= 0):
            greenwichside='E'
        else:
            greenwichside='W'
        filename="SRTMv3_1_"+hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
                greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)+'.tif'
    if source=='SRTMv3_3(void filled)':
        if (lat >= 0):
            hemisphere='N'
        else:
            hemisphere='S'
        if (lon >= 0):
            greenwichside='E'
        else:
            greenwichside='W'
        filename="SRTMv3_3_"+hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
                greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)+'.tif'
    elif source=='de_Ferranti':
        if (lat >= 0):
            hemisphere='N'
        else:
            hemisphere='S'
        if (lon >= 0):
            greenwichside='E'
        else:
            greenwichside='W'
        filename=hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
                greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)+\
                '.hgt'
    elif source=='FR':
        filename='' # for future use maybe
    return Ortho4XP_dir+"/Elevation_data/"+filename
##############################################################################


##############################################################################
#  Chargement en mémoire des DEM. Si aucun fichier spécifié de Ferranti a la 
#   priorité sur SRTM là où   il est disponible.
##############################################################################
def load_altitude_matrix(lat,lon,filename='None'):
    filename_srtm1=downloaded_dem_filename(lat,lon,'SRTMv3_1(void filled)')
    filename_srtm3=downloaded_dem_filename(lat,lon,'SRTMv3_3(void filled)')
    filename_viewfinderpanorama=downloaded_dem_filename(lat,lon,'de_Ferranti')
    if filename=='None':
        if os.path.isfile(filename_viewfinderpanorama):
            filename=filename_viewfinderpanorama
        elif os.path.isfile(filename_srtm1):
            filename=filename_srtm1
        elif os.path.isfile(filename_srtm3):
            filename=filename_srtm3
        else:
            usage('dem_files',do_i_quit=False) 
            return 'error'
    if ('.hgt') in filename or ('.HGT' in filename):
        try:
            ndem=int(round(sqrt(os.path.getsize(filename)/2)))
            f = open(filename, 'rb')
            format = 'h'
            alt = array.array(format)
            alt.fromfile(f,ndem*ndem)
            f.close()
        except:
            usage('dem_files',do_i_quit=False) 
            return 'error'
        alt.byteswap()
        alt=numpy.asarray(alt,dtype=numpy.float32).reshape((ndem,ndem)) 
        if alt.min()==-32768:
            print("")
            print("WARNING : The elevation file "+filename+" has no data zones, ")
            if ndem==1201 and os.path.isfile(filename_srtm3):
                try:
                    ds=gdal.Open(filename_srtm3)
                    altbis=numpy.float32(ds.GetRasterBand(1).ReadAsArray())
                    alt=numpy.where(alt==-32768,altbis,alt)
                    alt=numpy.array(alt,dtype=numpy.float32)
                    print("I have filled it with your available void filled SRTM data for the tile.")
                except:
                    print("I move forward by filling them with the mean altitude of the")
                    print("whole tile but you'd better fill them by hand (e.g. with gdal_translate).")
                    print("")
                    alt=alt+(32768+alt.mean())*(alt==-32768)
                    alt=numpy.array(alt,dtype=numpy.float32)
            elif ndem==3601 and os.path.isfile(filename_srtm1):
                try:
                    ds=gdal.Open(filename_srtm1)
                    altbis=numpy.float32(ds.GetRasterBand(1).ReadAsArray())
                    alt=numpy.where(alt==-32768,altbis,alt)
                    alt=numpy.array(alt,dtype=numpy.float32)
                    print("I have filled it with your available void filled SRTM data for the tile.")
                except:
                    print("I move forward by filling them with the mean altitude of the")
                    print("whole tile but you'd better fill them by hand (e.g. with gdal_translate).")
                    print("")
                    alt=alt+(32768+alt.mean())*(alt==-32768)
                    alt=numpy.array(alt,dtype=numpy.float32)
            else:
                print("I move forward by filling them with the mean altitude of the")
                print("whole tile but you'd better fill them by hand (e.g. with gdal_translate).")
                print("")
                alt=alt+(32768+alt.mean())*(alt==-32768)
                alt=numpy.array(alt,dtype=numpy.float32)
        return [alt,ndem]
    elif ('.tif' in filename) or ('.TIF' in filename):
        if gdal_loaded == True:
            try:
                ds=gdal.Open(filename)
                alt=numpy.float32(ds.GetRasterBand(1).ReadAsArray())
                ndem=ds.RasterXSize
            except:
                usage('dem_files',do_i_quit=False) 
                return 'error'
        else:
            try:
                # geotiff file do not seem to be easily treated by PIL,
                # smashing them through convert is a weird workaround
                # since it removes some of the tags layer, but it works.     
                os.system(convert_cmd+' "'+filename+'" "'+filename +'" '+\
                        devnull_rdir)
                im=Image.open(filename)
                alt=numpy.float32(im)
                alt=alt-65536*(alt>10000)
                if alt.shape[0]==alt.shape[1]:
                    ndem=alt.shape[0]
                else:
                    usage('dem_files',do_i_quit=False) 
                    return 'error'
            except:
                usage('dem_files',do_i_quit=False) 
                return 'error'
        if alt.min()==-32768:
            print("")
            print("WARNING : The elevation file "+filename+" has no data zones, ")
            print("I move forward by filling them with the mean altitude of the")
            print("whole tile but you'd better fill them by hand (e.g. with gdal_translate).")
            print("")
            alt=alt+(32768+alt.mean())*(alt==-32768)
            alt=numpy.array(alt,dtype=numpy.float32)
        return [alt,ndem]
    usage('dem_files',do_i_quit=False)
    return 'error'
##############################################################################
 

##############################################################################
# Altitude obtenue par interpolation pour les points hors de la grille du
# fichier DEM.
##############################################################################
def altitude(x,y,alt_dem,ndem):
    N=ndem-1
    if x<0:
        x=0
    if x>1:
        x=1
    if y<0:
        y=0
    if y>1:
        y=1
    px=x*N
    py=y*N
    nx=int(px)
    ny=int(py)
    rx=px-nx
    ry=py-ny
    if rx!=0 and ry!=0 and rx>=ry:
        z=(1-rx)*alt_dem[N-ny][nx]+\
           ry*alt_dem[N-ny-1][nx+1]+(rx-ry)*alt_dem[N-ny][nx+1]
    elif rx!=0 and ry!=0:
        z=(1-ry)*alt_dem[N-ny][nx]+\
          rx*alt_dem[N-ny-1][nx+1]+(ry-rx)*alt_dem[N-ny-1][nx]
    elif rx==0 and ry!=0:
        z=(1-ry)*alt_dem[N-ny][nx]+ry*alt_dem[N-ny-1][nx]
    elif ry==0 and rx!=0:
        z=(1-rx)*alt_dem[N-ny][nx]+rx*alt_dem[N-ny][nx+1]
    else:
        z=alt_dem[N-ny][nx]
    return z
##############################################################################


##############################################################################
#  Construction des altitudes des points du maillage, et mise à zéro des
#  triangles de mer (pour éviter les effets indésirables des erreurs des
#  fichiers DEM sur le litoral lorsque celui-ci est accidenté). 
##############################################################################
def build_3D_vertex_array(lat,lon,alt_dem,ndem):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    node_filename = build_dir+dir_sep+'Data'+strlat+strlon+'.1.node'
    ele_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.1.ele'
    apt_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.apt'
    f_node = open(node_filename,'r')
    f_ele  = open(ele_filename,'r')
    f_apt  = open(apt_filename,'r')
    nbr_pt=int(f_node.readline().split()[0])
    vertices=numpy.zeros(5*nbr_pt)
    print("-> Loading of the mesh computed by Triangle4XP.")
    for i in range(0,nbr_pt):
        coordlist=f_node.readline().split()
        vertices[5*i]=float(coordlist[1])+lon
        vertices[5*i+1]=float(coordlist[2])+lat
        vertices[5*i+2]=float(coordlist[3])
        vertices[5*i+3]=float(coordlist[4])
        vertices[5*i+4]=float(coordlist[5])
    f_node.close()
    # Now we modify the altitude we got from the DEM in certain 
    # circumstances, because we want flat water, flat (or correctly sloped
    # airports, etc. One pass would be sufficient in principle but I 
    # prefer one pass per triangle type, to have better control in
    # case of nodes belonging different triangle types.
    print("-> Flattening of oceans and seas, smoothing of lakes and rivers (1st pass)")
    # Here we put all nodes belonging to at least one sea triangle
    # i.e. (with ele marker = 2) to zero altitude. 
    f_ele=open(ele_filename,'r')
    nbr_tri=int(f_ele.readline().split()[0])
    regiontag=True
    for i in range(0,nbr_tri):
        idx=f_ele.readline().split()
        v1=(int(idx[1])-1)
        v2=(int(idx[2])-1)
        v3=(int(idx[3])-1)
        if idx[4] == dico_tri_markers['sea']:
            vertices[5*v1+2]=0
            vertices[5*v2+2]=0
            vertices[5*v3+2]=0
        elif idx[4] in [dico_tri_markers['water'],\
                dico_tri_markers['sea_equiv']]:
            zmean=(vertices[5*v1+2]+vertices[5*v2+2]+vertices[5*v3+2])/3
            vertices[5*v1+2]=zmean
            vertices[5*v2+2]=zmean
            vertices[5*v3+2]=zmean
    print("-> Flattening of airports and treatment of patches, smoothing (2nd pass).")
    f_ele.seek(0)
    f_ele.readline()
    dico_alt_ap={}
    for i in range(0,nbr_tri):
        idx=f_ele.readline().split()
        v1=(int(idx[1])-1)
        v2=(int(idx[2])-1)
        v3=(int(idx[3])-1)
        if idx[4] in [dico_tri_markers['water'],\
                    dico_tri_markers['sea_equiv']]:
            if tile_has_water_airport!=True: # the parallel process does not otherwise ensure that airports are flat
                zmean=(vertices[5*v1+2]+vertices[5*v2+2]+vertices[5*v3+2])/3
                vertices[5*v1+2]=zmean
                vertices[5*v2+2]=zmean
                vertices[5*v3+2]=zmean
        elif (100 <= int(idx[4])) and (int(idx[4])<1000):
            if idx[4] in dico_alt_ap:
                height=dico_alt_ap[idx[4]]
                vertices[5*v1+2]=height
                vertices[5*v2+2]=height
                vertices[5*v3+2]=height
                continue
            found=False
            f_apt.seek(0)
            while found!=True:
                tmplist=f_apt.readline()
                if tmplist=='':
                    print("Error processing the .apt file.")
                    sys.exit()
                if "Airport" in tmplist:
                    tmplist=tmplist.split()
                    if tmplist[1]==str(int(idx[4])):
                        nbr_nodes=int(tmplist[3])
                        found=True
            osm_height=f_apt.readline().split()[1]
            height=0
            apt_crosses_tile=False
            for k in range(0,nbr_nodes):
                tmplist=f_apt.readline().split()
                x=float(tmplist[1])-lon
                y=float(tmplist[0])-lat
                if (x<0 or x>1 or y<0 or y>1):
                    apt_crosses_tile=True
                height+=altitude(x,y,alt_dem,ndem)
            height=height/nbr_nodes
            if apt_crosses_tile==True and osm_height != 'unknown':
                # (crude) ele tag is max elevation, not mean elevation
                height=float(osm_height)-8  
            vertices[5*v1+2]=height
            vertices[5*v2+2]=height
            vertices[5*v3+2]=height
            dico_alt_ap[idx[4]]=height
        elif int(idx[4])>=1000 and int(idx[4])<10000:
            if idx[4] in dico_alt_ap:
                height=dico_alt_ap[idx[4]]
                vertices[5*v1+2]=height
                vertices[5*v2+2]=height
                vertices[5*v3+2]=height
                continue
            found=False
            f_apt.seek(0)
            while found!=True:
                tmplist=f_apt.readline()
                if tmplist=='':
                    print("Error processing the .apt file.")
                    sys.exit()
                if "Flat_patch" in tmplist:
                    tmplist=tmplist.split()
                    if tmplist[1]==str(int(idx[4])):
                        nbr_nodes=int(tmplist[3])
                        found=True
            patch_height=f_apt.readline().split()[1]
            if patch_height=='mean':
                height=0
                for k in range(0,nbr_nodes):
                    tmplist=f_apt.readline().split()
                    x=float(tmplist[1])-lon
                    y=float(tmplist[0])-lat
                    height+=altitude(x,y,alt_dem,ndem)
                height=height/nbr_nodes
            else:
                height=float(patch_height)
            vertices[5*v1+2]=height
            vertices[5*v2+2]=height
            vertices[5*v3+2]=height
            dico_alt_ap[idx[4]]=height
        elif 10000 <= int(idx[4]):
            if idx[4] in dico_alt_ap:
                tmplist=dico_alt_ap[idx[4]]
            else:
                found=False
                f_apt.seek(0)
                while found!=True:
                    tmplist=f_apt.readline()
                    if tmplist=='':
                        print("Error processing the .apt file.")
                        sys.exit()
                    if "Sloped_patch" in tmplist:
                        tmplist=tmplist.split()
                        if tmplist[1]==str(int(idx[4])):
                            found=True
                            dico_alt_ap[idx[4]]=tmplist
            xi=float(tmplist[3])
            yi=float(tmplist[4])
            xf=float(tmplist[5])
            yf=float(tmplist[6])
            zi=float(tmplist[7])
            zf=float(tmplist[8])
            x1=vertices[5*v1]-lon
            y1=vertices[5*v1+1]-lat
            x2=vertices[5*v2]-lon
            y2=vertices[5*v2+1]-lat
            x3=vertices[5*v3]-lon
            y3=vertices[5*v3+1]-lat
            rat1=((x1-xi)*(xf-xi)+(y1-yi)*(yf-yi))/((xf-xi)**2+(yf-yi)**2)
            rat2=((x2-xi)*(xf-xi)+(y2-yi)*(yf-yi))/((xf-xi)**2+(yf-yi)**2)
            rat3=((x3-xi)*(xf-xi)+(y3-yi)*(yf-yi))/((xf-xi)**2+(yf-yi)**2)
            steepness=float(tmplist[10])
            if tmplist[9]=='atanh':
                vertices[5*v1+2]=(zi+zf)/2+(zf-zi)/2*atan(steepness*(rat1-0.5))/\
                        atan(steepness/2)
                vertices[5*v2+2]=(zi+zf)/2+(zf-zi)/2*atan(steepness*(rat2-0.5))/\
                        atan(steepness/2)
                vertices[5*v3+2]=(zi+zf)/2+(zf-zi)/2*atan(steepness*(rat3-0.5))/\
                        atan(steepness/2)
            elif tmplist[9]=='spline':
                vertices[5*v1+2]=zi+3*(zf-zi)*rat1**2-2*(zf-zi)*rat1**3
                vertices[5*v2+2]=zi+3*(zf-zi)*rat2**2-2*(zf-zi)*rat2**3
                vertices[5*v3+2]=zi+3*(zf-zi)*rat3**2-2*(zf-zi)*rat3**3
            elif tmplist[9]=='parabolic':
                zi,zf=zf,zi
                rat1,rat2,rat3=1-rat1,1-rat2,1-rat3
                vertices[5*v1+2]=zi+(zf-zi)*rat1**2
                vertices[5*v2+2]=zi+(zf-zi)*rat2**2
                vertices[5*v3+2]=zi+(zf-zi)*rat3**2
            else:
                print("One of the patch profiles is unknown to me, I use a plane one instead.")
                vertices[5*v1+2]=zi+rat1*(zf-zi)
                vertices[5*v2+2]=zi+rat2*(zf-zi)
                vertices[5*v3+2]=zi+rat3*(zf-zi)
    if water_smoothing >= 3:
        print("   Smoothing of lakes and rivers (ultimate passes).")
        # Next, we average altitudes of triangles of fresh water type.  
        # Of course one such operation slightly breaks other ones, but there is 
        # not a perfect solution to this because the altitude close to the source
        # of a river differs from its altitude at is very end, water is not
        # flat all way long.
        for j in range(0,water_smoothing-2):   
            f_ele.seek(0)
            f_ele.readline()
            for i in range(0,nbr_tri):
                idx=f_ele.readline().split()
                v1=(int(idx[1])-1)
                v2=(int(idx[2])-1)
                v3=(int(idx[3])-1)
                if idx[4] in [dico_tri_markers['water'],\
                    dico_tri_markers['sea_equiv']]:
                    zmean=(vertices[5*v1+2]+vertices[5*v2+2]+vertices[5*v3+2])/3
                    vertices[5*v1+2]=zmean
                    vertices[5*v2+2]=zmean
                    vertices[5*v3+2]=zmean
    f_apt.close()
    f_ele.close()
    return vertices
##############################################################################

##############################################################################
# Write of the mesh file based on .1.ele, .1.node and vertices
##############################################################################
def build_mesh_file(lat,lon,vertices,mesh_filename):
    print("-> Writing of the final mesh to the file "+mesh_filename)
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    ele_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.1.ele'
    f_ele  = open(ele_filename,'r')
    nbr_vert=len(vertices)//5
    nbr_tri=int(f_ele.readline().split()[0])
    f=open(mesh_filename,"w")
    f.write("MeshVersionFormatted 1\n")
    f.write("Dimension 3\n\n")
    f.write("Vertices\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[5*i])+" "+\
                '{:.9f}'.format(vertices[5*i+1])+" "+\
                '{:.9f}'.format(vertices[5*i+2]/100000)+" 0\n") 
    f.write("\n")
    f.write("Normals\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[5*i+3])+" "+\
                '{:.9f}'.format(vertices[5*i+4])+"\n")
    f.write("\n")
    f.write("Triangles\n")
    f.write(str(nbr_tri)+"\n")
    for i in range(0,nbr_tri):
        f.write(' '.join(f_ele.readline().split()[1:])+"\n")
    f_ele.close()
    f.close()
    return
##############################################################################

##############################################################################
def build_mesh(lat,lon,build_dir):
    t2=time.time()
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    alt_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.alt'
    node_filename = build_dir+dir_sep+'Data'+strlat+strlon+'.1.node'
    ele_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.1.ele'
    poly_file     = build_dir+dir_sep+'Data'+strlat+strlon+'.poly'
    apt_filename  = build_dir+dir_sep+'Data'+strlat+strlon+'.apt'
    if os.path.isfile(apt_filename)!=True or os.path.isfile(poly_file)!=True:
        print("You must first build OSM data !")
        return
    mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
    print('-> Loading of elevation data.')
    try:
        if application.cdc.get()!=0:
            load_result=load_altitude_matrix(lat,lon,filename=application.cde.get())
        else:
            load_result=load_altitude_matrix(lat,lon)
    except:
        load_result=load_altitude_matrix(lat,lon)
    if load_result=='error':
        print('\nFailure.')
        print('_____________________________________________________________'+\
            '____________________________________')
        return
    [alt_dem,ndem]=load_result
    alt_dem.tofile(alt_filename)
    print("-> Start of the mesh algorithm Triangle4XP :\n") 
    if no_small_angles==True:
        Tri_option = ' -pq'+str(smallest_angle)+'uAYPQ '
    else:
        Tri_option = ' -pAuYPQ '
    mesh_cmd=[Triangle4XP_cmd.strip(),Tri_option.strip(),str(ndem),str(curvature_tol),\
            str(hmax/100000),str(hmin/100000),alt_filename,poly_file]
    fingers_crossed=subprocess.Popen(mesh_cmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print(line.decode("utf-8")[:-1])
    vertices=build_3D_vertex_array(lat,lon,alt_dem,ndem)
    build_mesh_file(lat,lon,vertices,mesh_filename)
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t2))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    return
##############################################################################


##############################################################################
#                                                                            #
# IV : Toutes les méthodes à vocation géographique, essentiellement ce       #
#      qui concerne les changements de référentiel (WGS84 - Lambert - UTM)   #
#      ou la numérotation des vignettes (TMS - Quadkey).                     #
#      J'appelle "vignette" les images de 256x256 ou 512x512 pixels qui      #
#      contiennent des orthophotos et que l'on pourra télécharger à la       #
#      chaîne chez nos amis du fichier Carnet_d_adresses.py                  #
#                                                                            #
##############################################################################
##############################################################################
def wgs84_to_gtile(lat,lon,zoomlevel):                                          
    half_meridian=pi*6378137
    rat_x=lon/180           
    rat_y=log(tan((90+lat)*pi/360))/pi
    pix_x=round((rat_x+1)*(2**(zoomlevel+7)))
    pix_y=round((1-rat_y)*(2**(zoomlevel+7)))
    til_x=pix_x//256
    til_y=pix_y//256
    return [til_x,til_y]
##############################################################################

##############################################################################
def gtile_to_wgs84(til_x,til_y,zoomlevel):
    """
    Returns the latitude and longitude of the top left corner of the tile 
    (til_x,til_y) at zoom level zoomlevel, using Google's numbering of tiles 
    (i.e. origin on top left of the earth map)
    """
    rat_x=(til_x/(2**(zoomlevel-1))-1)
    rat_y=(1-til_y/(2**(zoomlevel-1)))
    lon=rat_x*180
    lat=360/pi*atan(exp(pi*rat_y))-90
    return [lat,lon]
##############################################################################

##############################################################################
def gtile_to_quadkey(til_x,til_y,zoomlevel):
    """
    Translates Google coding of tiles to Bing Quadkey coding. 
    """
    quadkey=""
    temp_x=til_x
    temp_y=til_y    
    for step in range(1,zoomlevel+1):
        size=2**(zoomlevel-step)
        a=temp_x//size
        b=temp_y//size
        temp_x=temp_x-a*size
        temp_y=temp_y-b*size
        quadkey=quadkey+str(a+2*b)
    return quadkey
##############################################################################


##############################################################################
#                                                                            #
# V  :  Une texture est un fichier image de 4096x4096 pixels, obtenu à       #
#       partir de 256 vignettes accolées en 16 lignes et 16 colonnes.        #
#       Ce sont elles qui seront chargées ensuite par X-Plane.               #
#       La section qui suit propose entre autres des méthodes pour           #
#       télécharger et créer ces textures, déterminer si un masque alpha     #
#       de bord de mer est nécessaire, écrire les fichiers .ter ou encore    #
#       associer un pixel à un point géographique, et inversément.           #
#                                                                            #
##############################################################################

##############################################################################
#  Comment appeler le bébé ?
##############################################################################
def filename_from_attributes(strlat,strlon,til_x_left,til_y_top,\
                             zoomlevel,website):
    file_dir=Ortho4XP_dir+dir_sep+"Orthophotos"+dir_sep+strlat+strlon+\
                    dir_sep+website+'_'+str(zoomlevel)+dir_sep
    #if website=='g2xpl_8':
    #    file_name='g2xpl_8_'+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
    #            str(2**zoomlevel-8-til_y_top)
    #elif website=='g2xpl_16':
    #    file_name='g2xpl_16_'+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
    #            str(2**zoomlevel-16-til_y_top)
    #else:
    file_name=str(til_y_top)+"_"+str(til_x_left)+"_"+website+str(zoomlevel)   
    file_ext=".jpg"
    return [file_dir,file_name,file_ext]
##############################################################################

##############################################################################
#  Y suis-je ? (dans le rectangle)
##############################################################################
def is_in_region(lat,lon,latmin,latmax,lonmin,lonmax):
    if (lat>=latmin and lat<=latmax and lon>=lonmin and lon<=lonmax):
        retval=True
    else:
        retval=False
    return retval
##############################################################################

##############################################################################
def wgs84_to_texture(lat,lon,zoomlevel,website):
    ratio_x=lon/180           
    ratio_y=log(tan((90+lat)*pi/360))/pi
    #if website=='g2xpl_8':
    #    mult=2**(zoomlevel-4)
    #    til_x=int((ratio_x+1)*mult)*8
    #    til_y=int((1-ratio_y)*mult)*8
    #else:
    mult=2**(zoomlevel-5)
    til_x=int((ratio_x+1)*mult)*16
    til_y=int((1-ratio_y)*mult)*16
    return [til_x,til_y]
##############################################################################

##############################################################################
# Cfr. le manuel de DSFTool (wiki.x-plane.com), ce sont les coordonnées à 
# l'intérieur d'une texture avec (0,0) en bas à gauche et (1,1) en haut à 
# droite.
##############################################################################
def st_coord(lat,lon,tex_x,tex_y,zoomlevel,website):                        
    """
    ST coordinates of a point in a texture
    """
    if website=='SE2':
        [latmax,lonmin]=gtile_to_wgs84(tex_x,tex_y,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(tex_x+16,tex_y+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg4326,epsg3006,lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg4326,epsg3006,lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg4326,epsg3006,lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg4326,epsg3006,lonmax,latmin)
        minx=min(ulx,llx)
        maxx=max(urx,lrx)
        miny=min(lly,lry)
        maxy=max(uly,ury)
        deltax=maxx-minx
        deltay=maxy-miny
        [x,y]=pyproj.transform(epsg4326,epsg3006,lon,lat)
        s=(x-minx)/deltax
        t=(y-miny)/deltay
        s = s if s>=0 else 0
        s = s if s<=1 else 1
        t = t if t>=0 else 0
        t = t if t<=1 else 1
        return [s,t]
    elif website=='NO':
        [latmax,lonmin]=gtile_to_wgs84(tex_x,tex_y,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(tex_x+16,tex_y+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg4326,epsg32632,lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg4326,epsg32632,lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg4326,epsg32632,lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg4326,epsg32632,lonmax,latmin)
        minx=min(ulx,llx)
        maxx=max(urx,lrx)
        miny=min(lly,lry)
        maxy=max(uly,ury)
        deltax=maxx-minx
        deltay=maxy-miny
        [x,y]=pyproj.transform(epsg4326,epsg32632,lon,lat)
        s=(x-minx)/deltax
        t=(y-miny)/deltay
        s = s if s>=0 else 0
        s = s if s<=1 else 1
        t = t if t>=0 else 0
        t = t if t<=1 else 1
        return [s,t]
    #elif website=='g2xpl_8':
    #    ratio_x=lon/180           
    #    ratio_y=log(tan((90+lat)*pi/360))/pi
    #    mult=2**(zoomlevel-4)
    #    s=(ratio_x+1)*mult-(tex_x//8)
    #    t=1-((1-ratio_y)*mult-tex_y//8)
    #    s = s if s>=0 else 0
    #    s = s if s<=1 else 1
    #    t = t if t>=0 else 0
    #    t = t if t<=1 else 1
    #    return [s,t]
    else: #if website in px256_list+wms2048_list:
        ratio_x=lon/180           
        ratio_y=log(tan((90+lat)*pi/360))/pi
        mult=2**(zoomlevel-5)
        s=(ratio_x+1)*mult-(tex_x//16)
        t=1-((1-ratio_y)*mult-tex_y//16)
        s = s if s>=0 else 0
        s = s if s<=1 else 1
        t = t if t>=0 else 0
        t = t if t<=1 else 1
        return [s,t]
##############################################################################

##############################################################################
def attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,ortho_list,tri_type):
    bary_lat=(lat1+lat2+lat3)/3
    bary_lon=(lon1+lon2+lon3)/3
    asked_for=False
    if tri_type in ['2','3']:
        if sea_texture_params!=[]:
            website=sea_texture_params[0]
            zoomlevel=sea_texture_params[1]
            return wgs84_to_texture(bary_lat,bary_lon,zoomlevel,website)+\
                [zoomlevel]+[website]
    for region in ortho_list:
        if point_in_polygon([bary_lat,bary_lon],region[0]):
            zoomlevel=int(region[1])
            website=str(region[2])
            asked_for=True
            break
    if asked_for==False:
        return 'None'
    else:
        return wgs84_to_texture(bary_lat,bary_lon,zoomlevel,website)+\
                [zoomlevel]+[website]
##############################################################################


##############################################################################
#  The master procedure to download pieces of what will become a 4K texture.
#  The process depend on the provider.
##############################################################################
def download_texture(til_x_left,til_y_top,zoomlevel,website):
    jobs=[]
    if website in px256_list:
        for til_y in range(til_y_top,til_y_top+16):
            fargs=[til_x_left,til_y_top,til_y,zoomlevel,website]
            connection_thread=threading.Thread(target=obtain_texture_row,\
                          args=fargs)
            jobs.append(connection_thread)
    elif website in wms2048_list:
        for monty in [0,1]:
            for montx in [0,1]:
                fargs=[til_x_left,til_y_top,zoomlevel,website,montx,monty]
                connection_thread=threading.Thread(target=obtain_wms_image,\
                        args=fargs)
                jobs.append(connection_thread)
    else:
        print("!!! The requested provider no longer seems to be activated in your address book !!!")
        return
    for j in jobs:
        j.start()
    for j in jobs:
        j.join()
    return


def obtain_texture_row(til_x_left,til_y_top,til_y,zoomlevel,website):
    """
    Obtain 8 or 16 gtiles in a row, http transactions take time so better 
    stay in line for a few consecutive tiles. We shall thread these calls in 
    the next function.
    """
    s=requests.Session()
    for til_x in range(til_x_left,til_x_left+16):
        [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
        successful_download=False
        while successful_download==False:
            try:
                r=s.get(url, headers=fake_headers,timeout=10)
                if 'image' in r.headers['Content-Type'] or check_tms_response==False: 
                    successful_download=True
                else:
                    if use_bing_for_non_existent_data==True:
                        [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,'BI')
                    else:
                        print("Presumably a missed cache or non existent data, will try again in 1sec...")
                        print("(Leave check_response unchecked if you want to bypass this)")
                        #print(r.headers)
                        time.sleep(1)
            except requests.exceptions.RequestException as e:   
                print(e)
                print("We will try again in 1sec...")
                try:
                    if application.red_flag.get()==1:
                        print("Download process interrupted.")
                        return
                except:
                    pass
                time.sleep(1)
        filename=Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"image-"+str(til_x_left)+\
                 "-"+str(til_y_top)+"-"+str(til_y-til_y_top).zfill(2)+"-"+\
                 str(til_x-til_x_left).zfill(2)+".jpg"
        file=open(filename,"wb")
        if ('Response [20' in str(r)):
            file.write(r.content)
        else:
            os.system(copy_cmd+' "'+Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
                      'white.jpg'+'" "'+filename+'" '+devnull_rdir) 
        file.close()
    return
##############################################################################


##############################################################################
# Obtain a piece of texture from a wms 
##############################################################################
def obtain_wms_image(til_x_left,til_y_top,zoomlevel,website,montx,monty):
    til_x=til_x_left+montx*8
    til_y=til_y_top+monty*8
    [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
    file_ext=".jpg" 
    filename=Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"image-"+str(til_x_left)+\
             "-"+str(til_y_top)+"-"+str(monty)+"-"+str(montx)+file_ext
    successful_download=False
    tentatives=0
    while successful_download==False:
        s=requests.Session()
        try:
            r=s.get(url, headers=fake_headers,timeout=wms_timeout)
            if ('Response [20' in str(r)):
                if 'image' in r.headers['Content-Type']:
                    if len(r.content)>=tricky_provider_hack or tentatives>=5:
                        file=open(filename,"wb")
                        file.write(r.content)
                        file.close()
                        successful_download=True
                    else:
                        tentatives+=1
                else:
                    print("server "+str(url[10])+" error, len(r.content)="+\
                          str(len(r.content))+", : retrying in 2 secs...")
                    try:
                        if application.red_flag.get()==1:
                            print("Download process interrupted.")
                            return
                    except:
                        pass
                    #print(r.content)
                    # let's try another random server...
                    [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
                    time.sleep(2)
            else:
                print("Server said no data : ", r," , using white square instead")
                os.system(copy_cmd+' "'+Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
                      'white2048.jpg'+'" "'+filename+'" '+devnull_rdir) 
                successful_download=True
        except requests.exceptions.RequestException as e:    
            print(e)
            print("We will try again in 2sec...")
            # let's try another random server...
            try:
                if application.red_flag.get()==1:
                    print("Download process interrupted.")
                    return
            except:
                    pass
            [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
            time.sleep(2)
    return
##############################################################################

##############################################################################
def montage_texture(strlat,strlon,til_x_left,til_y_top,zoomlevel,website):
    global convert_to_do_list,busy_slots_mont
    busy_slots_mont+=1
    #print("Busy montage slots : "+str(busy_slots_mont))
    [file_dir,file_name,file_ext]=\
            filename_from_attributes(strlat,strlon,til_x_left,til_y_top,\
                                          zoomlevel,website)
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    if website in px256_list:
        cmd_mont=montage_cmd+' -tile 16x16 -geometry 256x256+0+0 '+\
                 Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'image-'+\
                 str(til_x_left)+'-'+str(til_y_top)+'-*.jpg'+' "'+\
                 file_dir+file_name+file_ext+'" ' +devnull_rdir
        os.system(cmd_mont)
    elif website in wms2048_list:
        cmd_mont=montage_cmd+' -tile 2x2 -geometry 2048x2048+0+0 '+\
                 Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'image-'+\
                 str(til_x_left)+'-'+str(til_y_top)+'-*'+file_ext+' "'+\
                 file_dir+file_name+file_ext+'" '
        os.system(cmd_mont)  
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+\
              dir_sep+'image-'+str(til_x_left)+'-' +str(til_y_top)+\
              '-*'+file_ext+devnull_rdir)
    if convert_to_do_list!='':
        convert_to_do_list.append([til_x_left,til_y_top,zoomlevel,website])
    busy_slots_mont-=1
    return
##############################################################################
        
##############################################################################
def build_texture(strlat,strlon,til_x_left,til_y_top,zoomlevel,website):
    [file_dir,file_name,file_ext]=\
            filename_from_attributes(strlat,strlon,til_x_left,til_y_top,\
                                            zoomlevel,website)
    if os.path.isfile(file_dir+file_name+file_ext) != True:
        if verbose_output==True:
            print("   Downloading missing orthophoto "+\
                file_name+file_ext+".")
        download_texture(til_x_left,til_y_top,zoomlevel,website)
        try:
            if application.red_flag.get()==1:
                print("Download process interrupted.")
                return
        except:
                pass
        montage_texture(strlat,strlon,til_x_left,til_y_top,zoomlevel,website)
    else:
        if verbose_output==True:
            print("   The orthophoto "+file_name+file_ext+" is already present.")
    return 
##############################################################################

###############################################################################
def build_texture_region(latmin,latmax,lonmin,lonmax,zoomlevel,website):
    [til_xmin,til_ymin]=wgs84_to_texture(latmax,lonmin,zoomlevel,website)
    [til_xmax,til_ymax]=wgs84_to_texture(latmin,lonmax,zoomlevel,website)
    print("Number of tiles to download (at most) : "+\
           str(((til_ymax-til_ymin)/16+1)*((til_xmax-til_xmin)/16+1)))
    for til_y_top in range(til_ymin,til_ymax+1,16):
        for til_x_left in range(til_xmin,til_xmax+1,16):
            build_texture('XXX','YYY',til_x_left,til_y_top,zoomlevel,website)
    return   
###############################################################################

###############################################################################
def create_tile_preview(latmin,lonmin,zoomlevel,website):
    strlat='{:+.0f}'.format(latmin).zfill(3)
    strlon='{:+.0f}'.format(lonmin).zfill(4)
    if not os.path.exists(Ortho4XP_dir+dir_sep+'Previews'):
        os.makedirs(Ortho4XP_dir+dir_sep+'Previews') 
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'Previews'+\
               dir_sep+'image-*.jpg '+devnull_rdir)
    filepreview=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+strlat+\
                  strlon+"_"+website+str(zoomlevel)+".jpg"       
    if os.path.isfile(filepreview) != True:
        [til_x_min,til_y_min]=wgs84_to_gtile(latmin+1,lonmin,zoomlevel)
        [til_x_max,til_y_max]=wgs84_to_gtile(latmin,lonmin+1,zoomlevel)
        s=requests.Session()
        total_x=(til_x_max+1-til_x_min)
        for til_x in range(til_x_min,til_x_max+1):
            for til_y in range(til_y_min,til_y_max+1):
                successful_download=False
                while successful_download==False:
                    try:
                        [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
                        r=s.get(url, headers=fake_headers)
                        successful_download=True
                    except:
                        #print("Connexion avortée par le serveur, nouvelle tentative dans 1sec")
                        time.sleep(1)
                filename=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+'image-'\
                         +str(til_y-til_y_min).zfill(3)+'-'+\
                          str(til_x-til_x_min).zfill(3)+'.jpg'
                file=open(filename,"wb")
                if ('Response [20' in str(r)):
                    file.write(r.content)
                else:
                    os.system(copy_cmd+' "'+Ortho4XP_dir+dir_sep+'Utils'+\
                                    dir_sep+'white.jpg'+'" "'+filename+'" '+devnull_rdir) 
                file.close()
            #try:
            application.preview_window.progress_preview.set(int(100*(til_x+1-til_x_min)/total_x))
            #except:
            #    pass
        nx=til_x_max-til_x_min+1
        ny=til_y_max-til_y_min+1
        os.system(montage_cmd+' -tile '+str(nx)+'x'+str(ny)+\
                  ' -geometry 256x256+0+0 "'+Ortho4XP_dir+dir_sep+\
                  'Previews'+dir_sep+'image-*.jpg'+'" "'+filepreview+'" '+devnull_rdir)
        os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'Previews'+\
                   dir_sep+'image-*.jpg '+devnull_rdir)
        return
##############################################################################


##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les zones non immergées).
##############################################################################
def create_terrain_file(file_name,til_x_left,til_y_top,zoomlevel,website):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+'.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
    half_meridian=pi*6378137
    texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
    file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')
    if use_decal_on_terrain==True:
        file.write('DECAL_LIB lib/g10/decals/maquify_1_green_key.dcl\n')
    file.write('NO_SHADOW\n')
    file.close()
    return
##############################################################################

##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les lacs et rivières).
##############################################################################
def create_overlay_file(file_name,til_x_left,til_y_top,zoomlevel,website):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+\
            '_overlay.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
    half_meridian=pi*6378137
    texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
    file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')  
    file.write('WET\n')
    file.write('BORDER_TEX ../textures/water_transition.png\n')
    file.write('NO_SHADOW\n')
    file.close()
    return
##############################################################################

##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les mers et océans).
##############################################################################
def create_sea_overlay_file(file_name,mask_name,til_x_left,til_y_top,\
        zoomlevel,website):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+\
            '_sea_overlay.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
    half_meridian=pi*6378137
    texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
    file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')
    file.write('WET\n')
    file.write('BORDER_TEX ../textures/'+mask_name+'\n')
    file.write('NO_SHADOW\n')
    if use_additional_water_shader==True:
        file.write('TEXTURE_NORMAL 128 ../textures/water_normal_map.png\n')
        file.write('SPECULAR 0.2\n')
    file.close()
    return
##############################################################################

##############################################################################
#  Y a-t-il besoin de mettre un masque ?
##############################################################################
def which_mask(layer,strlat,strlon):
    tilx=layer[0]
    tily=layer[1]
    zoomlevel=layer[2]
    website=layer[3]
    factor=2**(zoomlevel-14)
    tilx14=(int(tilx/factor)//16)*16
    tily14=(int(tily/factor)//16)*16
    #rx=(tilx/factor)%16
    rx=int((tilx-factor*tilx14)/16)
    #ry=(tily/factor)%16
    ry=int((tily-factor*tily14)/16)
    mask_file_spec=Ortho4XP_dir+dir_sep+'Masks'+dir_sep+strlat+strlon+dir_sep+\
            str(int(tily14))+'_'+str(int(tilx14))+'_'+website+'.png'
    mask_file_gen=Ortho4XP_dir+dir_sep+'Masks'+dir_sep+strlat+strlon+dir_sep+\
            str(int(tily14))+'_'+str(int(tilx14))+'.png'
    if os.path.isfile(mask_file_spec):
        mask_file=mask_file_spec
    elif os.path.isfile(mask_file_gen):
        mask_file=mask_file_gen
    else:
        return 'None'
    mask_tmp=Ortho4XP_dir+dir_sep+'Masks'+dir_sep+'test_mask.png'
    os.system(convert_cmd+' "'+mask_file+'" '+'-crop '+\
              str(int(4096/factor))+'x'+str(int(4096/factor))+'+'+\
               str(int(rx*4096/factor))+'+'+str(int(ry*4096/factor))+' +repage "'+\
                mask_tmp+'" '+devnull_rdir)
    check_black_cmd=convert_cmd+' '+mask_tmp+' -format "%[mean]" info:'
    mean=subprocess.check_output(check_black_cmd, shell=True)
    if "b'0" in str(mean):   # check when imagemagick is updated if not broken
        return 'None'
    else:
        return [mask_file,factor,rx,ry]
##############################################################################
 
##############################################################################
#  La routine de conversion jpeg -> dds, avec éventuel calcul du masque alpha.
##############################################################################
def convert_texture(file_dir,file_name,website):
    global busy_slots_conv
    busy_slots_conv+=1
    #print("Busy convert slots : "+str(busy_slots_conv))
    ctr_adj=0
    brt_adj=0
    sat_adj=0
    if website in contrast_adjust:
        ctr_adj=contrast_adjust[website]
    if website in brightness_adjust:
        brt_adj=brightness_adjust[website]
    if website in saturation_adjust:
        sat_adj=saturation_adjust[website]
    file_ext=".jpg"
    color_cmd=''
    if (website in full_color_correction) and  (full_color_correction[website]!=''):
        color_correction = full_color_correction[website]
        color_cmd = convert_cmd+' '+color_correction+' "'+\
                   file_dir+file_name+file_ext+'" "'+\
                   Ortho4XP_dir+dir_sep+'tmp'+dir_sep+file_name+'.png" '+devnull_rdir
    elif (ctr_adj!=0) or (brt_adj!=0) or (sat_adj!=0):
        color_cmd = convert_cmd+" -brightness-contrast "+\
                str(brt_adj)+"x"+str(ctr_adj)+\
                 " -modulate 100,"+str(100+sat_adj)+",100 "+\
                 '"'+file_dir+file_name+file_ext+'" "'+\
                 Ortho4XP_dir+dir_sep+'tmp'+dir_sep+file_name+'.png" '+devnull_rdir
    if color_cmd!='':
        os.system(color_cmd)
        conv_cmd=convert_cmd_bis +' "'+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+file_name+'.png" "'+\
                     build_dir+dir_sep+'textures'+dir_sep+file_name+'.'+dds_or_png+'" '+ devnull_rdir
        os.system(conv_cmd)
        os.remove(Ortho4XP_dir+dir_sep+'tmp'+dir_sep+file_name+'.png')
    else:
        conv_cmd=convert_cmd_bis + ' "'+file_dir+file_name+file_ext+'" "'+build_dir+dir_sep+\
                   'textures'+dir_sep+file_name+'.'+dds_or_png+'" '+devnull_rdir
        os.system(conv_cmd)
    busy_slots_conv-=1
    return 
##############################################################################

##############################################################################
#  Le séquenceur de la phase de téléchargement des textures.
##############################################################################
def download_textures(strlat,strlon):
    global download_to_do_list,montage_to_do_list,convert_to_do_list
    finished = False
    nbr_done=0
    nbr_done_or_in=0
    while finished != True:
        if download_to_do_list == [] or len(montage_to_do_list)>=20:
            time.sleep(0.1)
            try:
                if application.red_flag.get()==1:
                    print("Download process interrupted.")
                    return
            except:
                pass
        elif download_to_do_list[0] != 'finished':
            texture=download_to_do_list[0]
            [file_dir,file_name,file_ext]=filename_from_attributes(\
                               strlat,strlon,*texture)
            if os.path.isfile(file_dir+file_name+file_ext) != True:
                if verbose_output==True:
                    print("   Downloading missing orthophoto "+\
                      file_name+file_ext)
                download_texture(*texture)
                nbr_done+=1
                nbr_done_or_in+=1
                montage_to_do_list.append(texture)
            else:
                nbr_done_or_in+=1
                if verbose_output==True:
                    print("   The orthophoto "+file_name+file_ext+\
                                                    " is already present.")
                convert_to_do_list.append(texture)
            download_to_do_list.pop(0)
            try:
                application.progress_down.set(int(100*nbr_done_or_in/(nbr_done_or_in+len(download_to_do_list)))) 
                if application.red_flag.get()==1:
                    print("Download process interrupted.")
                    return
            except:
                pass
        else:
            finished=True
            try:
                application.progress_down.set(100) 
            except:
                pass
            if nbr_done >= 1:
                print("  Download of textures completed."+\
                      "                      ")
            montage_to_do_list.append('finished')
    return
##############################################################################

##############################################################################
#  Le séquenceur de la phase de montage des vignettes en textures.
##############################################################################
def montage_textures(strlat,strlon):
    global montage_to_do_list,convert_to_do_list,busy_slots_mont
    busy_slots_mont=0
    nbr_done=0
    finished = False
    while finished != True:
        if montage_to_do_list == [] or busy_slots_mont >= max_montage_slots:
            time.sleep(0.1)
            try:
                if application.red_flag.get()==1:
                    print("Mounting process interrupted.")
                    return
            except:
                pass
        elif montage_to_do_list[0] != 'finished':
            texture=montage_to_do_list.pop(0)
            fargs_mont_text=[strlat,strlon]+texture 
            threading.Thread(target=montage_texture,args=fargs_mont_text).start()
            #busy_slots_mont+=1
            #montage_texture(strlat,strlon,*texture)
            nbr_done+=1
            #convert_to_do_list.append(texture)
            try:
                application.progress_mont.set(int(100*nbr_done/(nbr_done+len(montage_to_do_list)))) 
                if application.red_flag.get()==1:
                    print("Mounting process interrupted.")
                    return
            except:
                pass
        else:
            finished=True
            if nbr_done >= 1:
                print("  Waiting for all montage threads to finish.")
                while busy_slots_mont > 0:
                    print("  ...")
                    time.sleep(3)
                try:
                    application.progress_mont.set(100) 
                except:
                    pass
                print("  Mounting of textures completed."+\
                      "                             ")
            time.sleep(1)
            convert_to_do_list.append('finished')
    return
##############################################################################

##############################################################################
#  Le séquenceur de la phase de conversion jpeg -> dds.
##############################################################################
def convert_textures(strlat,strlon):
    global convert_to_do_list,busy_slots_conv
    busy_slots_conv=0
    nbr_done=0
    nbr_done_or_in=0
    if not os.path.exists(build_dir+dir_sep+'textures'):
            os.makedirs(build_dir+dir_sep+'textures')
    finished = False
    while finished != True:
        if convert_to_do_list == [] or busy_slots_conv >= max_convert_slots:
            time.sleep(0.1)
            try:
                if application.red_flag.get()==1:
                    print("Convert process interrupted.")
                    return
            except:
                pass
        elif convert_to_do_list[0] != 'finished':
            texture=convert_to_do_list.pop(0)
            [file_dir,file_name,file_ext]=filename_from_attributes(\
                                                    strlat,strlon,*texture)
            if (os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                 file_name+'.'+dds_or_png) != True ):
                if verbose_output==True:
                    print("   Converting orthophoto to build texture "
                      +file_name+'.'+dds_or_png+".")
                fargs_conv_text=[file_dir,file_name,texture[3]] 
                threading.Thread(target=convert_texture,args=fargs_conv_text).start()
                #convert_texture(file_dir,file_name,texture[3])
                #busy_slots_conv+=1
                #conv_text_thread.start()
                nbr_done+=1
                #print(" "+str(nbr_done)+" ")
                nbr_done_or_in+=1
                #sys.stdout.write("  Textures déjà converties : "\
                #        +str(nbr_done)+" (restent :"+\
                #        str(len(convert_to_do_list)-1)+")             \r") 
            else:
                nbr_done_or_in+=1
                if verbose_output==True:
                    print("   Texture file "+file_name+"."+dds_or_png+\
                      " already present.")

            try:
                application.progress_conv.set(int(100*nbr_done_or_in/(nbr_done_or_in+len(convert_to_do_list)))) 
                if application.red_flag.get()==1:
                    print("Conversion process interrupted.")
                    return
            except:
                pass
        else:
            finished=True
            if nbr_done >= 1:
                print("  Waiting for all convert threads to finish.")
                while busy_slots_conv > 0:
                    print("  ...")
                    time.sleep(3)
                application.progress_conv.set(100) 
                print("  Conversion of textures completed."+\
                      "                         ")
    return
##############################################################################


##############################################################################
#                                                                            #
#  VI: La méthode maître après le mailleur, elle attribue les textures et    #
#      crée au final le DSF.                                                 #
#                                                                            #
##############################################################################


##############################################################################
def build_dsf(lat0,lon0,ortho_list,water_overlay,\
        ratio_water,mesh_filename):
    global download_to_do_list,pools_max_points
    pool_cols           = 16
    pool_rows           = 16
    strlat='{:+.0f}'.format(lat0).zfill(3)
    strlon='{:+.0f}'.format(lon0).zfill(4)
    strlatround='{:+.0f}'.format(floor(lat0/10)*10).zfill(3)
    strlonround='{:+.0f}'.format(floor(lon0/10)*10).zfill(4)
    dest_dir=build_dir+dir_sep+'Earth nav data'+dir_sep+strlatround+\
            strlonround
    dsf_filename=dest_dir+dir_sep+strlat+strlon+'.dsf'
    
    print("-> Computing the required pool division") 
    f_mesh=open(mesh_filename,"r")
    for i in range(0,4):
        f_mesh.readline()
    pool_nbr=pool_rows*pool_cols
    pool_pt_count=numpy.zeros(pool_nbr,'uint32')
    nbr_pt_in=int(f_mesh.readline())
    for i in range(0,nbr_pt_in):
        tmplist=f_mesh.readline().split()
        lon=float(tmplist[0])
        lat=float(tmplist[1])
        pool_x=int((lon-lon0)*pool_cols)
        pool_y=int((lat-lat0)*pool_rows)
        if pool_x==pool_rows:
            pool_x-=1
        if pool_y==pool_cols:
            pool_y-=1
        pool_idx=(pool_y)*pool_cols+(pool_x)
        pool_pt_count[pool_idx]+=1
    maxptpool=numpy.max(pool_pt_count)
    #print(maxptpool)
    if maxptpool>=65355:
        pool_rows=pool_rows*2
        pool_cols=pool_cols*2
        print("   Pool division = 32")
    elif maxptpool<=16383:
        pool_rows=pool_rows//2
        pool_cols=pool_cols//2
        print("   Pool division = 8")
    else:
        print("   Pool division = 16")
    f_mesh.close()

    
    pool_nbr  = pool_rows*pool_cols
    pools_params=numpy.zeros((4*pool_nbr,18),'float32')
    pools_planes=numpy.zeros(4*pool_nbr,'uint32')
    pools_planes[0:pool_nbr]=7
    pools_planes[pool_nbr:2*pool_nbr]=5
    pools_planes[2*pool_nbr:4*pool_nbr]=9
    pools_lengths=numpy.zeros((4*pool_nbr),'uint32')
    try:
        pools=numpy.zeros((4*pool_nbr,9*pools_max_points),'uint16')
        pools_z_temp=numpy.zeros((4*pool_nbr,pools_max_points),'float32')
        pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
        pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
    except:
        try:
            pools_max_points=pools_max_points//2
            pools=numpy.zeros((4*pool_nbr,9*pools_max_points),'uint16')
            pools_z_temp=numpy.zeros((4*pool_nbr,pools_max_points),'float32')
            pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
            pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
            print("\nWARNING : Even though I won't use all of it, for speed purposes I must ")
            print("reserve an amount of RAM which you don't seem have available, I try")
            print("with half of it but it could be that the process has to stop.\n")
        except:
            try:
                pools_max_points=pools_max_points//2
                pools=numpy.zeros((4*pool_nbr,9*pools_max_points),'uint16')
                pools_z_temp=numpy.zeros((4*pool_nbr,pools_max_points),'float32')
                pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
                pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
                print("\nWARNING : Even though I won't use all of it, for speed purposes I must ")
                print("reserve an amount of RAM which you don't seem have available, I try")
                print("with one fourth of it but it could be that the process has to stop.\n")
            except:
                return
    dico_new_pt={}
    dico_textures={'terrain_Water':0,'None':1}
    terrain_def="terrain_Water\0lib/g10/terrain10/fruit_tmp_wet_hill.ter\0"
    textures={}
    textures[0]=collections.defaultdict(list)
    textures[1]=collections.defaultdict(list)
    skipped_sea_textures=[]
    dico_mask={}

    # initialization of the pools parameters
    
    for pool_y in range(0,pool_rows):       
        for pool_x in range(0,pool_cols):  
            pool_idx=(pool_y)*pool_cols+(pool_x)
            pools_params[pool_idx,0]=1/pool_cols
            pools_params[pool_idx,1]=lon0+pool_x/pool_cols # lon
            pools_params[pool_idx,2]=1/pool_rows
            pools_params[pool_idx,3]=lat0+pool_y/pool_rows # lat 
            pools_params[pool_idx,4]=0
            pools_params[pool_idx,5]=0             # z (temp)
            pools_params[pool_idx,6]=2     
            pools_params[pool_idx,7]=-1            # u 
            pools_params[pool_idx,8]=2     
            pools_params[pool_idx,9]=-1            # v
            pools_params[pool_idx,10]=1    
            pools_params[pool_idx,11]=0            # s
            pools_params[pool_idx,12]=1    
            pools_params[pool_idx,13]=0            # t
            pools_params[pool_idx,14]=1    
            pools_params[pool_idx,15]=0            # bs
            pools_params[pool_idx,16]=1    
            pools_params[pool_idx,17]=0            # bt
    pools_params[pool_nbr:2*pool_nbr]=pools_params[0:pool_nbr]
    pools_params[2*pool_nbr:3*pool_nbr]=pools_params[0:pool_nbr]
    pools_params[3*pool_nbr:4*pool_nbr]=pools_params[0:pool_nbr]
    
    # We start by encoding the 5 coordinates (x,y,z,u,v) of the physical points of
    # the mesh into the array pt_in
    
    f_mesh=open(mesh_filename,"r")
    for i in range(0,4):
        f_mesh.readline()
    nbr_pt_in=int(f_mesh.readline())
    pt_in=numpy.zeros(5*nbr_pt_in,'float')
    for i in range(0,nbr_pt_in):
        tmplist=f_mesh.readline().split()
        pt_in[5*i]=float(tmplist[0])
        pt_in[5*i+1]=float(tmplist[1])
        pt_in[5*i+2]=float(tmplist[2])
    for i in range(0,3):
        f_mesh.readline()
    for i in range(0,nbr_pt_in):
        tmplist=f_mesh.readline().split()
        pt_in[5*i+3]=float(tmplist[0])
        pt_in[5*i+4]=float(tmplist[1])
   
    # Next, we go through the Triangle section of the mesh file and build DSF 
    # mesh points (these take into accound texture as well), point pools, etc. 
    
    for i in range(0,2): # skip 2 lines
        f_mesh.readline()
    nbr_tri_in=int(f_mesh.readline()) # read nbr of tris
    len_dico_new_pt=0
    total_cross_pool=0
    step_stones=nbr_tri_in//100
    percent=-1
    for i in range(0,nbr_tri_in):
        if i%step_stones==0:
            percent+=1
            try:
                application.progress_attr.set(int(percent*9/10))
                if application.red_flag.get()==1:
                    print("Attribution process interrupted.")
                    return
            except:
                pass
        tmplist=f_mesh.readline().split()
        # look for the texture that will possibly cover the tri
        n1=int(tmplist[0])-1
        n2=int(tmplist[1])-1
        n3=int(tmplist[2])-1
        tri_type=tmplist[3] 
        if int(tri_type)>=4:
            tri_type='0'
        [lon1,lat1,z1,u1,v1]=pt_in[5*n1:5*n1+5]
        [lon2,lat2,z2,u2,v2]=pt_in[5*n2:5*n2+5]
        [lon3,lat3,z3,u3,v3]=pt_in[5*n3:5*n3+5]
        texture=attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,ortho_list,tri_type)
        
        # do we need to download a texture and/or to create a ter file ?       
        if (tri_type=='0'):
            if str(texture) in dico_textures: # 'None' is in dico_textures by definition
                texture_idx=dico_textures[str(texture)]
            else:
                texture_idx=len(dico_textures)
                dico_textures[str(texture)]=texture_idx
                textures[texture_idx]=collections.defaultdict(list)
                [file_dir,file_name,file_ext]=\
                        filename_from_attributes(strlat,strlon,*texture)
                if ((str(texture)+'_overlay') not in dico_textures) and \
                           ((str(texture)+'_sea_overlay') not in dico_textures):
                    if (os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                            file_name+'.'+dds_or_png) != True ):
                        download_to_do_list.append(texture)
                    else:
                        if verbose_output==True:
                            print("   Texture file "+file_name+"."+dds_or_png+\
                            " already present.")
                create_terrain_file(file_name,*texture)
                terrain_def+='terrain/'+file_name+'.ter\0' 
            texture_overlay_idx=-1
        elif water_option in [2,3]:
            texture_idx=0
            if (tri_type=='1' and use_masks_for_inland==False) and (texture != 'None'):
                if str(texture)+'_overlay' in dico_textures:
                    texture_overlay_idx=dico_textures[str(texture)+'_overlay']
                else:
                    texture_overlay_idx=len(dico_textures)
                    dico_textures[str(texture)+'_overlay']=texture_overlay_idx
                    textures[texture_overlay_idx]=collections.defaultdict(list)
                    [file_dir,file_name,file_ext]=\
                            filename_from_attributes(strlat,strlon,*texture)
                    if (str(texture) not in dico_textures) and \
                            ((str(texture)+'_sea_overlay') not in dico_textures):
                        if (os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                            file_name+'.'+dds_or_png) != True ):
                            download_to_do_list.append(texture)
                        else:
                            if verbose_output==True:
                                print("   Texture file "+file_name+"."+dds_or_png+\
                                " already present.")
                    create_overlay_file(file_name,*texture)
                    terrain_def+='terrain/'+file_name+'_overlay.ter\0' 
            elif (tri_type in ['2','3'] or use_masks_for_inland==True) and (texture != 'None'):
                if str(texture)+'_sea_overlay' in dico_textures:
                    texture_overlay_idx=dico_textures[str(texture)+'_sea_overlay']
                elif str(texture) not in skipped_sea_textures:
                    mask_data = which_mask(texture,strlat,strlon)
                    dico_mask[str(texture)]=mask_data
                    if mask_data != 'None':
                        if verbose_output==True:
                            print("      Use of an alpha mask.")
                        mask_name=mask_data[0].split(dir_sep)[-1]
                        if os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                             mask_name) != True:
                            os.system(copy_cmd+' "'+mask_data[0]+'" "'+build_dir+\
                             dir_sep+'textures'+dir_sep+mask_name+'" '+devnull_rdir)
                        texture_overlay_idx=len(dico_textures)
                        dico_textures[str(texture)+'_sea_overlay']=texture_overlay_idx
                        textures[texture_overlay_idx]=collections.defaultdict(list)
                        [file_dir,file_name,file_ext]=\
                                filename_from_attributes(strlat,strlon,*texture)
                        if (str(texture) not in dico_textures) and \
                            ((str(texture)+'_overlay') not in dico_textures):
                            if (os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
                                file_name+'.'+dds_or_png) != True ):
                                download_to_do_list.append(texture)
                            else:
                                if verbose_output==True:
                                    print("   Texture file "+file_name+"."+dds_or_png+\
                                    " already present.")
                        create_sea_overlay_file(file_name,mask_name,*texture)
                        terrain_def+='terrain/'+file_name+'_sea_overlay.ter\0' 
                    else:    
                        skipped_sea_textures.append(str(texture))
                        texture_overlay_idx=-1
                else:
                    texture_overlay_idx=-1
            else: # texture = 'None'
                texture_overlay_idx=-1
        else:  # water_overlay = False
            texture_idx=0
            texture_overlay_idx=-1
        
        # now we put the tri in the right texture(s)   
        tri_p=[]
        if tri_type == '0':
            for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                if str(n)+'_'+str(texture_idx) in dico_new_pt:
                    [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_'+str(texture_idx)]
                else:
                    [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                    if texture!='None':
                        [s,t]=st_coord(lat,lon,*texture)
                    else:
                        [s,t]=[0,0]
                    len_dico_new_pt+=1
                    [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                            pools_params,pool_cols,pool_rows)
                    pos_in_pool=pools_lengths[pool_idx]
                    dico_new_pt[str(n)+'_'+str(texture_idx)]=[pool_idx,pos_in_pool]
                    pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                            pool_ny,0,round((1+normal_map_strength*u)/2*65535),round((1+normal_map_strength*v)/2*65535),\
                            round(s*65535),round(t*65535)]
                    pools_z_temp[pool_idx,pos_in_pool]=z
                    pools_z_max[pool_idx] = pools_z_max[pool_idx] if pools_z_max[pool_idx] >= z else z
                    pools_z_min[pool_idx] = pools_z_min[pool_idx] if pools_z_min[pool_idx] <= z else z
                    pools_lengths[pool_idx]+=1
                    if pools_lengths[pool_idx]==pools_max_points:
                        print("We have reached the maximum allowed number of points in the pool\n",
                              "centered at lat=", pools_params[pool_idx,3]+\
                              0.5*pools_params[pool_idx,2]," lon=",pools_params[pool_idx,1]+\
                              0.5*pools_params[pool_idx,0])
                        print("You should try the following : 1) test with a higher value of curv_tol (say 3 and \n"+\
                              "then lower untill before it breaks) 2) if it still doesn't work, look for an error on \n"+\
                              "OpenStreetMap (presumably encroached water segments or two nodes that should be one) in \n"+\
                              "a 1 mile radius of the indicated point.")
                        print("")
                        print("Failure.")
                        print('_____________________________________________________________'+\
                              '____________________________________')
                        return
                tri_p+=[pool_idx,pos_in_pool]
            if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                pool_idx=tri_p[0]
                textures[texture_idx][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]    
            else:
                total_cross_pool+=1
                pool_idx='cross-pool'
                textures[texture_idx][pool_idx]+=tri_p
        else: # water 
            # first x-plane water
            for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                if str(n)+'_0' in dico_new_pt:
                    [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_0']
                else:
                    [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                    len_dico_new_pt+=1
                    [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                            pools_params,pool_cols,pool_rows)
                    pool_idx+=pool_nbr # --> we start x-plane water pools at pool_nbr idx
                    pos_in_pool=pools_lengths[pool_idx]
                    dico_new_pt[str(n)+'_0']=[pool_idx,pos_in_pool]
                    pools[pool_idx,5*pos_in_pool:5*pos_in_pool+5]=[pool_nx,\
                            pool_ny,0,32768,32768]
                    pools_z_temp[pool_idx,pos_in_pool]=z
                    pools_z_max[pool_idx] = pools_z_max[pool_idx] if pools_z_max[pool_idx] >= z else z
                    pools_z_min[pool_idx] = pools_z_min[pool_idx] if pools_z_min[pool_idx] <= z else z
                    pools_lengths[pool_idx]+=1
                    if pools_lengths[pool_idx]==pools_max_points:
                        print("We have reached the maximum allowed number of points in the pool\n",
                              "centered at lat=", pools_params[pool_idx,3]+\
                              0.5*pools_params[pool_idx,2]," lon=",pools_params[pool_idx,1]+\
                              0.5*pools_params[pool_idx,0])
                        print("You should try the following : 1) test with a higher value of curv_tol (say 3 and \n"+\
                              "then lower untill before it breaks) 2) if it still doesn't work, look for an error on \n"+\
                              "OpenStreetMap (presumably encroached water segments or two nodes that should be one) in \n"+\
                              "a 1 mile radius of the indicated point.")
                        print("")
                        print("Failure.")
                        print('_____________________________________________________________'+\
                              '____________________________________')
                        return
                tri_p+=[pool_idx,pos_in_pool]
            if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                pool_idx=tri_p[0]
                textures[0][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]    
            else:
                total_cross_pool+=1
                pool_idx='cross-pool'
                textures[0][pool_idx]+=tri_p
            # next possibly overlays
            if water_overlay==False:
                continue
            if texture_overlay_idx!=-1 and tri_type=='1'and use_masks_for_inland==False:
                tri_p=[]
                for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                    if str(n)+'_'+str(texture_overlay_idx) in dico_new_pt:
                        [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_'+str(texture_overlay_idx)]
                    else:
                        [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                        [s,t]=st_coord(lat,lon,*texture)
                        len_dico_new_pt+=1
                        [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                                pools_params,pool_cols,pool_rows)
                        pool_idx+=2*pool_nbr  # we start textured water pools after x-plane water pools
                        pos_in_pool=pools_lengths[pool_idx]
                        dico_new_pt[str(n)+'_'+str(texture_overlay_idx)]=[pool_idx,pos_in_pool]
                        pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=\
                                [pool_nx,pool_ny,0,32768,32768,round(s*65535),\
                                 round(t*65535),0,round(ratio_water*65535)]
                        pools_z_temp[pool_idx,pos_in_pool]=z
                        pools_z_max[pool_idx] = pools_z_max[pool_idx] \
                                      if pools_z_max[pool_idx] >= z else z
                        pools_z_min[pool_idx] = pools_z_min[pool_idx] \
                                      if pools_z_min[pool_idx] <= z else z
                        pools_lengths[pool_idx]+=1
                        if pools_lengths[pool_idx]==pools_max_points:
                            print("We have reached the maximum allowed number of points in the pool\n",
                                  "centered at lat=", pools_params[pool_idx,3]+\
                                0.5*pools_params[pool_idx,2]," lon=",pools_params[pool_idx,1]+\
                                0.5*pools_params[pool_idx,0])
                            print("You should try the following : 1) test with a higher value of curv_tol (say 3 and \n"+\
                                  "then lower untill before it breaks) 2) if it still doesn't work, look for an error on \n"+\
                                  "OpenStreetMap (presumably encroached water segments or two nodes that should be one) in \n"+\
                                  "a 1 mile radius of the indicated point.")
                            print("")
                            print("Failure.")
                            print('_____________________________________________________________'+\
                              '____________________________________')
                            return
                    tri_p+=[pool_idx,pos_in_pool]
                if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                    pool_idx=tri_p[0]
                    textures[texture_overlay_idx][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]
                    #textures[0][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]
                else:
                    total_cross_pool+=1
                    pool_idx='cross-pool'
                    textures[texture_overlay_idx][pool_idx]+=tri_p
                    #textures[0][pool_idx]+=tri_p
            elif texture_overlay_idx!=-1 and (tri_type in ['2','3'] or use_masks_for_inland==True):
                tri_p=[]
                for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                    if str(n)+'_'+str(texture_overlay_idx) in dico_new_pt:
                        [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_'+str(texture_overlay_idx)]
                    else:
                        [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                        [s,t]=st_coord(lat,lon,*texture)
                        len_dico_new_pt+=1
                        [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                                pools_params,pool_cols,pool_rows)
                        pool_idx+=3*pool_nbr  # we end with textured sea water pools
                        pos_in_pool=pools_lengths[pool_idx]
                        dico_new_pt[str(n)+'_'+str(texture_overlay_idx)]=[pool_idx,pos_in_pool]
                        [ms,mt]=st_coord(lat,lon,texture[0],texture[1],texture[2],'BI') # Masks are always in epsg:4326!
                        mask_data=dico_mask[str(texture)]
                        rx=float(mask_data[2])
                        ry=float(mask_data[3])
                        factor=float(mask_data[1])
                        bs=rx/factor+ms/factor
                        bt=1-ry/factor+(mt-1)/factor
                        pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=[pool_nx,\
                                  pool_ny,0,32768,32768,round(s*65535),round(t*65535),\
                                  round(bs*65535),round(bt*65535)]
                        pools_z_temp[pool_idx,pos_in_pool]=z
                        pools_z_max[pool_idx] = pools_z_max[pool_idx]\
                                        if pools_z_max[pool_idx] >= z else z
                        pools_z_min[pool_idx] = pools_z_min[pool_idx] \
                                        if pools_z_min[pool_idx] <= z else z
                        pools_lengths[pool_idx]+=1
                        if pools_lengths[pool_idx]==pools_max_points:
                            print("We have reached the maximum allowed number of points in the pool\n",
                                  "centered at lat=", pools_params[pool_idx,3]+\
                                0.5*pools_params[pool_idx,2]," lon=",pools_params[pool_idx,1]+\
                                0.5*pools_params[pool_idx,0])
                            print("You should try the following : 1) test with a higher value of curv_tol (say 3 and \n"+\
                                  "then lower untill before it breaks) 2) if it still doesn't work, look for an error on \n"+\
                                  "OpenStreetMap (presumably encroached water segments or two nodes that should be one) in \n"+\
                                  "a 1 mile radius of the indicated point.")
                            print("")
                            print("Failure.")
                            print('_____________________________________________________________'+\
                              '____________________________________')
                            return
                    tri_p+=[pool_idx,pos_in_pool]
                if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                    pool_idx=tri_p[0]
                    textures[texture_overlay_idx][pool_idx]+=\
                            [tri_p[1],tri_p[3],tri_p[5]]
                    #textures[0][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]
                else:
                    total_cross_pool+=1
                    pool_idx='cross-pool'
                    textures[texture_overlay_idx][pool_idx]+=tri_p
                    #textures[0][pool_idx]+=tri_p
    f_mesh.close()
    download_to_do_list.append('finished')
    os.system(copy_cmd+' "'+Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
             'water_transition.png'+'" "'+build_dir+dir_sep+'textures'+\
              dir_sep+'" '+devnull_rdir) 
    print("  Encoding of the DSF file...")  
    if verbose_output==True:
        print("   Final nbr of points : "+str(len_dico_new_pt))
        print("   Final nbr of cross pool tris: "+str(total_cross_pool))
    for i in range(0,pool_nbr):
        #print(pools_lengths[i])
        if pools_lengths[i]>=35000 and pool_cols==32:
            print("A suspicious number (although non blocking) nbr of points was found\n"+\
                  "in the zone centered in lat=",pools_params[i,3]+0.5*pools_params[i,2],\
                  " lon=",pools_params[i,1]+0.5*pools_params[i,0]," : ",pools_lengths[i],".")
            print("That could be related to an OSM error, but also to a too large number of")
            print("triangles due to a too low value of the parameter curv_tol (cfr log in Step 2).")
    for pool_idx in range(0,4*pool_nbr):
        pools_params[pool_idx,5]=pools_z_min[pool_idx]*100000
        pools_params[pool_idx,4]=(pools_z_max[pool_idx]-pools_z_min[pool_idx])*100000 +100
        for pos_in_pool in range(0,pools_lengths[pool_idx]):
            pools[pool_idx,pools_planes[pool_idx]*pos_in_pool+2]=int(round((pools_z_temp[pool_idx,\
                    pos_in_pool]*100000-pools_params[pool_idx,5])/pools_params[pool_idx,4]*65535))

    # Now is time to write our DSF to disk, the exact binary format is described on the wiki
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    if os.path.exists(dest_dir+dir_sep+dsf_filename+'.dsf'):
        os.system(copy_cmd+' "'+dest_dir+dir_sep+dsf_file+'.dsf'+'" "'+\
         dest_dir+dir_sep+dsf_file+'.dsf.bak" '+devnull_rdir)
    
    properties="sim/west\0"+str(lon0)+"\0"+"sim/east\0"+str(lon0+1)+"\0"+\
               "sim/south\0"+str(lat0)+"\0"+"sim/north\0"+str(lat0+1)+"\0"+\
               "sim/creation_agent\0"+"Ortho4XP\0"

    # Computation of intermediate and of total length 
    size_of_prop_string=len(properties)
    size_of_terrain_string=len(terrain_def)
    size_of_head_atom=16+size_of_prop_string
    size_of_prop_atom=8+size_of_prop_string
    size_of_defn_atom=48+size_of_terrain_string
    size_of_tert_atom=8+size_of_terrain_string
    size_of_geod_atom=8
    for k in range(0,4*pool_nbr):
        if pools_lengths[k]>0:
            size_of_geod_atom+=21+pools_planes[k]*(9+2*pools_lengths[k])
    if verbose_output==True:
        print("   Size of DEFN atom : "+str(size_of_defn_atom)+" bytes.")    
        print("   Size of GEOD atom : "+str(size_of_geod_atom)+" bytes.")    
    f=open(dsf_filename,'wb')
    f.write(b'XPLNEDSF')
    f.write(struct.pack('<I',1))
    
    # Head super-atom
    f.write(b"DAEH")
    f.write(struct.pack('<I',size_of_head_atom))
    f.write(b"PORP")
    f.write(struct.pack('<I',size_of_prop_atom))
    f.write(bytes(properties,'ascii'))
    
    # Definitions super-atom
    f.write(b"NFED")
    f.write(struct.pack('<I',size_of_defn_atom))
    f.write(b"TRET")
    f.write(struct.pack('<I',size_of_tert_atom))
    f.write(bytes(terrain_def,'ascii'))
    f.write(b"TJBO")
    f.write(struct.pack('<I',8))
    f.write(b"YLOP")
    f.write(struct.pack('<I',8))
    f.write(b"WTEN")
    f.write(struct.pack('<I',8))
    f.write(b"NMED")
    f.write(struct.pack('<I',8))
    
    # Geodata super-atom
    f.write(b"DOEG")
    f.write(struct.pack('<I',size_of_geod_atom))
    for k in range(0,4*pool_nbr):
        if pools_lengths[k]==0:
            continue
        f.write(b'LOOP')
        f.write(struct.pack('<I',13+pools_planes[k]+2*pools_planes[k]*pools_lengths[k]))
        f.write(struct.pack('<I',pools_lengths[k]))
        f.write(struct.pack('<B',pools_planes[k]))
        for l in range(0,pools_planes[k]):
            f.write(struct.pack('<B',0))
            for m in range(0,pools_lengths[k]):
                f.write(struct.pack('<H',pools[k,pools_planes[k]*m+l]))
    for k in range(0,4*pool_nbr):
        if pools_lengths[k]==0:
            continue
        f.write(b'LACS')
        f.write(struct.pack('<I',8+8*pools_planes[k]))
        for l in range(0,2*pools_planes[k]):
            f.write(struct.pack('<f',pools_params[k,l]))
   
    try:
        application.progress_attr.set(95)
        if application.red_flag.get()==1:
            print("Attribution process interrupted.")
            return
    except:
        pass
    # Since we possibly skipped some pools, we rebuild a dico
    # which tells the pool position in the dsf of a pool prior
    # to the stripping :

    dico_new_pool={}
    new_pool_idx=0
    for k in range(0,4*pool_nbr):
        if pools_lengths[k] != 0:
            dico_new_pool[k]=new_pool_idx
            new_pool_idx+=1

    # Commands atom
    
    # we first compute its size :
    size_of_cmds_atom=8
    for texture_idx in textures:
        if len(textures[texture_idx])==0:
            continue
        size_of_cmds_atom+=3
        for pool_idx in textures[texture_idx]:
            if pool_idx != 'cross-pool':
                size_of_cmds_atom+= 13+2*(len(textures[texture_idx][pool_idx])+\
                        ceil(len(textures[texture_idx][pool_idx])/255))
            else:
                size_of_cmds_atom+= 13+2*(len(textures[texture_idx][pool_idx])+\
                        ceil(len(textures[texture_idx][pool_idx])/510))
    if verbose_output==True:
        print("   Size of CMDS atom : "+str(size_of_cmds_atom)+" bytes.")
    f.write(b'SDMC')                               # CMDS header 
    f.write(struct.pack('<I',size_of_cmds_atom))   # CMDS length
    
    for texture_idx in textures:
        if len(textures[texture_idx])==0:
            continue
        #print("texture_idx = "+str(texture_idx))
        f.write(struct.pack('<B',4))           # SET DEFINITION 16
        f.write(struct.pack('<H',texture_idx)) # TERRAIN INDEX
        flag=1   # physical
        for pool_idx in textures[texture_idx]:
            if pool_idx!='cross-pool':
                if pools_planes[pool_idx]==9:
                    #print("overlay flag set !")
                    flag=2 #overlay
            else:
                if pools_planes[textures[texture_idx]['cross-pool'][0]]==9:
                    flag=2
        for pool_idx in textures[texture_idx]:
            #print("  pool_idx = "+str(pool_idx))
            if pool_idx != 'cross-pool':
                f.write(struct.pack('<B',1))                          # POOL SELECT
                f.write(struct.pack('<H',dico_new_pool[pool_idx]))    # POOL INDEX
    
                f.write(struct.pack('<B',18))    # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack('<B',flag))  # FLAG
                f.write(struct.pack('<f',0))     # NEAR LOD
                f.write(struct.pack('<f',-1))    # FAR LOD
                
                blocks=floor(len(textures[texture_idx][pool_idx])/255)
                #print("     "+str(blocks)+" blocks")    
                for j in range(0,blocks):
                    f.write(struct.pack('<B',23))   # PATCH TRIANGLE
                    f.write(struct.pack('<B',255))  # COORDINATE COUNT

                    for k in range(0,255):
                        f.write(struct.pack('<H',textures[texture_idx][pool_idx][255*j+k]))  # COORDINATE IDX
                remaining_tri_p=len(textures[texture_idx][pool_idx])%255
                if remaining_tri_p != 0:
                    f.write(struct.pack('<B',23))               # PATCH TRIANGLE
                    f.write(struct.pack('<B',remaining_tri_p))  # COORDINATE COUNT
                    for k in range(0,remaining_tri_p):
                        f.write(struct.pack('<H',textures[texture_idx][pool_idx][255*blocks+k]))  # COORDINATE IDX
            elif pool_idx == 'cross-pool':
                pool_idx_init=textures[texture_idx][pool_idx][0]
                f.write(struct.pack('<B',1))                               # POOL SELECT
                f.write(struct.pack('<H',dico_new_pool[pool_idx_init]))    # POOL INDEX
                f.write(struct.pack('<B',18))    # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack('<B',flag))  # FLAG
                f.write(struct.pack('<f',0))     # NEAR LOD
                f.write(struct.pack('<f',-1))  # FAR LOD
                
                blocks=floor(len(textures[texture_idx][pool_idx])/510)
                for j in range(0,blocks):
                    f.write(struct.pack('<B',24))   # PATCH TRIANGLE CROSS-POOL
                    f.write(struct.pack('<B',255))  # COORDINATE COUNT
                    for k in range(0,255):
                        f.write(struct.pack('<H',dico_new_pool[textures[texture_idx][pool_idx][510*j+2*k]]))    # POOL IDX
                        f.write(struct.pack('<H',textures[texture_idx][pool_idx][510*j+2*k+1]))                 # POS_IN_POOL IDX
                remaining_tri_p=int((len(textures[texture_idx][pool_idx])%510)/2)
                if remaining_tri_p != 0:
                    f.write(struct.pack('<B',24))               # PATCH TRIANGLE CROSS-POOL
                    f.write(struct.pack('<B',remaining_tri_p))  # COORDINATE COUNT
                    for k in range(0,remaining_tri_p):
                        f.write(struct.pack('<H',dico_new_pool[textures[texture_idx][pool_idx][510*blocks+2*k]]))   # POOL IDX
                        f.write(struct.pack('<H',textures[texture_idx][pool_idx][510*blocks+2*k+1]))                # POS_IN_PO0L IDX
    try:
        application.progress_attr.set(98)
        if application.red_flag.get()==1:
            print("Attribution process interrupted.")
            return
    except:
        pass
    f.close()
    f=open(dsf_filename,'rb')
    data=f.read()
    m=hashlib.md5()
    m.update(data)
    #print(str(m.digest_size))
    md5sum=m.digest()
    #print(str(md5sum))
    f.close()
    f=open(dsf_filename,'ab')
    f.write(md5sum)
    f.close()
    try:
        application.progress_attr.set(100)
    except:
        pass
    print("  DSF file encoded, total size is  : "+str(28+size_of_head_atom+\
            size_of_defn_atom+size_of_geod_atom+size_of_cmds_atom)+" bytes.")
    return
##############################################################################


##############################################################################
def point_params(lat,lon,lat0,lon0,pools_params,pool_cols,pool_rows):
    pool_x=int((lon-lon0)*pool_cols)
    pool_y=int((lat-lat0)*pool_rows)
    if pool_x==pool_rows:
        pool_x-=1
    if pool_y==pool_cols:
        pool_y-=1
    pool_idx=(pool_y)*pool_cols+(pool_x)
    pool_nx=int(round((lon-pools_params[pool_idx][1])/\
            pools_params[pool_idx][0]*65535))
    pool_ny=int(round((lat-pools_params[pool_idx][3])/\
            pools_params[pool_idx][2]*65535))
    return [pool_idx,pool_nx,pool_ny]
##############################################################################

def build_tile(lat,lon,build_dir,mesh_filename,clean_tmp_files):
    global download_to_do_list,montage_to_do_list,convert_to_do_list
    download_to_do_list=[]
    montage_to_do_list=[]
    convert_to_do_list=[]
    t3=time.time()
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    fargs_dsf=[lat,lon,ortho_list,\
            water_overlay,ratio_water,mesh_filename] 
    if clean_unused_dds_and_ter_files==True:
        print("Purging old .ter files")
        if os.path.exists(build_dir+dir_sep+'terrain'):
            for oldterfile in os.listdir(build_dir+dir_sep+'terrain'):
                os.remove(build_dir+dir_sep+'terrain'+dir_sep+oldterfile)
    build_dsf_thread=threading.Thread(target=build_dsf,args=fargs_dsf)
    fargs_down=[strlat,strlon]
    download_thread=threading.Thread(target=download_textures,args=fargs_down)
    fargs_mont=[strlat,strlon]
    montage_thread=threading.Thread(target=montage_textures,args=fargs_mont)
    fargs_conv=[strlat,strlon]
    convert_thread=threading.Thread(target=convert_textures,args=fargs_conv)
    try:
        application.red_flag.set(0)
        application.progress_attr.set(0) 
        application.progress_down.set(0) 
        application.progress_mont.set(0) 
        application.progress_conv.set(0) 
    except:
        pass
    print("Start of the texture attribution process...")
    build_dsf_thread.start()
    #build_dsf_thread.join()
    if skip_downloads != True:
        download_thread.start()
        montage_thread.start()
        if skip_converts != True:
            convert_thread.start()
    build_dsf_thread.join()
    if skip_downloads != True:
        download_thread.join()
        montage_thread.join()
        if skip_converts != True:
            convert_thread.join()
    if clean_unused_dds_and_ter_files==True:
        print("Purging non necessary .dds files")
        for oldfilename in os.listdir(build_dir+dir_sep+'textures'):
            try:
                [oldfilenamebase,oldfilenameext]=oldfilename.split('.')
            except:
                continue
            if oldfilenameext!='dds':
                    continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfilenamebase+'.ter'):
                continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfilenamebase+'_overlay.ter'):
                continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfilenamebase+'_sea_overlay.ter'):
                continue
            # if we have reached here we are facing a dds which is no longer need and therefore we delete it
            print("  -> removing "+oldfilename)
            os.remove(build_dir+dir_sep+'textures'+dir_sep+oldfilename)
    if clean_tmp_files==True:
        clean_temporary_files(build_dir,['POLY','ELE'])                                                 
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t3))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
     # --> mth
    try:
        comp_func = application.comp_func.get()
        print('\n')
        shutdown=True
        if comp_func=='Exit program':
            for i in range(0, shutdown_timer-1):
                if application.red_flag.get()==1:
                    shutdown=False
                    print('\nExit timer interrupted.')
                    break;
                if i % shutd_msg_interval == 0:
                    print('Closing program in '+str(shutdown_timer-i)+' seconds ...')
                time.sleep(1)
            if shutdown==True:
                print('\nClosing program now ...')
                application.quit()
        elif comp_func=='Shutdown computer':
            for i in range(0, shutdown_timer-1):
                if application.red_flag.get()==1:
                    shutdown=False
                    print('\nShutdown timer interrupted.')
                    break;
                if i % shutd_msg_interval == 0:
                    print('Shutting down computer in '+str(shutdown_timer-i)+' seconds ...')
                time.sleep(1)
            if shutdown==True:
                print('\nShutting down computer now ...')
                os.system(shutdown_cmd)
    except:
        pass
    # <-- mth
    return
##############################################################################


##############################################################################
def build_overlay(lat,lon,file_to_sniff):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
    strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
    t_ov=time.time()
    file_to_sniff_loc=Ortho4XP_dir+dir_sep+"tmp"+dir_sep+strlat+strlon+'.dsf'
    print("-> Making a copy of the original overlay DSF in tmp dir")
    os.system(copy_cmd + '  "'+file_to_sniff+'" "'+file_to_sniff_loc+'"')
    file = open(file_to_sniff_loc,'rb')
    # Merci Pascal P. pour cette élégante solution !
    dsfid = file.read(2).decode('ascii')
    file.close()
    if dsfid == '7z':
        print("-> The original DSF is a 7z archive, uncompressing...")
        os.system(rename_cmd+'"'+file_to_sniff_loc+'" "'+file_to_sniff_loc+'.7z" '+\
              devnull_rdir)
        os.system(unzip_cmd+' e -o'+Ortho4XP_dir+dir_sep+'tmp'+' "'+\
              file_to_sniff_loc+'.7z"')
    if 'dar' in sys.platform:
        dsftool_cmd=Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"DSFTool.app "
    elif 'win' in sys.platform:
        dsftool_cmd=Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"DSFTool.exe "
    else:
        dsftool_cmd=Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"DSFTool "
    print("-> Converting the copy to text format")
    dsfconvertcmd=[dsftool_cmd.strip(),' -dsf2text '.strip(),file_to_sniff_loc,Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'tmp_dsf.txt']
    fingers_crossed=subprocess.Popen(dsfconvertcmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print('     '+line.decode("utf-8")[:-1])
    print("-> Expurging the mesh and the beach polygons from the text DSF")
    f=open(Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'tmp_dsf.txt','r')
    g=open(Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'tmp_dsf_without_mesh.txt','w')
    line=f.readline()
    g.write('PROPERTY sim/overlay 1\n')
    while line!='':
        if 'PROPERTY' in line:
            g.write(line)
        elif 'TERRAIN_DEF' in line:
            pass
        elif 'POLYGON_DEF' in line:
            g.write(line)
        elif 'NETWORK_DEF' in line:
            g.write(line)
        elif 'BEGIN_POLYGON 0' in line:
            while 'END_POLYGON' not in line:
                line=f.readline()
        elif 'BEGIN_POLYGON' in line:
            while 'END_POLYGON' not in line:
                g.write(line)
                line=f.readline()
            g.write(line)
        elif 'BEGIN_SEGMENT' in line:
            while 'END_SEGMENT' not in line:
                g.write(line)
                line=f.readline()
            g.write(line)
        else:
            pass
        line=f.readline()
    f.close()
    g.close()
    print("-> Converting back the text DSF to binary format")
    dsfconvertcmd=[dsftool_cmd.strip(),' -text2dsf '.strip(),Ortho4XP_dir+dir_sep+\
              'tmp'+dir_sep+'tmp_dsf_without_mesh.txt',Ortho4XP_dir+\
              dir_sep+'tmp'+dir_sep+'tmp_dsf_without_mesh.dsf'] 
    fingers_crossed=subprocess.Popen(dsfconvertcmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print('     '+line.decode("utf-8")[:-1])
    dest_dir=Ortho4XP_dir+dir_sep+'yOrtho4XP_Overlays'+dir_sep+'Earth nav data'+dir_sep+\
            strlatround+strlonround
    print("-> Coping the final overlay DSF in "+dest_dir) 
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    os.system(copy_cmd+' "'+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'tmp_dsf_without_mesh.dsf" '+\
              ' "'+dest_dir+dir_sep+strlat+strlon+'.dsf"')
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'*.dsf' +devnull_rdir)
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'*.txt' +devnull_rdir)
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'*.raw' +devnull_rdir)
    if dsfid == '7z':
        os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'*.7z' +devnull_rdir)
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t_ov))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    return
##############################################################################


##############################################################################
def build_masks(lat,lon,build_dir,mesh_filename_list):
    t4=time.time()
    try:
        application.red_flag.set(0)
    except:
        pass
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    eps=0.000001
    [til_x_min,til_y_min]=wgs84_to_texture(lat+1-eps,lon+eps,14,'BI')
    [til_x_max,til_y_max]=wgs84_to_texture(lat+eps,lon+1-eps,14,'BI')
    nx=(til_x_max-til_x_min)//16+1
    ny=(til_y_max-til_y_min)//16+1
    masks_im=Image.new("1",(nx*4096,ny*4096))
    masks_draw=ImageDraw.Draw(masks_im)
    
    masks_dir=Ortho4XP_dir+dir_sep+"Masks"+dir_sep+strlat+strlon
    if not os.path.exists(masks_dir):
        os.makedirs(masks_dir)
    if not os.path.isfile(masks_dir+dir_sep+'whole_tile.png') or keep_old_pre_mask==False:
        for mesh_filename in mesh_filename_list:
            try:
                f_mesh=open(mesh_filename,"r")
            except:
                continue
            for i in range(0,4):
                f_mesh.readline()
            nbr_pt_in=int(f_mesh.readline())
            pt_in=numpy.zeros(5*nbr_pt_in,'float')
            for i in range(0,nbr_pt_in):
                tmplist=f_mesh.readline().split()
                pt_in[5*i]=float(tmplist[0])
                pt_in[5*i+1]=float(tmplist[1])
                pt_in[5*i+2]=float(tmplist[2])
            for i in range(0,3):
                f_mesh.readline()
            for i in range(0,nbr_pt_in):
                tmplist=f_mesh.readline().split()
                pt_in[5*i+3]=float(tmplist[0])
                pt_in[5*i+4]=float(tmplist[1])
            for i in range(0,2): # skip 2 lines
                f_mesh.readline()
            nbr_tri_in=int(f_mesh.readline()) # read nbr of tris
            step_stones=nbr_tri_in//100
            percent=-1
            print(" Constructing binary mask for sea water / ground from mesh file "+str(mesh_filename))
            for i in range(0,nbr_tri_in):
                if i%step_stones==0:
                    percent+=1
                    try:
                        application.progress_attr.set(int(percent*5/10))
                        if application.red_flag.get()==1:
                            print("Masks construction process interrupted.")
                            return
                    except:
                        pass
                tmplist=f_mesh.readline().split()
                # look for the texture that will possibly cover the tri
                n1=int(tmplist[0])-1
                n2=int(tmplist[1])-1
                n3=int(tmplist[2])-1
                tri_type=tmplist[3] 
                if (tri_type in ['2','3']) or (tri_type=='1' and use_masks_for_inland==True):
                    continue
                # The next would be best to mask rivers as well
                #if (tri_type in ['1','2','3']):
                #    continue
                [lon1,lat1]=pt_in[5*n1:5*n1+2]
                [lon2,lat2]=pt_in[5*n2:5*n2+2]
                [lon3,lat3]=pt_in[5*n3:5*n3+2]
                bary_lat=(lat1+lat2+lat3)/3
                bary_lon=(lon1+lon2+lon3)/3
                [til_x,til_y]=wgs84_to_texture(bary_lat,bary_lon,14,'BI')
                nxloc=(til_x-til_x_min)//16
                nyloc=(til_y-til_y_min)//16
                [s1,t1]=st_coord(lat1,lon1,til_x,til_y,14,'BI')
                [s2,t2]=st_coord(lat2,lon2,til_x,til_y,14,'BI')
                [s3,t3]=st_coord(lat3,lon3,til_x,til_y,14,'BI')
                [px1,py1]=[nxloc*4096+int(s1*4096),nyloc*4096+int((1-t1)*4096)]
                [px2,py2]=[nxloc*4096+int(s2*4096),nyloc*4096+int((1-t2)*4096)]
                [px3,py3]=[nxloc*4096+int(s3*4096),nyloc*4096+int((1-t3)*4096)]
                try:
                    masks_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill='white')
                except:
                    pass
            f_mesh.close()
        masks_im.save(masks_dir+dir_sep+'whole_tile.png')
    if use_gimp==True:
        print(" Gaussian blur and level adjustment applied to the binary mask with Gimp...")
        if ('dar' in sys.platform) or ('win' not in sys.platform):   # Mac and Linux
            os.system(gimp_cmd+" -i -c -b '(blurX "+' "'+masks_dir+dir_sep+\
                'whole_tile.png" '+str(masks_width)+' "'+masks_dir+dir_sep+\
                'whole_tile_blured.png")'+"' -b '(gimp-quit 0)' ")
        else: # Windows specific
            tmpf=open('batchgimp.bat','w')
            tmpcmd='"'+gimp_cmd+'" '+\
                   '-i -c -b "(blurX \\\".\\\\Masks\\\\'+strlat+strlon+'\\\\whole_tile.png\\\" '+\
                   str(masks_width)+' \\\".\\\\Masks\\\\'+strlat+strlon+'\\\\whole_tile_blured.png\\\")"'+\
                   ' -b "(gimp-quit 0)"'
            tmpf.write(tmpcmd)
            tmpf.close()
            os.system('batchgimp.bat')
            os.system(delete_cmd+' batchgimp.bat')
        try:
            masks_im=Image.open(masks_dir+dir_sep+'whole_tile_blured.png')
        except:
            print("\nGimp is either not present on your system, or didn't configure its")
            print("access command correctly, or it has no access to the blurX script-fu.")
            print("Check in the manual for testing instructions.")
            print("\nFailure.")
            print('_____________________________________________________________'+\
            '____________________________________')
            try:
                application.progress_attr.set(0)
            except:
                pass
            return
    else:
        print(" Gaussian blur and level adjustment applied to the binary mask with Netpbm and Imagemagick...")
        os.system(netpbm_bin_dir+dir_sep+'pngtopnm '+' "'+masks_dir+dir_sep+'whole_tile.png"' +\
                  ' > '+' "'+masks_dir+dir_sep+'whole_tile.pnm"')
        os.system(netpbm_bin_dir+dir_sep+'pamdice '+'-outstem='+masks_dir+dir_sep+'tile_part -width='+str(nx*2048+2*masks_width)+' -height='+\
                  str(ny*2048+2*masks_width)+' -hoverlap='+str(4*masks_width)+\
                  ' -voverlap='+str(4*masks_width)+' "'+masks_dir+dir_sep+'whole_tile.pnm"')
        for i in range(0,2):
            for j in range(0,2):
                # from rawbit to png 
                os.system(netpbm_bin_dir+dir_sep+'pnmtopng '+' "'+masks_dir+dir_sep+'tile_part_'+str(i)+'_'+str(j)+'.pbm" '+\
                  ' > '+ ' "'+masks_dir+dir_sep+'tile_part_'+str(i)+'_'+str(j)+'.png" ')
                # blur
                os.system(convert_cmd+' "'+masks_dir+dir_sep+'tile_part_'+str(i)+'_'+str(j)+'.png" '+\
                  '-blur 0x'+str(masks_width)+' "'+masks_dir+dir_sep+'tile_blured_part_'+str(i)+\
                  '_'+str(j)+'.png" ')
                # back from png to pgm
                os.system(netpbm_bin_dir+dir_sep+'pngtopam '+' "'+masks_dir+dir_sep+\
                        'tile_blured_part_'+str(i)+'_'+str(j)+'.png" '+\
                  ' > '+ ' "'+masks_dir+dir_sep+'tile_blured_part_'+str(i)+'_'+str(j)+'.pnm" ')
                try:
                    application.progress_attr.set(50+10*i+5*j+5)
                    if application.red_flag.get()==1:
                        print("Masks construction process interrupted.")
                        return
                except:
                    pass
        os.system(netpbm_bin_dir+dir_sep+'pamcut '+'-left=0 -top=0 -width='+str(nx*2048)+\
                   ' -height='+str(ny*2048)+\
                   ' "'+masks_dir+dir_sep+'tile_blured_part_0_0.pnm" ' + '  > '+\
                   ' "'+masks_dir+dir_sep+'tile_blured_part_0_0_2.pnm" ')
        os.system(netpbm_bin_dir+dir_sep+'pgmtopgm'+' < "'+masks_dir+dir_sep+\
                'tile_blured_part_0_0_2.pnm" '+' > '+\
                   ' "'+masks_dir+dir_sep+'tile_blured_part_0_0.pgm" ')
        os.system(netpbm_bin_dir+dir_sep+'pamcut '+'-left='+str(2*masks_width)+\
                  ' -top=0 -width='+str(nx*2048)+' -height='+str(ny*2048)+\
                ' "'+masks_dir+dir_sep+'tile_blured_part_0_1.pnm" ' + '  > '+\
                ' "'+masks_dir+dir_sep+'tile_blured_part_0_1_2.pnm" ')
        os.system(netpbm_bin_dir+dir_sep+'pgmtopgm'+' < "'+masks_dir+dir_sep+\
                'tile_blured_part_0_1_2.pnm" '+' > '+\
                   ' "'+masks_dir+dir_sep+'tile_blured_part_0_1.pgm" ')
        os.system(netpbm_bin_dir+dir_sep+'pamcut '+'-left=0 -top='+str(2*masks_width)+\
                ' -width='+str(nx*2048)+' -height='+str(ny*2048)+\
                ' "'+masks_dir+dir_sep+'tile_blured_part_1_0.pnm" ' + '  > '+\
                ' "'+masks_dir+dir_sep+'tile_blured_part_1_0_2.pnm" ')
        os.system(netpbm_bin_dir+dir_sep+'pgmtopgm'+' < "'+masks_dir+dir_sep+\
                'tile_blured_part_1_0_2.pnm" '+' > '+\
                   ' "'+masks_dir+dir_sep+'tile_blured_part_1_0.pgm" ')
        os.system(netpbm_bin_dir+dir_sep+'pamcut '+'-left='+str(2*masks_width)+\
                ' -top='+str(2*masks_width)+' -width='+str(nx*2048)+' -height='+str(ny*2048)+\
                ' "'+masks_dir+dir_sep+'tile_blured_part_1_1.pnm" ' + '  > '+\
                ' "'+masks_dir+dir_sep+'tile_blured_part_1_1_2.pnm" ')
        os.system(netpbm_bin_dir+dir_sep+'pgmtopgm'+' < "'+masks_dir+dir_sep+\
                'tile_blured_part_1_1_2.pnm" '+' > '+\
                   ' "'+masks_dir+dir_sep+'tile_blured_part_1_1.pgm" ')
        os.system(netpbm_bin_dir+dir_sep+'pamundice '+'-across=2 -down=2 '+' "'+masks_dir+\
                  dir_sep+'tile_blured_part_%1d_%1a.pgm"'+\
                  ' > '+' "'+masks_dir+dir_sep+'whole_tile_blured.pgm"')
        try:
            application.progress_attr.set(80)
            if application.red_flag.get()==1:
                print("Masks construction process interrupted.")
                return
        except:
            pass
        os.system(netpbm_bin_dir+dir_sep+'pnmnorm '+' -bvalue=0 -wvalue=140 ' +' "'+\
                masks_dir+dir_sep+'whole_tile_blured.pgm" '+\
                ' > '+' "'+masks_dir+dir_sep+'whole_tile_blured_leveled.pgm" ')
        os.system(netpbm_bin_dir+dir_sep+'pnmtopng '+' "'+masks_dir+dir_sep+'whole_tile_blured_leveled.pgm"' +' > '+\
                ' "'+masks_dir+dir_sep+'whole_tile_blured.png"')
        os.system(convert_cmd+' "'+masks_dir+dir_sep+'whole_tile_blured.png" '+\
                  '-level 0,60% "'+masks_dir+dir_sep+'whole_tile_blured.png"')
        os.system(delete_cmd+' '+masks_dir+dir_sep+'tile*.* '+ devnull_rdir)
        os.system(delete_cmd+' '+masks_dir+dir_sep+'*.pgm' + devnull_rdir)
        os.system(delete_cmd+' '+masks_dir+dir_sep+'*.pnm' + devnull_rdir)
        try:
            masks_im=Image.open(masks_dir+dir_sep+'whole_tile_blured.png')
        except:
            print("\nImagemagick and/or Netpbm can't be reached or were not compiled with the")
            print("required functionalities.")
            print("\nFailure.")
            print('_____________________________________________________________'+\
            '____________________________________')
            try:
                application.progress_attr.set(0)
            except:
                pass
            return
    try:
        application.progress_attr.set(90)
        if application.red_flag.get()==1:
            print("Masks construction process interrupted.")
            return
    except:
        pass
    print(" Purging old masks files if needed.") 
    for oldmaskfile in os.listdir(masks_dir):
        if 'tile' in oldmaskfile:
            continue
        else:
            os.remove(masks_dir+dir_sep+oldmaskfile)
    print(" Spitting tile mask into ZL14 based submasks and skipping black ones.")
    for nxloc in range(0,nx):
        for nyloc in range(0,ny):
            box=(nxloc*4096,nyloc*4096,(nxloc+1)*4096,(nyloc+1)*4096)
            tex_im=masks_im.crop(box)
            if tex_im.getextrema()[1]>=10:
                tex_im.save(masks_dir+dir_sep+str(til_y_min+nyloc*16)+'_'+str(til_x_min+nxloc*16)+'.png')
                tex_im.save(build_dir+dir_sep+"textures"+dir_sep+str(til_y_min+nyloc*16)+'_'+str(til_x_min+nxloc*16)+'.png')
    try:
        application.progress_attr.set(100)
        if application.red_flag.get()==1:
            print("Masks construction process interrupted.")
            return
    except:
        pass
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t4))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    return


##############################################################################
def point_in_polygon(point,polygon):
    '''
    This procedures determines wether the input point belongs to the 
    polygon. The algorithm is based on the computation of the index 
    of the boundary of the polygon with respect to the point.
    A point is a list of 2 floats and a polygon is a list of 2N floats, N>=3,   
    and the first two floats equal the last two ones.  
    '''
    total_winding_nbr=0
    quadrants=[]
    for j in range(0,len(polygon)//2):
        if polygon[2*j] >= point[0]:
            if polygon[2*j+1] >= point[1]:
                quadrants.append(1)
            else:
                quadrants.append(4)
        else:
            if polygon[2*j+1] >= point[1]:
                quadrants.append(2)
            else:
                quadrants.append(3)
    winding_nbr=0
    for k in range(0,len(quadrants)-1):
        change=quadrants[k+1]-quadrants[k]
        if change in [1,-1,0]:
            winding_nbr += change
        elif change in [-3,3]:
            winding_nbr += (-1)*change/3
        elif change in [-2,2]:
            if (polygon[2*k]-point[0])*(polygon[2*k+3]-point[1])\
-(polygon[2*k+1]-point[1])*(polygon[2*k+2]-point[0])>=0:
                winding_nbr+=2
            else:
                winding_nbr+=-2
    change=quadrants[0]-quadrants[len(quadrants)-1]
    if change in [1,-1,0]:
        winding_nbr += change
    elif change in [-3,3]:
        winding_nbr += (-1)*change/3
    elif change in [-2,2]:
        if (polygon[2*len(quadrants)-2]-point[0])*(polygon[1]\
-point[1])-(polygon[2*len(quadrants)-1]-point[1])*(polygon[0]-point[0])>=0:
            winding_nbr+=2
        else:
            winding_nbr+=-2
    total_winding_nbr+=winding_nbr/4
    if total_winding_nbr == 0:
        return False
    else:
        return True
##############################################################################

##############################################################################
def clean_temporary_files(build_dir,steps):
    for step in steps:
        if step=='OSM':
            for f in os.listdir(build_dir):
                if 'OSM_' in f:
                    os.remove(os.path.join(build_dir,f))
        elif step=='POLY':
            for f in os.listdir(build_dir):
                if ('.poly' in f) or ('.apt' in f):
                    os.remove(os.path.join(build_dir,f))
        elif step=='ELE':
            for f in os.listdir(build_dir):
                if ('.ele' in f) or ('.node' in f) or ('.alt' in f):
                    os.remove(os.path.join(build_dir,f))
        elif step=='MESH':
            for f in os.listdir(build_dir):
                if ('.mesh' in f):
                    os.remove(os.path.join(build_dir,f))
    return
##############################################################################

##############################################################################
class Preview_window(Toplevel):

    dico_color={15:'cyan',16:'green',17:'yellow',18:'orange',19:'red'}
    points=[]
    coords=[]
    polygon_list=[]
    polyobj_list=[]

    
    
    def __init__(self,lat,lon):
        self.points=[]
        self.coords=[]
        self.polygon_list=[]
        self.polyobj_list=[]
        Toplevel.__init__(self)
        self.title('Preview')
        toplevel = self.winfo_toplevel()
        try:
        # On MS Windows one can set the "zoomed" state.
            toplevel.wm_state('zoomed')
        except:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight() - 60
            geom_string = "%dx%d+0+0" % (w,h)
            toplevel.wm_geometry(geom_string) 
        self.columnconfigure(1,weight=1)
        self.rowconfigure(0,weight=1)
    
        # Constants

        self.map_list        = px256_list
        self.map_list2       = px256_list+wms2048_list
        self.zl_list         = ['10','11','12','13']
    
        self.map_choice      = StringVar()
        self.map_choice.set('OSM')
        self.zl_choice=StringVar()
        self.zl_choice.set('11')
        self.progress_preview = IntVar()
        self.progress_preview.set(0)
        self.zmap_choice      = StringVar()
        if application.map_choice.get()!='None':
            self.zmap_choice.set(application.map_choice.get())
        else:
            self.zmap_choice.set('BI')

        self.zlpol=IntVar()
        self.zlpol.set(17)
        self.gb = StringVar()
        self.gb.set('0Gb')
    
        # Frames
        self.frame_left   =  Frame(self, border=4, relief=RIDGE,bg='light green')
        self.frame_right  =  Frame(self, border=4, relief=RIDGE,bg='light green')

        # Frames properties
        self.frame_right.rowconfigure(0,weight=1)
        self.frame_right.columnconfigure(0,weight=1)
    
        # Frames placement
        self.frame_left.grid(row=0,column=0,sticky=N+S+W+E)
        self.frame_right.grid(row=0,rowspan=60,column=1,sticky=N+S+W+E)

        # Widgets
        self.label_pp         =  Label(self.frame_left,anchor=W,text="Preview params ",\
                                 fg = "light green",bg = "dark green",\
                                 font = "Helvetica 16 bold italic")
        self.title_src        =  Label(self.frame_left,anchor=W,text="Source : ",bg="light green") 
        self.map_combo        =  ttk.Combobox(self.frame_left,textvariable=self.map_choice,\
                                 values=self.map_list,state='readonly',width=8)
        self.title_zl         =  Label(self.frame_left,anchor=W,text="Zoomlevel : ",bg="light green")
        self.zl_combo         =  ttk.Combobox(self.frame_left,textvariable=self.zl_choice,\
                                 values=self.zl_list,state='readonly',width=3)
        self.preview_btn      =  Button(self.frame_left, text='Preview',\
                                 command=lambda: self.preview_tile(lat,lon))
        self.pgbar_preview    =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_preview,)
        self.label_zp         =  Label(self.frame_left,anchor=W,text="Zone params ",\
                                 fg = "light green",bg = "dark green",\
                                 font = "Helvetica 16 bold italic")
        self.title_zsrc       =  Label(self.frame_left,anchor=W,text="Source : ",bg="light green") 
        self.zmap_combo       =  ttk.Combobox(self.frame_left,textvariable=self.zmap_choice,\
                                 values=self.map_list2,state='readonly',width=8)
        self.B15 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[15],\
                    activebackground=self.dico_color[15],selectcolor=self.dico_color[15],\
                    height=3,indicatoron=0,text='ZL15',variable=self.zlpol,value=15,\
                    command=self.redraw_poly)
        self.B16 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[16],\
                    activebackground=self.dico_color[16],selectcolor=self.dico_color[16],height=3,\
                    indicatoron=0,text='ZL16',variable=self.zlpol,value=16,command=self.redraw_poly)
        self.B17 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[17],\
                    activebackground=self.dico_color[17],selectcolor=self.dico_color[17],height=3,\
                    indicatoron=0,text='ZL17',variable=self.zlpol,value=17,command=self.redraw_poly)
        self.B18 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[18],\
                    activebackground=self.dico_color[18],selectcolor=self.dico_color[18],height=3,\
                    indicatoron=0,text='ZL18',variable=self.zlpol,value=18,command=self.redraw_poly)
        self.B19 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[19],\
                    activebackground=self.dico_color[19],selectcolor=self.dico_color[19],height=3,\
                    indicatoron=0,text='ZL19',variable=self.zlpol,value=19,command=self.redraw_poly)
        self.save_zone_btn    =  Button(self.frame_left,text='  Save zone  ',command=self.save_zone_cmd)
        self.del_zone_btn     =  Button(self.frame_left,text=' Delete zone ',command=self.delete_zone_cmd)
        self.save_zones_btn   =  Button(self.frame_left,text='Save and Exit',command=self.save_zone_list)
        self.exit_btn         =  Button(self.frame_left,text='   Abandon   ',command=self.destroy)
        self.title_gbsize     =  Label(self.frame_left,anchor=W,text="Approx. Add. Size : ",bg="light green") 
        self.gbsize           =  Entry(self.frame_left,width=6,bg="white",fg="blue",textvariable=self.gb)
        self.canvas           =  Canvas(self.frame_right,bd=0)

        # Placement of Widgets
        self.label_pp.grid(row=0,column=0,sticky=W+E)
        self.title_src.grid(row=1,column=0,sticky=W,padx=5,pady=5)
        self.map_combo.grid(row=1,column=0,padx=5,pady=5,sticky=E)
        self.title_zl.grid(row=2,column=0,sticky=W,padx=5,pady=5)
        self.zl_combo.grid(row=2,column=0,padx=5,pady=5,sticky=E)
        self.preview_btn.grid(row=5,column=0, padx=5, pady=0,sticky=N+S+W+E)
        self.pgbar_preview.grid(row=6,column=0, padx=5, pady=0,sticky=N+S+W+E)
        self.label_zp.grid(row=7,column=0,pady=10,sticky=W+E)
        self.title_zsrc.grid(row=8,column=0,sticky=W,padx=5,pady=10)
        self.zmap_combo.grid(row=8,column=0,padx=5,pady=10,sticky=E)
        self.B15.grid(row=10 ,column=0,padx=5,pady=0,sticky=N+S+E+W) 
        self.B16.grid(row=11,column=0,padx=5,pady=0,sticky=N+S+E+W) 
        self.B17.grid(row=12,column=0,padx=5,pady=0,sticky=N+S+E+W) 
        self.B18.grid(row=13,column=0,padx=5,pady=0,sticky=N+S+E+W) 
        self.B19.grid(row=14,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.save_zone_btn.grid(row=16,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.del_zone_btn.grid(row=17,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.save_zones_btn.grid(row=18,column=0,padx=5,pady=5,sticky=N+S+E+W)
        self.exit_btn.grid(row=19,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.title_gbsize.grid(row=15,column=0,padx=5,pady=10,sticky=W)
        self.gbsize.grid(row=15,column=0,padx=5,pady=10,sticky=E)
        self.canvas.grid(row=0,column=0,sticky=N+S+E+W)     
        
        
    def preview_tile(self,lat,lon):
        zoomlevel=int(self.zl_combo.get())
        website=self.map_combo.get()    
        strlat='{:+.0f}'.format(float(lat)).zfill(3)
        strlon='{:+.0f}'.format(float(lon)).zfill(4)
        [tilxleft,tilytop]=wgs84_to_gtile(lat+1,lon,zoomlevel)
        [self.latmax,self.lonmin]=gtile_to_wgs84(tilxleft,tilytop,zoomlevel)
        [tilxright,tilybot]=wgs84_to_gtile(lat,lon+1,zoomlevel)
        [self.latmin,self.lonmax]=gtile_to_wgs84(tilxright+1,tilybot+1,zoomlevel)
        filepreview=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+strlat+strlon+\
                    "_"+website+str(zoomlevel)+".jpg"       
        if os.path.isfile(filepreview) != True:
            fargs_ctp=[int(lat),int(lon),int(zoomlevel),website]
            self.ctp_thread=threading.Thread(target=create_tile_preview,args=fargs_ctp)
            self.ctp_thread.start()
            fargs_dispp=[filepreview,lat,lon]
            dispp_thread=threading.Thread(target=self.show_tile_preview,args=fargs_dispp)
            dispp_thread.start()
        else:
            self.show_tile_preview(filepreview,lat,lon)
        return

    def show_tile_preview(self,filepreview,lat,lon):
        global zone_list
        for item in self.polyobj_list:
            try:
                self.canvas.delete(item)
            except:
                pass
        try:
            self.canvas.delete(self.img_map)
        except:
            pass
        try:
            self.canvas.delete(self.boundary)
        except:
            pass
        try:
            self.ctp_thread.join()
        except:
            pass
        self.image=Image.open(filepreview)
        self.photo=ImageTk.PhotoImage(self.image)
        self.map_x_res=self.photo.width()
        self.map_y_res=self.photo.height()
        self.img_map=self.canvas.create_image(0,0,anchor=NW,image=self.photo)
        self.canvas.config(scrollregion=self.canvas.bbox(ALL))
        self.canvas.bind("<ButtonPress-1>", self.scroll_start)
        self.canvas.bind("<B1-Motion>", self.scroll_move)
        self.canvas.bind("<Shift-ButtonPress-1>",self.newPoint) 
        self.canvas.focus_set()
        self.canvas.bind('p', self.newPoint)
        self.canvas.bind('d', self.delete_zone_cmd)
        self.canvas.bind('n', self.save_zone_cmd)
        self.canvas.bind('<BackSpace>', self.delLast)
        self.polygon_list=[]
        self.polyobj_list=[]
        self.poly_curr=[]
        bdpoints=[]
        for [latp,lonp] in [[lat,lon],[lat,lon+1],[lat+1,lon+1],[lat+1,lon]]:
                x=(lonp-self.lonmin)/(self.lonmax-self.lonmin)*self.map_x_res
                y=(self.latmax-latp)/(self.latmax-self.latmin)*self.map_y_res
                bdpoints+=[int(x),int(y)]
        self.boundary=self.canvas.create_polygon(bdpoints,\
                           outline='black',fill='', width=2)
        for zone in zone_list:
            self.coords=zone[0][0:-2]
            self.zlpol.set(zone[1])
            self.zmap_combo.set(zone[2])
            self.points=[]
            for idxll in range(0,len(self.coords)//2):
                latp=self.coords[2*idxll]
                lonp=self.coords[2*idxll+1]
                x=(lonp-self.lonmin)/(self.lonmax-self.lonmin)*self.map_x_res
                y=(self.latmax-latp)/(self.latmax-self.latmin)*self.map_y_res
                self.points+=[int(x),int(y)]
            self.redraw_poly()
            self.save_zone_cmd()
        return

    def scroll_start(self,event):
        self.canvas.scan_mark(event.x, event.y)
        return

    def scroll_move(self,event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        return


    def redraw_poly(self):
        try:
            self.canvas.delete(self.poly_curr)
        except:
            pass
        try:
            color=self.dico_color[self.zlpol.get()]
            self.poly_curr=self.canvas.create_polygon(self.points,\
                           outline=color,fill='', width=2)
        except:
            pass
        return

    def newPoint(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        self.points+=[x,y]
        latp=self.latmax-(y/self.map_y_res)*(self.latmax-self.latmin)
        lonp=self.lonmin+(x/self.map_x_res)*(self.lonmax-self.lonmin)
        self.coords+=[latp,lonp]
        self.redraw_poly()
        return
 
    def delLast(self,event):
        self.points=self.points[0:-2]
        self.coords=self.coords[0:-2]
        self.redraw_poly()
        return
    
    def compute_size(self):
        total_size=0
        for polygon in self.polygon_list:
            polyp=polygon[0]+polygon[0][0:2]
            area=0
            x1=polyp[0]
            y1=polyp[1]
            for j in range(1,len(polyp)//2):
                x2=polyp[2*j]
                y2=polyp[2*j+1]
                area+=(x2-x1)*(y2+y1)
                x1=x2
                y1=y2
            total_size+=abs(area)/2*((40000*cos(pi/180*polygon[1][0])/2**(int(self.zl_combo.get())+8))**2)*2**(2*(int(polygon[2])-17))/1024
        self.gb.set('{:.1f}'.format(total_size)+"Gb")
        return

    def save_zone_cmd(self):
        if len(self.points)<6:
            return
        self.polyobj_list.append(self.poly_curr)
        self.polygon_list.append([self.points,self.coords,self.zlpol.get(),\
                                 self.zmap_combo.get()])
        self.compute_size()
        self.poly_curr=[]
        self.points=[]
        self.coords=[]
        return
    
    def delete_zone_cmd(self):
        try:
            self.canvas.delete(self.poly_curr)
            self.poly_curr=self.polyobj_list[-1]
            self.points=self.polygon_list[-1][0]
            self.coords=self.polygon_list[-1][1]
            self.zlpol.set(self.polygon_list[-1][2])
            self.zmap_combo.set(self.polygon_list[-1][3])
            self.polygon_list.pop(-1)
            self.polyobj_list.pop(-1)
            self.compute_size()
        except:
            self.points=[]
            self.coords=[]
        return
    
    def save_zone_list(self):
        global zone_list
        
        def zlkey(item):
            return item[2]
        ordered_list=sorted(self.polygon_list,key=zlkey,reverse=True)
        zone_list=[]
        for item in ordered_list:
            tmp=[]
            for pt in item[1]:
                tmp.append(float('{:.3f}'.format(float(pt))))
            for pt in item[1][0:2]:     # repeat first point for point_in_polygon algo
                tmp.append(float('{:.3f}'.format(float(pt))))
            zone_list.append([tmp,item[2],item[3]])
        self.destroy()    
        return


class Ortho4XP_Graphical(Tk):

    def __init__(self):
        
        Tk.__init__(self)
        self.title('Ortho4XP')
        toplevel = self.winfo_toplevel()
        try:
            toplevel.wm_state('zoomed')
        except:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight() - 60
            geom_string = "%dx%d+0+0" % (w,h)
            toplevel.wm_geometry(geom_string) 
        self.columnconfigure(1,weight=1)
        self.rowconfigure(0,weight=1)
        sys.stdout=self
        
        # Variables
        self.red_flag        = IntVar()
        self.red_flag.set(0)
        self.lat             = IntVar()
        self.lat.set(48)
        self.lon             = IntVar()
        self.lon.set(-6)
        self.bdc             = IntVar()
        self.bdc.set(0)
        self.bd              = StringVar()
        self.bd.set('')
        self.ma              = StringVar()
        self.ma.set('0.01')
        self.ct              = StringVar()
        self.ct.set('0.2')
        self.minangc         = IntVar()
        self.minangc.set(0)
        self.minang          = StringVar()
        self.minang.set('')
        self.cdc             = IntVar()
        self.cdc.set(0)
        self.cde             = StringVar()
        self.cde.set('')
        self.water_type      = IntVar()
        self.water_type.set(3)
        self.rw              = StringVar()
        self.rw.set('0.2')
        self.skipd           = IntVar()
        self.skipd.set(0)
        self.skipc           = IntVar()
        self.skipc.set(0)
        self.cleantmp        = IntVar()
        self.cleantmp.set(0)
        self.cleanddster     = IntVar()
        self.cleanddster.set(0)
        self.verbose         = IntVar()
        self.verbose.set(1)
        self.sniff           = IntVar()
        self.sniff.set(0)
        self.sniff_dir       = StringVar()
        self.sniff_dir.set('')
        self.mw              = IntVar()
        self.mw.set(32)
        self.zl_choice=StringVar()
        self.zl_choice.set('16')
        self.c_tms_r         = IntVar()
        self.c_tms_r.set(0)
        self.map_choice      = StringVar()
        self.map_choice.set('BI')
        self.progress_attr   = IntVar()
        self.progress_attr.set(0)
        self.progress_down   = IntVar()
        self.progress_down.set(0)
        self.progress_mont   = IntVar()
        self.progress_mont.set(0)
        self.progress_conv   = IntVar()
        self.progress_conv.set(0)
        # --> mth
        self.comp_func       = StringVar()
        self.comp_func.set('Do nothing')
        # <-- mth

        # Constants
        self.map_list        = ['None']+px256_list+wms2048_list
        self.zl_list         = ['12','13','14','15','16','17','18','19']
        # --> mth
        self.comp_func_list  = ['Do nothing','Exit program','Shutdown computer']
        # <-- mth
        # Frames
        self.frame_left       =  Frame(self, border=4,\
                                 relief=RIDGE,bg='light green')
        self.frame_right      =  Frame(self, border=4,\
                                 relief=RIDGE,bg='light green')
        self.frame_rdbtn      =  Frame(self.frame_left,\
                                 border=0,padx=5,pady=5,bg="light green")
        self.frame_lastbtn    =  Frame(self.frame_left,\
                                 border=0,padx=5,pady=5,bg="light green")
        # Frames properties
        self.frame_right.rowconfigure(0,weight=1)
        self.frame_right.columnconfigure(0,weight=1)
        self.frame_lastbtn.columnconfigure(0,weight=1)
        self.frame_lastbtn.columnconfigure(1,weight=1)
        self.frame_lastbtn.columnconfigure(2,weight=1)
        self.frame_lastbtn.columnconfigure(3,weight=1)
        self.frame_lastbtn.rowconfigure(0,weight=1)
        # Frames placement
        self.frame_left.grid(row=0,column=0,sticky=N+S+W+E)
        self.frame_right.grid(row=0,rowspan=60,column=1,sticky=N+S+W+E)
        self.frame_rdbtn.grid(row=16,column=0,columnspan=3,sticky=N+S+E+W)
        # --> mth
        # --> original
        # self.frame_lastbtn.grid(row=21,column=0,columnspan=6,sticky=N+S+E+W)
        # <-- original
        self.frame_lastbtn.grid(row=23,column=0,columnspan=6,sticky=N+S+E+W)
        # <-- mth

        # Widgets style
        combostyle  = ttk.Style()
        combostyle.theme_create('combostyle', parent='alt',settings = {'TCombobox':\
             {'configure':{'selectbackground': 'white','selectforeground':'blue',\
              'fieldbackground': 'white','foreground': 'blue','background': 'white'}}})
        combostyle.theme_use('combostyle') 
        # Widgets
        self.label_tc         =  Label(self.frame_left,anchor=W,text="Tile coordinates",\
                                   fg = "light green",bg = "dark green",\
                                   font = "Helvetica 16 bold italic")
        self.title_lat        =  Label(self.frame_left,anchor=W,text='Latitude  :',\
                                   bg="light green")
        self.latitude         =  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.lat)
        self.title_lon        =  Label(self.frame_left,anchor=W,text='  Longitude  :',\
                                   bg="light green")
        self.longitude        =  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.lon)
        self.build_dir_check  =  Checkbutton(self.frame_left,text='Custom build_dir  :',anchor=W,\
                                   variable=self.bdc,command=self.choose_dir,bg="light green",\
                                   activebackground="light green",highlightthickness=0)
        self.build_dir_entry  =  Entry(self.frame_left,width=20,bg="white",fg="blue",textvariable=self.bd)
        self.label_zl         =  Label(self.frame_left,anchor=W,text="Zoomlevel and Water options",\
                                    fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.title_src        =  Label(self.frame_left,anchor=W,text="Base source  :",bg="light green") 
        self.map_combo        =  ttk.Combobox(self.frame_left,textvariable=self.map_choice,\
                                    values=self.map_list,state='readonly',width=6)
        self.title_zl         =  Label(self.frame_left,anchor=W,text="  Base zoomlevel  :",bg="light green")
        self.zl_combo         =  ttk.Combobox(self.frame_left,textvariable=self.zl_choice,\
                                    values=self.zl_list,state='readonly',width=3)
        self.preview_btn      =  Button(self.frame_left, text='Choose custom zoomlevel',command=self.preview_tile)
        self.title_water      =  Label(self.frame_left,anchor=W,text="Water type  :",bg="light green")
        self.watertype1       =  Radiobutton(self.frame_left,variable=self.water_type,value=1,text="X-Plane only",\
                                    border=0,bg="light green",activebackground="light green",highlightthickness=0,\
                                    command=self.choose_wt)
        self.watertype2       =  Radiobutton(self.frame_left,variable=self.water_type,value=2,text="Photoreal only",\
                                    border=0,bg="light green",activebackground="light green",highlightthickness=0,\
                                    command=self.choose_wt)
        self.watertype3       =  Radiobutton(self.frame_left,variable=self.water_type,value=3,text="Mixed with transparency",\
                                    border=0,bg="light green",activebackground="light green",highlightthickness=0,\
                                    command=self.choose_wt)
        self.title_ratio_water=  Label(self.frame_left,text='ratio_water  : ',bg="light green")
        self.ratio_water_entry=  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.rw)
        self.label_osm        =  Label(self.frame_left,justify=RIGHT,anchor=W,text="Build vector data (OSM/Patches)",\
                                   fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.title_min_area   =  Label(self.frame_left,text='Min_area  :',anchor=W,bg="light green")
        self.min_area         =  Entry(self.frame_left,width=5,bg="white",fg="blue",textvariable=self.ma)
        self.del_osm_btn      =  Button(self.frame_left,text='Purge OSM data',command=self.purge_osm)
        self.get_osm_btn      =  Button(self.frame_left,text='Step 1 : Build vector data',command=self.build_poly_ifc)
        self.label_bm         =  Label(self.frame_left,anchor=W,text="Build base mesh",\
                                   fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.title_curv_tol   =  Label(self.frame_left,text='Curv_tol  :',anchor=W,bg="light green")
        self.curv_tol         =  Entry(self.frame_left,width=5,bg="white",fg="blue",textvariable=self.ct)
        self.min_angle_check  =  Checkbutton(self.frame_left,text='Min_angle :',anchor=W,variable=self.minangc,
                                 command=self.choose_minang,bg="light green",activebackground="light green",\
                                         highlightthickness=0)
        self.min_angle        =  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.minang)
        self.build_mesh_btn   =  Button(self.frame_left,text='Step 2 : Build base mesh',command=self.build_mesh_ifc)
        self.custom_dem_check =  Checkbutton(self.frame_left,text='Custom DEM file :',anchor=W,\
                                   variable=self.cdc,command=self.choose_dem,bg="light green",\
                                   activebackground="light green",highlightthickness=0)
        self.custom_dem_entry =  Entry(self.frame_left,width=20,bg="white",fg="blue",textvariable=self.cde)
        self.label_dsf        =  Label(self.frame_left,justify=RIGHT,anchor=W,text="Build Tile",\
                                    fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.skipdown_check   =  Checkbutton(self.frame_left,text="Skip downloads",\
                                    anchor=W,variable=self.skipd,command=self.set_skip_downloads,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.skipconv_check   =  Checkbutton(self.frame_left,text="Skip converts",\
                                    anchor=W,variable=self.skipc,command=self.set_skip_converts,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.verbose_check    =  Checkbutton(self.frame_left,text="Verbose output",\
                                    anchor=W,variable=self.verbose,command=self.set_verbose_output,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.cleantmp_check   =  Checkbutton(self.frame_left,text="Clean tmp files",\
                                    anchor=W,variable=self.cleantmp,command=self.set_cleantmp,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.cleanddster_check=  Checkbutton(self.frame_left,text="Clean unused dds/ter",\
                                    anchor=W,variable=self.cleanddster,command=self.set_cleanddster,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.sniff_check      =  Checkbutton(self.frame_left,text="Custom overlay dir :",\
                                    anchor=W,variable=self.sniff,command=self.choose_sniff_dir,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.sniff_dir_entry  =  Entry(self.frame_left,width=30,bg="white",fg="blue",textvariable=self.sniff_dir)
        self.sniff_btn        =  Button(self.frame_left,text='Build overlay',command=self.build_overlay_ifc)
        self.check_response   =  Checkbutton(self.frame_left,text="Check TMS response ",\
                                    anchor=W,variable=self.c_tms_r,command=self.set_c_tms_r,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.build_tile_btn   =  Button(self.frame_left,text='Step 3 : Build Tile',command=self.build_tile_ifc)
        self.title_masks_width=  Label(self.frame_left,text='Masks_width  :',anchor=W,bg="light green")
        self.masks_width_e    =  Entry(self.frame_left,width=5,bg="white",fg="blue",textvariable=self.mw)
        self.build_masks_btn  =  Button(self.frame_left,text='(Step 2.5 : Build Masks)',command=self.build_masks_ifc)
        self.read_cfg_btn     =  Button(self.frame_lastbtn,text='Read Config ',command=self.read_cfg)
        self.write_cfg_btn    =  Button(self.frame_lastbtn,text='Write Config',command=self.write_cfg)
        self.kill_proc_btn    =  Button(self.frame_lastbtn,text='Stop process',command=self.stop_process)
        self.exit_btn         =  Button(self.frame_lastbtn,text='    Exit    ',command=self.quit)
        self.title_progress_a =  Label(self.frame_left,anchor=W,text="DSF/Masks progress",bg="light green")
        self.progressbar_attr =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_attr,)
        self.title_progress_d =  Label(self.frame_left,anchor=W,text="Download progress",bg="light green")
        self.progressbar_down =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_down,)
        self.title_progress_m =  Label(self.frame_left,anchor=W,text="Montage progress",bg="light green")
        self.progressbar_mont =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_mont,)
        self.title_progress_c =  Label(self.frame_left,anchor=W,text="Convert progress",bg="light green")
        self.progressbar_conv =  ttk.Progressbar(self.frame_left,mode='determinate',\
                                 orient=HORIZONTAL,variable=self.progress_conv,)
        # --> mth
        self.title_comp_func  = Label(self.frame_left,anchor=W,text="On completion :",bg="light green")
        self.comp_func_combo  = ttk.Combobox(self.frame_left,textvariable=self.comp_func,\
                                    values=self.comp_func_list,state='readonly')
        # <-- mth
        self.std_out          =  Text(self.frame_right)
        # Placement of Widgets
        self.label_tc.grid(row=0,column=0,columnspan=6,sticky=W+E)
        self.title_lat.grid(row=1,column=0, padx=5, pady=5,sticky=E+W)
        self.latitude.grid(row=1,column=1, padx=5, pady=5,sticky=W)
        self.title_lon.grid(row=1,column=2, padx=5, pady=5,sticky=E+W) 
        self.longitude.grid(row=1,column=3, padx=5, pady=5,sticky=W)
        self.build_dir_check.grid(row=2,column=0,columnspan=2, pady=5,sticky=N+S+E+W) 
        self.build_dir_entry.grid(row=2,column=2,columnspan=4, padx=5, pady=5,sticky=W+E)
        self.label_zl.grid(row=3,column=0,columnspan=6,sticky=W+E)
        self.title_src.grid(row=4,column=0,sticky=E+W,padx=5,pady=5)
        self.map_combo.grid(row=4,column=1,padx=5,pady=5,sticky=W)
        self.title_zl.grid(row=4,column=2,sticky=N+S+E+W,padx=5,pady=5)
        self.zl_combo.grid(row=4,column=3,columnspan=1,padx=5,pady=5,sticky=W)
        self.preview_btn.grid(row=4,column=4, columnspan=2,padx=5, pady=5,sticky=N+S+W+E)
        self.title_water.grid(row=5,column=0,columnspan=1, padx=5,pady=5,sticky=N+S+E+W)
        self.watertype1.grid(row=5,column=1,columnspan=2, pady=5,sticky=N+S+W)
        self.watertype2.grid(row=6,column=1,columnspan=2, pady=5,sticky=N+S+W)
        self.watertype3.grid(row=7,column=1,columnspan=2, pady=5,sticky=N+S+W)
        self.title_ratio_water.grid(row=7,column=3,columnspan=1, padx=5, pady=5,sticky=N+S+W+E) 
        self.ratio_water_entry.grid(row=7,column=4, padx=5, pady=5,sticky=N+S+W)
        self.label_osm.grid(row=8,column=0,columnspan=6,sticky=W+E)
        self.title_min_area.grid(row=9,column=0, padx=5, pady=5,sticky=W+E) 
        self.min_area.grid(row=9,column=1, padx=5, pady=5,sticky=W)
        self.del_osm_btn.grid(row=9,column=2, columnspan=2, pady=5,sticky=N+S+W)
        self.get_osm_btn.grid(row=9,column=4, columnspan=2,padx=5, pady=5,sticky=N+S+W+E)
        self.label_bm.grid(row=10,column=0,columnspan=6,sticky=W+E)
        self.title_curv_tol.grid(row=11,column=0, padx=5, pady=5,sticky=W+E) 
        self.curv_tol.grid(row=11,column=1, padx=5, pady=5,sticky=W)
        self.min_angle_check.grid(row=11,column=2, padx=5, pady=5,sticky=W)
        self.min_angle.grid(row=11,column=3, padx=5, pady=5,sticky=W)
        self.build_mesh_btn.grid(row=11,column=4, columnspan=2,padx=5, pady=5,sticky=N+S+W+E)
        self.custom_dem_check.grid(row=12,column=0,columnspan=2, padx=5, pady=5,sticky=W)
        self.custom_dem_entry.grid(row=12,column=2,columnspan=4, padx=5, pady=5,sticky=N+S+E+W)
        self.label_dsf.grid(row=13,column=0,columnspan=6,sticky=W+E)
        self.skipdown_check.grid(row=14,column=0,columnspan=2, pady=5,sticky=N+S+E+W)
        self.skipconv_check.grid(row=14,column=2,columnspan=1, pady=5,sticky=N+S+E+W)
        self.verbose_check.grid(row=16,column=0,columnspan=2, pady=5,sticky=N+S+W)
        self.cleantmp_check.grid(row=16,column=2,columnspan=1, pady=5,sticky=N+S+W)
        self.cleanddster_check.grid(row=16,column=3,columnspan=2, pady=5,sticky=N+S+W)
        self.build_tile_btn.grid(row=18,rowspan=3,column=4,columnspan=2,padx=5,sticky=N+S+W+E)
        self.check_response.grid(row=14,column=3,columnspan=3,sticky=W)
        self.sniff_check.grid(row=15,column=0,columnspan=2, pady=5,sticky=N+S+E+W)
        self.sniff_dir_entry.grid(row=15,column=2,columnspan=3, padx=5, pady=5,sticky=N+S+E+W)
        self.sniff_btn.grid(row=15,column=5,columnspan=1, padx=5, pady=5,sticky=N+S+E+W)
        self.title_masks_width.grid(row=17,column=0, padx=5, pady=5,sticky=W+E) 
        self.masks_width_e.grid(row=17,column=1, padx=5, pady=5,sticky=W)
        self.build_masks_btn.grid(row=17,column=2,columnspan=2,padx=5,pady=5,sticky=N+S+W+E)
        self.read_cfg_btn.grid(row=0,column=0,padx=5, pady=5,sticky=N+S+W+E)
        self.write_cfg_btn.grid(row=0,column=1,padx=5, pady=5,sticky=N+S+W+E)
        self.kill_proc_btn.grid(row=0,column=2,padx=5,pady=5,sticky=N+S+W+E)
        self.exit_btn.grid(row=0,column=3, padx=5, pady=5,sticky=N+S+W+E)
        self.title_progress_a.grid(row=18,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_attr.grid(row=18,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.title_progress_d.grid(row=19,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_down.grid(row=19,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.title_progress_m.grid(row=20,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_mont.grid(row=20,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.title_progress_c.grid(row=21,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_conv.grid(row=21,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        # --> mth
        self.title_comp_func.grid(row=22,column=0,columnspan=2,padx=5,pady=5,sticky=E+W)
        self.comp_func_combo.grid(row=22,column=2,columnspan=2,padx=5,pady=5,sticky=E+W)
        # <-- mth
        self.std_out.grid(row=0,column=0,padx=5,pady=5,sticky=N+S+E+W)
        # read default choices from config file 
        try:
            self.water_type.set(water_option)
            self.rw.set(ratio_water)
            self.ma.set(min_area)
            self.ct.set(curvature_tol)
            if no_small_angles==True:
                self.minangc.set(1)
                self.minang.set(smallest_angle)
            else:
                self.minangc.set(0)
                self.minang.set('')
            self.skipd.set(skip_downloads)
            self.skipc.set(skip_converts)
            self.cleantmp.set(clean_tmp_files)
            self.cleanddster.set(clean_unused_dds_and_ter_files)
            self.verbose.set(verbose_output)
            if check_tms_response==True:
                self.c_tms_r.set(1)
            else:
                self.c_tms_r.set(0)
            self.map_choice.set(default_website)
            self.zl_choice.set(default_zl)
            self.mw.set(masks_width)
            self.sniff_dir.set(default_sniff_dir)
        except:
            print("\nWARNING : the main config file is incomplete or does not follow the syntax,")
            print("I could not initialize all the parameters to your wish.")
            print('_____________________________________________________________'+\
                '____________________________________')
        return 
        
    def write(self,text):
        if text=='' or text[-1]!='\r':
            self.std_out.insert(END,str(text))
            self.std_out.see(END)
        else:
            self.std_out.delete("end linestart", "end") 
            self.std_out.insert(END,str(text))
            self.std_out.see(END)
        return

    def flush(self):
        return
    
    def stop_process(self):
        application.red_flag.set(1)
        return

    def choose_dir(self):
        if self.bdc.get()==1:
            self.bd.set(filedialog.askdirectory())
        else:
            self.bd.set('')
        return 
    
    def choose_dem(self):
        if self.cdc.get()==1:
            self.cde.set(filedialog.askopenfilename())
        else:
            self.cde.set('')
        return 
    
    def choose_minang(self):
        if self.minangc.get()==1:
            self.minang.set('5')
        else:
            self.minang.set('')
        return
    
    def choose_sniff_dir(self):
        if self.sniff.get()==1:
            self.sniff_dir.set(filedialog.askdirectory())
        else:
            self.sniff_dir.set('')
        return 
    
    def choose_wt(self):
        if self.water_type.get()==3:
            self.rw.set('0.2')
        else:
            self.rw.set('')
        return
    

    def read_cfg(self):
        global build_dir,water_option,ratio_water,min_area,curvature_tol,\
               no_small_angles,smallest_angle,default_website,default_zl,\
               skip_downloads,skip_converts,verbose_output,clean_tmp_files,\
               dds_or_png,check_tms_response,zone_list
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
        try:
            exec(open(build_dir+dir_sep+'Ortho4XP.cfg').read(),globals())
        except:
            print('\nFailure : the tile specific config file is not present or does follow the syntax.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return 
        try:
            self.water_type.set(water_option)
            self.rw.set(ratio_water)
            self.ma.set(min_area)
            self.ct.set(curvature_tol)
            if no_small_angles==True:
                self.minangc.set(1)
                self.minang.set(smallest_angle)
            else:
                self.minangc.set(0)
                self.minang.set('')
            self.skipd.set(skip_downloads)
            self.skipc.set(skip_converts)
            self.cleantmp.set(clean_tmp_files)
            self.cleanddster.set(clean_unused_dds_and_ter_files)
            self.verbose.set(verbose_output)
            if check_tms_response==True:
                self.c_tms_r.set(1)
            else:
                self.c_tms_r.set(0)
            try:
                self.map_choice.set(default_website)
            except:
                print("\nFailure : your default provider is no longer present in your address book.")
                print('_____________________________________________________________'+\
                   '____________________________________')
                return
            self.zl_choice.set(default_zl)
            self.mw.set(masks_width)
        except:
            print("\nWARNING : the main config file is incomplete or does not follow the syntax,")
            print("I could not initialize all the parameters to your wish.")
            print('_____________________________________________________________'+\
                '____________________________________')
        return
      
    def write_cfg(self):
        global zone_list
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
        try:
            fgen=open(Ortho4XP_dir+dir_sep+"Ortho4XP.cfg",'r')
            fbuild=open(build_dir+dir_sep+"Ortho4XP.cfg",'w')
            fbuild.write("# generated from the generic config file :\n")
        except:
            print("\nI could not read or write the config file.")
            print("Are you sure about the indicated build_dir directory ?")
            print("\n Failure.")
            print('_____________________________________________________________'+\
                '____________________________________')
            return
        for line in fgen.readlines():
            fbuild.write(line)
        fgen.close()
        fbuild.write("\n# generated from the interface :\n")
        if self.skipd.get()==0:
            fbuild.write("skip_downloads=False\n")
        else:
            fbuild.write("skip_downloads=True\n")
        if self.skipc.get()==0:
            fbuild.write("skip_converts=False\n")
        else:
            fbuild.write("skip_converts=True\n")
        if self.c_tms_r.get()==0:
            fbuild.write("check_tms_response=False\n")
        else:
            fbuild.write("check_tms_response=True\n")
        if self.verbose.get()==0:
            fbuild.write("verbose_output=False\n")
        else:
            fbuild.write("verbose_output=True\n")
        if self.cleantmp.get()==0:
            fbuild.write("clean_tmp_files=False\n")
        else:
            fbuild.write("clean_tmp_files=True\n")
        if self.cleanddster.get()==0:
            fbuild.write("clean_unused_dds_and_ter_files=False\n")
        else:
            fbuild.write("clean_unused_dds_and_ter_files=True\n")
        fbuild.write("min_area="+str(min_area)+"\n")
        fbuild.write("curvature_tol="+str(curvature_tol)+"\n")
        if self.minangc.get()==0:
            fbuild.write("no_small_angles=False\n")
        else:
            fbuild.write("no_small_angles=True\n")
        if self.minangc.get()==1:
            fbuild.write("smallest_angle="+str(smallest_angle)+"\n")
        fbuild.write("default_website='"+str(self.map_choice.get())+"'\n") 
        fbuild.write("default_zl="+str(self.zl_choice.get())+"\n") 
        fbuild.write("zone_list=[]\n")
        for zone in zone_list:
            fbuild.write("zone_list.append("+str(zone)+")\n")
        fbuild.write("water_option="+str(water_option)+"\n")
        if water_option==3:
            fbuild.write("ratio_water="+str(ratio_water)+"\n")
        fbuild.write("masks_width="+str(masks_width)+"\n")
        fbuild.close()
        return

    def load_latlon(self):
        try:
            lat=int(self.latitude.get())
            lon=int(self.longitude.get())
            if lat<-85 or lat>85 or lon<-180 or lon>180:
                print('\nFailure : latitude and/or longitude exceed limit.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return ['error','error']
        except:
            print('\nFailure : latitude and/or longitude wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return ['error','error']
        return [lat,lon]
 
    def preview_tile(self):
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        self.preview_window=Preview_window(lat,lon)
        return
    
    def purge_osm(self):
        global build_dir
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
        try:
            for f in os.listdir(build_dir):
                if 'OSM_' in f:
                    os.remove(os.path.join(build_dir,f))
        except:
            print("\nFailure : Custom build_dir seems non existing.")
            print('_____________________________________________________________'+\
            '____________________________________')
        return
    
    def build_poly_ifc(self):
        global build_dir, min_area
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        try:
            min_area=float(self.min_area.get())
        except:
            print('\nFailure : parameter min_area wrongly encoded.')
            print('_____________________________________________________________'+\
            '____________________________________')
            return
        if (min_area<0):
            print('\nFailure : parameter min_area exceeds limits.')
            print('_____________________________________________________________'+\
            '____________________________________')
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
        water_option= self.water_type.get()
        print("\nStep 1 : Building OSM and patch data for tile "+strlat+strlon+" : ")
        print("--------\n")
        fargs_get_osm=[lat,lon,water_option,build_dir]
        build_dir_thread=threading.Thread(target=build_poly_file,args=fargs_get_osm)
        build_dir_thread.start()
        return

    def build_mesh_ifc(self):
        global build_dir,curvature_tol,no_small_angles,smallest_angle
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
        try:
            curvature_tol=float(self.curv_tol.get())
            if curvature_tol < 0.01 or curvature_tol>100:
                print('\nFailure : curvature_tol exceeds limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        except:
            print('\nFailure : curvature_tol wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return
        if self.minangc.get()==0:
            no_small_angles=False
        else:
            no_small_angles=True
        if no_small_angles==True:
            try:
                smallest_angle=int(self.minang.get())
            except:
                print('\nFailure : minimum angle wrongly encoded.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
            if (smallest_angle<0) or (smallest_angle>30):
                print('\nFailure : minimum angle larger than 30° not allowed.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        print("\nStep 2 : Building mesh for tile "+strlat+strlon+" : ")
        print("--------\n")
        fargs_build_mesh=[lat,lon,build_dir]
        build_mesh_thread=threading.Thread(target=build_mesh,args=fargs_build_mesh)
        build_mesh_thread.start()
        return

    def build_overlay_ifc(self):
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
        strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
        base_sniff_dir=self.sniff_dir_entry.get()
        print("\nIndependent Step  : Building of an Overlay DSF from third party data : ")
        print("-------------------\n")
        file_to_sniff=base_sniff_dir+dir_sep+"Earth nav data"+dir_sep+\
                      strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'
        if not os.path.isfile(file_to_sniff):
            print('\nFailure : there is no file to sniff from at the indicated place.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return 
        fargs_build_overlay=[lat,lon,file_to_sniff]
        build_overlay_thread=threading.Thread(target=build_overlay,args=fargs_build_overlay)
        build_overlay_thread.start()
        return 
    
    def build_tile_ifc(self):
        global lat,lon,build_dir,skip_downloads,skip_converts,verbose_output,\
                clean_tmp_files,dds_or_png,water_overlay,ratio_water,ortho_list,zone_list
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
        if self.skipd.get()==1:
            skip_downloads=True
        else:
            skip_downloads=False
        if self.skipc.get()==1:
            skip_converts=True
        else:
            skip_converts=False
        if self.verbose.get()==1:
            verbose_output=True
        else:
            verbose_output=False
        mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
        if os.path.isfile(mesh_filename)!=True:
            print("You must first construct the mesh !")
            return
        if self.water_type.get()==1:
            water_overlay=False
        else:
            water_overlay=True
            try:
                ratio_water=float(self.ratio_water_entry.get())
            except:
                print("The ratio_water parameter is wrongly encoded.")
                return
        self.set_cleantmp()
        website=self.map_choice.get()
        zoomlevel=self.zl_choice.get()
        ortho_list=zone_list[:]
        if website!='None':
            ortho_list.append([[lat,lon,lat,lon+1,lat+1,lon+1,lat+1,lon,lat,lon],\
                    str(zoomlevel),str(website)])
        self.write_cfg()
        print("\nStep 3 : Building Tile "+strlat+strlon+" : ")
        print("--------\n")
        fargs_build_tile=[lat,lon,build_dir,mesh_filename,clean_tmp_files]
        build_tile_thread=threading.Thread(target=build_tile,\
                args=fargs_build_tile)
        build_tile_thread.start()
        return
    
    def build_masks_ifc(self):
        global lat,lon,build_dir,water_overlay,masks_width
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
        try:
            masks_width=int(self.masks_width_e.get())
            if masks_width < 1 or masks_width>11048:
                print('\nFailure : masks_width off limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        except:
            print('\nFailure : masks_width wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return
        if not os.path.exists(build_dir+dir_sep+"textures"):
            os.makedirs(build_dir+dir_sep+"textures")
        mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
        if os.path.isfile(mesh_filename)!=True:
            print("You must first construct the mesh !")
            return
        print("\nStep 2.5 : Building Masks for Tile "+strlat+strlon+" : ")
        print("----------\n")
        if complex_masks==False:
            mesh_filename_list=[mesh_filename]
        else:
            mesh_filename_list=[]
            for closelat in [lat-1,lat,lat+1]:
                for closelon in [lon-1,lon,lon+1]:
                    strcloselat='{:+.0f}'.format(closelat).zfill(3)
                    strcloselon='{:+.0f}'.format(closelon).zfill(4)
                    closemesh_filename=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strcloselat+strcloselon+\
                                   dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                    if os.path.isfile(closemesh_filename):
                        mesh_filename_list.append(closemesh_filename)
        fargs_build_masks=[lat,lon,build_dir,mesh_filename_list]
        build_masks_thread=threading.Thread(target=build_masks,\
                args=fargs_build_masks)
        build_masks_thread.start()
        return

    def set_skip_downloads(self):
        if self.skipd.get()==1:
            self.skipc.set(1)
        return
    
    def set_skip_converts(self):
        if self.skipc.get()==0:
            if self.skipd.get()==1:
                self.skipc.set(1)
        return
    
    def set_c_tms_r(self):
        global check_tms_response
        if self.c_tms_r.get()==0:
            check_tms_response=False
        else:
            check_tms_response=True
        return

    def set_verbose_output(self):
        if self.verbose.get()==0:
            verbose_output=False
        else:
            verbose_output=True
        return
    
    def set_cleantmp(self):
        global clean_tmp_files
        if self.cleantmp.get()==0:
            clean_tmp_files=False
        else:
            clean_tmp_files=True
        return
    
    def set_cleanddster(self):
        global clean_unused_dds_and_ter_files
        if self.cleanddster.get()==0:
            clean_unused_dds_and_ter_files=False
        else:
            clean_unused_dds_and_ter_files=True
        return
    
    def kill_process(self):
        return

##############################################################################


##############################################################################
#                                                                            #
#   LE PROGRAMME CHEF, QUI DIRIGE TOUT MAIS QUI NE FAIT RIEN.                #
#                                                                            #
##############################################################################

if __name__ == '__main__':
    if len(sys.argv)==1: # switch to the graphical interface
        ortho_list=[]
        zone_list=[]
        exec(open(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg').read())
        os.system(delete_cmd+" "+Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"*.jpg "+devnull_rdir)
        os.system(delete_cmd+" "+Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"*.png "+devnull_rdir)
        application = Ortho4XP_Graphical()
        application.mainloop()	    
        application.quit()
        sys.exit()
    # sequel is only concerned with command line (AND NOT UP TO DATE !!!) 
    tinit=time.time()
    ortho_list=[]
    zone_list=[]
    if len(sys.argv)<3:
        usage('command_line')
    exec(open(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg').read())
    try:
        lat=int(sys.argv[1])
        lon=int(sys.argv[2])
    except:
        usage('command_line')
    if len(sys.argv)==4:
        try:
            exec(open(Ortho4XP_dir+dir_sep+sys.argv[3]).read())
        except:
            print("Could not read the custom config file, probably a syntax error")
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    if water_option in [2,3]:
        water_overlay=True
    else:
        water_overlay=False
    try:
        exec(open(Ortho4XP_dir+dir_sep+'Carnet_d_adresses.py').read())
    except:
        usage('adresses')
    if build_dir=="default":
        build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
    print("\nStep 1 : Building OSM and patch data for tile "+strlat+strlon+" : ")
    print("--------\n")
    build_poly_file(lat,lon,water_option,build_dir)
    print("\nStep 2 : Building mesh for tile "+strlat+strlon+" : ")
    print("--------\n")
    build_mesh(lat,lon,build_dir)
    print("\nStep 2.5 : Building Masks for Tile "+strlat+strlon+" : ")
    print("----------\n")
    mesh_filename = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
    if complex_masks==False:
        mesh_filename_list=[mesh_filename]
    else:
        mesh_filename_list=[]
        for closelat in [lat-1,lat,lat+1]:
            for closelon in [lon-1,lon,lon+1]:
                strcloselat='{:+.0f}'.format(closelat).zfill(3)
                strcloselon='{:+.0f}'.format(closelon).zfill(4)
                closemesh_filename=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strcloselat+strcloselon+\
                               dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                if os.path.isfile(closemesh_filename):
                    mesh_filename_list.append(closemesh_filename)
    # [Thanks to Simheaven] fix for missing folder textures
    build_dir=Ortho4XP_dir+dir_sep+'zOrtho4XP_'+strlat+strlon
    if not os.path.exists(build_dir+dir_sep+"textures"):
        os.makedirs(build_dir+dir_sep+"textures")
    build_masks(lat,lon,build_dir,mesh_filename_list)
    ortho_list=zone_list[:]
    if default_website!='None':
        ortho_list.append([[lat,lon,lat,lon+1,lat+1,lon+1,lat+1,lon,lat,lon],\
                    str(default_zl),str(default_website)])
    print("\nStep 3 : Building Tile "+strlat+strlon+" : ")
    print("--------\n")
    build_tile(lat,lon,build_dir,mesh_filename,clean_tmp_files)
    print('\nBon vol !')
##############################################################################
#                                                                            #
#                           THAT'S ALL FOLKS                                 #
#                                                                            #
##############################################################################





