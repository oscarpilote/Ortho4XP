#!/usr/bin/env python3                                                       
##############################################################################
# Ortho4XP : A base mesh creation tool for the X-Plane 11 flight simulator.  #
# Version  : devel                                                           #
# Copyright 2017 Oscar Pilote                                                #
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

version=' devel'

import os
import sys

try:
    import encodings.idna
except:
    pass

if getattr(sys,'frozen',False):
    Ortho4XP_dir        = '..'
    os.environ["REQUESTS_CA_BUNDLE"] = os.path.join(os.getcwd(), "cacert.pem") # needed to access https providers with the bin version
else:
    Ortho4XP_dir        = '.'

try:
    sys.path.append(os.getcwd()+'/'+Ortho4XP_dir+'/bin/Modules')
except:
    pass

import requests
import pyproj
import threading,subprocess,time,gc,shutil,io
from math import pi,floor,ceil,sqrt,log,exp,sin,cos,tan,atan,atanh
import array,numpy
import random
from collections import defaultdict
import struct
import hashlib
from tkinter import *               # GUI
from tkinter import filedialog
import tkinter.ttk as ttk           # Themed Widgets
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps, ImageTk
Image.MAX_IMAGE_PIXELS = 1000000000 # Not a decompression bomb attack!   
import subprocess 
import queue
from shapely import geometry
from shapely import ops
from rtree import index
import itertools

try:
    import gdal
    gdal_loaded = True
except:
    gdal_loaded = False


########################################################################
#
# FACTORY DEFAULT VALUES 
#
# The following are initialisation of the variables, they are then superseded by your Ortho4XP.cfg file but are here
# in case your config file misses some of then (evolution, edit, ...).  Do not modify them here but use your
# config file instead.

configvars=['default_website','default_zl','water_option','sea_texture_params','cover_airports_with_highres',
            'cover_zl','cover_extent','min_area','road_level','road_banking_limit','max_levelled_segs',
            'clean_bad_geometries','max_pols_for_merge','sea_equiv','do_not_flatten_these_list','meshzl',
            'insert_custom_zoom_in_mesh','poly_simplification_tol','overpass_server_list','overpass_server_choice',
            'max_osm_tentatives',
            # 
            'curvature_tol','apt_curv_tol','apt_curv_ext','coast_curv_tol','coast_curv_ext','no_small_angles','smallest_angle',
            'hmin','hmax','tile_has_water_airport','water_smoothing','sea_smoothing_mode','is_custom_dem','custom_dem',
            # 
            'masks_width','complex_masks','use_masks_for_inland','legacy_masks','keep_old_pre_mask',
            'maskszl','use_DEM_too_for_masks','use_gimp','gimp_cmd',
            # 
            'ratio_water','sea_texture_blur_radius','normal_map_strength','terrain_casts_shadows','use_decal_on_terrain',
            'dds_or_png','use_bing_for_non_existent_data', 'max_convert_slots','be_nice_timer',
            'skip_downloads','skip_converts','check_tms_response',
            'verbose_output','clean_tmp_files','clean_unused_dds_and_ter_files',
            'contrast_adjust','brightness_adjust','saturation_adjust',
            'full_color_correction','g2xpl_8_prefix','g2xpl_8_suffix','g2xpl_16_prefix','g2xpl_16_suffix',
            #
            'Custom_scenery_prefix','Custom_scenery_dir','default_sniff_dir',
            'keep_orig_zuv','seven_zip','landclass_mesh_division','snap_to_z_grid','overlay_lod',
            'keep_overlays'
           ]

configvars_strings=['default_website','overpass_server_choice','gimp_cmd','dds_or_png',
                    'g2xpl_8_prefix','g2xpl_8_suffix','g2xpl_16_prefix','g2xpl_16_suffix',
                    'Custom_scenery_prefix','Custom_scenery_dir','default_sniff_dir','custom_dem'
                   ]

configvars_defaults={
        'default_website':'BI',
        'default_zl':16,
        'water_option':3,
        'sea_texture_params':[],
        'cover_airports_with_highres':False,
        'cover_zl':18,
        'cover_extent':1,
        'min_area':0.01,
        'road_level':1,
        'road_banking_limit':0.5,
        'max_levelled_segs':100000,
        # the next will merge intersecting OSM polygons to get the cleanest mesh, deactive it if this is too slow on some data.  
        'clean_bad_geometries':True,
        'max_pols_for_merge':10,
        'sea_equiv':[],
        'do_not_flatten_these_list':[],
        'meshzl':19,
        'insert_custom_zoom_in_mesh':False,
        'poly_simplification_tol':0.002,
        'overpass_server_list':{"FR":"http://api.openstreetmap.fr/oapi/interpreter", 
            "DE":"http://overpass-api.de/api/interpreter",
            "RU":"http://overpass.osm.rambler.ru/cgi/interpreter"},
        'overpass_server_choice':'DE',
        'max_osm_tentatives':10,
        'curvature_tol':3,
        'apt_curv_tol':1,
        # extent past airport bbox, in km
        'apt_curv_ext':0.5,    
        'coast_curv_tol':1,
        # extent from coastline, in km
        'coast_curv_ext':0.5,
        'no_small_angles':False,
        'smallest_angle':5,
        'is_custom_dem':False,
        'custom_dem':'',
        'hmin':20,
        'hmax':2000,
        'tile_has_water_airport':False,
        'water_smoothing':2,
        'sea_smoothing_mode':0,
        'masks_width':16,
        'complex_masks':False,
        'use_masks_for_inland':False,
        'legacy_masks':True,
        'keep_old_pre_mask':False,
        'maskszl':14,
        'use_DEM_too_for_masks':False,
        'use_gimp':False,
        'gimp_cmd':'',
        'ratio_water':0.3,
        'sea_texture_blur_radius':0,
        'normal_map_strength':0.3,
        'terrain_casts_shadows':False,
        'use_decal_on_terrain':False,
        'dds_or_png':'dds',
        'use_bing_for_non_existent_data':False,
        'max_convert_slots':4,
        'be_nice_timer':0,
        'skip_downloads':False,
        'skip_converts':False,
        'check_tms_response':True,
        'verbose_output':True,
        'clean_tmp_files':True,
        'clean_unused_dds_and_ter_files':False,
        'contrast_adjust':{},
        'brightness_adjust':{},
        'saturation_adjust':{},
        'full_color_correction':{},
        'g2xpl_8_prefix':'g2xpl_8_',
        'g2xpl_8_suffix':'',
        'g2xpl_16_prefix':'g2xpl_16_',
        'g2xpl_16_suffix':'',
        'Custom_scenery_prefix':'',
        'Custom_scenery_dir':'',
        'default_sniff_dir':'',
        'keep_orig_zuv':True,
        'seven_zip':True,
        'landclass_mesh_division':8,
        'snap_to_z_grid':True,
        'overlay_lod':20000,
        'keep_overlays':True
        } 
              
explanation={}
for item in configvars:
    explanation[item]='TODO!'    
try:
    exec(open(Ortho4XP_dir+dir_sep+'Help.py').read(),globals())
except:
    pass    
    
for item in configvars:
    try:
        globals()[item]=configvars_defaults[item] 
    except:
        print("I could not set the variable",item,". Perhaps was there a typo ?")

# These are not put in the interface
build_dir           = "default"     
tricky_provider_hack= 70000    # The minimum size a wms2048 image should be to be accepted (trying to avoid missed cached) 
water_overlay       = True
http_timeout        = 10
pools_max_points    = 65536    # do not change this !
shutdown_timer      = 60       # Time in seconds to close program / shutdown computer after completition
shutd_msg_interval  = 15       # Shutdown message display interval
raster_resolution = 10000      # Image size for the raster of the sniffed landclass terrain, not yet used

#!!!!!!!!!!!!! To put in a better place !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
max_connect_retries=3
max_baddata_retries=3
custom_url_list=[]
flatten_airports=False
tweak_resol_factor=1   # fake texture size factor in the TER files, should be similar effect as the texture resolution tab
use_test_texture=False

# Will be used as global variables
#download_queue=[]
#convert_queue=[]
#busy_slots_mont=0
#busy_slots_conv=0

if 'dar' in sys.platform:
    dir_sep         = '/'
    Triangle4XP_cmd = os.path.join(Ortho4XP_dir,"Utils","Triangle4XP2.app ")
    copy_cmd        = "cp "
    delete_cmd      = "rm "
    rename_cmd      = "mv "
    unzip_cmd       = "7z "
    convert_cmd     = "convert " 
    dds_convert_cmd = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"nvcompress"+dir_sep+"nvcompress-osx -bc1 -fast " 
    dds_conv_dxt5   = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"nvcompress"+dir_sep+"nvcompress-osx -bc3 -fast " 
    gimp_cmd        = "gimp "
    devnull_rdir    = " >/dev/null 2>&1"
    shutdown_cmd    = 'sudo shutdown -h now'
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/DSFTool.app')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/Triangle4XP2.app')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/nvcompress/nvcompress-osx')
elif 'win' in sys.platform: 
    dir_sep         = '\\'
    Triangle4XP_cmd = os.path.join(Ortho4XP_dir,"Utils","Triangle4XP2.exe ")
    copy_cmd        = "copy "
    delete_cmd      = "del "
    rename_cmd      = "move "
    unzip_cmd       = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"7z.exe "
    if os.path.isfile(Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"convert.exe"):
        convert_cmd = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"convert.exe " 
    else:    
        convert_cmd = "convert " 
    dds_convert_cmd = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"nvcompress"+dir_sep+"nvcompress.exe -bc1 -fast " 
    dds_conv_dxt5   = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"nvcompress"+dir_sep+"nvcompress.exe -bc3 -fast " 
    gimp_cmd        = "c:\\Program Files\\GIMP 2\\bin\\gimp-console-2.8.exe "
    showme_cmd      = Ortho4XP_dir+"/Utils/showme.exe "
    devnull_rdir    = " > nul  2>&1"
    shutdown_cmd    = 'shutdown /s /f /t 0'
else:
    dir_sep         = '/'
    Triangle4XP_cmd = Ortho4XP_dir+dir_sep+"Utils"+dir_sep+"Triangle4XP6 "
    delete_cmd      = "rm "
    copy_cmd        = "cp "
    rename_cmd      = "mv "
    unzip_cmd       = "7z "
    convert_cmd     = "convert " 
    dds_convert_cmd = "nvcompress -bc1 -fast " 
    dds_conv_dxt5   = "nvcompress -bc3 -fast " 
    gimp_cmd        = "gimp "
    devnull_rdir    = " >/dev/null 2>&1 "
    shutdown_cmd    = 'sudo shutdown -h now'
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/DSFTool')
    os.system('chmod a+x '+Ortho4XP_dir+dir_sep+'Utils/Triangle4XP')

#
#   END OF FACTORY DEFAULT VALUES
#
##############################################################################

dico_edge_markers   = {'outer':'1','inner':'1','coastline':'2',\
                       'tileboundary':'3','orthogrid':'3',\
                       'airport':'4','runway':'5','patch':'6','road':'3'}
dico_tri_markers    = {'water':'1','sea':'2','sea_equiv':'3','altitude':'4'} 

user_agent_generic="Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
fake_headers_generic={\
            'User-Agent':user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Accept':'*/*',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate'\
            }

try:
    exec(open(Ortho4XP_dir+dir_sep+'Carnet_d_adresses.py').read())
except:
    print("The file Carnet_d_adresses.py does not follow the syntactic rules.")
    time.sleep(5)
    sys.exit()

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
        print("!!!I could not fin the elevation data file, or it was broken.\n!!!I go on with all zero elevation (perhaps a tile full of sea ?)") 
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
class mesh_input():
    
    nodata=-32768
    dico_attributes = {'DUMMY':0,'WATER':1,'SEA':2,'INTERP_ALT':4,'SMOOTHED_ALT':8}
    def __init__(self):
        self.dico_nodes={}  # keys are tuples of 2 floats (locations) and values are ints (ids)  
        self.dico_edges={}  # keys are tuples of 2 ints (end-points ids) and values are ints (ids), and egde id is needed for the index (bbox)
        self.nodes_dico={}  # inverse of dico_nodes : ids to 2-uples (coordinates)
        self.edges_dico={}  # inverse of dico_edges : ids to 2-uples (end-points ids)
        self.ebbox=index.Index()
        self.data_nodes={}  # keys are ints (ids) and values are floats (vector altitude)  # could easily be upgraded to arrays if necessary  
        self.data_edges={}  # keys are ints (ids) and values are ints (attribute)
        self.next_node_id=1
        self.next_edge_id=1
        self.holes=[]
        self.seeds={} 

    def insert_node(self,x,y,z):
        if (x,y) in self.dico_nodes:
            node_id=self.dico_nodes[(x,y)]
            if self.data_nodes[node_id]==self.nodata: self.data_nodes[node_id]=z
        else:
            node_id=self.next_node_id
            self.dico_nodes[(x,y)]=node_id 
            self.nodes_dico[node_id]=(x,y)
            self.data_nodes[node_id]=z
            self.next_node_id+=1
        return node_id

    def interp_nodes(self,node0_id,node1_id,weight):
        x=(1-weight)*self.nodes_dico[node0_id][0]+weight*self.nodes_dico[node1_id][0]
        y=(1-weight)*self.nodes_dico[node0_id][1]+weight*self.nodes_dico[node1_id][1]
        if self.data_nodes[node0_id]!=self.nodata and self.data_nodes[node1_id]!=self.nodata:
            z=(1-weight)*self.data_nodes[node0_id]+weight*self.data_nodes[node1_id]
        else:
            z=self.nodata
        return (x,y,z)
    
    
    def update_edge(self,nodeid0,nodeid1,marker):
        if nodeid0==nodeid1: return 1
        if (nodeid0,nodeid1) in self.dico_edges:
            edge_id=self.dico_edges[(nodeid0,nodeid1)]
            self.data_edges[edge_id]=  self.data_edges[edge_id] | marker # bitwise add new marker if necessary
            return 1 
        if (nodeid1,nodeid0) in self.dico_edges:
            edge_id=self.dico_edges[(nodeid1,nodeid0)]
            self.data_edges[edge_id]=  self.data_edges[edge_id] | marker # bitwise add new marker if necessary
            return 1
        return 0


    def create_edge(self,nodeid0,nodeid1,marker):
        if self.update_edge(nodeid0,nodeid1,marker): return
        edge_id=self.next_edge_id
        self.next_edge_id+=1
        self.dico_edges[(nodeid0,nodeid1)]=edge_id
        self.edges_dico[edge_id]=(nodeid0,nodeid1)
        self.data_edges[edge_id]=marker
        self.ebbox.insert(edge_id,self.bbox_from_node_ids(nodeid0,nodeid1))
        return

    
    def insert_edge(self,id0,id1,marker,check=True):
        #vprint(1,"Inserting :",self.nodes_dico[id0],self.nodes_dico[id1])
        if not check:
            self.create_edge(id0,id1,marker)
            return
        if self.update_edge(id0,id1,marker): 
            #vprint(1,"  -> only updated")
            return
        weight_list=[]
        id_list=[]
        task=self.ebbox.intersection(self.bbox_from_node_ids(id0,id1),objects=True)
        for hits in task:
            edge_id=hits.id
            edge_bbox=hits.bbox 
            (id2,id3)=self.edges_dico[edge_id]
            c_marker=self.data_edges[edge_id]
            #vprint(1,"  checking against:",self.nodes_dico[id2],self.nodes_dico[id3])
            coeffs=self.are_encroached(numpy.array(self.nodes_dico[id0]),\
                    numpy.array(self.nodes_dico[id1]),\
                    numpy.array(self.nodes_dico[id2]),\
                    numpy.array(self.nodes_dico[id3]))
            if not coeffs: 
                #vprint(2,"    -> not encroached")
                continue
            if len(coeffs)==2:
                (alpha,beta)=coeffs  
                #vprint(1,"    encroached transverse",alpha,beta)  
                (c_x,c_y,c_z)=self.interp_nodes(id2,id3,beta)  # ! important to choose id2 id3 beta and not id0 id1 alpha for the c_z component !
                c_id=self.insert_node(c_x,c_y,c_z)
                #print("      new vertex",self.nodes_dico[c_id])
                weight_list.append(alpha)
                id_list.append(c_id)
                # destroy edge
                del(self.dico_edges[(id2,id3)])
                del(self.edges_dico[edge_id])
                del(self.data_edges[edge_id])
                self.ebbox.delete(edge_id,edge_bbox)
                #
                self.create_edge(id2,c_id,c_marker)
                self.create_edge(c_id,id3,c_marker)
            else:
                (alpha0,alpha1,beta0,beta1)=coeffs
                ordered_data=sorted(zip((beta0,beta1,0,1),(id0,id1,id2,id3)))     
                #vprint(1,"    encroached colinear:",ordered_data)
                for i in range(1,3):
                    if ordered_data[i][0]>0 and ordered_data[i][0]<1:
                        # destroy edge
                        #vprint(2,"delete:",id2,id3)
                        del(self.dico_edges[(id2,id3)])
                        del(self.edges_dico[edge_id])
                        del(self.data_edges[edge_id])
                        self.ebbox.delete(edge_id,edge_bbox)
                        #
                        self.create_edge(ordered_data[i-1][1],ordered_data[i][1],c_marker)  
                        self.create_edge(ordered_data[i][1],ordered_data[i+1][1],c_marker)  
                        if ordered_data[i+1][0]<1:
                           self.create_edge(ordered_data[i+1][1],ordered_data[i+2][1],c_marker)  
                        break
                if alpha0>0 and alpha0<1: 
                    weight_list.append(alpha0)
                    #vprint(2,"encode cut :",alpha0,id2) 
                    id_list.append(id2)
                if alpha1>0 and alpha1<1: 
                    weight_list.append(alpha1)
                    #vprint(2,"encode cut :",alpha1,id3) 
                    id_list.append(id3)
        for alpha,cut_id in zip(weight_list,id_list):
            if self.data_nodes[cut_id]==self.nodata: self.data_nodes[cut_id]=self.interp_nodes(id1,id0,alpha)[2]  
        id_list = list(zip(*([(0,id0)]+sorted(zip(weight_list,id_list)) +[(1,id1)])))[1]
        for i in range(0,len(id_list)-1):
            if (id_list[i],id_list[i+1]) in self.dico_edges: 
                #vprint(1,"update edge:",id_list[i],id_list[i+1])
                edge_id=self.dico_edges[(id_list[i],id_list[i+1])] 
                self.data_edges[edge_id]= self.data_edges[edge_id] | marker
            elif (id_list[i+1],id_list[i]) in self.dico_edges:
                #vprint(1,"update edge:",id_list[i+1],id_list[i])
                edge_id=self.dico_edges[(id_list[i+1],id_list[i])] 
                self.data_edges[edge_id]= self.data_edges[edge_id] | marker
            else: 
                #vprint(1,"create edge:",id_list[i],id_list[i+1])
                self.create_edge(id_list[i],id_list[i+1],marker)
        #print(self.nodes_dico)
        #print(self.edges_dico)
                                  
    def insert_way(self,way,marker,check=True):
        if isinstance(marker,str):
            marker=self.dico_attributes[marker] 
        node0_id=self.insert_node(*way[0])
        for node_array in way[1:]:
            node1_id=self.insert_node(*node_array)
            self.insert_edge(node0_id,node1_id,marker,check)
            node0_id=node1_id     
                                  
    def bbox_from_node_ids(self,id0,id1):
        # takes the ids of two nodes
        # returns a 4-uple of the form (xmin,ymin,xmax,ymax) taken from the nodes coords
        (xmin,xmax,ymin,ymax) = (self.nodes_dico[id0][0]<=self.nodes_dico[id1][0] and \
                                (self.nodes_dico[id0][0],self.nodes_dico[id1][0]) or \
                                (self.nodes_dico[id1][0],self.nodes_dico[id0][0])) + \
                                (self.nodes_dico[id0][1]<=self.nodes_dico[id1][1] and \
                                (self.nodes_dico[id0][1],self.nodes_dico[id1][1]) or \
                                (self.nodes_dico[id1][1],self.nodes_dico[id0][1]))
        return (xmin,ymin,xmax,ymax)
                                  
    def are_encroached(self,a,b,c,d): 
        #print(a,b,c,d) 
        # returns False if the only mutual points of the closed segments a->b and c->d are in {a,b,c,d}
        # returns [alpha,beta] where (1-alpha)*a * alpha*b = (1-beta)*c+beta*d otherwise and 
        #    if the segments otherwise cut each other transversally (possibly only in one point)
        # returns [alpha0,alpha1,beta0,beta1] where alpha0*(a-b)=(a-c), alpha1*(a-b)=(a-d), 
        #    beta0*(c-d)=(c-a), beta1*(c-d)=(c-b) otherwise and if the segments are colinear.
        # In the last case we hence have : c=(1-alpha0)*a+alpha0*b, d=(1-alpha1)*a+alpha1*b, 
        # a=(1-beta0)*c+beta0*d, b=(1-beta1)*c+beta1*d
        eps=1e-12               
        A=numpy.column_stack((b-a,c-d))
        F=c-a                     
        if abs(numpy.linalg.det(A))>eps:
            [alpha,beta]=numpy.linalg.solve(A,F)
            #print(alpha,beta)
            enc_lim=1e-7
            return (alpha>=0 and alpha<=1) and (beta>=0 and beta<=1) and ((alpha>enc_lim and alpha<1-enc_lim)\
                    or (beta>enc_lim and beta<1-enc_lim)) and [alpha,beta] 
        elif abs(numpy.linalg.det(numpy.column_stack((b-a,c-a))))>eps:
            return False          
        else:
            g_idx = numpy.argmax(abs(a-b))
            d_idx = numpy.argmax(abs(c-d))
            alpha0,alpha1=(a-c)[g_idx]/(a-b)[g_idx],(a-d)[g_idx]/(a-b)[g_idx]
            beta0,beta1=(c-a)[d_idx]/(c-d)[d_idx],(c-b)[d_idx]/(c-d)[d_idx]
            return (alpha0>0 or alpha1>0) and (alpha0<1 or alpha1<1) and [alpha0,alpha1,beta0,beta1]

    def encode_MultiPolygon(self,multipol,pol_to_alt,marker,area_limit=1e-10,check=True,simplify=False,refine=False): 
        progress_bar(1,0)
        if isinstance(multipol,dict):
            iterloop=multipol.values()
            todo=len(multipol)
        elif ('Multi' in multipol.geom_type or 'Collection' in multipol.geom_type):
            iterloop=multipol
            todo=len(multipol)
        else:
            iterloop=[multipol]
            todo=1
        step=int(todo/100)+1
        done=0
        for pol in iterloop:
            pol=cut_to_tile(pol)
            if simplify:
                pol=pol.simplify(simplify)  
            for polygon in pol.geoms if ('Multi' in pol.geom_type or 'Collection' in pol.geom_type) else [pol]:
                if polygon.area<=area_limit:
                    continue
                try:
                    polygon=geometry.polygon.orient(polygon)  # important for certain pol_to_alt instances
                except:
                    continue
                way=numpy.array(polygon.exterior)
                if refine: way=refine_way(way,refine)
                alti_way=pol_to_alt(way).reshape((len(way),1))
                self.insert_way(numpy.hstack([way,alti_way]),marker,check)
                for linestring in polygon.interiors:
                    if linestring.is_empty: 
                        continue
                    way=numpy.array(linestring)
                    if refine: way=refine_way(way,refine)
                    alti_way=pol_to_alt(way).reshape((len(way),1))
                    self.insert_way(numpy.hstack([way,alti_way]),marker,check)
                try:
                    if marker in self.seeds:
                        self.seeds[marker].append(numpy.array(polygon.representative_point()))
                    else:
                        self.seeds[marker]=[numpy.array(polygon.representative_point())]
                except Exception as e:
                    vprint(2,e+str(list(polygon.exterior.coords))) 
            done+=1
            if done%step==0: 
                progress_bar(1,int(100*done/todo))
                if check_flag(): return 0
        return 1

    def encode_MultiLineString(self,multilinestring,line_to_alt,marker,check=True,refine=False,skip_cut=False): 
        progress_bar(1,0)
        todo=len(multilinestring)
        step=int(todo/100)+1
        done=0
        for line in multilinestring:
            if not skip_cut: line=cut_to_tile(line)
            for linestring in line.geoms if 'Multi' in line.geom_type else [line]:
                if linestring.is_empty: 
                    continue
                way=numpy.array(linestring)
                if refine: way=refine_way(way,refine)
                alti_way=line_to_alt(way).reshape((len(way),1))
                self.insert_way(numpy.hstack([way,alti_way]),marker,check)
            done+=1
            if done%step==0: 
                progress_bar(1,int(100*done/todo))
                if check_flag(): return 0
        return 1

    def collapse_nodes_to_grid(self,h):
        print("Avant simplification :",len(self.dico_nodes),len(self.dico_edges)) 
        next_node_id=1
        next_edge_id=1 
        new_dico_nodes={}
        new_nodes_dico={}
        new_data_nodes={}
        dico_nodes_map={}
        new_dico_edges={}
        new_edges_dico={} 
        new_data_edges={}
        for key,node_id in self.dico_nodes.items():
            new_key=tuple(h*round(z/h) for z in key) 
            if new_key not in new_dico_nodes: 
                new_dico_nodes[new_key]=next_node_id
                new_nodes_dico[next_node_id]=new_key
                new_data_nodes[next_node_id]=self.data_nodes[node_id]
                next_node_id+=1 
            elif new_data_nodes[new_dico_nodes[new_key]]==self.nodata:
                new_data_nodes[new_dico_nodes[new_key]]=self.data_nodes[node_id]
            dico_nodes_map[node_id]=new_dico_nodes[new_key]
        for key,edge_id in self.dico_edges.items():
            new_key=tuple(dico_nodes_map[z] for z in key)
            if new_key[0]==new_key[1]: continue  
            if new_key in new_dico_edges: 
                new_edge_id = new_dico_edges[new_key]
                new_data_edges[new_edge_id]=new_data_edges[new_edge_id] | self.data_edges[edge_id]
                continue
            if new_key[::-1] in new_dico_edges: 
                new_edge_id = new_dico_edges[new_key[::-1]]
                new_data_edges[new_edge_id]=new_data_edges[new_edge_id] | self.data_edges[edge_id]
                continue
            new_dico_edges[new_key]=next_edge_id
            new_edges_dico[next_edge_id]=new_key
            new_data_edges[next_edge_id]=self.data_edges[edge_id]
            next_edge_id+=1 
        self.dico_nodes=new_dico_nodes
        self.nodes_dico=new_nodes_dico 
        self.dico_edges=new_dico_edges
        self.edges_dico=new_edges_dico 
        self.data_nodes=new_data_nodes
        self.data_edges=new_data_edges 
        print("Après simplification :",len(self.dico_nodes),len(self.dico_edges)) 
        return 1
                 
 
    def write_node_file(self,node_file_name): 
        total_nodes=len(self.dico_nodes)
        f= open(node_file_name,'w')
        f.write(str(total_nodes)+' 2 1 0\n')
        for idx in sorted(list(self.nodes_dico.keys())):
            f.write(str(idx)+' '+str(self.nodes_dico[idx][0])+' '+str(self.nodes_dico[idx][1])+' '+str(self.data_nodes[idx])+'\n')        
        f.close() 
    
    def write_poly_file(self,poly_file_name): 
        f=open(poly_file_name,'w')
        f.write('0 2 1 0\n')
        f.write('\n')
        total_edges=len(self.edges_dico)
        f.write(str(total_edges)+' 1\n')
        idx=1
        for edge_id in self.edges_dico:
            f.write(str(idx)+' '+str(self.edges_dico[edge_id][0])+' '+str(self.edges_dico[edge_id][1])+' '+str(self.data_edges[edge_id])+'\n')
            idx+=1
        f.write('\n'+str(len(self.holes))+'\n')
        idx=1
        for hole in self.holes:        
            f.write(str(idx)+' '+' '.join([str(h) for h in hole])+'\n')
            idx+=1
        total_seeds=numpy.sum([len(self.seeds[key]) for key in self.seeds])
        if total_seeds==0:
            f.write('\n0\n')
        else: 
            f.write('\n'+str(total_seeds)+'\n')
            idx=1
            for long_key in sorted(self.dico_attributes.items(),key=lambda item:item[1]):
                (key,marker)=long_key
                if key not in self.seeds: continue
                for seed in self.seeds[key]:
                    f.write(str(idx)+' '+' '.join([str(s) for s in seed])+' '+str(marker)+'\n')
                    idx+=1
        f.close()
        return 
##############################################################################


##############################################################################
class OSM_layer():

    def __init__(self):
        self.dicosmn={}
        self.dicosmw={}
        # rels already sorted out and containing nodeids rather than wayids 
        self.dicosmr={}
        # original rels containing wayids only, not sorted and/or reversed
        self.dicosmrorig={}
        # ids of objects directly queried, not of child or 
        # parent objects pulled indirectly by queries. Since
        # osm ids are only unique per object type we need one for each:
        self.dicosmfirst={'n':[],'w':[],'r':[]}  
        self.dicosmtags={'n':{},'w':{},'r':{}}
        self.dicosm=[self.dicosmn,self.dicosmw,self.dicosmr,self.dicosmrorig,
                     self.dicosmfirst,self.dicosmtags]       
        

    def update_dicosm(self,osm_input,target_tags):
        initnodes=len(self.dicosmn)
        initways=len(self.dicosmfirst['w'])
        initrels=len(self.dicosmfirst['r'])
        # osm_input may either refer to an osm filename (e.g. cached data) or 
        # to a xml bytestring (direct download) 
        if isinstance(osm_input,str):
            osm_file_name=osm_input 
            pfile=open(osm_file_name,'r',encoding="utf-8")
        elif isinstance(osm_input,bytes):
            pfile=io.StringIO(osm_input.decode(encoding="utf-8"))
        finished_with_file=False
        first_line=pfile.readline()
        separator="'" if "'" in first_line else '"'
        new_segs=0
        while not finished_with_file==True:
            items=pfile.readline().split(separator)
            if '<node id=' in items[0]:
                osmtype='n'
                osmid=items[1]
                for j in range(0,len(items)):
                    if items[j]==' lat=':
                        latp=items[j+1]
                    elif items[j]==' lon=':
                        lonp=items[j+1]
                self.dicosmn[osmid]=(lonp,latp)
            elif '<way id=' in items[0]:
                osmtype='w'
                osmid=items[1]
                self.dicosmw[osmid]=[]  
                if target_tags==None: self.dicosmfirst['w'].append(osmid)
            elif '<nd ref=' in items[0]:
                self.dicosmw[osmid].append(items[1])
                new_segs+=1
            elif '<relation id=' in items[0]:
                osmtype='r'
                osmid=items[1]
                self.dicosmr[osmid]={'outer':[],'inner':[]}
                self.dicosmrorig[osmid]={'outer':[],'inner':[]}
                dico_rel_check={'inner':{},'outer':{}}
                if target_tags==None: self.dicosmfirst['r'].append(osmid)
            elif '<member type=' in items[0]:
                if items[1]!='way':
                    logprint("Relation id=",osmid,"contains member",items[1],"which was not treated because it is not a way.")
                    continue                
                role=items[5]
                if role not in ['outer','inner']:
                    logprint("Relation id=",osmid,"contains a member with role different from inner or outer, it was not treated.")
                    continue
                if items[3] not in self.dicosmw: 
                    logprint("Relation id=",osmid,"contains a member way which was void and hence discarded.")
                    continue
                self.dicosmrorig[osmid][role].append(items[3])
                endpt1=self.dicosmw[items[3]][0]
                endpt2=self.dicosmw[items[3]][-1]
                if endpt1==endpt2:
                    self.dicosmr[osmid][role].append(self.dicosmw[items[3]])
                else:
                    if endpt1 in dico_rel_check[role]:
                        dico_rel_check[role][endpt1].append(items[3])
                    else:
                        dico_rel_check[role][endpt1]=[items[3]]
                    if endpt2 in dico_rel_check[role]:
                        dico_rel_check[role][endpt2].append(items[3])
                    else:
                        dico_rel_check[role][endpt2]=[items[3]]
            elif ('<tag k=' in items[0]):
                if (not self.dicosmfirst[osmtype] or self.dicosmfirst[osmtype][-1]!=osmid) and (items[1],items[3]) in target_tags[osmtype]:
                    self.dicosmfirst[osmtype].append(osmid)
                if target_tags==None or (('all','') in target_tags[osmtype])\
                                     or ((items[1],'') in target_tags[osmtype])\
                                     or ((items[1],items[3]) in target_tags[osmtype]):
                    if osmid not in self.dicosmtags[osmtype]: 
                        self.dicosmtags[osmtype][osmid]={items[1]:items[3]}
                    else:
                        self.dicosmtags[osmtype][osmid][items[1]]=items[3]
            elif '</way' in items[0]:
                if not self.dicosmw[osmid]: 
                    del(self.dicosmw[osmid]) 
                    if self.dicosmfirst['w'] and self.dicosmfirst['w'][-1]==osmid: del(self.dicosmfirst['w'][-1])
            elif '</relation>' in items[0]:
                bad_rel=False
                for role,endpt in ((r,e) for r in ['outer','inner'] for e in dico_rel_check[r]):
                    if len(dico_rel_check[role][endpt])!=2:
                        bad_rel=True
                        break
                if bad_rel==True:
                    logprint("Relation id=",osmid,"is ill formed and was not treated.")
                    del(self.dicosmr[osmid])
                    del(self.dicosmrorig[osmid])
                    del(dico_rel_check)
                    if self.dicosmfirst['r'] and self.dicosmfirst['r'][-1]==osmid: del(self.dicosmfirst['r'][-1])
                    continue
                for role in ['outer','inner']:
                    while dico_rel_check[role]:
                        nodeids=[]
                        endpt=next(iter(dico_rel_check[role]))
                        wayid=dico_rel_check[role][endpt][0]
                        endptinit=self.dicosmw[wayid][0]
                        endpt1=endptinit
                        endpt2=self.dicosmw[wayid][-1]
                        for nodeid in self.dicosmw[wayid][:-1]:
                            nodeids.append(nodeid)
                        while endpt2!=endptinit:
                            if dico_rel_check[role][endpt2][0]==wayid:
                                    wayid=dico_rel_check[role][endpt2][1]
                            else:
                                    wayid=dico_rel_check[role][endpt2][0]
                            endpt1=endpt2
                            if self.dicosmw[wayid][0]==endpt1:
                                endpt2=self.dicosmw[wayid][-1]
                                for nodeid in self.dicosmw[wayid][:-1]:
                                    nodeids.append(nodeid)
                            else:
                                endpt2=self.dicosmw[wayid][0]
                                for nodeid in self.dicosmw[wayid][-1:0:-1]:
                                    nodeids.append(nodeid)
                            del(dico_rel_check[role][endpt1])
                        nodeids.append(endptinit)
                        self.dicosmr[osmid][role].append(nodeids)
                        del(dico_rel_check[role][endptinit])
                if not self.dicosmr[osmid]['outer']: 
                    del(self.dicosmr[osmid])
                    del(self.dicosmrorig[osmid])
                    if self.dicosmfirst['r'] and self.dicosmfirst['r'][-1]==osmid: del(self.dicosmfirst['r'][-1])
                if target_tags==None:
                    for wayid in self.dicosmrorig[osmid]:
                        self.dicosmfirst['w'].remove(wayid)
                del(dico_rel_check)
            elif '</osm>' in items[0]:
                finished_with_file=True
        pfile.close()
        vprint(2,"     A total of "+str(len(self.dicosmn)-initnodes)+" new node(s), "+\
               str(len(self.dicosmfirst['w'])-initways)+" new ways and "+str(len(self.dicosmfirst['r'])-initrels)+" new relation(s).")
        return 1

    def write_to_file(self,filename):
        try:
            fout=open(filename,'w')
        except:
            vprint(1,"    Could not open",filename,"for writing.")
            return 0
        fout.write('<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="Overpass API postprocessed by Ortho4XP">\n')
        for nodeid,(lonp,latp) in self.dicosmn.items():
            fout.write('  <node id="'+nodeid+'" lat="'+latp+'" lon="'+lonp+'" version="1"/>\n')
        for wayid in self.dicosmfirst['w']+list(set(self.dicosmw).difference(set(self.dicosmfirst['w']))):
            fout.write('  <way id="'+wayid+'" version="1">\n')
            for nodeid in self.dicosmw[wayid]:
                fout.write('    <nd ref="'+nodeid+'"/>\n')
            for tag in self.dicosmtags['w'][wayid] if wayid in self.dicosmtags['w'] else []:
                fout.write('    <tag k="'+tag+'" v="'+self.dicosmtags['w'][wayid][tag]+'"/>\n')
            fout.write('  </way>\n')
        for relid in self.dicosmfirst['r']+list(set(self.dicosmrorig).difference(set(self.dicosmfirst['r']))):
            fout.write('  <relation id="'+relid+'" version="1">\n')
            for wayid in self.dicosmrorig[relid]['outer']:
                fout.write('    <member type="way" ref="'+wayid+'" role="outer"/>\n')
            for wayid in self.dicosmrorig[relid]['inner']:
                fout.write('    <member type="way" ref="'+wayid+'" role="inner"/>\n')
            for tag in self.dicosmtags['r'][relid] if relid in self.dicosmtags['r'] else []:
                fout.write('    <tag k="'+tag+'" v="'+self.dicosmtags['r'][relid][tag]+'"/>\n')
            fout.write('  </relation>\n')
        fout.write('</osm>')    
        return 1
##############################################################################


##############################################################################
def OSM_queries_to_OSM_layer(queries,osm_layer,lat,lon,tags_of_interest,server_code="DE",cached_suffix=''):
    target_tags={'n':[],'w':[],'r':[]}
    for query in queries:
        for tag in [query] if isinstance(query,str) else query:
            items=tag.split('"')
            osm_type=items[0][0]
            target_tags[osm_type].append((items[1],items[3]))
    for tag in tags_of_interest:
        if isinstance(tag,str):
            target_tags['n'].append((tag,''))
            target_tags['w'].append((tag,''))
            target_tags['r'].append((tag,''))
        else:
            target_tags['n'].append(tag)
            target_tags['w'].append(tag)
            target_tags['r'].append(tag)
    cached_data_filename=os.path.join(Ortho4XP_dir,'OSM_data',long_latlon(lat,lon),short_latlon(lat,lon)+'_'+cached_suffix+'.osm')
    if cached_suffix and os.path.isfile(cached_data_filename):
        osm_layer.update_dicosm(cached_data_filename,target_tags)
        return 1
    for query in queries:
        # look first for cached data (old scheme)
        if isinstance(query,str):
            subtags=query.split('"')
            old_cached_data_filename=os.path.join(Ortho4XP_dir,'OSM_data',\
                    long_latlon(lat,lon),short_latlon(lat,lon)+'_'+\
                    subtags[0][0:-1]+'_'+subtags[1]+'_'+subtags[3]+'.osm')
            if os.path.isfile(old_cached_data_filename):
                vprint(2,"    Recycling OSM data for "+query)
                osm_layer.update_dicosm(old_cached_data_filename,target_tags)
                continue
        response=get_overpass_data(query,(lat,lon,lat+1,lon+1),server_code)
        if check_flag(): return 0
        if response[0]!='ok': 
           vprint(1,"    Error while trying to obtain ",query,", exiting.")
           vprint(2,"   ",response[1])
           return 0
        osm_layer.update_dicosm(response[1],target_tags)
    if cached_suffix: osm_layer.write_to_file(cached_data_filename)
    return 1
##############################################################################

##############################################################################
def get_overpass_data(query,bbox,server_code="DE"):
    overpass_servers={
             "DE":"http://overpass-api.de/api/interpreter",
             "FR":"http://api.openstreetmap.fr/oapi/interpreter",
             "KU":"https://overpass.kumi.systems/api/interpreter", 
             "RU":"http://overpass.osm.rambler.ru/cgi/interpreter"
             }
    if server_code not in overpass_servers: server_code="DE"
    osm_download_ok = False
    tentative=1
    while True:
        s=requests.Session()
        base=overpass_servers[server_code]
        if isinstance(query,str):
            overpass_query=query+str(bbox)
        else:
            overpass_query=''.join([x+str(bbox)+";" for x in query])
        url=base+"?data=("+overpass_query+");(._;>>;);out meta;"
        vprint(2,url)
        try:
            r=s.get(url,timeout=60)
            vprint(2,"OSM response status :",r)
            if '200' in str(r):
                break
            else:
                vprint(1,"      OSM server rejected our query, new tentative in 5 sec...")
        except:
            vprint(1,"      OSM server was too busy, new tentative in 5 sec...")
            pass
        if tentative>=max_osm_tentatives:
            return ["error","no response"]
        if check_flag(): return 0
        tentative+=1           
        time.sleep(5)
    if len(r.content)<=1000 and b"error" in r.content: 
       return ["error",b"data too big"]
    return ["ok",r.content]
##############################################################################

##############################################################################
def OSM_to_MultiLineString(osm_layer,lat,lon,tags_for_exclusion=set(),filter=None,limit_segs=None):
    multiline=[]
    multiline_reject=[]
    todo=len(osm_layer.dicosmfirst['w'])
    step=int(todo/100)+1
    done=0
    filtered_segs=0
    for wayid in osm_layer.dicosmfirst['w']:
        if done%step==0: progress_bar(1,int(100*done/todo))
        if tags_for_exclusion and wayid in osm_layer.dicosmtags['w'] \
          and not set(osm_layer.dicosmtags['w'][wayid].keys()).isdisjoint(tags_for_exclusion):
            done+=1
            continue  
        way=numpy.array([osm_layer.dicosmn[nodeid] for nodeid in osm_layer.dicosmw[wayid]],dtype=numpy.float)-numpy.array([[lon,lat]],dtype=numpy.float) 
        if filter and not filter(way):
            try:
                multiline_reject.append(geometry.LineString(way))
            except:
                pass
            done+=1
            continue
        try:
            multiline.append(geometry.LineString(way))
        except:
            pass
        done+=1
        filtered_segs+=len(way)
        if limit_segs and filtered_segs>=limit_segs: 
            vprint(1,"     -> Caution : result stripped by user defined limit 'max_levelled_segs'.")
            vprint(2,osm_layer.dicosmtags['w'][wayid])
            break
    progress_bar(1,100)
    if not filter:
        return geometry.MultiLineString(multiline)
    else:
        vprint(2,"    Number of filtered segs :",filtered_segs)
        return (geometry.MultiLineString(multiline),geometry.MultiLineString(multiline_reject))
##############################################################################

##############################################################################
def OSM_to_MultiPolygon(osm_layer,lat,lon):
    multilist=[]
    todo=len(osm_layer.dicosmfirst['w'])+len(osm_layer.dicosmfirst['r'])
    step=int(todo/100)+1
    done=0
    for wayid in osm_layer.dicosmfirst['w']:
        if done%step==0: progress_bar(1,int(100*done/todo))
        if osm_layer.dicosmw[wayid][0]!=osm_layer.dicosmw[wayid][-1]: 
            logprint("Non closed way starting at",osm_layer.dicosmn[osm_layer.dicosmw[wayid][0]],", skipped.")
            done+=1
            continue
        way=numpy.array([osm_layer.dicosmn[nodeid] for nodeid in osm_layer.dicosmw[wayid]],dtype=numpy.float)
        way=way-numpy.array([[lon,lat]],dtype=numpy.float) 
        try:
            pol=geometry.Polygon(way)
            if not pol.area: continue
            if not pol.is_valid:
                logprint("Invalid OSM way starting at",osm_layer.dicosmn[osm_layer.dicosmw[wayid][0]],", skipped.")
                done+=1
                continue
        except Exception as e:
            vprint(2,e)
            done+=1
            continue
        multilist.append(pol) 
        done+=1
    for relid in osm_layer.dicosmfirst['r']:
        if done%step==0: progress_bar(1,int(100*done/todo))
        try:
            multiout=[geometry.Polygon(numpy.array([osm_layer.dicosmn[nodeid] \
                                        for nodeid in nodelist],dtype=numpy.float)-numpy.array([lon,lat],dtype=numpy.float)) \
                                        for nodelist in osm_layer.dicosmr[relid]['outer']]
            multiout=ops.cascaded_union([geom for geom in multiout if geom.is_valid])
            multiin=[geometry.Polygon(numpy.array([osm_layer.dicosmn[nodeid] \
                                        for nodeid in nodelist],dtype=numpy.float)-numpy.array([lon,lat],dtype=numpy.float)) \
                                        for nodelist in osm_layer.dicosmr[relid]['inner']]
            multiin=ops.cascaded_union([geom for geom in multiin if geom.is_valid])
        except Exception as e:
            logprint(e)
            done+=1
            continue
        multipol = multiout.difference(multiin)
        for pol in multipol.geoms if ('Multi' in multipol.geom_type or 'Collection' in multipol.geom_type) else [multipol]:
            if not pol.area: 
                done+=1
                continue
            if not pol.is_valid: 
                logprint("Relation",relid,"contains an invalid polygon which was discarded") 
                done+=1
                continue
            multilist.append(pol)  
        done+=1
    ret_val=geometry.MultiPolygon(multilist)
    vprint(2,"Total number of geometries:",len(ret_val.geoms))
    progress_bar(1,100)
    return ret_val
##############################################################################

##############################################################################
def is_multipart(input_geometry):
    return 'Multi' in input_geometry.geom_type or 'Collection' in input_geometry.geom_type   
##############################################################################

##############################################################################
def split_polygon(input_pol, max_size):
    (xmin,ymin,xmax,ymax) = input_pol.bounds
    if xmax-xmin <= max_size and ymax-ymin <= max_size:
        return [input_pol]
    ret_val=[]
    if xmax-xmin >= ymax-ymin:
        subpols1 = input_pol.intersection(geometry.box(xmin,ymin,(xmin+xmax)/2,ymax))
        subpols2 = input_pol.intersection(geometry.box((xmin+xmax)/2,ymin,xmax,ymax))
    else:
        subpols1 = input_pol.intersection(geometry.box(xmin,ymin,xmax,(ymin+ymax)/2))
        subpols2 = input_pol.intersection(geometry.box(xmin,(ymin+ymax)/2,xmax,ymax))
    for subpol in subpols1 if is_multipart(subpols1) else [subpols1]:
        if isinstance(subpol,geometry.Polygon): 
            ret_val.extend(split_polygon(subpol,max_size))
    for subpol in subpols2 if is_multipart(subpols2) else [subpols2]:
        if isinstance(subpol,geometry.Polygon): 
            ret_val.extend(split_polygon(subpol,max_size))
    return ret_val
##############################################################################


##############################################################################
def MultiPolygon_to_Indexed_Polygons(multipol,merge_overlappings=True,limit=10):
    ########################################################################
    def merge_pol(pol,id_pol):
        # HACK !!!
        todo_list=list(idx_pol.intersection(pol.bounds))
        if limit and len(todo_list)>limit: 
            vprint(2,"    Skipping some too complex merging process (based on max_pols_for_merge)")
            return add_pol(pol,id_pol)
        ids_to_merge=[]
        for polid in todo_list:
            if pol.intersects(dico_pol[polid]):
                ids_to_merge.append(polid)
        #if ids_to_merge: print("Number to be merged :",len(ids_to_merge))        
        #timer=time.time()
        try:
            merged_pols=ops.cascaded_union([dico_pol[polid] for polid in ids_to_merge]+[pol])
        except Exception as e:
            print(e)
            return
        #print("merge:                 ",time.time()-timer)
        #timer=time.time()
        for polid in ids_to_merge:
            idx_pol.delete(polid,dico_pol[polid].bounds)
            dico_pol.pop(polid,None)
        for pol in merged_pols.geoms if 'Multi' in merged_pols.geom_type else [merged_pols]:
            for subpol in split_polygon(pol,0.1):
                idx_pol.insert(id_pol,subpol.bounds)
                dico_pol[id_pol]=subpol
                id_pol+=1
        #print("updatee:",time.time()-timer)
        return id_pol
    def add_pol(pol,id_pol):
        dico_pol[id_pol]=pol
        id_pol+=1
        return id_pol   
    ########################################################################
    progress_bar(1,0)
    idx_pol=index.Index() 
    dico_pol={} 
    id_pol=0
    todo=len(multipol.geoms) if 'Multi' in multipol.geom_type else 1
    step=int(todo/100)+1 
    done=0 
    # we sort the geometries according to the area of their bounding box, larger first
    # since it is probably more efficient this way
    iterloop=sorted(multipol.geoms, key=lambda geom:geometry.box(*geom.bounds).area, reverse=True) if 'Multi' in multipol.geom_type else [multipol]
    for pol in iterloop:
        if not pol.area: 
            done+=1
            continue
        if not pol.is_valid: 
            logprint("Invalid polygon detected at",list(pol.exterior.coords)[0]) 
            done+=1
            continue
        if merge_overlappings:
            id_pol=merge_pol(pol,id_pol)
        else:
            id_pol=add_pol(pol,id_pol)
        done+=1
        if done%step==0: 
            progress_bar(1,int(100*done/todo))
            if check_flag(): return 0
    return (idx_pol,dico_pol)
##############################################################################

##############################################################################
def cut_to_tile(input_geometry):
    return input_geometry.intersection(geometry.Polygon(
            [(0,0),(1,0),(1,1),(0,1),(0,0)]))
##############################################################################

##############################################################################
def ensure_MultiPolygon(input_geometry):
    if input_geometry.is_empty: 
        return geometry.MultiPolygon()
    if 'Multi' not in input_geometry.geom_type: 
        return geometry.MultiPolygon([input_geometry])
    return input_geometry
##############################################################################
##############################################################################
def ensure_MultiLineString(input_geometry):
    if input_geometry.is_empty: 
        return geometry.MultiLineString()
    if 'Multi' not in input_geometry.geom_type: 
        return geometry.MultiLineString([input_geometry])
    return input_geometry
##############################################################################
    
##############################################################################
def ensure_ccw(input_geometry):
    if input_geometry.is_empty: 
        return geometry.MultiLineString()
    geometries=[]
    for line in input_geometry.geoms if 'Multi' in input_geometry.geom_type else [input_geometry]:
        if line.is_ring and not geometry.LinearRing(line).is_ccw:
            line.coords = list(line.coords)[::-1]
        geometries.append(line)
    return geometry.MultiLineString(geometries)
##############################################################################

##############################################################################
def indexed_difference(idx_pol1,dico_pol1,idx_pol2,dico_pol2):
    idx_out=index.Index()
    dico_out={}
    idnew=0
    for polid1,pol1 in dico_pol1.items():
        for polid2 in idx_pol2.intersection(pol1.bounds):
            if pol1.intersects(dico_pol2[polid2]):
                pol1=pol1.difference(dico_pol2[polid2])
        if pol1.area:
            for pol in pol1 if 'Multi' in pol1.geom_type else [pol1]: 
                idx_out.insert(idnew,pol.bounds)
                dico_out[idnew]=pol
                idnew+=1 
    return idx_out,dico_out
##############################################################################

##############################################################################
def improved_buffer(input_geometry,buffer_width,separation_width,simplify_length):
    progress_bar(1,0)
    output_geometry=input_geometry.buffer(buffer_width+separation_width,join_style=2,mitre_limit=1.5,resolution=1)
    progress_bar(1,40)
    if check_flag(): return 0
    output_geometry=output_geometry.buffer(-1*separation_width,join_style=2,mitre_limit=1.5,resolution=1)
    progress_bar(1,80)
    if check_flag(): return 0
    output_geometry=output_geometry.simplify(simplify_length)
    progress_bar(1,100)
    if check_flag(): return 0
    return output_geometry
##############################################################################

##############################################################################
def improved_buffer2(input_geometry,buffer_width,separation_width,simplify_length):
    progress_bar(1,0)
    output_geometry=ops.cascaded_union([geom.buffer(buffer_width+separation_width,join_style=2,mitre_limit=1.5,resolution=1) for geom in input_geometry])
    progress_bar(1,40)
    if check_flag(): return 0
    output_geometry=output_geometry.buffer(-1*separation_width,join_style=2,mitre_limit=1.5,resolution=1)
    progress_bar(1,80)
    if check_flag(): return 0
    output_geometry=output_geometry.simplify(simplify_length)
    progress_bar(1,100)
    if check_flag(): return 0
    return output_geometry
##############################################################################

##############################################################################
def coastline_to_MultiPolygon(coastline):
    ######################################################################
    def encode_to_next(coord,new_way,remove_coords):
        if coord in inits:
            vprint(2,"in inits")
            idx=inits.index(coord)
            new_way+=segments[idx][2]
            next_coord=segments[idx][1]
            remove_coords.append(coord)
            remove_coords.append(next_coord)
        else:
            vprint(2,"not in inits")
            idx=bdcoords.index(coord)                
            if idx<len(bdcoords)-1: 
               next_coord=bdcoords[idx+1] 
               next_coord_loop=next_coord
            else:
               next_coord=bdcoords[0]
               next_coord_loop=next_coord+4  
            interp_coord=ceil(coord)
            while interp_coord<next_coord_loop:
                new_way+=bd_point(interp_coord) 
                interp_coord+=1
        return next_coord               
    ######################################################################
    # code starts here :
    #coastline=cut_to_tile(coastline)
    islands=[]
    segments=[]
    bdpolys=[]
    ends=[]
    inits=[]
    for line in coastline.geoms if 'Multi' in coastline.geom_type else [coastline]:
        if line.is_ring:
            islands.append(list(line.coords)) 
        else:
            tmp=list(line.coords)
            if numpy.min(numpy.abs([tmp[0][0]-int(tmp[0][0]),tmp[0][1]-int(tmp[0][1])]))>0.00001: vprint(2, "!!!!!!!!!!!!!!!!:",tmp[0])
            if numpy.min(numpy.abs([tmp[-1][0]-int(tmp[-1][0]),tmp[-1][1]-int(tmp[-1][1])]))>0.00001: vprint(2,"!!!!!!!!!!!!!!!!:",tmp[-1])
            segments.append([bd_coord(tmp[0]),bd_coord(tmp[-1]),tmp])
            ends.append(bd_coord(tmp[-1]))
            inits.append(bd_coord(tmp[0]))
    vprint(2,"Islands:",len(islands),"Others:",len(segments))
    bdcoords=sorted(ends+inits)
    vprint(2,"bdcoords",len(bdcoords))
    vprint(2,bdcoords)
    while bdcoords:
        new_way=[]
        remove_coords=[]
        first_coord=bdcoords[0]
        next_coord=encode_to_next(first_coord,new_way,remove_coords) 
        count=0
        while next_coord!=first_coord:
           count+=1
           next_coord=encode_to_next(next_coord,new_way,remove_coords)  
           if count==100: return "error"
        bdpolys.append(new_way)
        for coord in remove_coords:
            try:
                bdcoords.remove(coord)
            except Exception as e:
                vprint(2,e)
    if islands and not bdpolys:
        bdpolys.append([(0,0),(0,1),(1,1),(1,0)])
    vprint(2,"cascaded union out")
    outpol=ops.cascaded_union([geometry.Polygon(bdpoly) for bdpoly in bdpolys])
    vprint(2,"cascaded union in")
    inpol=ops.cascaded_union([geometry.Polygon(island) for island in islands]) 
    vprint(2,"difference")
    return outpol.difference(inpol)
##############################################################################


##############################################################################
def bd_coord(pt):
    # distance along the boundary of the unit square in cw direction starting
    # from (0,0)  
    return geometry.LineString([(0,0),(0,1),(1,1),(1,0),(0,0)]).project(geometry.Point(pt))
##############################################################################

##############################################################################
def bd_point(coord):
    # point a coord distance along the boundary of the unit square in cw direction starting
    # from (0,0)  
    return list(geometry.LineString([(0,0),(0,1),(1,1),(1,0),(0,0)]).interpolate(coord%4).coords)
##############################################################################

##############################################################################
def grow_or_shrink_loops(multilinestring,extent):
   coords_list=[] 
   for line in multilinestring.geoms:
       if line.is_ring:
           tmp=geometry.polygon.orient(geometry.Polygon(line).buffer(extent/111170,resolution=1)).exterior 
           coords_list.append(list(tmp.coords))
       else:
           coords_list.append(list(line.coords))
   return geometry.MultiLineString(coords_list)
##############################################################################


##############################################################################
def include_patches(Mesh_input,dem,lat,lon):
    print("-> Dealing with patches")
    patch_dir   = os.path.join(Ortho4XP_dir,'Patches',long_latlon(lat,lon))
    if not os.path.exists(patch_dir): 
        return geometry.Polygon()
    patch_layer = OSM_layer()
    for pfile_name in os.listdir(patch_dir):
        if pfile_name[-10:]!='.patch.osm':
            continue
        vprint(1,"    "+pfile_name)
        if True: #try:
            patch_layer.update_dicosm(os.path.join(patch_dir,pfile_name),target_tags=None)
        else: #except:
            lvprint(1,"     Error in treating",pfile_name," , skipped.")
    dw=patch_layer.dicosmw
    dn=patch_layer.dicosmn
    df=patch_layer.dicosmfirst
    dt=patch_layer.dicosmtags
    patches_area=geometry.Polygon()
    def tanh_profile(alpha,x):
        return (numpy.tanh((x-0.5)*alpha)/numpy.tanh(0.5*alpha)+1)/2
    def spline_profile(x):
        return 3*x**2-2*x**3
    def plane_profile(x):
        return x
    # reorganize them so that untagged dummy ways are treated last (due to altitude being first done kept for all)
    #waylist=list(set(dw).intersection(df['w']).intersection(dt['w']))+list(set(dw).intersection(df['w']).difference(dt['w']))
    waylist=list(set(df['w']).intersection(dt['w']))+list(set(df['w']).difference(dt['w']))
    for wayid in waylist:
        way=numpy.array([dn[nodeid] for nodeid in dw[wayid]],dtype=numpy.float)
        way=way-numpy.array([[lon,lat]]) 
        alti_way_orig=dem.alt_vec(way)
        cplx_patch=False
        if wayid in dt['w']:
            wtags=dt['w'][wayid]
            if 'cst_alt_abs' in wtags:
                alti_way=numpy.ones((len(way),1))*float(wtags['cst_alt_abs'])
            elif 'cst_alt_rel' in wtags:
                alti_way=dem.alt_vec_mean(way)+float(wtags['cst_alt_rel'])
            elif 'var_alt_rel' in wtags:
                alti_way=alti_way_orig+float(wtags['var_alt_rel'])
            elif 'altitude' in wtags:                   # deprecated : for backward compatibility only
                alti_way=numpy.ones((len(way),1))*float(wtags['altitude'])
            elif 'altitude_high' in wtags:
                cplx_patch=True
                if len(way)!=5 or (way[0]!=way[-1]).all():
                    lvprint(1,"    Wrong number of nodes or non closed way for a altitude_high/altitude_low polygon, skipped.")
                    continue
                short_high = way[-2:]
                short_low  = way[1:3]
                long_high_to_low = way[:2]
                long_low_to_high = way[2:4]
                try:
                    altitude_high=float(wtags['altitude_high'])
                    altitude_low =float(wtags['altitude_low'])
                except:
                    altitude_high=dem.alt_vec(short_high).mean()
                    altitude_low =dem.alt_vec(short_low).mean()
                try:
                    cell_size=float(wtags['cell_size'])
                except:
                    cell_size=10
                try:
                    rnw_profile=wtags['profile']
                except:
                    rnw_profile='plane'
                try:
                    alpha=float(wtags['steepness'])
                except:
                    alpha=2
                if rnw_profile=='atanh': 
                    rnw_profile= lambda x:atanh_profile(alpha,x)
                elif rnw_profile=='spline':
                    rnw_profile=spline_profile
                else:
                    rnw_profile=plane_profile
                rnw_vect=(short_high[0]+short_high[1]-short_low[0]-short_low[1])/2
                rnw_length=sqrt(rnw_vect[0]**2*cos(lat*pi/180)**2+rnw_vect[1]**2)*111120
                cuts_long=int(rnw_length/cell_size)
                if cuts_long:
                    cuts_long+=1
                    way=numpy.array([way[0]+i/cuts_long*(way[1]-way[0]) for i in range(cuts_long)]+\
                            [way[1]]+[way[2]+i/cuts_long*(way[3]-way[2]) for i in range(cuts_long)]+[way[3],way[4]]) 
                    alti_way=numpy.array([altitude_high-rnw_profile(i/cuts_long)*(altitude_high-altitude_low) for i in range(cuts_long+1)])
                    alti_way=numpy.hstack([alti_way,alti_way[::-1],alti_way[0]])
            else:
                alti_way=alti_way_orig
        else:
            alti_way=alti_way_orig
        if not cplx_patch:
          for i in range(len(way)):
            nodeid=dw[wayid][i]
            if nodeid in dt:
                ntags=dt['n'][nodeid]
                if 'alt_abs' in ntags:
                    alti_way[i]=float(ntags['alt_abs'])
                elif 'alt_rel' in ntags:
                    alti_way[i]=alti_way_orig[i]+float(ntags['alt_rel'])
        alti_way=alti_way.reshape((len(alti_way),1))
        if (way[0]==way[-1]).all():
            try:
                pol=geometry.Polygon(way)
                if pol.is_valid and pol.area:
                    patches_area=patches_area.union(pol)
                    Mesh_input.insert_way(numpy.hstack([way,alti_way]),'INTERP_ALT',check=True)
                    seed=numpy.array(pol.representative_point())
                    if 'INTERP_ALT' in Mesh_input.seeds:
                        Mesh_input.seeds['INTERP_ALT'].append(seed)
                    else:
                        Mesh_input.seeds['INTERP_ALT']=[seed]
                else:
                    lvprint(2,"Skipping invalid patch polygon.")
            except:
                lvprint(2,"Skipping invalid patch polygon.")
        else:
            Mesh_input.insert_way(numpy.hstack([way,alti_way]),'DUMMY',check=True)
    return patches_area
##############################################################################
        

##############################################################################
def build_curv_tol_weight_map(lat,lon,weight_array):
    if apt_curv_tol!=curvature_tol:
        vprint(1,"-> Modifying curv_tol weight map according to runway locations.")
        airport_layer=OSM_layer()
        queries=[('rel["aeroway"="runway"]','rel["aeroway"="taxiway"]','rel["aeroway"="apron"]',
          'way["aeroway"="runway"]','way["aeroway"="taxiway"]','way["aeroway"="apron"]')]
        tags_of_interest=["all"]
        if not OSM_queries_to_OSM_layer(queries,airport_layer,lat,lon,tags_of_interest,overpass_server_choice,cached_suffix='airports'): 
            return 0
        runway_network=OSM_to_MultiLineString(airport_layer,lat,lon,[])
        runway_area=improved_buffer(runway_network,0.0003,0.0001,0.00001)
        if not runway_area: return 0
        runway_area=ensure_MultiPolygon(runway_area)
        for polygon in runway_area.geoms if ('Multi' in runway_area.geom_type or 'Collection' in runway_area.geom_type) else [runway_area]:
            (xmin,ymin,xmax,ymax)=polygon.bounds
            x_shift=apt_curv_ext/(111.12*cos(lat*pi/180))
            y_shift=apt_curv_ext/(111.12)
            colmin=round((xmin-x_shift)*1000)
            colmax=round((xmax+x_shift)*1000)
            rowmax=round(((1-ymin)+y_shift)*1000)
            rowmin=round(((1-ymax)-y_shift)*1000)
            weight_array[rowmin:rowmax+1,colmin:colmax+1]=curvature_tol/apt_curv_tol if apt_curv_tol>0 else 1 
        del(airport_layer)
        del(runway_network) 
        del(runway_area)
    if coast_curv_tol!=curvature_tol:
        vprint(1,"-> Modifying curv_tol weight map according to coastline location.")
        sea_layer=OSM_layer()
        queries=['way["natural"="coastline"]']    
        tags_of_interest=[]
        if not OSM_queries_to_OSM_layer(queries,sea_layer,lat,lon,tags_of_interest,overpass_server_choice,cached_suffix='coastline'):
            return 0
        for nodeid in sea_layer.dicosmn:
            (lonp,latp)=[float(x) for x in sea_layer.dicosmn[nodeid]]
            x_shift=coast_curv_ext/(111.12*cos(lat*pi/180))
            y_shift=coast_curv_ext/(111.12)
            colmin=round((lonp-lon-x_shift)*1000)
            colmax=round((lonp-lon+x_shift)*1000)
            rowmax=round((lat+1-latp+y_shift)*1000)
            rowmin=round((lat+1-latp-y_shift)*1000)
            weight_array[rowmin:rowmax+1,colmin:colmax+1]=curvature_tol/coast_curv_tol if coast_curv_tol>0 else 1 
        del(sea_layer)
    Image.fromarray((weight_array!=1).astype(numpy.uint8)*255).save('weight.png')
    return
##############################################################################

##############################################################################
def include_airports(Mesh_input,dem,lat,lon,patches_area):
    # patches_area if not None is the extent to substract from runway_area
    # we enlarge it (local copy) slightly for security
    patches_area=patches_area.buffer(0.00002)
    print("-> Dealing with airports")
    airport_layer=OSM_layer()
    queries=[('rel["aeroway"="runway"]','rel["aeroway"="taxiway"]','rel["aeroway"="apron"]',
          'way["aeroway"="runway"]','way["aeroway"="taxiway"]','way["aeroway"="apron"]')]
    tags_of_interest=["all"]
    if not OSM_queries_to_OSM_layer(queries,airport_layer,lat,lon,tags_of_interest,overpass_server_choice,cached_suffix='airports'): 
        return 0
    # Runway and taxiway center lines (they will be incorporated to ensure triangles
    # are not too badly aligned with these lines (improves removal of bumpiness)
    runway_network=OSM_to_MultiLineString(airport_layer,lat,lon,[])
    # Buffer these for later smoothing
    runway_area=improved_buffer(runway_network,0.0003,0.0001,0.00001)
    if not runway_area: return 0
    runway_area=runway_area.difference(patches_area).buffer(0).simplify(0.00001)
    runway_network=runway_network.difference(patches_area)
    # Now we encode in Mesh_input
    Mesh_input.encode_MultiLineString(runway_network,dem.alt_vec,'DUMMY',check=True,refine=20)
    Mesh_input.encode_MultiPolygon(runway_area,dem.alt_vec,'SMOOTHED_ALT',check=True,refine=50)
    return 1
##############################################################################

##############################################################################
def include_roads(Mesh_input,dem,lat,lon,road_level):    
    if not road_level: return
    print("-> Dealing with roads")
    tags_of_interest=["bridge","tunnel"]
    #Need to evaluate if including bridges is better or worse
    tags_for_exclusion=set(["bridge","tunnel"]) 
    #tags_for_exclusion=set(["tunnel"]) 
    road_layer=OSM_layer()
    queries=[
           'way["highway"="motorway"]',
           'way["highway"="trunk"]',
           'way["highway"="primary"]',
           'way["highway"="secondary"]',
           'way["railway"="rail"]',
           'way["railway"="narrow_gauge"]'
         ]
    if not OSM_queries_to_OSM_layer(queries,road_layer,lat,lon,tags_of_interest,overpass_server_choice,cached_suffix='big_roads'):
        return 0
    (road_network_banked,road_network_flat)=OSM_to_MultiLineString(road_layer,lat,lon,tags_for_exclusion,dem.way_is_too_much_banked)
    if check_flag(): return 0
    if road_level>=2:
        road_layer=OSM_layer()
        queries=[\
           'way["highway"="tertiary"]']
        if road_level>=3:
            queries+=[
               'way["highway"="unclassified"]',
               'way["highway"="residential"]']
        if road_level>=4:
            queries+=['way["highway"="service"]']
        if road_level>=5:
            queries+=['way["highway"="track"]']
        if not OSM_queries_to_OSM_layer(queries,road_layer,lat,lon,tags_of_interest,overpass_server_choice,cached_suffix='small_roads'):
            return 0
        vprint(1,"    Checking which roads need levelling.") 
        timer=time.time()
        (road_network_banked_2,road_network_flat_2)=OSM_to_MultiLineString(road_layer,\
                lat,lon,tags_for_exclusion,dem.way_is_too_much_banked,limit_segs=max_levelled_segs)
        vprint(2,"    Time for check :",time.time()-timer)
        road_network_banked=geometry.MultiLineString(list(road_network_banked)+list(road_network_banked_2)).simplify(0.000005)
    if not road_network_banked.is_empty:
        vprint(1,"    Buffering banked road network.")
        timer=time.time()
        road_area=improved_buffer(road_network_banked,0.00004,0.00002,0.000005)
        vprint(2,"    Time for improved buffering:",time.time()-timer)
        if check_flag(): return 0 
        vprint(1,"    Encoding it.")
        Mesh_input.encode_MultiPolygon(road_area,dem.alt_vec_road,'INTERP_ALT',check=True,refine=False)
        if check_flag(): return 0 
    if not road_network_flat.is_empty:
        road_network_flat=road_network_flat.simplify(0.00001) #.difference(road_area)
        vprint(1,"    Encoding the remaining primary road network as linestrings.")
        Mesh_input.encode_MultiLineString(road_network_flat,dem.alt_vec_road,'DUMMY',check=True)
    return 1
##############################################################################

##############################################################################
def include_sea(Mesh_input,dem,lat,lon):
    print("-> Dealing with coastline")
    sea_layer=OSM_layer()
    custom_coastline=os.path.join(Ortho4XP_dir,'OSM_data',long_latlon(lat,lon),short_latlon(lat,lon)+'_custom_coastline.osm')
    if os.path.isfile(custom_coastline):
        sea_layer.update_dicosm(custom_coastline,target_tags=None)
    else:
        queries=['way["natural"="coastline"]']    
        tags_of_interest=[]
        if not OSM_queries_to_OSM_layer(queries,sea_layer,lat,lon,tags_of_interest,overpass_server_choice,cached_suffix='coastline'):
            return 0
    coastline=OSM_to_MultiLineString(sea_layer,lat,lon,None)
    if not coastline.is_empty:
        #vprint(2,"simplify")
        #coastline=coastline.simplify(0.00001)
        coastline=ensure_MultiLineString(coastline) 
        complete_islands=geometry.MultiLineString([line for line in coastline.geoms if line.is_ring])
        remainder=geometry.MultiLineString([line for line in coastline.geoms if not line.is_ring])
        vprint(2,"encode")
        coastline=cut_to_tile(coastline) 
        Mesh_input.encode_MultiLineString(coastline,dem.alt_vec,'SEA',check=True,refine=False)
        vprint(2,"find seeds")
        remainder=cut_to_tile(remainder) 
        remainder=ensure_MultiLineString(remainder) 
        vprint(2,"  linemerge")
        if not remainder.is_empty: 
            remainder=ops.linemerge(remainder)
            remainder=ensure_MultiLineString(remainder) 
        vprint(2,"  transform to polygons")
        coastline=geometry.MultiLineString([line for line in remainder]+[line for line in complete_islands])
        sea_area=coastline_to_MultiPolygon(coastline) 
        vprint(2,"encode seeds")
        for polygon in sea_area.geoms if 'Multi' in sea_area.geom_type else [sea_area]:
            seed=numpy.array(polygon.representative_point()) 
            if 'SEA' in Mesh_input.seeds:
                Mesh_input.seeds['SEA'].append(seed)
            else:
                Mesh_input.seeds['SEA']=[seed]
##############################################################################

##############################################################################
def include_water(Mesh_input,dem,lat,lon):
    print("-> Dealing with inland water")
    water_layer=OSM_layer()
    custom_water=os.path.join(Ortho4XP_dir,'OSM_data',long_latlon(lat,lon),short_latlon(lat,lon)+'_custom_water.osm')
    if os.path.isfile(custom_water):
        water_layer.update_dicosm(custom_water,target_tags=None)
    else:
        queries=[
              'rel["natural"="water"]',
              'rel["waterway"="riverbank"]',
              'way["natural"="water"]',
              'way["waterway"="riverbank"]',
              'way["waterway"="dock"]'
             ]
        tags_of_interest=["name",("NATURE","Surface d&apos;eau")]
        if not OSM_queries_to_OSM_layer(queries,water_layer,lat,lon,tags_of_interest,overpass_server_choice,cached_suffix='water'):
            return 0
    vprint(1,"    Building water multipolygon.")
    water_area=OSM_to_MultiPolygon(water_layer,lat,lon)
    if not water_area.is_empty: 
        vprint(1,"    Cleaning it.")
        try:
            (idx_water,dico_water)=MultiPolygon_to_Indexed_Polygons(water_area,merge_overlappings=clean_bad_geometries,limit=max_pols_for_merge)
        except:
            return 0
        vprint(2,"Number of water Multipolygons : "+str(len(dico_water)))  
        vprint(1,"    Encoding it.")
        Mesh_input.encode_MultiPolygon(dico_water,dem.alt_vec,'WATER',area_limit=min_area/10000,simplify=0.00001,check=True)
    return 1
##############################################################################
    
##############################################################################
def include_buildings(Mesh_input):
    # should be all revisited
    print("-> Dealing with buildings")
    building_layer=OSM_layer()
    queries=[]#'way["building"="yes"]']
    tags_of_interest=[]
    if not OSM_queries_to_OSM_layer(queries,building_layer,lat,lon,tags_of_interest,overpass_server_choice,cached_suffix='buildings'):
        return 0
    for (i,j) in itertools.product(range(1),range(1)):
        print("    Obtaining part ",4*i+j," of OSM data for "+tag)
        response=get_overpass_data(tag,(lat+i/4,lon+j/4,lat+(i+1)/4,lon+(j+1)/4),"FR")
        if check_flag(): return 0
        if response[0]!='ok': 
           print("    Error while trying to obtain ",query,", exiting.")
           return 0
        building_layer.update_dicosm(response[1],tags_of_interest)
    building_area=OSM_to_MultiPolygon(building_layer,lat,lon)
    try:
        (idx_building,dico_building)=MultiPolygon_to_Indexed_Polygons(building_area,merge_overlappings=True)
    except:
        return 0
    vprint(2,"Number of building Multipolygons :",len(dico_pol_building))  
    Mesh_input.encode_MultiPolygon(dico_building,dem.alt_vec,'WATER',area_limit=min_area/10000,check=True)
    return 1
##############################################################################

##############################################################################
def build_poly_file(lat,lon,build_dir):
    set_flag(0)
    logprint("Step 1 for tile lat=",lat,", lon=",lon,": starting.")
    timer=time.time()
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
    node_file     =  os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.node')
    poly_file     =  os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.poly')
    alt_file      =  os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.alt')
    patch_dir     =  os.path.join(Ortho4XP_dir,'Patches',long_latlon(lat,lon))
    Mesh_input=mesh_input()
    
    print("-> Loading elevation data")
    try: 
        application.dem=DEM(lat,lon,application.cde.get())
        dem=application.dem
    except Exception as e:
        vprint(1,"Failed to load",application.cde.get())
        application.dem=DEM(lat,lon)
        dem=application.dem
   
    if check_flag(): exit_message_and_bottom_line(); return 0

    # Patches
    patches_area=include_patches(Mesh_input,dem,lat,lon)
    vprint(1,"    * Number of edges at this point:",len(Mesh_input.dico_edges))
    

    if check_flag(): exit_message_and_bottom_line(); return 0

    # Airports
    include_airports(Mesh_input,dem,lat,lon,patches_area)
    vprint(1,"    * Number of edges at this point:",len(Mesh_input.dico_edges))
    
    if check_flag(): exit_message_and_bottom_line(); return 0

    # Roads
    include_roads(Mesh_input,dem,lat,lon,road_level)
    vprint(1,"    * Number of edges at this point:",len(Mesh_input.dico_edges))
    
    if check_flag(): exit_message_and_bottom_line(); return 0

    # Sea
    include_sea(Mesh_input,dem,lat,lon)
    vprint(1,"    * Number of edges at this point:",len(Mesh_input.dico_edges))
 
    if check_flag(): exit_message_and_bottom_line(); return 0

    # Water 
    include_water(Mesh_input,dem,lat,lon)
    vprint(1,"    * Number of edges at this point:",len(Mesh_input.dico_edges))

    if check_flag(): exit_message_and_bottom_line(); return 0

    # Buildings 
    # include_buildings(Mesh_input)
    # if check_flag("step 1 interrupted"): return 0
    
    # Orthogrid
    print("-> Inserting edges related to the orthophotos grid")
    xgrid=set()  # x coordinates of vertical grid lines
    ygrid=set()  # y coordinates of horizontal grid lines
    (til_xul,til_yul) = wgs84_to_texture(lat+1,lon,meshzl,'BI')
    (til_xlr,til_ylr) = wgs84_to_texture(lat,lon+1,meshzl,'BI')
    for til_x in range(til_xul+16,til_xlr+1,16):
        pos_x=(til_x/(2**(meshzl-1))-1)
        xgrid.add(pos_x*180-lon)
    for til_y in range(til_yul+16,til_ylr+1,16):
        pos_y=(1-(til_y)/(2**(meshzl-1)))
        ygrid.add(360/pi*atan(exp(pi*pos_y))-90-lat)
    xgrid.add(0); xgrid.add(1); ygrid.add(0); ygrid.add(1)
    xgrid=list(sorted(xgrid))
    ygrid=list(sorted(ygrid))
    ortho_network=geometry.MultiLineString([geometry.LineString([(x,0),(x,1)]) for x in xgrid]+[geometry.LineString([(0,y),(1,y)]) for y in ygrid])
    Mesh_input.encode_MultiLineString(ortho_network,dem.alt_vec,'DUMMY',check=True,skip_cut=True)
    if check_flag(): exit_message_and_bottom_line(); return 0
    print("-> Inserting additional boundary edges for gluing")
    segs=2500
    gluing_network=geometry.MultiLineString([\
        geometry.LineString([(x,0) for x in numpy.arange(0,segs+1)/segs]),\
        geometry.LineString([(x,1) for x in numpy.arange(0,segs+1)/segs]),\
        geometry.LineString([(0,y) for y in numpy.arange(0,segs+1)/segs]),\
        geometry.LineString([(1,y) for y in numpy.arange(0,segs+1)/segs])])
    Mesh_input.encode_MultiLineString(gluing_network,dem.alt_vec,'DUMMY',check=True,skip_cut=True)
    if check_flag(): exit_message_and_bottom_line(); return 0
    vprint(1,"-> Transcription to the files ",poly_file,"and .node")
    if 'SEA' not in Mesh_input.seeds: Mesh_input.seeds['SEA']=[numpy.array([1000,1000])]
    #Mesh_input.collapse_nodes_to_grid(1e-7)
    Mesh_input.write_node_file(node_file)
    Mesh_input.write_poly_file(poly_file)
    vprint(1,"\nFinal number of constrained edges :",len(Mesh_input.dico_edges))
    timings_and_bottom_line(timer)
    logprint("Step 1 for tile lat=",lat,", lon=",lon,": normal exit.")
    return 1
##############################################################################
    


##############################################################################
class DEM():

    def __init__(self,lat,lon,filename=''):
        self.lat=lat
        self.lon=lon
        self.load_data(filename) 

    def load_data(self,filename=''):
        if not filename:
            filename=os.path.join(Ortho4XP_dir,"Elevation_data",self.viewfinderpanorama_filename(self.lat,self.lon))
            if not os.path.exists(filename):
                self.download_viewfinderpanorama(self.lat,self.lon)
        self.ds=gdal.Open(filename)
        self.rs=self.ds.GetRasterBand(1)
        self.alt_dem=self.rs.ReadAsArray().astype(numpy.float32)
        (self.nxdem,self.nydem)=(self.ds.RasterXSize,self.ds.RasterYSize) 
        self.nodata=self.rs.GetNoDataValue()
        if self.nodata is None: self.nodata=-32768
        try: 
            self.epsg=int(ds.GetProjection().split('"')[-2])
        except:
            self.epsg=4326
        self.geo=self.ds.GetGeoTransform()
        # remaining not meaningful if epsg not = 4326...which we assume now
        self.x0=self.geo[0]+.5*self.geo[1]-self.lon
        self.y1=self.geo[3]+.5*self.geo[5]-self.lat
        self.x1=self.x0+(self.nxdem-1)*self.geo[1] 
        self.y0=self.y1+(self.nydem-1)*self.geo[5]  
        # !!!!!!
        if not ('refine' in filename):
            self.nodata_to_zero()
        #self.fill_void()

 
    def fill_void(self):
        print(self.alt_dem.min(),self.nodata)  
        if self.alt_dem.min()!=self.nodata: return
        step=0
        while True:
            step+=1
            print(step)
            alt10=numpy.roll(self.alt_dem,1,axis=0)
            alt10[0]=self.alt_dem[0]
            alt20=numpy.roll(self.alt_dem,-1,axis=0)
            alt20[-1]=self.alt_dem[-1]
            alt01=numpy.roll(self.alt_dem,1,axis=1)
            alt01[:,0]=self.alt_dem[:,0]
            alt02=numpy.roll(self.alt_dem,-1,axis=1)
            alt02[:,-1]=self.alt_dem[:,-1]
            atemp=numpy.maximum(alt10,alt20)
            atemp=numpy.maximum(atemp,alt01)
            atemp=numpy.maximum(atemp,alt02)
            self.alt_dem[self.alt_dem==self.nodata]=atemp[self.alt_dem==self.nodata]
            if self.alt_dem.min()>self.nodata:
                break
            if step>10:
                print("The hole seems to big to be filled as is... I fill the remainder with zero.")
                self.alt_dem[self.alt_dem==self.nodata]=0
                break
        print("          Done.\n") 
        
    def nodata_to_zero(self):
        if self.nodata!=0 and (self.alt_dem==self.nodata).any():
            vprint(1,"    Caution: Replacing nodata nodes with zero altitude.")
            self.alt_dem[self.alt_dem==self.nodata]=0
        return

    def write_to_file(self,filename):
        self.alt_dem.tofile(filename)
        return
    
    def smoothen(self,smoothing_width):
        kernel=numpy.array(range(1,2*smoothing_width))
        kernel[smoothing_width:]=range(smoothing_width-1,0,-1)
        kernel=kernel/smoothing_width**2
        self.alt_dem=numpy.array(self.alt_dem)
        for _ in range(2):
            top_add=numpy.ones((smoothing_width,1)).dot(self.alt_dem[[0]]) 
            bottom_add=numpy.ones((smoothing_width,1)).dot(self.alt_dem[[-1]]) 
            self.alt_dem=numpy.vstack((top_add,self.alt_dem,bottom_add))
            self.alt_dem=self.alt_dem.transpose()
        for i in range(0,len(self.alt_dem)):
            self.alt_dem[i]=numpy.convolve(self.alt_dem[i],kernel,'same')
        self.alt_dem=self.alt_dem.transpose() 
        for i in range(0,len(self.alt_dem)):
            self.alt_dem[i]=numpy.convolve(self.alt_dem[i],kernel,'same')
        self.alt_dem=self.alt_dem.transpose()
        self.alt_dem=self.alt_dem[smoothing_width:-smoothing_width,smoothing_width:-smoothing_width]
        for i in range(smoothing_width):
            self.alt_dem[i]=i/smoothing_width*self.alt_dem[i]+(smoothing_width-i)/smoothing_width*self.alt_dem[i]
            self.alt_dem[-i-1]=i/smoothing_width*self.alt_dem[-i-1]+(smoothing_width-i)/smoothing_width*self.alt_dem[-i-1]
        for i in range(smoothing_width):
            self.alt_dem[:,i]=i/smoothing_width*self.alt_dem[:,i]+(smoothing_width-i)/smoothing_width*self.alt_dem[:,i]
            self.alt_dem[:,-i-1]=i/smoothing_width*self.alt_dem[:,-i-1]+(smoothing_width-i)/smoothing_width*self.alt_dem[:,-i-1]
        return

    def create_normal_map(self,pixx,pixy):
        s=18001
        dx=numpy.zeros((s,s))
        dy=numpy.zeros((s,s))
        dx[:,1:-1]=(self.alt_dem[:,2:]-self.alt_dem[:,0:-2])/(2*pixx)
        dx[:,0]=(self.alt_dem[:,1]-self.alt_dem[:,0])/(pixx)
        dx[:,-1]=(self.alt_dem[:,-1]-self.alt_dem[:,-2])/(pixx)
        dy[1:-1,:]=(self.alt_dem[:-2,:]-self.alt_dem[2:,:])/(2*pixy)
        dy[0,:]=(self.alt_dem[0,:]-self.alt_dem[1,:])/(pixy)
        dy[-1,:]=(self.alt_dem[-2,:]-self.alt_dem[-1,:])/(pixy)
        del(self.alt_dem)
        norm=numpy.sqrt(1+dx**2+dy**2)
        dx=dx/norm
        dy=dy/norm
        del(norm)
        band_r=Image.fromarray(((1+dx)/2*255).astype(numpy.uint8)).resize((4096,4096))
        del(dx)
        band_g=Image.fromarray(((1-dy)/2*255).astype(numpy.uint8)).resize((4096,4096))
        del(dy)
        band_b=Image.fromarray((numpy.ones((4096,4096))*10).astype(numpy.uint8))
        band_a=Image.fromarray((numpy.ones((4096,4096))*128).astype(numpy.uint8))
        im=Image.merge('RGBA',(band_r,band_g,band_b,band_a))
        im.save('normal_map.png')
        
        
        #for i in range(0,1):
        #    for j in range(0,1):
        #        dx=(self.alt_dem[s*i:s*(i+1),s*j+1:s*(j+1)+1]-self.alt_dem[s*i:s*(i+1),s*j-1:s*(j+1)-1])/(2*pixx)
        #        dy=(self.alt_dem[s*i-1:s*(i+1)-1,s*j:s*(j+1)]-self.alt_dem[s*i+1:s*(i+1)+1,s*j:s*(j+1)])/(2*pixy)
        #        norm=numpy.sqrt(1+dx**2+dy**2)
        #        dx=dx/norm
        #        dy=dy/norm
        #        band_r=Image.fromarray(((1+dx)/2*255).astype(numpy.uint8))
        #        band_g=Image.fromarray(((1-dy)/2*255).astype(numpy.uint8))
        #        band_b=Image.fromarray((numpy.ones(dx.shape)*10).astype(numpy.uint8))
        #        band_a=Image.fromarray((numpy.ones(dx.shape)*128).astype(numpy.uint8))
        #        im=Image.merge('RGBA',(band_r,band_g,band_b,band_a))
        #        im.save(str(i)+'_'+str(j)+'.png')


    def super_level_set(self,level,wgs84_bbox):
        (lonmin,lonmax,latmin,latmax)=wgs84_bbox
        xmin=lonmin-self.lon
        xmax=lonmax-self.lon
        ymin=latmin-self.lat
        ymax=latmax-self.lat
        if xmin<self.x0: xmin=self.x0
        if xmax>self.x1: xmax=self.x1
        if ymin<self.y0: ymin=self.y0
        if ymax>self.y1: ymax=self.y1
        pixx0=round((xmin-self.x0)/(self.x1-self.x0)*(self.nxdem-1))  
        pixx1=round((xmax-self.x0)/(self.x1-self.x0)*(self.nxdem-1))  
        pixy0=round((self.y1-ymax)/(self.y1-self.y0)*(self.nydem-1))  
        pixy1=round((self.y1-ymin)/(self.y1-self.y0)*(self.nydem-1))
        print((xmin+self.lon,xmax+self.lon,ymin+self.lat,ymax+self.lat))
        print((self.alt_dem[pixy0:pixy1+1,pixx0:pixx1+1]>=level).max())
        print((self.alt_dem[pixy0:pixy1+1,pixx0:pixx1+1]>=level).min())
        return ((xmin+self.lon,xmax+self.lon,ymin+self.lat,ymax+self.lat),Image.fromarray((self.alt_dem[pixy0:pixy1+1,pixx0:pixx1+1]>=level).astype(numpy.uint8)*255))

    def alt_vec(self,way):
        Nx=self.nxdem-1
        Ny=self.nydem-1
        x=way[:,0]
        y=way[:,1]
        x=numpy.maximum.reduce([x,self.x0*numpy.ones(x.shape)])
        x=numpy.minimum.reduce([x,self.x1*numpy.ones(x.shape)])
        y=numpy.maximum.reduce([y,self.y0*numpy.ones(y.shape)])
        y=numpy.minimum.reduce([y,self.y1*numpy.ones(y.shape)])
        px=(x-self.x0)/(self.x1-self.x0)*Nx
        py=(y-self.y0)/(self.y1-self.y0)*Ny
        nx=px.astype(numpy.uint16)
        Nminusny=Ny-py.astype(numpy.uint16)
        rx=px-nx
        ry=py+Nminusny-Ny
        t1=[self.alt_dem[i][j] for i,j in zip(Nminusny,nx)]
        t2=[self.alt_dem[i][j] for i,j in zip((Nminusny-1)*(Nminusny>=1),(nx+1)*(nx<Nx)+Nx*(nx==Nx))]
        t3=[self.alt_dem[i][j] for i,j in zip(Nminusny,(nx+1)*(nx<Nx)+Nx*(nx==Nx))]
        t4=[self.alt_dem[i][j] for i,j in zip((Nminusny-1)*(Nminusny>=1),nx)]
        return ((1-rx)*t1+ry*t2+(rx-ry)*t3)*(rx>=ry)+((1-ry)*t1+rx*t2+(ry-rx)*t4)*(rx<ry)

    def alt_vec_road(self,way):
        return self.alt_vec(way+0.00005*weighted_normals(way))

    def alt_vec_mean(self,way):
        return self.alt_vec(way).mean()*numpy.ones(len(way))

    def alt_vec_nodata(self,way):
        return self.nodata*numpy.ones(len(way))

    def way_is_too_much_banked(self,way):
        return (numpy.abs(self.alt_vec(way)-self.alt_vec_road(way))>=road_banking_limit).any()
    
    def viewfinderpanorama_filename(self,lat,lon):
        if (lat >= 0):
            hemisphere='N'
        else:
            hemisphere='S'
        if (lon >= 0):
            greenwichside='E'
        else:
            greenwichside='W'
        return hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
                greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)+'.hgt'

    def download_viewfinderpanorama(self,lat,lon):
        print("   No elevation file found, I download it from viewfinderpanorama (J. de Ferranti)")
        deferranti_nbr=31+lon//6
        if deferranti_nbr<10:
            deferranti_nbr='0'+str(deferranti_nbr)
        else:
            deferranti_nbr=str(deferranti_nbr)
        alphabet=list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        deferranti_letter=alphabet[lat//4] if lat>=0 else alphabet[(-1-lat)//4]
        if lat<0:
            deferranti_letter='S'+deferranti_letter
        s=requests.Session()
        dem_download_ok = False
        tentative=0
        while dem_download_ok != True and tentative<10:
            url="http://viewfinderpanoramas.org/dem3/"+deferranti_letter+deferranti_nbr+".zip"
            r=s.get(url)
            if ('Response [20' in str(r)):
                print("   Done. The zip archive will now be extracted in the Elevation_data dir.") 
                dem_download_ok=True
            else:
                tentative+=1 
                print("      Viewfinderpanorama server was busy, new tentative...")
                time.sleep(1)
        if tentative==10:
            return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
        zipfile=open(os.path.join(Ortho4XP_dir,"tmp",deferranti_letter+deferranti_nbr+".zip"),'wb')
        zipfile.write(r.content)
        zipfile.close()
        os.system(unzip_cmd+' e -y -o'+os.path.join(Ortho4XP_dir,'Elevation_data')+' "'+\
          os.path.join(Ortho4XP_dir,'tmp',deferranti_letter+deferranti_nbr+'.zip')+'"')
        os.system(delete_cmd+' '+os.path.join(Ortho4XP_dir,'tmp',deferranti_letter+deferranti_nbr+'.zip'))
        return 
    
    def downloaded_dem_file_name(self,lat,lon,source):
        if source=='SRTMv3_1(void filled)':
            if (lat >= 0):
                hemisphere='N'
            else:
                hemisphere='S'
            if (lon >= 0):
                greenwichside='E'
            else:
                greenwichside='W'
            file_name="SRTMv3_1_"+hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
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
            file_name="SRTMv3_3_"+hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
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
            file_name=hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+\
                    greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)+\
                    '.hgt'
        elif source=='FR':
            file_name='' # for future use maybe
        return Ortho4XP_dir+"/Elevation_data/"+file_name

    def load_altitude_matrix(self,lat,lon,file_name=''):
        file_name_srtm1=downloaded_dem_file_name(lat,lon,'SRTMv3_1(void filled)')
        file_name_srtm3=downloaded_dem_file_name(lat,lon,'SRTMv3_3(void filled)')
        file_name_viewfinderpanorama=downloaded_dem_file_name(lat,lon,'de_Ferranti')
        if file_name=='':
            if os.path.isfile(file_name_viewfinderpanorama):
                file_name=file_name_viewfinderpanorama
            elif os.path.isfile(file_name_srtm1):
                file_name=file_name_srtm1
            elif os.path.isfile(file_name_srtm3):
                file_name=file_name_srtm3
            else:
                print("   No elevation file found, I download it from viewfinderpanorama (J. de Ferranti)")
                deferranti_nbr=31+lon//6
                if deferranti_nbr<10:
                    deferranti_nbr='0'+str(deferranti_nbr)
                else:
                    deferranti_nbr=str(deferranti_nbr)
                alphabet=list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                deferranti_letter=alphabet[lat//4] if lat>=0 else alphabet[(-1-lat)//4]
                if lat<0:
                    deferranti_letter='S'+deferranti_letter
                s=requests.Session()
                dem_download_ok = False
                tentative=0
                while dem_download_ok != True and tentative<10:
                    url="http://viewfinderpanoramas.org/dem3/"+deferranti_letter+deferranti_nbr+".zip"
                    
                    r=s.get(url)
                    if ('Response [20' in str(r)):
                        print("   Done. The zip archive will now be extracted in the Elevation_data dir.") 
                        dem_download_ok=True
                    else:
                        tentative+=1 
                        print("      Viewfinderpanorama server was busy, new tentative...")
                        time.sleep(1)
                if tentative==10:
                    return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
                zipfile=open(Ortho4XP_dir+dir_sep+"tmp"+dir_sep+deferranti_letter+deferranti_nbr+".zip",'wb')
                zipfile.write(r.content)
                zipfile.close()
                os.system(unzip_cmd+' e -y -o'+Ortho4XP_dir+dir_sep+'Elevation_data'+' "'+\
                  Ortho4XP_dir+dir_sep+'tmp'+dir_sep+deferranti_letter+deferranti_nbr+'.zip"')
                os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'tmp'+dir_sep+deferranti_letter+deferranti_nbr+'.zip')
                file_name=file_name_viewfinderpanorama
                #usage('dem_files',do_i_quit=False) 
                #return 'error'
        if ('.hgt') in file_name or ('.HGT' in file_name):
            try:
                ndem=int(round(sqrt(os.path.getsize(file_name)/2)))
                alt=numpy.fromfile(file_name,numpy.dtype('>i2')).astype(numpy.float32).reshape((ndem,ndem))
                print(alt.min(),alt.max())
                time.sleep(2)
            except:
                usage('dem_files',do_i_quit=False) 
                return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
        elif ('.raw') in file_name or ('.RAW' in file_name):
            try:
                ndem=int(round(sqrt(os.path.getsize(file_name)/2)))
                f = open(file_name, 'rb')
                format = 'h'
                alt = array.array(format)
                alt.fromfile(f,ndem*ndem)
                f.close()
            except:
                usage('dem_files',do_i_quit=False) 
                return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
            alt=numpy.asarray(alt,dtype=numpy.float32).reshape((ndem,ndem))
            alt=alt[::-1]  
        elif ('.tif' in file_name) or ('.TIF' in file_name):
            if gdal_loaded == True:
                try:
                    ds=gdal.Open(file_name)
                    alt=numpy.float32(ds.GetRasterBand(1).ReadAsArray())
                    ndem=ds.RasterXSize
                except:
                    usage('dem_files',do_i_quit=False) 
                    return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
            else:
                try:
                    # geotiff file do not seem to be easily treated by PIL,
                    # smashing them through convert is a weird workaround
                    # since it removes some of the tags layer, but it works.     
                    #os.system(convert_cmd+' "'+file_name+'" "'+file_name +'" '+\
                    #        devnull_rdir)
                    im=Image.open(file_name)
                    alt=numpy.array(im)
                    #alt=alt-65536*(alt>10000)
                    if alt.shape[0]==alt.shape[1]:
                        ndem=alt.shape[0]
                    else:
                        usage('dem_files',do_i_quit=False) 
                        return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
                except:
                    usage('dem_files',do_i_quit=False) 
                    return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
        else:
            usage('dem_files',do_i_quit=False) 
            return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
        if alt.min()<-500:
            print("")
            print("WARNING : The elevation file "+file_name+" has some 'no data' zones, ")
            print("          I am filling the holes using a nearest neighbour approach.") 
            alt[alt<-500]=-32768
            is_filled=False
            step=0
            while not is_filled:
                step+=1
                print(step)
                alt10=numpy.roll(alt,1,axis=0)
                alt10[0]=alt[0]
                alt20=numpy.roll(alt,-1,axis=0)
                alt20[-1]=alt[-1]
                alt01=numpy.roll(alt,1,axis=1)
                alt01[:,0]=alt[:,0]
                alt02=numpy.roll(alt,-1,axis=1)
                alt02[:,-1]=alt[:,-1]
                atemp=numpy.maximum(alt10,alt20)
                atemp=numpy.maximum(atemp,alt01)
                atemp=numpy.maximum(atemp,alt02)
                alt=alt+(32768+atemp)*(alt==-32768)
                if alt.min()>-32768:
                    is_filled=True
                else:
                    print(numpy.sum(alt<=-32768))
                if step>100:
                    print("The hole seems to big to be filled as is... I fill the remainder with zero.")
                    alt[alt==-32768]=0
                    break
            print("          Done.\n") 
        return [alt,ndem]
##############################################################################


##############################################################################
def weighted_normals(way,side='left'):
    # traiter les cas de petits N !!!
    N=len(way)
    if N<2: return numpy.zeros(N)
    sign=numpy.array([[-1,1]]) if side=='left' else numpy.array([[1,-1]])
    tg=way[1:]-way[:-1]
    tg=tg/(1e-6+numpy.linalg.norm(tg,axis=1)).reshape(N-1,1)
    tg=numpy.vstack([tg,tg[-1]])   
    if N>2:
        scale=1e-6+numpy.linalg.norm(tg[1:-1]+tg[:-2],axis=1).reshape(N-2,1)
        #tg[1:-1]=2*(tg[1:-1]+tg[:-2])/(scale*numpy.maximum(scale,0.5))
        tg[1:-1]=(tg[1:-1]+tg[:-2])/(scale)
    if (way[0]==way[-1]).all():
        scale=1e-6+numpy.linalg.norm(tg[0]+tg[-1])
        #tg[0]=tg[-1]=2*(tg[0]+tg[-1])/(scale*numpy.maximum(scale,0.5))
        tg[0]=tg[-1]=(tg[0]+tg[-1])/(scale) 
    return  numpy.roll(tg,1,axis=1)*sign
##############################################################################











#############################################################################
def refine_way(way,max_length):
    new_way=[]
    for i in range(len(way)-1):
        new_way.append(way[i]) 
        l=sqrt((way[i][0]-way[i+1][0])**2+(way[i][1]-way[i+1][1])**2)
        ins=int(l//(max_length/111120))
        leff=l/(ins+1) 
        for j in range(1,ins+1):
            new_way.append((j/(ins+1)*way[i+1][0]+(ins+1-j)/(ins+1)*way[i][0],j/(ins+1)*way[i+1][1]+(ins+1-j)/(ins+1)*way[i][1]))
    new_way.append(way[-1])
    return numpy.array(new_way)
#############################################################################




 



##############################################################################
#  Construction des altitudes des points du maillage, et mise à zéro des
#  triangles de mer (pour éviter les effets indésirables des erreurs des
#  fichiers DEM sur le litoral lorsque celui-ci est accidenté). 
##############################################################################
def post_process_nodes_altitudes(lat,lon,iterate,dem,build_dir):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    dico_attributes=mesh_input.dico_attributes 
    node_file_name = build_dir+dir_sep+'Data'+strlat+strlon+'.'+str(iterate)+'.node'
    ele_file_name  = build_dir+dir_sep+'Data'+strlat+strlon+'.'+str(iterate)+'.ele'
    f_node = open(node_file_name,'r')
    f_ele  = open(ele_file_name,'r')
    init_line_f_node=f_node.readline()
    nbr_pt=int(init_line_f_node.split()[0])
    vertices=numpy.zeros(6*nbr_pt)   
    #input_alt=numpy.zeros(nbr_pt)
    print("-> Loading of the mesh computed by Triangle4XP.")
    for i in range(0,nbr_pt):
        vertices[6*i:6*i+6]=[float(x) for x in f_node.readline().split()[1:7]]
    end_line_f_node=f_node.readline()
    f_node.close()
    # Now we modify the altitude we got from the DEM in certain 
    # circumstances, because we want flat water, flat (or correctly sloped
    # airports, etc. One pass would be sufficient in principle but I 
    # prefer one pass per triangle type, to have better control in
    # case of nodes belonging different triangle types.
    print("-> Smoothing elevation file for airport levelling.")
    dem.smoothen(4)
    print("-> Post processing of altitudes according to vector data")
    f_ele  = open(ele_file_name,'r')
    nbr_tri= int(f_ele.readline().split()[0])
    water_tris=set()
    sea_tris=set()
    smoothed_alt_tris=set()
    interp_alt_tris=set()
    #triangles=numpy.zeros(4*nbr_tri,dtype=numpy.int)   
    for i in range(0,nbr_tri):
        line = f_ele.readline()
        if line[-2]=='0': continue
        (v1,v2,v3,attr)=[int(x)-1 for x in line.split()[1:5]]
        attr+=1
        if attr & dico_attributes['INTERP_ALT']: 
            interp_alt_tris.add((v1,v2,v3))
        elif attr & dico_attributes['SMOOTHED_ALT'] and iterate<=1: 
            smoothed_alt_tris.add((v1,v2,v3))
        elif attr & dico_attributes['SEA']:
            sea_tris.add((v1,v2,v3))
        elif attr & dico_attributes['WATER']:
            water_tris.add((v1,v2,v3))
        #triangles[4*i:4*i+4]=[int(x)-1 for x in f_ele.readline().split()[1:5]] # BEWARE Triangle4XP and Medit numbering start at 1!
        #triangles[4*i+3]+=1                                                    # but attributes are not concerned        
    if water_smoothing:
        print("   Smoothing inland water.")
        # Next, we average altitudes of triangles of fresh water type.  
        # Of course one such operation slightly breaks other ones, but there is 
        # not a perfect solution to this because the altitude close to the source
        # of a river differs from its altitude at is very end, water is not
        # flat all way long.
        for j in range(water_smoothing):   
            for (v1,v2,v3) in water_tris:
                #(v1,v2,v3,attr)=triangles[4*i:4*i+4]  
                #if attr & dico_attributes['WATER']:
                    zmean=(vertices[6*v1+2]+vertices[6*v2+2]+vertices[6*v3+2])/3
                    vertices[6*v1+2]=zmean
                    vertices[6*v2+2]=zmean
                    vertices[6*v3+2]=zmean
    print("   Smoothing of sea water.")
    for (v1,v2,v3) in sea_tris:
        #(v1,v2,v3,attr)=triangles[4*i:4*i+4]  
        #if attr & dico_attributes['SEA']:
            if sea_smoothing_mode==0:
                vertices[6*v1+2]=0
                vertices[6*v2+2]=0
                vertices[6*v3+2]=0
            elif sea_smoothing_mode==1:
                zmean=(vertices[6*v1+2]+vertices[6*v2+2]+vertices[6*v3+2])/3
                vertices[6*v1+2]=zmean
                vertices[6*v2+2]=zmean
                vertices[6*v3+2]=zmean
            else:
                vertices[6*v1+2]=max(vertices[6*v1+2],0)
                vertices[6*v2+2]=max(vertices[6*v2+2],0)
                vertices[6*v3+2]=max(vertices[6*v3+2],0)
    print("   Smoothing of airports.")
    for (v1,v2,v3) in smoothed_alt_tris:
        #(v1,v2,v3,attr)=triangles[4*i:4*i+4]  
        #if (attr &  dico_attributes['SMOOTHED_ALT']) and iterate<=1:
            vertices[6*v1+2]=dem.alt_vec(numpy.array([[vertices[6*v1],vertices[6*v1+1]]]))
            vertices[6*v2+2]=dem.alt_vec(numpy.array([[vertices[6*v2],vertices[6*v2+1]]]))
            vertices[6*v3+2]=dem.alt_vec(numpy.array([[vertices[6*v3],vertices[6*v3+1]]]))
    print("   Treatment of roads and patches.")
    for (v1,v2,v3) in interp_alt_tris:
        #(v1,v2,v3,attr)=triangles[4*i:4*i+4]  
        #if attr & dico_attributes['INTERP_ALT']:
            vertices[6*v1+2]=vertices[6*v1+5]
            vertices[6*v2+2]=vertices[6*v2+5]
            vertices[6*v3+2]=vertices[6*v3+5]
    print("-> Writing output nodes file.")        
    f_node = open(node_file_name,'w')
    f_node.write(init_line_f_node)
    for i in range(0,nbr_pt):
        f_node.write(str(i+1)+" "+' '.join((str(x) for x in vertices[6*i:6*i+6]))+"\n")
    f_node.write(end_line_f_node)
    f_node.close()
    return vertices
##############################################################################

##############################################################################
# Write of the mesh file based on .1.ele, .1.node and vertices
##############################################################################
def build_mesh_file(lat,lon,vertices,iterate,mesh_file_name,build_dir):
    print("-> Writing of the final mesh to the file "+mesh_file_name)
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    ele_file_name  = build_dir+dir_sep+'Data'+strlat+strlon+'.'+str(iterate)+'.ele'
    f_ele  = open(ele_file_name,'r')
    nbr_vert=len(vertices)//6
    nbr_tri=int(f_ele.readline().split()[0])
    f=open(mesh_file_name,"w")
    f.write("MeshVersionFormatted 1\n")
    f.write("Dimension 3\n\n")
    f.write("Vertices\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[6*i]+lon)+" "+\
                '{:.9f}'.format(vertices[6*i+1]+lat)+" "+\
                '{:.9f}'.format(vertices[6*i+2]/100000)+" 0\n") 
    f.write("\n")
    f.write("Normals\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[6*i+3])+" "+\
                '{:.9f}'.format(vertices[6*i+4])+"\n")
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
# Write of the wavefront obj file based on .1.ele, .1.node and vertices
##############################################################################
def build_obj_file(lat,lon,vertices,obj_file_name,build_dir):
    print("-> Writing of the final mesh to the file "+obj_file_name)
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    ele_file_name  = build_dir+dir_sep+'Data'+strlat+strlon+'.1.ele'
    f_ele  = open(ele_file_name,'r')
    nbr_vert=len(vertices)//5
    nbr_tri=int(f_ele.readline().split()[0])
    f=open(obj_file_name,"w")
    for i in range(0,nbr_vert):
        f.write("v "+'{:.9f}'.format(vertices[5*i])+" "+\
                '{:.9f}'.format(vertices[5*i+1])+" "+\
                '{:.9f}'.format(vertices[5*i+2]/100000)+"\n") 
    f.write("\n")
    for i in range(0,nbr_vert):
        f.write("vn "+'{:.9f}'.format(vertices[5*i+3])+" "+\
                '{:.9f}'.format(vertices[5*i+4])+" "+'{:.9f}'.format(sqrt(1-vertices[5*i+3]**2-vertices[5*i+4]**2))+" \n")
    f.write("\n")
    for i in range(0,nbr_tri):
        [one,two,three]=f_ele.readline().split()[1:4]
        f.write("f "+one+"//"+one+" "+two+"//"+two+" "+three+"//"+three+"\n")
    f_ele.close()
    f.close()
    return
##############################################################################

##############################################################################
# Transform a mesh file to a wavefront obj file with possible cut region
##############################################################################
# Under construction (?)
def mesh_to_obj(lat,lon,mesh_file_name,obj_file_name,latmin,latmax,lonmin,lonmax):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    f_mesh=open(mesh_file_name,"r")
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
    dico_new_pt={}
    dico_new_pt_inv={}
    len_dico_new_pt=0
    dico_new_tri={}
    len_dico_new_tri=0
    for i in range(0,nbr_tri_in):
        if i%100000==0: print(i)
        tmplist=f_mesh.readline().split()
        # look for the texture that will possibly cover the tri
        n1=int(tmplist[0])-1
        n2=int(tmplist[1])-1
        n3=int(tmplist[2])-1
        tri_type=tmplist[3] 
        [lon1,lat1,z1,u1,v1]=pt_in[5*n1:5*n1+5]
        [lon2,lat2,z2,u2,v2]=pt_in[5*n2:5*n2+5]
        [lon3,lat3,z3,u3,v3]=pt_in[5*n3:5*n3+5]
        if is_in_region((lat1+lat2+lat3)/3.0,(lon1+lon2+lon3)/3.0,latmin,latmax,lonmin,lonmax):
            if n1 not in dico_new_pt_inv:
                len_dico_new_pt+=1 
                dico_new_pt_inv[n1]=len_dico_new_pt
                dico_new_pt[len_dico_new_pt]=n1
            n1new=dico_new_pt_inv[n1]
            if n2 not in dico_new_pt_inv:
                len_dico_new_pt+=1 
                dico_new_pt_inv[n2]=len_dico_new_pt
                dico_new_pt[len_dico_new_pt]=n2
            n2new=dico_new_pt_inv[n2]
            if n3 not in dico_new_pt_inv:
                len_dico_new_pt+=1 
                dico_new_pt_inv[n3]=len_dico_new_pt
                dico_new_pt[len_dico_new_pt]=n3
            n3new=dico_new_pt_inv[n3]
            dico_new_tri[len_dico_new_tri]=(n1new,n2new,n3new)
            len_dico_new_tri+=1
    nbr_vert=len_dico_new_pt
    nbr_tri=len_dico_new_tri
    f=open(obj_file_name,"w")
    for i in range(1,nbr_vert+1):
        j=dico_new_pt[i]
        if i%1000000==0: print(i,j)
        f.write("v "+'{:.9f}'.format(pt_in[5*j]-lonmin)+" "+\
                '{:.9f}'.format(pt_in[5*j+1]-latmin)+" "+\
                '{:.9f}'.format(pt_in[5*j+2])+"\n") 
    f.write("\n")
    for i in range(1,nbr_vert+1):
        j=dico_new_pt[i]
        f.write("vn "+'{:.9f}'.format(pt_in[5*j+3])+" "+\
                '{:.9f}'.format(pt_in[5*j+4])+" "+'{:.9f}'.format(sqrt(1-pt_in[5*j+3]**2-pt_in[5*j+4]**2))+" \n")
    f.write("\n")
    for i in range(0,nbr_tri):
        (one,two,three)=dico_new_tri[i]
        f.write("f "+str(one)+"//"+str(one)+" "+str(two)+"//"+str(two)+" "+str(three)+"//"+str(three)+"\n")
    f_mesh.close()
    f.close()
    return
##############################################################################


##############################################################################
def build_mesh(lat,lon,build_dir):
    set_flag(0)    
    logprint("Step 2 for tile lat=",lat,", lon=",lon,": starting.")
    progress_bar(1,0)
    timer=time.time()
    
    if 'refine' not in application.cde.get():
        iterate=1
        Tri_option = ' -pAuYBQ '
    else:
        iterate=2
        Tri_option = ' -pruYBQ '
    node_file_name    = os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.'+str(iterate)+'.node')
    ele_file_name     = os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.'+str(iterate)+'.ele')
    if iterate==1:
        poly_file         = os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.poly')
    else:
        poly_file         = os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.'+str(iterate-1)+'.poly')
    
    alt_file_name     = os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.alt')
    weight_file_name  = os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.weight')
    mesh_file_name    = os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.mesh')
    
    if not os.path.isfile(poly_file):
        print("You must first build vector data !")
        return

    try:
        dem=application.dem
        print('-> Recycling elevation data.')
    except:
        try: 
            print('-> Loading of elevation data.')
            application.dem=DEM(lat,lon,application.cde.get())
            dem=application.dem
            vprint(1,"    Min altitude: ",dem.alt_dem.min(),", Max altitude :",dem.alt_dem.max())
        except Exception as e:
            vprint(2,e)
            print('  -> ERROR, reverting to default elevation data.')
            application.dem=DEM(lat,lon)
            dem=application.dem
    
    if check_flag(): return 0
    dem.write_to_file(alt_file_name)
    if check_flag(): return 0

    weight_array=numpy.ones((1000,1000),dtype=numpy.float32)
    build_curv_tol_weight_map(lat,lon,weight_array)
    vprint(2,"Mean curv_tol weight array",weight_array.mean())
    weight_array.tofile(weight_file_name)
    del(weight_array)
 
    curv_tol_scaling=dem.nxdem/(1000*(dem.x1-dem.x0))
    mesh_cmd=[Triangle4XP_cmd.strip(),Tri_option.strip(),str(111170*cos(lat*pi/180)),str(111170),str(dem.nxdem),str(dem.nydem),str(dem.x0),str(dem.y0),str(dem.x1),str(dem.y1),str(dem.nodata),str(curvature_tol*curv_tol_scaling),str(smallest_angle),str(hmin),alt_file_name,weight_file_name,poly_file]
    vprint(2,mesh_cmd)
    fingers_crossed=subprocess.Popen(mesh_cmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print(line.decode("utf-8")[:-1])
    #return
    if check_flag(): return 0
    vertices=post_process_nodes_altitudes(lat,lon,iterate,application.dem,build_dir)
    if check_flag(): return 0
    build_mesh_file(lat,lon,vertices,iterate,mesh_file_name,build_dir)
    #build_obj_file(lat,lon,vertices,obj_file_name,build_dir)
    del(application.dem)
    timings_and_bottom_line(timer)
    return 1
##############################################################################


##############################################################################
#                                                                            #
# IV : Initialisation des fournisseurs, des étendues et des filtres couleur  #
#                                                                            #
##############################################################################

providers_dict={}
combined_providers_dict={}
local_combined_providers_dict={}
extents_dict={'global':{}}
color_filters_dict={'none':[]}
epsg={}
epsg['4326']=pyproj.Proj(init='epsg:4326')
epsg['3857']=pyproj.Proj(init='epsg:3857')

def read_tilematrixsets(file_name):
    f=open(file_name,'r')
    def xml_decode(line):
        field=line.split('<')[1].split('>')[0]
        str_value=line.split('>')[1].split('<')[0]
        return [field,str_value]

    tilematrixsets=[]
    
    line=f.readline()
    while line:
        if line.strip()=='<TileMatrixSet>':
            tilematrixset={}
            tilematrixset['tilematrices']=[]
            line=f.readline()
            while not line.strip()=='</TileMatrixSet>':
                if line.strip()=='<TileMatrix>':
                    tilematrix={}
                    line=f.readline()
                    while not line.strip()=='</TileMatrix>':
                        field,str_value=xml_decode(line)
                        if 'Identifier' in field: field='identifier'
                        tilematrix[field]=str_value
                        line=f.readline()
                    tilematrixset['tilematrices'].append(tilematrix)
                elif 'Identifier' in line:
                    field,str_value=xml_decode(line)
                    tilematrixset['identifier']=str_value
                line=f.readline()
            tilematrixsets.append(tilematrixset)
        else:
            pass
        line=f.readline()
    f.close()
    return tilematrixsets

def initialize_extents_dict():
    for dir_name in os.listdir(os.path.join(Ortho4XP_dir,"active_extents")):
        if not os.path.isdir(os.path.join(Ortho4XP_dir,"active_extents",dir_name)):
            continue
        for file_name in os.listdir(os.path.join(Ortho4XP_dir,"active_extents",dir_name)):
            if '.' not in file_name or file_name.split('.')[-1]!='ext': continue
            extent_code=file_name.split('.')[0]
            extent={}
            f=open(os.path.join(Ortho4XP_dir,"active_extents",dir_name,file_name),'r')
            valid_extent=True
            for line in f.readlines():
                line=line[:-1]
                if "#" in line: line=line.split('#')[0]
                if ("=" not in line): continue
                try:
                    key=line.split("=")[0]
                    value=line[len(key)+1:]
                    extent[key]=value
                except:
                    print("Error for extent",extent_code,"in line",line)
                    continue
                # structuring data
                if key=='epsg_code':
                    try:
                        epsg[value]=pyproj.Proj(init='epsg:'+value)
                    except:
                        print("Error in epsg code for provider",provider_code)
                        valid_extent=False
                elif key=='mask_bounds':
                    try:
                        extent[key]=[float(x) for x in value.split(",")]
                    except:
                        print("Error in reading mask bounds for extent",extent_code)
                        valid_extent=False
            if valid_extent:
                extent['code']=extent_code
                extent['dir']=dir_name
                extents_dict[extent_code]=extent
            else:
                print("Error in reading extent definition file for",file_name)
                pass
            f.close()

def initialize_color_filters_dict():
    for file_name in os.listdir(os.path.join(Ortho4XP_dir,"active_filters")):
            if '.' not in file_name or file_name.split('.')[-1]!='flt': continue
            color_code=file_name.split('.')[0]
            extent={}
            f=open(os.path.join(Ortho4XP_dir,"active_filters",file_name),'r')
            valid_color_filters=True
            color_filters=[]
            for line in f.readlines():
                line=line[:-1]
                if "#" in line: line=line.split('#')[0]
                if not line: continue
                try:
                    items=line.split()            
                    color_filters.append([items[0]]+[float(x) for x in items[1:]])
                except:
                    valid_color_filters=False
            if valid_color_filters:
                color_filters_dict[color_code]=color_filters
            else:
                print("Could not understand color filter ",color_code,", skipping it.") 
                pass
            f.close()

# Look for lay files
def initialize_providers_dict():
    for dir_name in os.listdir(os.path.join(Ortho4XP_dir,"active_providers")):
        if not os.path.isdir(os.path.join(Ortho4XP_dir,"active_providers",dir_name)):
            continue
        for file_name in os.listdir(os.path.join(Ortho4XP_dir,"active_providers",dir_name)):
            if '.' not in file_name or file_name.split('.')[-1]!='lay': continue
            provider_code=file_name.split('.')[0]
            provider={}
            f=open(os.path.join(Ortho4XP_dir,"active_providers",dir_name,file_name),'r')
            valid_provider=True
            for line in f.readlines():
                line=line[:-1]
                if "#" in line:
                    if line[0]=="#": 
                        continue
                    else:
                        line=line.split('#')[0]
                if ("=" not in line): continue
                try:
                    key=line.split("=")[0]
                    value=line[len(key)+1:]
                    provider[key]=value
                except:
                    print("Error for provider",provider_code,"in line",line)
                    continue
                # structuring data
                if key=='request_type' and value not in ['wms','wmts','tms','local_tms']:
                    print("Unknown request_type field for provider",provider_code,":",value)
                    valid_provider=False
                if key=='grid_type' and value not in ['webmercator']:
                    print("Unknown grid_type field for provider",provider_code,":",value)
                    valid_provider=False
                elif key=='fake_headers':
                    try:
                        provider[key]=eval(value)
                        if type(provider[key]) is not dict:
                            print("Definition of fake headers for provider",provider_code,"not valid.")
                            valid_provider=False
                    except:
                        print("Definition of fake headers for provider",provider_code,"not valid.")
                        valid_provider=False
                elif key=='epsg_code':
                    try:
                        epsg[value]=pyproj.Proj(init='epsg:'+value)
                    except:
                        print("Error in epsg code for provider",provider_code)
                        valid_provider=False
                elif key=='image_type':
                    pass
                elif key=='url_prefix':
                    pass
                elif key=='url_template':
                    pass
                elif key=='layers':
                    pass
                elif key in ['wms_size','tile_size']:
                    try:
                        provider[key]=int(value)
                        if provider[key]<100 or provider[key]>10000:
                            print("Wm(t)s size for provider ",provider_code,"seems off limits, provider skipped.")
                    except:
                        print("Error in reading wms size for provider",provider_code)
                        valid_provider=False
                elif key in ['wms_version','wmts_version']:
                    if len(value.split('.'))<2: 
                        print("Error in reading wms version for provider",provider_code)
                        valid_provider=False
                elif key=='top_left_corner':
                    try:
                        provider[key]=[numpy.array([float(x) for x in value.split()]) for _ in range(0,21)]
                    except:
                        print("Error in reading top left corner for provider",provider_code)
                        valid_provider=False
                    pass 
                elif key == 'tilematrixset':
                    pass
                elif key=='resolutions':
                    try:
                        provider[key]=numpy.array([float(x) for x in value.split()])
                    except:
                        print("Error in reading resolutions for provider",provider_code)
                        valid_provider=False
                elif key=='max_threads':
                    try:
                        provider[key]=int(value)
                    except:
                        pass            
                elif key=='extent':
                    pass
                elif key=='color_filters':
                    pass
                elif key=='imagery_dir':
                   pass
            if 'request_type' in provider and provider['request_type']=='wmts':
                try: 
                    tilematrixsets=read_tilematrixsets(os.path.join(Ortho4XP_dir,'active_providers',dir_name,'capabilities.xml'))
                    tms_found=False
                    for tilematrixset in tilematrixsets:
                        if tilematrixset['identifier']==provider['tilematrixset']:
                            provider['tilematrixset']=tilematrixset
                            tms_found=True
                            break
                    if tms_found: 
                        provider['scaledenominator']=numpy.array([float(x['ScaleDenominator']) for x in provider['tilematrixset']['tilematrices']]) 
                        provider['top_left_corner']=[[float(x) for x in y['TopLeftCorner'].split()] for y in provider['tilematrixset']['tilematrices']] 
                    else:
                        print("no tilematrixset found")  
                        valid_provider=False
                except:
                    print("Error in reading capabilities for provider",provider_code) 
            if valid_provider:
                provider['code']=provider_code
                provider['directory']=dir_name
                if 'image_type' not in provider: 
                    provider['image_type']='jpeg'
                if 'extent' not in provider: 
                    provider['extent']='global'
                if 'color_filters' not in provider: 
                    provider['color_filters']='none'
                if 'imagery_dir' not in provider:
                    provider['imagery_dir']='code'
                if 'scaledenominator' in provider:
                    units_per_pix=0.00028 if provider['epsg_code'] not in ['4326'] else 2.5152827955e-09 
                    provider['resolutions']=units_per_pix*provider['scaledenominator']
                if 'grid_type' in provider and provider['grid_type']=='webmercator':
                    provider['request_type']='tms'
                    provider['tile_size']=256
                    provider['epsg_code']='3857'
                    provider['top_left_corner']=[[-20037508.34, 20037508.34] for i in range(0,21)]
                    provider['resolutions']=numpy.array([20037508.34/(128*2**i) for i in range(0,21)])
                providers_dict[provider_code]=provider
            else:
                print("Error in reading provider definition file for",file_name)
                pass
            f.close()

def initialize_combined_providers_dict():   
    for file_name in os.listdir("active_providers"):
        if '.' not in file_name or file_name.split('.')[-1]!='comb': continue
        provider_code=file_name.split('.')[0]
        try:
            comb_list=[]
            f=open(os.path.join(Ortho4XP_dir,"active_providers",file_name),'r')
            for line in f.readlines():
                if '#' in line: line=line.split('#')[0]
                if not line[:-1]: continue
                layer_code,extent_code,color_code,priority=line[:-1].split()
                if layer_code not in providers_dict:
                    print("Unknown provider in combined provider",provider_code,":",layer_code)
                    continue
                if extent_code=='default':
                    extent_code=providers_dict[layer_code]['extent']
                if extent_code not in extents_dict:
                    print("Unknown extent in combined provider",provider_code,":",extent_code)
                    continue
                if color_code=='default':
                    color_code=providers_dict[layer_code]['color_filters']
                if color_code not in color_filters_dict:
                    print("Unknown color filter in combined provider",provider_code,":",color_code)
                    continue
                if priority not in ['low','medium','high','mask']:
                    print("Unknown priority in combined provider",provider_code,":",priority)
                    continue
                comb_list.append({'layer_code':layer_code,'extent_code':extent_code,'color_code':color_code,'priority':priority})
            f.close()
            if comb_list:
                combined_providers_dict[provider_code]=comb_list
            else:
                print("Combined provider",provider_code,"did not contained valid providers, skipped.")
        except:
            print("Error reading definition of combined provider",provider_code)
                
def has_data(bbox_4326,extent_code,return_mask=False,mask_size=(4096,4096),is_sharp_resize=False,is_mask_layer=False):
    # This function checks wether a given provider has data instersecting the given bbox in epsg:4326
    # It returns either False or True or (in the latter case) the mask image over the bbox and properly resized accroding to input parameter.
    # is_sharp_resize determined if the upsamplique of the extent mask is nearest (good when sharp transitions are ) or bicubic (good in all other cases)
    # is_mask_layer allows to "multiply" extent masks with water masks, this is a smooth alternative for the old sea_texture_params. 
    # (x0,y0) is top-left, (x1,y1) is bottom-right
    (x0,y0,x1,y1)=bbox_4326
    try:
        if extent_code=='global':
            return (not return_mask) or Image.new('L',mask_size,'white')
        if extent_code[0]=='!': 
            extent_code=extent_code[1:]
            negative=True 
        else:
            negative=False 
        (xmin,ymin,xmax,ymax)=extents_dict[extent_code]['mask_bounds']
        if x0>xmax or x1<xmin or y0<ymin or y1>ymax:
            return negative
        if not is_mask_layer:
            mask_im=Image.open(os.path.join(Ortho4XP_dir,"active_extents",extents_dict[extent_code]['dir'],extents_dict[extent_code]['code']+".png")).convert("L")
            (sizex,sizey)=mask_im.size
            pxx0=int((x0-xmin)/(xmax-xmin)*sizex)
            pxx1=int((x1-xmin)/(xmax-xmin)*sizex)
            pxy0=int((ymax-y0)/(ymax-ymin)*sizey)
            pxy1=int((ymax-y1)/(ymax-ymin)*sizey)
            mask_im=mask_im.crop((pxx0,pxy0,pxx1,pxy1))
            if negative: mask_im=ImageOps.invert(mask_im)
            if not mask_im.getbbox():
                return False
            if not return_mask:
                return True
            if is_sharp_resize:
                return mask_im.resize(mask_size)
            else:
                return mask_im.resize(mask_size,Image.BICUBIC)
        else:
            # following code only visited when is_mask_layer is True
            # check if sea mask file exists
            (m_tilx,m_tily)=wgs84_to_texture((y0+y1)/2,(x0+x1)/2,maskszl,'')
            if not os.path.isfile(os.path.join(Ortho4XP_dir,'Masks',short_latlon(lat,lon),str(m_tily)+'_'+str(m_tilx)+'.png')):
                    return False
            # build extent mask_im
            mask_im=Image.open(os.path.join(Ortho4XP_dir,"active_extents",extents_dict[extent_code]['dir'],extents_dict[extent_code]['code']+".png")).convert("L")
            (sizex,sizey)=mask_im.size
            pxx0=int((x0-xmin)/(xmax-xmin)*sizex)
            pxx1=int((x1-xmin)/(xmax-xmin)*sizex)
            pxy0=int((ymax-y0)/(ymax-ymin)*sizey)
            pxy1=int((ymax-y1)/(ymax-ymin)*sizey)
            mask_im=mask_im.crop((pxx0,pxy0,pxx1,pxy1))
            if negative: mask_im=ImageOps.invert(mask_im)
            if not mask_im.getbbox():
                return False
            if is_sharp_resize:
                mask_im=mask_im.resize(mask_size)
            else:
                mask_im=mask_im.resize(mask_size,Image.BICUBIC)
            # build sea mask_im2    
            (ymax,xmin)=gtile_to_wgs84(m_tilx,m_tily,maskszl)
            (ymin,xmax)=gtile_to_wgs84(m_tilx+16,m_tily+16,maskszl)
            mask_im2=Image.open(os.path.join(Ortho4XP_dir,'Masks',short_latlon(lat,lon),str(m_tily)+'_'+str(m_tilx)+'.png')).convert("L")
            (sizex,sizey)=mask_im2.size
            pxx0=int((x0-xmin)/(xmax-xmin)*sizex)
            pxx1=int((x1-xmin)/(xmax-xmin)*sizex)
            pxy0=int((ymax-y0)/(ymax-ymin)*sizey)
            pxy1=int((ymax-y1)/(ymax-ymin)*sizey)
            mask_im2=mask_im2.crop((pxx0,pxy0,pxx1,pxy1)).resize(mask_size,Image.BICUBIC)
            # invert it 
            mask_array2=255-numpy.array(mask_im2,dtype=numpy.uint8)
            # let full sea down
            mask_array2[mask_array2==255]=0
            # combine (multiply) both
            mask_array=numpy.array(mask_im,dtype=numpy.uint16)
            mask_array=(mask_array*mask_array2/255).astype(numpy.uint8)
            mask_im = Image.fromarray(mask_array).convert('L')
            if not mask_im.getbbox():
                return False
            if not return_mask:
                return True
            return mask_im
    except:
        vprint(1,"Could not test coverage of ",extent_code," !!!!!!!!!!!!")
        return False

def initialize_local_combined_providers_dict(lat,lon,ortho_list):
    # This function will select from list of providers the only
    # ones whose coverage intersect the given tile.
    global local_combined_providers_dict
    local_combined_providers_dict={} 
    test_set=set()
    for region in ortho_list[:]:
        test_set.add(region[2])
    for provider_code in test_set.intersection(combined_providers_dict):
            comb_list=[]
            for rlayer in combined_providers_dict[provider_code]:
                if has_data((lon,lat+1,lon+1,lat),rlayer['extent_code']):
                    comb_list.append(rlayer)
            if comb_list:
                local_combined_providers_dict[provider_code]=comb_list
            else:
                vprint(1,"Combined provider",provider_code,"did not contained data for this tile, skipping it.")
                ortho_list.remove(region)

##############################################################################
#                                                                            #
# IV : Toutes les méthodes à vocation géographique, essentiellement ce       #
#      qui concerne les changements de référentiel (WGS84 - Lambert - UTM)   #
#      ou la numérotation des vignettes (TMS - Quadkey).                     #
#                                                                            #
##############################################################################

##############################################################################
def wgs84_to_gtile(lat,lon,zoomlevel):                                          
    rat_x=lon/180           
    rat_y=log(tan((90+lat)*pi/360))/pi
    pix_x=round((rat_x+1)*(2**(zoomlevel+7)))
    pix_y=round((1-rat_y)*(2**(zoomlevel+7)))
    til_x=pix_x//256
    til_y=pix_y//256
    return (til_x,til_y)
##############################################################################

##############################################################################
def wgs84_to_pix(lat,lon,zoomlevel):                                          
    rat_x=lon/180           
    rat_y=log(tan((90+lat)*pi/360))/pi
    pix_x=round((rat_x+1)*(2**(zoomlevel+7)))
    pix_y=round((1-rat_y)*(2**(zoomlevel+7)))
    return (pix_x,pix_y)
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
    return (lat,lon)
##############################################################################

##############################################################################
def pix_to_wgs84(pix_x,pix_y,zoomlevel):
    rat_x=(pix_x/(2**(zoomlevel+7))-1)
    rat_y=(1-pix_y/(2**(zoomlevel+7)))
    lon=rat_x*180
    lat=360/pi*atan(exp(pi*rat_y))-90
    return (lat,lon)
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
# V  :  Une texture est un fichier image de 4096x4096 pixels, dont l'emprise #
#       géographie correspond nécessairement au tilematrixset web-mercator   #
#       utilisé notamment par les grands fournisseurs tels Google et Bing.   #
#       Les imageries utilisant d'autres projections ou découpages devront   #
#       être reprojetées/redécoupées suivant cette grille (le programme s'en #
#       charge tout seul.                                                    #
#                                                                            #
##############################################################################

##############################################################################
#  Comment appeler le bébé ?
##############################################################################
    
def short_latlon(lat,lon):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    return strlat+strlon

def round_latlon(lat,lon):
    strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
    strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
    return strlatround+strlonround

def long_latlon(lat,lon):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
    strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
    return os.path.join(strlatround+strlonround,strlat+strlon)

def dds_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code,file_ext='dds'):
    if provider_code=='g2xpl_8':
        file_name=g2xpl_8_prefix+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
                str(2**zoomlevel-8-til_y_top)+g2xpl_8_suffix+"."+file_ext
    elif provider_code=='g2xpl_16':
        file_name=g2xpl_16_prefix+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
                str(2**zoomlevel-16-til_y_top)+g2xpl_16_suffix+"."+file_ext
    else:
        file_name=str(til_y_top)+"_"+str(til_x_left)+"_"+provider_code+str(zoomlevel)+"."+file_ext   
    return file_name

def mask_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code,file_ext='png'):
    if provider_code=='g2xpl_8':
        file_name=g2xpl_8_prefix+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
                str(2**zoomlevel-8-til_y_top)+g2xpl_8_suffix+"."+file_ext
    elif provider_code=='g2xpl_16':
        file_name=g2xpl_16_prefix+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
                str(2**zoomlevel-16-til_y_top)+g2xpl_16_suffix+"."+file_ext
    else:
        file_name=str(til_y_top)+"_"+str(til_x_left)+"_ZL"+str(zoomlevel)+"."+file_ext   
    return file_name

def jpeg_file_name_from_attributes(lat,lon,til_x_left,til_y_top,zoomlevel,provider_code,file_ext='jpg'):
    if providers_dict[provider_code]['imagery_dir']=='normal':
        tmp_dir=short_latlon(lat,lon)
    elif providers_dict[provider_code]['imagery_dir']=='grouped':
        tmp_dir=long_latlon(lat,lon)
    elif providers_dict[provider_code]['imagery_dir']=='code':
        tmp_dir=providers_dict[provider_code]['code']
    else:
        tmp_dir=providers_dict[provider_code]['imagery_dir']
    file_dir=os.path.join(Ortho4XP_dir,"Orthophotos",\
                 tmp_dir,provider_code+'_'+str(zoomlevel))
    if provider_code=='g2xpl_8':
        file_name=g2xpl_8_prefix+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
                str(2**zoomlevel-8-til_y_top)+g2xpl_8_suffix+"."+file_ext
    elif provider_code=='g2xpl_16':
        file_name=g2xpl_16_prefix+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
                str(2**zoomlevel-16-til_y_top)+g2xpl_16_suffix+"."+file_ext
    else:
        file_name=str(til_y_top)+"_"+str(til_x_left)+"_"+provider_code+str(zoomlevel)+"."+file_ext   
    return (file_dir,file_name)
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
def wgs84_to_texture(lat,lon,zoomlevel,provider_code):
    ratio_x=lon/180           
    ratio_y=log(tan((90+lat)*pi/360))/pi
    if provider_code=='g2xpl_8':
        mult=2**(zoomlevel-4)
        til_x=int((ratio_x+1)*mult)*8
        til_y=int((1-ratio_y)*mult)*8
    else:
        mult=2**(zoomlevel-5)
        til_x=int((ratio_x+1)*mult)*16
        til_y=int((1-ratio_y)*mult)*16
    return (til_x,til_y)
##############################################################################

##############################################################################
# Cfr. le manuel de DSFTool (wiki.x-plane.com), ce sont les coordonnées à 
# l'intérieur d'une texture avec (0,0) en bas à gauche et (1,1) en haut à 
# droite.
##############################################################################
def st_coord(lat,lon,tex_x,tex_y,zoomlevel,provider_code):                        
    """
    ST coordinates of a point in a texture
    """
    if provider_code=='g2xpl_8':
        ratio_x=lon/180           
        ratio_y=log(tan((90+lat)*pi/360))/pi
        mult=2**(zoomlevel-4)
        s=(ratio_x+1)*mult-(tex_x//8)
        t=1-((1-ratio_y)*mult-tex_y//8)
        s = s if s>=0 else 0
        s = s if s<=1 else 1
        t = t if t>=0 else 0
        t = t if t<=1 else 1
        return [s,t]
    else: # provider_code not in st_proj_coord_dict: # hence in epsg:4326
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
    #else:
    #    [latmax,lonmin]=gtile_to_wgs84(tex_x,tex_y,zoomlevel)
    #    [latmin,lonmax]=gtile_to_wgs84(tex_x+16,tex_y+16,zoomlevel)
    #    [ulx,uly]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[provider_code]],lonmin,latmax)
    #    [urx,ury]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[provider_code]],lonmax,latmax)
    #    [llx,lly]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[provider_code]],lonmin,latmin)
    #    [lrx,lry]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[provider_code]],lonmax,latmin)
    #    minx=min(ulx,llx)
    #    maxx=max(urx,lrx)
    #    miny=min(lly,lry)
    #    maxy=max(uly,ury)
    #    deltax=maxx-minx
    #    deltay=maxy-miny
    #    [x,y]=pyproj.transform(epsg['4326'],epsg[st_proj_coord_dict[provider_code]],lon,lat)
    #    s=(x-minx)/deltax
    #    t=(y-miny)/deltay
    #    s = s if s>=0 else 0
    #    s = s if s<=1 else 1
    #    t = t if t>=0 else 0
    #   t = t if t<=1 else 1
    #    return [s,t]
##############################################################################

##############################################################################
def attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,dico_customzl,tri_type):
    bary_lat=(lat1+lat2+lat3)/3
    bary_lon=(lon1+lon2+lon3)/3
    return dico_customzl[wgs84_to_texture(bary_lat,bary_lon,meshzl,'BI')]
    #if tri_type in ['2','3']:
    #    if sea_texture_params!=[]:
    #        provider_code=sea_texture_params[0]
    #        zoomlevel=sea_texture_params[1]
    #        return wgs84_to_texture(bary_lat,bary_lon,zoomlevel,provider_code)+\
    #            [zoomlevel]+[provider_code]
    #for region in ortho_list:
    #    if point_in_polygon([bary_lat,bary_lon],region[0]):
    #        zoomlevel=int(region[1])
    #        provider_code=str(region[2])
    #        return wgs84_to_texture(bary_lat,bary_lon,zoomlevel,provider_code)+\
    #            [zoomlevel]+[provider_code]
    #print("No provider for ",lat1,lon1,lat2,lon2,lat3,lon3,bary_lat,bary_lon)
    #return 'None'
##############################################################################


##############################################################################
#  The master procedure to download pieces of what will become a 4K texture.
#  The process depend on the provider.
##############################################################################

class parallel_worker(threading.Thread):
    def __init__(self,task,queue,progress=None):
        threading.Thread.__init__(self)
        self._task=task
        self._queue=queue
        self._progress=progress
    def run(self):
        while True:
            args=self._queue.get()
            if isinstance(args,str) and args=='quit':
                break
            self._task(*args)
            if self._progress:
                self._progress['done']+=1
                self._progress['bar'].set(int(100*self._progress['done']/(self._progress['done']+self._queue.qsize()))) 
            try:
                if application.red_flag.get()==1:
                    break
            except:
                pass
   
def parallel_execute(task,queue,nbr_workers):
    workers=[]
    for _ in range(nbr_workers):
        queue.put('quit')
        worker=parallel_worker(task,queue)
        worker.start()
        workers.append(worker)
    for worker in workers:
        worker.join() 
     
def parallel_launch(task,queue,nbr_workers,progress=None):
    workers=[]
    for _ in range(nbr_workers):
        worker=parallel_worker(task,queue,progress)
        worker.start()
        workers.append(worker)
    return workers   

def parallel_join(workers):
    for worker in workers:
        worker.join() 



def build_texture_from_tilbox(tilbox,zoomlevel,provider):
    t=time.time() 
    (til_x_min,til_y_min,til_x_max,til_y_max)=tilbox
    parts_x=til_x_max-til_x_min
    parts_y=til_y_max-til_y_min
    width=height=provider['tile_size']
    big_image=Image.new('RGB',(width*parts_x,height*parts_y)) 
    print(width*parts_x,height*parts_y)
    # we set-up the queue of downloads
    http_session=requests.Session() 
    download_queue=queue.Queue()
    for monty in range(0,parts_y):
        for montx in range(0,parts_x):
            x0=montx*width
            y0=monty*height
            fargs=[zoomlevel,til_x_min+montx,til_y_min+monty,provider,big_image,x0,y0,http_session]
            download_queue.put(fargs)
    # then the number of workers
    if 'max_threads' in provider: 
        max_threads=int(provider['max_threads'])
    else:
        max_threads=16
    # and finally activate them
    parallel_execute(get_and_paste_wmts_part,download_queue,max_threads)
    # once out big_image has been filled and we return it
    return big_image


def build_texture_from_bbox_and_size(t_bbox,t_epsg,t_size,provider):
    # warp will be needed for projections not parallel to 3857
    # if warp is not needed, crop could still be needed if the grids do not match
    warp_needed=crop_needed=False
    (ulx,uly,lrx,lry)=t_bbox
    (t_sizex,t_sizey)=t_size 
    [s_ulx,s_uly]=pyproj.transform(epsg[t_epsg],epsg[provider['epsg_code']],ulx,uly)
    [s_urx,s_ury]=pyproj.transform(epsg[t_epsg],epsg[provider['epsg_code']],lrx,uly)
    [s_llx,s_lly]=pyproj.transform(epsg[t_epsg],epsg[provider['epsg_code']],ulx,lry)
    [s_lrx,s_lry]=pyproj.transform(epsg[t_epsg],epsg[provider['epsg_code']],lrx,lry)
    if s_ulx!=s_llx or s_uly!=s_ury or s_lrx!=s_urx or s_lly!=s_lry:
        s_ulx=min(s_ulx,s_llx)
        s_uly=max(s_uly,s_ury)
        s_lrx=max(s_urx,s_lrx)
        s_lry=min(s_lly,s_lry)
        warp_needed=True
    x_range=s_lrx-s_ulx
    y_range=s_uly-s_lry
    if provider['request_type']=='wms':
        wms_size=int(provider['wms_size'])
        parts_x=int(ceil(t_sizex/wms_size))
        #width=t_sizex//parts_x
        width=wms_size
        parts_y=int(ceil(t_sizey/wms_size))
        #height=t_sizey//parts_y
        height=wms_size
    elif provider['request_type'] in ['wmts','tms','local_tms']:
        asked_resol=max(x_range/t_sizex,y_range/t_sizey)
        vprint(2,"asked_resol",asked_resol)
        wmts_tilematrix=numpy.argmax(provider['resolutions']<=asked_resol*1.1)
        #wmts_tilematrix=numpy.argmin(numpy.abs(numpy.log(provider['resolutions']/asked_resol)))
        wmts_resol=provider['resolutions'][wmts_tilematrix]   # in s_epsg unit per pix !
        vprint(1,asked_resol,wmts_resol)
        width=height=provider['tile_size']
        cell_size=wmts_resol*width
        [wmts_x0,wmts_y0]=provider['top_left_corner'][wmts_tilematrix]  
        til_x_min=int((s_ulx-wmts_x0)//cell_size)
        til_x_max=int((s_lrx-wmts_x0)//cell_size)
        til_y_min=int((wmts_y0-s_uly)//cell_size)
        til_y_max=int((wmts_y0-s_lry)//cell_size)
        parts_x=til_x_max-til_x_min+1
        parts_y=til_y_max-til_y_min+1
        s_box_ulx=wmts_x0+cell_size*til_x_min
        s_box_uly=wmts_y0-cell_size*til_y_min
        s_box_lrx=wmts_x0+cell_size*(til_x_max+1)
        s_box_lry=wmts_y0-cell_size*(til_y_max+1)
        if s_box_ulx!=s_ulx or s_box_uly!=s_uly or s_box_lrx!=s_lrx or s_box_lry!=s_lry:
            crop_x0=int(round((s_ulx-s_box_ulx)/wmts_resol))
            crop_y0=int(round((s_box_uly-s_uly)/wmts_resol))
            crop_x1=int(round((s_lrx-s_box_ulx)/wmts_resol))
            crop_y1=int(round((s_box_uly-s_lry)/wmts_resol))
            s_ulx=s_box_ulx    
            s_uly=s_box_uly    
            s_lrx=s_box_lrx
            s_lry=s_box_lry
            crop_needed=True
        downscale=int(min(log(width*parts_x/t_sizex),log(height/t_sizey))/log(2))-1
        if downscale>=1:
            width/=2**downscale
            height/=2**downscale
            subt_size=(width,height) 
        else:
            subt_size=None
    big_image=Image.new('RGB',(width*parts_x,height*parts_y)) 
    http_session=requests.Session()
    download_queue=queue.Queue()
    for monty in range(0,parts_y):
        for montx in range(0,parts_x):
            x0=montx*width
            y0=monty*height
            if provider['request_type']=='wms':
                p_ulx=s_ulx+montx*x_range/parts_x
                p_uly=s_uly-monty*y_range/parts_y
                p_lrx=p_ulx+x_range/parts_x
                p_lry=p_uly-y_range/parts_y
                p_bbox=[p_ulx,p_uly,p_lrx,p_lry]
                fargs=[p_bbox[:],width,height,provider,big_image,x0,y0,http_session]
            elif provider['request_type'] in ['wmts','tms','local_tms']:
                fargs=[wmts_tilematrix,til_x_min+montx,til_y_min+monty,provider,big_image,x0,y0,http_session,subt_size]
            download_queue.put(fargs)
    # We execute the downloads and subimage pastes
    if 'max_threads' in provider: 
        max_threads=int(provider['max_threads'])
    else:
        max_threads=16
    if provider['request_type']=='wms':
        parallel_execute(get_and_paste_wms_part,download_queue,max_threads)
    elif provider['request_type'] in ['wmts','tms','local_tms']:
        parallel_execute(get_and_paste_wmts_part,download_queue,max_threads)
    # We modify big_image if necessary
    if warp_needed:
        vprint(2,"warp_needed!!!!!!!!!!!!!!!")
        big_image=gdalwarp_alternative((s_ulx,s_uly,s_lrx,s_lry),provider['epsg_code'],big_image,t_bbox,t_epsg,t_size)
    elif crop_needed:
        vprint(2,"crop_needed!!!!!!!!!!!!!!!")
        big_image=big_image.crop((crop_x0,crop_y0,crop_x1,crop_y1))
    if big_image.size!=t_size:
        vprint(1,"resize_needed!!!!!!!!!!!!!!!"+str(t_size[0]/big_image.size[0])+" "+str(t_size[1]/big_image.size[1]))
        big_image=big_image.resize(t_size,Image.BICUBIC)
    return big_image

def build_texture_from_bbox_and_resol(t_bbox,t_epsg,t_resol,provider):
    return


def gdalwarp_alternative(s_bbox,s_epsg,s_im,t_bbox,t_epsg,t_size):
        [s_ulx,s_uly,s_lrx,s_lry]=s_bbox
        [t_ulx,t_uly,t_lrx,t_lry]=t_bbox
        (s_w,s_h)=s_im.size
        (t_w,t_h)=t_size
        t_quad = (0, 0, t_w, t_h)
        meshes = []
        def cut_quad_into_grid(quad, steps):
            w = quad[2]-quad[0]
            h = quad[3]-quad[1]
            x_step = w / float(steps)
            y_step = h / float(steps)
            y = quad[1]
            for k in range(steps):
                x = quad[0]
                for l in range(steps):
                    yield (int(x), int(y), int(x+x_step), int(y+y_step))
                    x += x_step
                y += y_step
        for quad in cut_quad_into_grid(t_quad,8):
            s_quad=[]
            for (t_pixx,t_pixy) in [(quad[0],quad[1]),(quad[0],quad[3]),(quad[2],quad[3]),(quad[2],quad[1])]:
                t_x=t_ulx+t_pixx/t_w*(t_lrx-t_ulx)
                t_y=t_uly-t_pixy/t_h*(t_uly-t_lry)
                (s_x,s_y)=pyproj.transform(epsg[t_epsg],epsg[s_epsg],t_x,t_y)
                s_pixx=int(round((s_x-s_ulx)/(s_lrx-s_ulx)*s_w))    
                s_pixy=int(round((s_uly-s_y)/(s_uly-s_lry)*s_h))
                s_quad.extend((s_pixx,s_pixy))
            meshes.append((quad,s_quad))    
        return s_im.transform(t_size,Image.MESH,meshes,Image.BICUBIC)


def get_and_paste_wms_part(bbox,width,height,provider,big_image,x0,y0,http_session):
    small_image=get_wms_image(bbox,width,height,provider,http_session)
    big_image.paste(small_image,(x0,y0))
    return

def get_and_paste_wmts_part(tilematrix,til_x,til_y,provider,big_image,x0,y0,http_session,subt_size=None):
    small_image=get_wmts_image(tilematrix,til_x,til_y,provider,http_session)
    if not subt_size:
        big_image.paste(small_image,(x0,y0))
    else:
        big_image.paste(small_image.resize(subt_size,Image.BICUBIC),(x0,y0))
    return


def get_wms_image(bbox,width,height,provider,http_session):
    if provider['code'] in custom_url_list:
        url=custom_url_request(bbox,width,height,provider)
    else:
        [minx,maxy,maxx,miny]=bbox
        if provider['wms_version'].split('.')[1]=="3":
            bbox_string=str(miny)+','+str(minx)+','+str(maxy)+','+str(maxx)
            _RS='CRS'
        else:
            bbox_string=str(minx)+','+str(miny)+','+str(maxx)+','+str(maxy) 
            _RS='SRS' 
        url=provider['url_prefix']+"SERVICE=WMS&VERSION="+provider['wms_version']+"&FORMAT=image/"+provider['image_type']+\
                "&REQUEST=GetMap&LAYERS="+provider['layers']+"&STYLES=&"+_RS+"=EPSG:"+str(provider['epsg_code'])+\
                "&WIDTH="+str(width)+"&HEIGHT="+str(height)+\
                "&BBOX="+bbox_string 
    if 'fake_headers' in provider:
        fake_headers=provider['fake_headers']
    else:
        fake_headers=fake_headers_generic 
    vprint(2,"One wms image ok")
    (success,data)=http_request_to_image(width,height,url,fake_headers,http_session)
    if success: 
        return data 
    else:
        return Image.new('RGB',(width,height),'red')


def get_wmts_image(tilematrix,til_x,til_y,provider,http_session):
  tilematrix_orig,til_x_orig,til_y_orig=tilematrix,til_x,til_y
  down_sample=0
  while True:   
    if provider['request_type']=='tms':
        url=provider['url_template'].replace('{zoom}',str(tilematrix))
        url=url.replace('{x}',str(til_x)) 
        url=url.replace('{y}',str(til_y))
        url=url.replace('{|y|}',str(abs(til_y)-1))
        url=url.replace('{-y}',str(2**tilematrix-1-til_y))
        url=url.replace('{quadkey}',gtile_to_quadkey(til_x,til_y,tilematrix))
        url=url.replace('{xcenter}',str((til_x+0.5)*provider['resolutions'][tilematrix]*provider['tile_size']+provider['top_left_corner'][tilematrix][0]))
        url=url.replace('{ycenter}',str(-1*(til_y+0.5)*provider['resolutions'][tilematrix]*provider['tile_size']+provider['top_left_corner'][tilematrix][1]))
        url=url.replace('{size}',str(int(provider['resolutions'][tilematrix]*provider['tile_size'])))
        if '{switch:' in url:
            (url_0,tmp)=url.split('{switch:')
            (tmp,url_2)=tmp.split('}')
            server_list=tmp.split(',')
            url_1=random.choice(server_list).strip()
            url=url_0+url_1+url_2 
    elif provider['request_type']=='wmts': #wmts
        url=provider['url_prefix']+"&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER="+\
            provider['layers']+"&STYLE=&FORMAT=image/"+provider['image_type']+"&TILEMATRIXSET="+provider['tilematrixset']['identifier']+\
            "&TILEMATRIX="+provider['tilematrixset']['tilematrices'][tilematrix]['identifier']+"&TILEROW="+str(til_y)+"&TILECOL="+str(til_x)
    elif provider['request_type']=='local_tms':
        url_local=provider['url_template'].replace('{x}',str(5*til_x).zfill(4)) # ! Too much specific, needs to be changed by a x,y-> file_name lambda fct
        url_local=url_local.replace('{y}',str(-5*til_y).zfill(4))
        if os.path.isfile(url_local):
            return(Image.open(url_local))
        else:
            vprint(1,"!!!!!!! File ",url_local,"absent, using white texture instead !!!!!!!!!!")
            return(Image.new('RGB',(provider['tile_size'],provider['tile_size']),'white'))
    if 'fake_headers' in provider:
        fake_headers=provider['fake_headers']
    else:
        fake_headers=fake_headers_generic
    width=height=provider['tile_size'] 
    (success,data)=http_request_to_image(width,height,url,fake_headers,http_session)
    if success and not down_sample: 
        return data 
    elif success and down_sample:
        x0=(til_x_orig-2**down_sample*til_x)*width//(2**down_sample)
        y0=(til_y_orig-2**down_sample*til_y)*height//(2**down_sample)
        x1=x0+width//(2**down_sample)
        y1=y0+height//(2**down_sample)
        return data.crop((x0,y0,x1,y1)).resize((width,height),Image.BICUBIC) 
    elif data=='data not found on server, try to down_sample':
        til_x=til_x//2
        til_y=til_y//2
        tilematrix-=1
        down_sample+=1 
        if down_sample>=6:
            return Image.new('RGB',(width,height),'white')
    else:
        return Image.new('RGB',(width,height),'white')
       
        
def http_request_to_image(width,height,url,fake_headers,http_session):
    vprint(2,url)
    tentative_request=0
    tentative_image=0
    r=False
    reason=''
    #!!! UK hack
    #XX=16
    #url_orig=url
    #url=url_orig.replace('XX',str(XX))
    #!!! End of UK hack
    while True:
        try:
            if fake_headers:
                r=http_session.get(url, timeout=http_timeout,headers=fake_headers) 
            else:
                r=http_session.get(url, timeout=http_timeout) 
            print(r)
            if ('Response [20' in str(r)) and ('image' in r.headers['Content-Type']):
                try:
                    small_image=Image.open(io.BytesIO(r.content))
                    #!!! UK hack
                    #if small_image.size!=(250,250):
                    #    XX-=1
                    #    if XX==11: return(0,'UK out')
                    #    url=url_orig.replace('XX',str(XX))
                    #    continue
                    #else:
                    #    return (1,small_image)
                    #!!! End of UK hack
                    return (1,small_image)
                except:
                    vprint(1,"Server said all is correct but did not send us a valid image :",r,r.headers)
                    reason='corrupted data'
                print("gooood!!!!!")
            # F44 Hack
            elif 'makina-corpus' in url:
                url=url.replace('jpg','png')
                continue
            # fin Hack 44
            elif ('Response [20' in str(r)):
            #elif (b'was not found on this server' in r.content) or (b'\x00\x00\x02\x02' in r.content):
                vprint(1,"Server said it has no data for",url)
                reason='data not found on server, try to down_sample'
                vprint(1,str(r))
                vprint(1,r.headers)
                vprint(1,r.content)
                break
            elif ('Response [404]' in str(r)):
                vprint(1,"Server said it has no data for",url)
                reason='data not found on server'
                break
            else:      
                vprint(1,"Server did not send us an image and his answer is not known, retrying in 2 secs")
                vprint(1,"(--> Uncheck 'Check against white textures' now if you want to bypass this <--)")
                vprint(1,url) 
                vprint(1,r.content)
                vprint(1,str(r))
                vprint(1,r.headers)
                time.sleep(5)
                reason='not an image, unknown message'
                if not check_tms_response:
                    break 
                time.sleep(1)
            try:
                if application.red_flag.get()==1:
                    return (0,'stopped')
            except:
                pass
            tentative_image+=1  
        except requests.exceptions.RequestException as e:    
            vprint(1,"Server could not be connected, retrying in 2 secs")
            vprint(1,"(--> Uncheck 'Check against white textures' now if you want to bypass this <--)")
            vprint(1,e)
            if not check_tms_response:
                break
            # trying a new session ? 
            http_session=requests.Session()
            time.sleep(2)
            reason='no response from server'
            try:
                if application.red_flag.get()==1:
                    return (0,'stopped')
            except:
                pass
            tentative_request+=1
        if tentative_request==max_connect_retries or tentative_image==max_baddata_retries: break 
    vprint(1,"Part of an image could not be constructed, the reason seems to be :",reason,".") 
    return (0,reason)

def build_jpeg_ortho(file_dir,file_name,til_x_left,til_y_top,zoomlevel,provider_code,super_resol_factor=1):
    provider=providers_dict[provider_code]
    if 'super_resol_factor' in provider and super_resol_factor==1: super_resol_factor=int(provider['super_resol_factor'])
    # we treat first the case of webmercator grid type servers
    if 'max_zl' in provider and zoomlevel>int(provider['max_zl']):
        max_zl=int(provider['max_zl'])
        super_resol_factor=2**(max_zl-zoomlevel)
    if 'grid_type' in provider and provider['grid_type']=='webmercator':
        # just in case it was a mistake
        if provider['code']=='g2xpl_8': 
            tilbox=[til_x_left,til_y_top,til_x_left+8,til_y_top+8] 
            width=height=int(2048*super_resol_factor)
        else:
            tilbox=[til_x_left,til_y_top,til_x_left+16,til_y_top+16] 
            width=height=int(4096*super_resol_factor)
        tilbox_mod=[int(round(p*super_resol_factor)) for p in tilbox]
        zoom_shift=round(log(super_resol_factor)/log(2))
        big_image=build_texture_from_tilbox(tilbox_mod,zoomlevel+zoom_shift,provider)
    # if not we are in the world of epsg:3857 bboxes
    else:
        if provider['code']=='g2xpl_8': 
            [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
            [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
            width=height=int(2048*super_resol_factor)
        else:
            [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
            [latmin,lonmax]=gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
            width=height=int(4096*super_resol_factor)
        [xmin,ymax]=pyproj.transform(epsg['4326'],epsg['3857'],lonmin,latmax)
        [xmax,ymin]=pyproj.transform(epsg['4326'],epsg['3857'],lonmax,latmin)
        big_image=build_texture_from_bbox_and_size([xmin,ymax,xmax,ymin],'3857',(width,height),provider)
    try:
        if application.red_flag.get()==1:
            return
    except:
        pass
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    if super_resol_factor==1:
        big_image.save(os.path.join(file_dir,file_name))
    else:
        big_image.resize((int(width/super_resol_factor),int(height/super_resol_factor)),Image.BICUBIC).save(os.path.join(file_dir,file_name))
    return
 

###############################################################################
def build_texture_region(dest_dir,latmin,latmax,lonmin,lonmax,zoomlevel,provider_code):
    [til_xmin,til_ymin]=wgs84_to_texture(latmax,lonmin,zoomlevel,provider_code)
    [til_xmax,til_ymax]=wgs84_to_texture(latmin,lonmax,zoomlevel,provider_code)
    nbr_to_do=((til_ymax-til_ymin)/16+1)*((til_xmax-til_xmin)/16+1)
    print("Number of tiles to download at most : ",nbr_to_do)
    for til_y_top in range(til_ymin,til_ymax+1,16):
        for til_x_left in range(til_xmin,til_xmax+1,16):
            (y0,x0)=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
            (y1,x1)=gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
            bbox_4326=(x0,y0,x1,y1)
            if has_data(bbox_4326,providers_dict[provider_code]['extent'],return_mask=False,mask_size=(4096,4096)):
                (file_dir,file_name)=jpeg_file_name_from_attributes(latmin,lonmin,til_x_left,til_y_top,zoomlevel,provider_code)
                if dest_dir: file_dir=dest_dir
                if os.path.isfile(os.path.join(file_dir,file_name)):
                    print("recycling one")
                    nbr_to_do-=1
                    continue 
                print("building one")
                build_jpeg_ortho(file_dir,file_name,til_x_left,til_y_top,zoomlevel,provider_code,super_resol_factor=1)
            else:
                print("skipping one")
            nbr_to_do-=1
            print(nbr_to_do)
    return   
###############################################################################

###############################################################################
def build_provider_texture(dest_dir,provider_code,zoomlevel):
    (lonmin,latmin,lonmax,latmax)=extents_dict[providers_dict[provider_code]['extent']]['mask_bounds']
    build_texture_region(dest_dir,latmin,latmax,lonmin,lonmax,zoomlevel,provider_code)
    return   
###############################################################################



###############################################################################
def create_tile_preview(latmin,lonmin,zoomlevel,provider_code):
    strlat='{:+.0f}'.format(latmin).zfill(3)
    strlon='{:+.0f}'.format(lonmin).zfill(4)
    if not os.path.exists(Ortho4XP_dir+dir_sep+'Previews'):
        os.makedirs(Ortho4XP_dir+dir_sep+'Previews') 
    os.system(delete_cmd+' '+Ortho4XP_dir+dir_sep+'Previews'+\
               dir_sep+'image-*.jpg '+devnull_rdir)
    filepreview=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+strlat+\
                  strlon+"_"+provider_code+str(zoomlevel)+".jpg"       
    if os.path.isfile(filepreview) != True:
        [til_x_min,til_y_min]=wgs84_to_gtile(latmin+1,lonmin,zoomlevel)
        [til_x_max,til_y_max]=wgs84_to_gtile(latmin,lonmin+1,zoomlevel)
        tilbox=(til_x_min,til_y_min,til_x_max+1,til_y_max+1)
        big_image=build_texture_from_tilbox(tilbox,zoomlevel,providers_dict[provider_code])
        big_image.save(filepreview)
        return
##############################################################################

###############################################################################
def create_vignette(tilx0,tily0,tilx1,tily1,zoomlevel,provider_code,vignette_name):
        big_image=Image.new('RGB',(tilx1-tilx0)*256,(tily1-tily0)*256)
        s=requests.Session()
        for til_x in range(tilx0,tilx1):
            for til_y in range(tily0,tily1):
                successful_download=False
                while successful_download==False:
                    try:
                        [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,provider_code)
                        r=s.get(url, headers=fake_headers)
                        successful_download=True
                    except:
                        #print("Connexion avortée par le serveur, nouvelle tentative dans 1sec")
                        time.sleep(0.01)
                if ('Response [20' in str(r)):
                    small_image=Image.open(io.BytesIO(r.content))
                    big_image.paste(small_image,((til_x-tilx0)*256,(til_y-tily0)*256))
                else:
                    small_image=Image.open(Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
                      'white.jpg')
                    big_image.paste(small_image,((til_x-tilx0)*256,(til_y-tily0)*256))
        big_image.save(vignette_name)
        return
##############################################################################

###############################################################################
def create_vignettes(zoomlevel,provider_code):
        nbr_pieces=2**(zoomlevel-3)
        for nx in range(0,nbr_pieces):
            for ny in range(0,nbr_pieces):
               vignette_name=Ortho4XP_dir+dir_sep+"Previews"+dir_sep+"Earth"+\
                  dir_sep+"Earth2_ZL"+str(zoomlevel)+"_"+str(nx)+'_'+str(ny)+'.jpg'
               tilx0=nx*8
               tily0=ny*8
               create_vignette(tilx0,tily0,tilx0+8,tily0+8,zoomlevel,provider_code,vignette_name) 
        return
##############################################################################

##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les zones non immergées).
##############################################################################
def create_terrain_file(build_dir,file_name,til_x_left,til_y_top,zoomlevel,provider_code):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+'.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    if provider_code !='g2xpl_8':
        [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        half_meridian=pi*6378137
        texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))*tweak_resol_factor
        file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    else:
        [lat_med,lon_med]=gtile_to_wgs84(til_x_left+4,til_y_top+4,zoomlevel)
        half_meridian=pi*6378137
        texture_approx_size=int(2*half_meridian/2**(zoomlevel-3)*\
                        cos(lat_med*pi/180))
        file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 2048\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')
    file.write('NORMAL_METALNESS\n')
    #file.write('TEXTURE_NORMAL 1 ../textures/normal_map.png\n')
    if use_decal_on_terrain or zoomlevel<14:
        file.write('DECAL_LIB lib/g10/decals/maquify_1_green_key.dcl\n')
    if not terrain_casts_shadows:
        file.write('NO_SHADOW\n')
    file.close()
    return
##############################################################################

##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les lacs et rivières).
##############################################################################
def create_overlay_file(build_dir,file_name,til_x_left,til_y_top,zoomlevel,provider_code):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+\
            '_overlay.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    if provider_code !='g2xpl_8':
        [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        half_meridian=pi*6378137
        texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
        file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    else:
        [lat_med,lon_med]=gtile_to_wgs84(til_x_left+4,til_y_top+4,zoomlevel)
        half_meridian=pi*6378137
        texture_approx_size=int(2*half_meridian/2**(zoomlevel-3)*\
                        cos(lat_med*pi/180))
        file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 2048\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')  
    file.write('WET\n')
    #file.write('NORMAL_METALNESS\n')
    #file.write('TEXTURE_NORMAL 1 ../textures/reflect_water.dds\n')
    file.write('BORDER_TEX ../textures/water_transition.png\n')
    file.write('NO_SHADOW\n')
    file.close()
    return
##############################################################################

##############################################################################
# Les fichiers .ter de X-Plane (ici la version pour les mers et océans).
##############################################################################
def create_sea_overlay_file_new(build_dir,til_x_left,til_y_top,zoomlevel,provider_code):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    fprefix=dds_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)[:-4]
    file=open(build_dir+dir_sep+'terrain'+dir_sep+fprefix+\
            '_sea_overlay.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    half_meridian=pi*6378137
    if provider_code !='g2xpl_8':
        [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
        file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    else:
        [lat_med,lon_med]=gtile_to_wgs84(til_x_left+4,til_y_top+4,zoomlevel)
        texture_approx_size=int(2*half_meridian/2**(zoomlevel-3)*\
                        cos(lat_med*pi/180))
        file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 2048\n')
    #file.write('NORMAL_METALNESS\n')
    #file.write('TEXTURE_NORMAL 1 ../textures/reflect_water.dds\n')
    file.write('WET\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+dds_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)+'\n')
    #(m_til_y_top,m_til_x_left)=(int(z) for z in mask_name.split('.')[0].split('_')) 
    #(m_lat_med,m_lon_med)=gtile_to_wgs84(m_til_x_left+8,m_til_y_top+8,maskszl)
    #m_approx_size=int(2*half_meridian/2**(maskszl-4)*\
    #                cos(m_lat_med*pi/180))
    #file.write('LOAD_CENTER_BORDER '+'{:.5f}'.format(lat_med)+' '\
    #       +'{:.5f}'.format(lon_med)+' '\
    #       +str(texture_approx_size)+' '+str(4096//2**(zoomlevel-maskszl))+'\n')
    file.write('BORDER_TEX ../textures/'+mask_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)+'\n') #.replace('png','dds')+'\n')
    file.write('NO_SHADOW\n')
    #if use_additional_water_shader==True:
    file.close()
    return
def create_sea_overlay_file(build_dir,file_name,mask_name,til_x_left,til_y_top,\
        zoomlevel,provider_code):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_dir+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+\
            '_sea_overlay.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    half_meridian=pi*6378137
    if provider_code !='g2xpl_8':
        [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                        cos(lat_med*pi/180))
        file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    else:
        [lat_med,lon_med]=gtile_to_wgs84(til_x_left+4,til_y_top+4,zoomlevel)
        texture_approx_size=int(2*half_meridian/2**(zoomlevel-3)*\
                        cos(lat_med*pi/180))
        file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 2048\n')
    #file.write('NORMAL_METALNESS\n')
    #file.write('TEXTURE_NORMAL 1 ../textures/reflect_water.dds\n')
    file.write('WET\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.'+dds_or_png+'\n')
    (m_til_y_top,m_til_x_left)=(int(z) for z in mask_name.split('.')[0].split('_')) 
    (m_lat_med,m_lon_med)=gtile_to_wgs84(m_til_x_left+8,m_til_y_top+8,maskszl)
    m_approx_size=int(2*half_meridian/2**(maskszl-4)*\
                    cos(m_lat_med*pi/180))
    file.write('LOAD_CENTER_BORDER '+'{:.5f}'.format(lat_med)+' '\
           +'{:.5f}'.format(lon_med)+' '\
           +str(m_approx_size)+' 4096\n')
    file.write('BORDER_TEX ../textures/'+mask_name+'\n') #.replace('png','dds')+'\n')
    file.write('NO_SHADOW\n')
    #if use_additional_water_shader==True:
    file.close()
    return
##############################################################################

##############################################################################
#  Y a-t-il besoin de mettre un masque ?
##############################################################################
def needs_mask(tilx,tily,zoomlevel,provider_code,masks_zl=14):
    if int(zoomlevel)<masks_zl:
        return False
    factor=2**(zoomlevel-masks_zl)
    tilxmask=(int(tilx/factor)//16)*16
    tilymask=(int(tily/factor)//16)*16
    #rx=(tilx/factor)%16
    rx=int((tilx-factor*tilxmask)/16)
    #ry=(tily/factor)%16
    ry=int((tily-factor*tilymask)/16)
    mask_file=os.path.join(Ortho4XP_dir,'Masks',short_latlon(lat,lon),\
            str(int(tilymask))+'_'+str(int(tilxmask))+'.png')
    if not os.path.isfile(mask_file): return False
    big_img=Image.open(mask_file)
    x0=int(rx*4096/factor)
    y0=int(ry*4096/factor)
    small_img=big_img.crop((x0,y0,x0+4096//factor,y0+4096//factor))
    small_array=numpy.array(small_img,dtype=numpy.uint8)
    if small_array.max()<=30: #  or small_array.min()==255:
        return False
    else:
        #print("Mask size :",small_img.size)
        return small_img
def which_mask(layer,lat,lon,masks_zl=14):
    tilx=layer[0]
    tily=layer[1]
    zoomlevel=layer[2]
    if int(zoomlevel)<masks_zl:
        return 'None'
    provider_code=layer[3]
    factor=2**(zoomlevel-masks_zl)
    tilx14=(int(tilx/factor)//16)*16
    tily14=(int(tily/factor)//16)*16
    #rx=(tilx/factor)%16
    rx=int((tilx-factor*tilx14)/16)
    #ry=(tily/factor)%16
    ry=int((tily-factor*tily14)/16)
    mask_file=os.path.join(Ortho4XP_dir,'Masks',short_latlon(lat,lon),\
            str(int(tily14))+'_'+str(int(tilx14))+'.png')
    if not os.path.isfile(mask_file): return 'None'
    big_img=Image.open(mask_file)
    x0=int(rx*4096/factor)
    y0=int(ry*4096/factor)
    small_img=big_img.crop((x0,y0,x0+4096//factor,y0+4096//factor))
    if not small_img.getbbox():
        return 'None'
    else:
        return [mask_file,factor,rx,ry]
##############################################################################
 
##############################################################################
#  La routine de conversion jpeg -> dds, avec éventuel calcul du masque alpha.
##############################################################################
def convert_texture(build_dir,lat,lon,til_x_left,til_y_top,zoomlevel,provider_code,test=False):
    dds_file_name=dds_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)
    vprint(1,"   Converting orthophoto(s) to build texture "+dds_file_name+".")
    png_file_name=dds_file_name.replace('dds','png')
    if provider_code in local_combined_providers_dict:
        big_image=combine_textures(lat,lon,til_x_left,til_y_top,zoomlevel,provider_code)
        file_to_convert=os.path.join(Ortho4XP_dir,'tmp',png_file_name)
        big_image.save(file_to_convert) 
        #big_image.convert('RGB').save(os.path.join(build_dir,'textures',dds_file_name.replace('dds','jpg')),quality=70)
    # now if provider_code was not in local_combined_providers_dict but color correction is required
    elif providers_dict[provider_code]['color_filters']!='none':
        (file_dir,jpeg_file_name)=jpeg_file_name_from_attributes(lat,lon,til_x_left,til_y_top,zoomlevel,provider_code)
        big_image=Image.open(os.path.join(file_dir,jpeg_file_name),'r').convert('RGB')
        big_image=color_transform(big_image,providers_dict[provider_code]['color_filters'])
        file_to_convert=os.path.join(Ortho4XP_dir,'tmp',png_file_name)
        big_image.save(file_to_convert) 
    # finally if nothing needs to be done prior to the dds conversion
    else:
        (file_dir,jpeg_file_name)=jpeg_file_name_from_attributes(lat,lon,til_x_left,til_y_top,zoomlevel,provider_code)
        file_to_convert=os.path.join(file_dir,jpeg_file_name)
    # eventually the dds conversion
    conv_cmd=dds_convert_cmd +' "'+file_to_convert+'" "'+\
                 os.path.join(build_dir,'textures',dds_file_name)+'" '+ devnull_rdir
    if not test:
        os.system(conv_cmd)
        try:
            os.remove(os.path.join(Ortho4XP_dir,'tmp',png_file_name))
        except:
            pass  
    return 
##############################################################################

##############################################################################
def combine_textures(lat,lon,til_x_left,til_y_top,zoomlevel,provider_code):
    big_image=Image.new('RGBA',(4096,4096))
    (y0,x0)=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
    (y1,x1)=gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
    mask_weight_below=numpy.zeros((4096,4096),dtype=numpy.uint16)
    for rlayer in local_combined_providers_dict[provider_code][::-1]:
        mask=has_data((x0,y0,x1,y1),rlayer['extent_code'],return_mask=True,is_mask_layer=rlayer['priority']=='mask')
        if not mask: continue
        # we turn the image mask into an array 
        mask=numpy.array(mask,dtype=numpy.uint16)
        (true_file_dir,true_file_name)=jpeg_file_name_from_attributes(\
                   lat,lon,til_x_left,til_y_top,zoomlevel,rlayer['layer_code'])
        true_im=Image.open(os.path.join(true_file_dir,true_file_name))
        # in case the smoothing of the extent mask was too strong we remove the
        # the mask (where it is nor 0 nor 255) the pixels for which the true_im
        # is all white
        true_arr=numpy.array(true_im).astype(numpy.uint16)
        #mask[(numpy.sum(true_arr,axis=2)>=715)*(mask>=1)*(mask<=253)]=0
        #mask[(numpy.sum(true_arr,axis=2)<=15)*(mask>=1)*(mask<=253)]=0
        # 
        if rlayer['priority']=='low':
            # low priority layers, do not increase mask_weight_below
            wasnt_zero=(mask_weight_below+mask)!=0
            mask[wasnt_zero]=255*mask[wasnt_zero]/(mask_weight_below+mask)[wasnt_zero]
        elif rlayer['priority'] in ['high','mask']:
            mask_weight_below+=mask
        elif rlayer['priority']=='medium':
            #mask[(numpy.sum(true_arr,axis=2)>=760)*(mask>=1)*(mask<=253)]=0
            #mask[(numpy.sum(true_arr,axis=2)<=5)*(mask>=1)*(mask<=253)]=0
            #mask_weight_below+=mask
            #wasnt_zero=mask_weight_below!=0
            #mask[wasnt_zero]=255*mask[wasnt_zero]/mask_weight_below[wasnt_zero]
            ## undecided about the next two lines
            #was_zero=mask_weight_below==0
            #mask[was_zero]=255 
            not_zero=mask!=0
            mask_weight_below+=mask
            mask[not_zero]=255*mask[not_zero]/mask_weight_below[not_zero]
            # undecided about the next two lines
            #was_zero=mask_weight_below==0
            #mask[was_zero]=255 
        # we turn back the array mask into an image
        mask=Image.fromarray(mask.astype(numpy.uint8))
        # !!! imagery dir change !!!
        vprint(2,"Inprinting for provider",rlayer,til_x_left,til_y_top) 
        true_im=color_transform(true_im,rlayer['color_code'])  
        if rlayer['priority']=='mask' and sea_texture_blur_radius:
            print("Blur of a mask !!!!!!!!")
            true_im=true_im.filter(ImageFilter.GaussianBlur(sea_texture_blur_radius*2**(zoomlevel-17)))
        big_image=Image.composite(true_im,big_image,mask)
    vprint(2,"Finished imprinting",til_x_left,til_y_top)
    return big_image
##############################################################################

##############################################################################
def color_transform(im,color_code):
    for color_filter in color_filters_dict[color_code]:
        if color_filter[0]=='brightness-contrast': #both range from -127 to 127, http://gimp.sourcearchive.com/documentation/2.6.1/gimpbrightnesscontrastconfig_8c-source.html
            (brightness,contrast)=color_filter[1:3]
            if brightness>=0:  
                im=im.point(lambda i: 128+tan(pi/4*(1+contrast/128))*(brightness+(255-brightness)/255*i-128))
            else:
                im=im.point(lambda i: 128+tan(pi/4*(1+contrast/128))*((255+brightness)/255*i-128))
        elif color_filter[0]=='saturation':  
            saturation=color_filter[1]   
            #(h,s,v)=im.convert('HSV').split()
            #h.paste(h.point(lambda i:i*(500+5*saturation)/(500+saturation)))
            #im=Image.merge('HSV',(h,s,v)).convert('RGB')
            im=ImageEnhance.Color(im).enhance(1+saturation/100)
        elif color_filter[0]=='sharpness':
            im=ImageEnhance.Sharpness(im).enhance(color_filter[1])
        elif color_filter[0]=='blur':
            im=im.filter(ImageFilter.GaussianBlur(color_filter[1]))
        elif color_filter[0]=='levels': # levels range between 0 and 255, gamma is neutral at 1 / https://pippin.gimp.org/image-processing/chap_point.html
            bands=im.split()
            for j in [0,1,2]:
               in_min,gamma,in_max,out_min,out_max=color_filter[5*j+1:5*j+6]
               bands[j].paste(bands[j].point(lambda i: out_min+(out_max-out_min)*((max(in_min,min(i,in_max))-in_min)/(in_max-in_min))**(1/gamma)))
            im=Image.merge(im.mode,bands)
    return im
##############################################################################

##############################################################################
#  Le séquenceur de la phase de téléchargement des textures.
##############################################################################
def download_textures(lat,lon,build_dir,download_queue,convert_queue,progress=None):
    while True:
        texture=download_queue.get()
        if isinstance(texture,str) and texture=='quit':
            try:
                progress['bar'].set(100) 
            except:
                pass
            break
        (til_x_left,til_y_top,zoomlevel,provider_code)=texture
        dds_file_name=dds_file_name_from_attributes(*texture)
        if provider_code in local_combined_providers_dict:
            data_found=False
            for rlayer in local_combined_providers_dict[provider_code]:
                (y0,x0)=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
                (y1,x1)=gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
                if has_data((x0,y0,x1,y1),rlayer['extent_code']):
                    data_found=True
                    true_texture=(*texture[:-1],rlayer['layer_code'])
                    (true_file_dir,true_file_name)=jpeg_file_name_from_attributes(lat,lon,*true_texture)
                    if not os.path.isfile(os.path.join(true_file_dir,true_file_name)):
                        vprint(1,"   Downloading missing orthophoto "+true_file_name+" (for combining in "+provider_code+")\n")
                        build_jpeg_ortho(true_file_dir,true_file_name,*true_texture)
                    else:
                        vprint(1,"   The orthophoto "+true_file_name+" (for combining in "+provider_code+") is already present.\n")
            if not data_found: print("     -> !!! Warning : No data found for building the combined texture",dds_file_name," !!!")
        else:  
            (file_dir,file_name)=jpeg_file_name_from_attributes(lat,lon,*texture)
            if not os.path.isfile(os.path.join(file_dir,file_name)):
                vprint(1,"   Downloading missing orthophoto "+file_name)
                build_jpeg_ortho(file_dir,file_name,*texture)
            else:
                vprint(1,"   The orthophoto "+file_name+" is already present.")
        try:
            progress['done']+=1 
            progress['bar'].set(int(100*progress['done']/(progress['done']+download_queue.qsize()))) 
            if application.red_flag.get()==1:
                print("Download process interrupted.")
                return
        except:
            pass
        convert_queue.put([build_dir,lat,lon,*texture])
    return
##############################################################################

##############################################################################
def build_combined_ortho(lat,lon,zoomlevel,provider_code,filename='test.png'):
    initialize_color_filters_dict()
    initialize_extents_dict()
    initialize_providers_dict()
    initialize_combined_providers_dict()
    initialize_local_combined_providers_dict(floor(lat),floor(lon),[[1,1,'Z']])
    (til_x_left,til_y_top)=wgs84_to_texture(lat,lon,zoomlevel,provider_code)
    texture=(til_x_left,til_y_top,zoomlevel,provider_code)
    for rlayer in local_combined_providers_dict[provider_code]:
        (y0,x0)=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        (y1,x1)=gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
        if has_data((x0,y0,x1,y1),rlayer['extent_code']):
            data_found=True
            true_texture=(*texture[:-1],rlayer['layer_code'])
            (true_file_dir,true_file_name)=jpeg_file_name_from_attributes(lat,lon,*true_texture)
            if not os.path.isfile(os.path.join(true_file_dir,true_file_name)):
                vprint(1,"   Downloading missing orthophoto "+true_file_name+" (for combining in "+provider_code+")\n")
                build_jpeg_ortho(true_file_dir,true_file_name,*true_texture)
            else:
                vprint(1,"   The orthophoto "+true_file_name+" (for combining in "+provider_code+") is already present.\n")
    big_img=combine_textures(lat,lon,til_x_left,til_y_top,zoomlevel,provider_code)
    big_img.save(filename)
##############################################################################




##############################################################################
#  Le séquenceur de la phase de conversion jpeg -> dds.
##############################################################################
def convert_textures(lat,lon,build_dir,convert_queue):
    #global convert_queue,busy_slots_conv
    #busy_slots_conv=0
    nbr_done=0
    nbr_done_or_in=0
    if not os.path.exists(os.path.join(build_dir,'textures')):
            os.makedirs(os.path.join(build_dir,'textures'))
    finished = False
    while finished != True:
        if convert_queue == [] or busy_slots_conv >= max_convert_slots:
            time.sleep(3)
            try:
                if application.red_flag.get()==1:
                    print("Convert process interrupted.")
                    return
            except:
                pass
        elif convert_queue[0] != 'finished':
            texture=convert_queue.pop(0)
            file_name=dds_file_name_from_attributes(*texture)
            if not os.path.isfile(os.path.join(build_dir,'textures',file_name)):
                vprint(1,"   Converting orthophoto to build texture "+file_name+".")
                fargs_conv_text=[build_dir,lat,lon,*texture] 
                threading.Thread(target=convert_texture,args=fargs_conv_text).start()
                nbr_done+=1
                nbr_done_or_in+=1
            else:
                nbr_done_or_in+=1
                vprint(1,"   Texture file "+file_name+" already present.")
            try:
                application.progress_conv.set(int(100*nbr_done_or_in/(nbr_done_or_in+convert_queue.qsize()))) 
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
def point_params(lat,lon,lat0,lon0,pools_params,pool_cols,pool_rows):
    pool_x=int((lon-lon0)*pool_cols)
    pool_y=int((lat-lat0)*pool_rows)
    if pool_x==pool_rows:
        pool_x-=1
    if pool_y==pool_cols:
        pool_y-=1
    pool_idx=(pool_y)*(pool_cols)+(pool_x)
    pool_nx=int(round((lon-pools_params[pool_idx][1])/\
            pools_params[pool_idx][0]*65535))
    pool_ny=int(round((lat-pools_params[pool_idx][3])/\
            pools_params[pool_idx][2]*65535))
    return [pool_idx,pool_nx,pool_ny]
##############################################################################

##############################################################################
def ortho_list_to_ortho_dico(lat,lon,ortho_list):
        masks_im=Image.new("L",(4096,4096),'black')
        masks_draw=ImageDraw.Draw(masks_im)
        dico_tmp={}
        dico_customzl={}
        i=1
        for region in ortho_list[::-1]:
            dico_tmp[i]=(region[1],region[2])
            pol=[(int(round((x-lon)*4095)),int(round((lat+1-y)*4095))) for (x,y) in zip(region[0][1::2],region[0][::2])]
            print(pol)
            masks_draw.polygon(pol,fill=i)
            i+=1
        eps=1e-7 
        til_x_min,til_y_min=wgs84_to_texture(lat+1,lon,meshzl,'BI')
        til_x_max,til_y_max=wgs84_to_texture(lat,lon+1,meshzl,'BI')
        for til_x in numpy.arange(til_x_min,til_x_max+1,16):
            for til_y in numpy.arange(til_y_min,til_y_max+1,16):
                (latp,lonp)=gtile_to_wgs84(til_x+8,til_y+8,meshzl)
                lonp=max(min(lonp,lon+1),lon) 
                latp=max(min(latp,lat+1),lat) 
                (zoomlevel,provider_code)=dico_tmp[masks_im.getpixel((int(round((lonp-lon)*4095)),int(round((lat+1-latp)*4095))))]
                til_x_text=16*(int(til_x/2**(meshzl-int(zoomlevel)))//16)
                til_y_text=16*(int(til_y/2**(meshzl-int(zoomlevel)))//16)
                dico_customzl[(til_x,til_y)]=(til_x_text,til_y_text,int(zoomlevel),provider_code)
        return dico_customzl
##############################################################################
  


    
##############################################################################


##############################################################################
def build_dsf(lat0,lon0,ortho_list,water_overlay,\
        ratio_water,mesh_file_name,build_dir,download_queue):
    ####################################################################
    # The following is a simple web hit counter, it will count how much 
    # tiles are made by Ortho4XP. One aim is to get an idea of how much
    # we weight on OSM servers, the second is just curiosity.
    # Just comment the following lines if you do not wish your tiles
    # to be counted. 
    ####################################################################
    try:
        s=requests.Session()
        r=s.get("http://simplehitcounter.com/hit.php?uid=2163525&f=16777215&b=0",timeout=1)
        del(s)
        del(r)
    except:
        pass
    ######################################################

    dico_customzl=ortho_list_to_ortho_dico(lat0,lon0,ortho_list)
    tested_masks=skipped_masks=0

    pool_cols           = 16
    pool_rows           = 16
    pools_pts = pools_max_points
    dest_dir=os.path.join(build_dir,'Earth nav data',round_latlon(lat0,lon0))
    dsf_file_name=os.path.join(dest_dir,short_latlon(lat0,lon0)+'.dsf')
    
    print("-> Computing the required pool division") 
    found_division=False
    while not found_division:
        f_mesh=open(mesh_file_name,"r")
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
        vprint(2,"    Max points in a pool :",maxptpool)
        if maxptpool>=60000:
            print("     ",pool_rows,"too large.")
            pool_rows=pool_rows*2
            pool_cols=pool_cols*2
        elif maxptpool<=15000:
            print("     ",pool_rows,"unecessarilly small.")
            pool_rows=pool_rows//2
            pool_cols=pool_cols//2
            found_division=True 
        else:
            found_division=True 
        f_mesh.close()
    print("   Pool division = ",pool_rows)
    pool_nbr  = pool_rows*pool_cols
    pools_params=numpy.zeros((4*pool_nbr,18),'float32')
    #pools_params=numpy.zeros((pool_nbr,14),'float32')
    pools_planes=numpy.zeros(4*pool_nbr,'uint32')
    #pools_planes=numpy.zeros(2*pool_nbr,'uint32')
    pools_planes[0:pool_nbr]=7  # for points with s,t coords
    pools_planes[pool_nbr:2*pool_nbr]=5 # for X-Plane water
    pools_planes[2*pool_nbr:4*pool_nbr]=9 # for for points with s,t and border tex (masks)
    pools_lengths=numpy.zeros((4*pool_nbr),'uint32')
    try:
        pools=numpy.zeros((4*pool_nbr,9*pools_pts),'uint16')
        pools_z_temp=numpy.zeros((4*pool_nbr,pools_pts),'float32')
        pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
        pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
    except:
        try:
            pools_pts=pools_pts//2
            pools=numpy.zeros((4*pool_nbr,9*pools_pts),'uint16')
            pools_z_temp=numpy.zeros((4*pool_nbr,pools_pts),'float32')
            pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
            pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
            print("\nWARNING : Even though I won't use all of it, for speed purposes I must ")
            print("reserve an amount of RAM which you don't seem have available, I try")
            print("with half of it but it could be that the process has to stop.\n")
        except:
            try:
                pools_pts=pools_pts//2
                pools=numpy.zeros((4*pool_nbr,9*pools_pts),'uint16')
                pools_z_temp=numpy.zeros((4*pool_nbr,pools_pts),'float32')
                pools_z_max=-9999*numpy.ones(4*pool_nbr,'float32')
                pools_z_min=9999*numpy.ones(4*pool_nbr,'float32')
                print("\nWARNING : Even though I won't use all of it, for speed purposes I must ")
                print("reserve an amount of RAM which you don't seem have available, I try")
                print("with one fourth of it but it could be that the process has to stop.\n")
            except:
                return
    dico_new_pt={}
    textures={}
    dico_textures={}
    try:
        raster_map_im=Image.open(os.path.join(build_dir,'terrain_map_'+short_latlon(lat0,lon0)+'.png')).convert("L")
        raster_map_array=numpy.array(raster_map_im,dtype=numpy.uint8)
        try:
            raster_map_im_mult=Image.open(os.path.join(build_dir,'terrain_map_mult_'+short_latlon(lat0,lon0)+'.png')).convert("L")
            raster_map_array_mult=numpy.array(raster_map_im_mult,dtype=numpy.uint8)
            mult_draw=True
            #print("mult_draw")
        except:
            mult_draw=False
            #print("mult_draw")
        fin=open(build_dir+dir_sep+'PROP.atm','rb')
        bPROP=fin.read()
        fin.close()
        try:
            fin=open(build_dir+dir_sep+'TERT.atm','rb')
            bTERT=fin.read()
            fin.close()
        except:
            bTERT=b''
        try:
            fin=open(build_dir+dir_sep+'OBJT.atm','rb')
            bOBJT=fin.read()
            fin.close()
        except:
            bOBJT=b''
        try:
            fin=open(build_dir+dir_sep+'POLY.atm','rb')
            bPOLY=fin.read()
            fin.close()
        except:
            bPOLY=b''
        try:
            fin=open(build_dir+dir_sep+'NETW.atm','rb')
            bNETW=fin.read()
            fin.close()
        except:
            bNETW=b''
        try:
            fin=open(build_dir+dir_sep+'DEMN.atm','rb')
            bDEMN=fin.read()
            fin.close()
        except:
            bDEMN=b''
        fin=open(build_dir+dir_sep+'GEOD.atm','rb')
        bGEOD=fin.read()
        (nbr_pools_yet_in,)=struct.unpack('<I',bGEOD[-4:])
        #print(nbr_pools_yet_in)
        bGEOD=bGEOD[:-4]
        fin.close()
        try:
            fin=open(build_dir+dir_sep+'DEMS.atm','rb')
            bDEMS=fin.read()
            fin.close()
        except:
            bDEMS=b''
        fin=open(build_dir+dir_sep+'CMDS.atm','rb')
        bCMDS=fin.read()
        fin.close()
        dico_textures={}
        for i in range(len(bTERT.split(b'\0'))-1):
            dico_textures[str(i)]=i
            textures[i]=defaultdict(list)
    except:
        bPROP=bTERT=bOBJT=bPOLY=bNETW=bDEMN=bGEOD=bDEMS=bCMDS=b'' 
        nbr_pools_yet_in=0
        dico_textures={'terrain_Water':0,'None':1}
        bTERT=bytes("terrain_Water\0lib/g10/terrain10/fruit_tmp_wet_hill.ter\0",'ascii')
        textures[0]=defaultdict(list)
        textures[1]=defaultdict(list)
    #print(dico_textures) 
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
    
    f_mesh=open(mesh_file_name,"r")
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
    step_stones=nbr_tri_in//100+1
    if step_stones==0: step_stones=1
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
        [lon1,lat1,z1,u1,v1]=pt_in[5*n1:5*n1+5]
        [lon2,lat2,z2,u2,v2]=pt_in[5*n2:5*n2+5]
        [lon3,lat3,z3,u3,v3]=pt_in[5*n3:5*n3+5]
        if tri_type=='0':
            pass
        elif int(tri_type)>=4:
            tri_type='0'
        # TEST !!!!!!!!!!!!!!!!!
        #elif tri_type=='2' and abs(z1-z2)+abs(z2-z3) > 0.5*1e-5: 
        #    tri_type='0'  
        ####
        #texture=attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,dico_customzl,tri_type)
        bary_lat=(lat1+lat2+lat3)/3
        bary_lon=(lon1+lon2+lon3)/3
        texture=dico_customzl[wgs84_to_texture(bary_lat,bary_lon,meshzl,'BI')]
        #print(texture) 
        if False: #texture=='None':
            pixx=int(((lon1+lon2+lon3)/3-lon0)*raster_resolution)     
            pixy=int((lat0+1-(lat1+lat2+lat3)/3)*raster_resolution)
            #print(pixx,pixy)
            if not mult_draw:
                texture=str(raster_map_array[pixy,pixx])
            else:
                texture=str(raster_map_array[pixy,pixx]+256*raster_map_array_mult[pixy,pixx])
            #texture='0'
            #print(texture)
            #if texture=='terrain_Water': texture='None'
            #print(texture)    
            #print(tri_type) 
        # do we need to download a texture and/or to create a ter file ?       
        if (tri_type=='0'):
            if str(texture) in dico_textures: 
                texture_idx=dico_textures[str(texture)]
            else:
                texture_idx=len(dico_textures)
                dico_textures[str(texture)]=texture_idx
                textures[texture_idx]=defaultdict(list)
                file_name=dds_file_name_from_attributes(*texture)
                if ((str(texture)+'_overlay') not in dico_textures) and \
                           ((str(texture)+'_sea_overlay') not in dico_textures):
                    if not os.path.isfile(os.path.join(build_dir,'textures',file_name)):
                      if use_test_texture:
                        shutil.copyfile('test_texture.txt',os.path.join(build_dir,'textures',file_name))
                      else:  
                        if  'g2xpl' not in texture[3]:
                            download_queue.put(texture)
                        elif os.path.isfile(os.path.join(build_dir,'textures',file_name.replace('dds','partial.dds'))):
                            file_name=file_name.replace('dds','partial.dds')
                            vprint(1,"   Texture file "+file_name+" already present.")
                        else:
                            print("!!! Missing a required texture, conversion from g2xpl requires texture download !!!")
                            download_queue.put(texture)
                    else:
                        vprint(1,"   Texture file "+file_name+" already present.")
                create_terrain_file(build_dir,file_name[:-4],*texture)
                bTERT+=bytes('terrain/'+file_name[:-4]+'.ter\0','ascii') 
            texture_overlay_idx=-1
        elif water_option in [2,3]:
            texture_idx=0
            #if (tri_type=='1' and use_masks_for_inland==False) and (texture != 'None'):
            if len(texture)<4:
                texture_overlay_idx=-1
            elif ((tri_type=='1' and use_masks_for_inland==False) or (int(texture[2])<14 and sea_texture_params!=[])):
                if str(texture)+'_overlay' in dico_textures:
                    texture_overlay_idx=dico_textures[str(texture)+'_overlay']
                else:
                    texture_overlay_idx=len(dico_textures)
                    dico_textures[str(texture)+'_overlay']=texture_overlay_idx
                    textures[texture_overlay_idx]=defaultdict(list)
                    #print(texture)
                    file_name=dds_file_name_from_attributes(*texture)
                    if (str(texture) not in dico_textures) and \
                            ((str(texture)+'_sea_overlay') not in dico_textures):
                        if not os.path.isfile(os.path.join(build_dir,'textures',file_name)):
                          if use_test_texture:
                            shutil.copyfile('test_texture.dds',os.path.join(build_dir,'textures',file_name))
                          else:
                            if  'g2xpl' not in texture[3]:
                                download_queue.put(texture)
                            elif os.path.isfile(os.path.join(build_dir,'textures',file_name.replace('dds','partial.dds'))):
                                file_name=file_name.replace('dds','partial.dds')
                                vprint(1,"   Texture file "+file_name+" already present.")
                            else:
                                print("!!!!!!!!! Missing a required texture, conversion from g2xpl requires new textures !!!!!!!")
                                #download_queue.put(texture)
                        else:
                            vprint(1,"   Texture file "+file_name+" already present.")
                    create_overlay_file(build_dir,file_name[:-4],*texture)
                    bTERT+=bytes('terrain/'+file_name[:-4]+'_overlay.ter\0','ascii') 
            elif (tri_type in ['2','3'] or use_masks_for_inland==True) :
                if str(texture)+'_sea_overlay' in dico_textures:
                    texture_overlay_idx=dico_textures[str(texture)+'_sea_overlay']
                elif str(texture) not in skipped_sea_textures:
                    tested_masks+=1
                    #mask_data = which_mask(texture,lat0,lon0,maskszl)
                    #dico_mask[str(texture)]=mask_data
                    #if mask_data != 'None':
                    mask_im=needs_mask(*texture,maskszl)
                    if mask_im:
                        vprint(1,"      Use of an alpha mask.")
                        mask_im.save(os.path.join(build_dir,"textures",mask_file_name_from_attributes(*texture)))
                        #mask_name=mask_data[0].split(dir_sep)[-1]
                        #if not os.path.isfile(os.path.join(build_dir,'textures',mask_name)):
                        #    os.system(copy_cmd+' "'+mask_data[0]+'" "'+os.path.join(build_dir,'textures',mask_name)+'" '+devnull_rdir)
                        
                        texture_overlay_idx=len(dico_textures)
                        dico_textures[str(texture)+'_sea_overlay']=texture_overlay_idx
                        textures[texture_overlay_idx]=defaultdict(list)
                        file_name=dds_file_name_from_attributes(*texture)
                        if (str(texture) not in dico_textures) and \
                            ((str(texture)+'_overlay') not in dico_textures):
                            if not os.path.isfile(os.path.join(build_dir,'textures',file_name)):
                              if use_test_texture:
                                shutil.copyfile('test_texture.dds',os.path.join(build_dir,'textures',file_name))
                              else: 
                                if  'g2xpl' not in texture[3]:
                                    download_queue.put(texture)
                                elif os.path.isfile(os.path.join(build_dir,'textures',file_name.replace('dds','partial.dds'))):
                                    file_name=file_name+'.partial'
                                    vprint(1,"   Texture file "+file_name+" already present.")
                                else:
                                    print("!!!!!!!!! Missing a required texture, conversion from g2xpl requires new texture !!!!!!!")
                                    print(texture)
                                    download_queue.put(texture)
                            else:
                                vprint(1,"   Texture file "+file_name+" already present.")
                        #create_sea_overlay_file(build_dir,file_name[:-4],mask_name,*texture)
                        create_sea_overlay_file_new(build_dir,*texture)
                        bTERT+=bytes('terrain/'+file_name[:-4]+'_sea_overlay.ter\0','ascii') 
                    else:
                        try:
                            os.remove(os.path.join(build_dir,"textures",mask_file_name_from_attributes(*texture)))
                        except:
                            pass
                        skipped_masks+=1    
                        skipped_sea_textures.append(str(texture))
                        texture_overlay_idx=-1
                else:
                    texture_overlay_idx=-1
            else: 
                texture_overlay_idx=-1
        else:  # water_overlay = False
            texture_idx=0
            texture_overlay_idx=-1
        # now we put the tri in the right texture(s)   
        tri_p=[]
        if tri_type == '0':
            #continue
            for n in [n1,n3,n2]:     # beware of ordering for orientation ! 
                if str(n)+'_'+str(texture_idx) in dico_new_pt:
                    [pool_idx,pos_in_pool]=dico_new_pt[str(n)+'_'+str(texture_idx)]
                else:
                    [lon,lat,z,u,v]=pt_in[5*n:5*n+5]
                    #if type(texture) is list:
                    [s,t]=st_coord(lat,lon,*texture)
                    #else:
                    #    [s,t]=[0,0]
                    len_dico_new_pt+=1
                    [pool_idx,pool_nx,pool_ny]=point_params(lat,lon,lat0,lon0,\
                            pools_params,pool_cols,pool_rows)
                    pos_in_pool=pools_lengths[pool_idx]
                    dico_new_pt[str(n)+'_'+str(texture_idx)]=[pool_idx,pos_in_pool]
                    # BEWARE : normal coordinates are pointing (EAST,SOUTH) in X-Plane, not (EAST,NORTH) ! (cfr DSF specs), so v -> -v
                    pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                            pool_ny,0,round((1+normal_map_strength*u)/2*65535),round((1+normal_map_strength*(-v))/2*65535),\
                            round(s*65535),round(t*65535)]
                    # HACK !!!
                    #pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                    #        pool_ny,0,round((1+(lon-lon0))/2*65535),round((1+(lat-lat0))/2*65535),\
                    #        round(s*65535),round(t*65535)]
                    pools_z_temp[pool_idx,pos_in_pool]=z
                    pools_z_max[pool_idx] = pools_z_max[pool_idx] if pools_z_max[pool_idx] >= z else z
                    pools_z_min[pool_idx] = pools_z_min[pool_idx] if pools_z_min[pool_idx] <= z else z
                    pools_lengths[pool_idx]+=1
                    if pools_lengths[pool_idx]==pools_pts:
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
                    # HACK !!!
                    #pools[pool_idx,5*pos_in_pool:5*pos_in_pool+5]=[pool_nx,\
                    #        pool_ny,0,32768,32768]
                    pools[pool_idx,5*pos_in_pool:5*pos_in_pool+5]=[pool_nx,\
                            pool_ny,0,round((1+normal_map_strength*u)/2*65535),round((1+normal_map_strength*(-v))/2*65535)]
                    pools_z_temp[pool_idx,pos_in_pool]=z
                    pools_z_max[pool_idx] = pools_z_max[pool_idx] if pools_z_max[pool_idx] >= z else z
                    pools_z_min[pool_idx] = pools_z_min[pool_idx] if pools_z_min[pool_idx] <= z else z
                    pools_lengths[pool_idx]+=1
                    if pools_lengths[pool_idx]==pools_pts:
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
            if texture_overlay_idx!=-1 and ((tri_type=='1'and use_masks_for_inland==False) or int(texture[2])<14):
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
                        # HACK !!!
                        #pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=\
                        #        [pool_nx,pool_ny,0,32768,32768,round(s*65535),\
                        #         round(t*65535),0,round(ratio_water*65535)]
                        pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=\
                                [pool_nx,pool_ny,0,round((1+normal_map_strength*u)/2*65535),round((1+normal_map_strength*(-v))/2*65535),round(s*65535),\
                                 round(t*65535),0,round(ratio_water*65535)]
                        pools_z_temp[pool_idx,pos_in_pool]=z
                        pools_z_max[pool_idx] = pools_z_max[pool_idx] \
                                      if pools_z_max[pool_idx] >= z else z
                        pools_z_min[pool_idx] = pools_z_min[pool_idx] \
                                      if pools_z_min[pool_idx] <= z else z
                        pools_lengths[pool_idx]+=1
                        if pools_lengths[pool_idx]==pools_pts:
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
                        #mask_data=dico_mask[str(texture)]
                        #rx=float(mask_data[2])
                        #ry=float(mask_data[3])
                        #factor=float(mask_data[1])
                        #bs=rx/factor+ms/factor
                        #bt=1-ry/factor+(mt-1)/factor
                        # HACK !!!
                        #pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=[pool_nx,\
                        #          pool_ny,0,32768,32768,round(s*65535),round(t*65535),\
                        #          round(bs*65535),round(bt*65535)]
                        #pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=[pool_nx,\
                        #          pool_ny,0,round((1+normal_map_strength*u)/2*65535),round((1+normal_map_strength*v)/2*65535),round(s*65535),round(t*65535),\
                        #          round(bs*65535),round(bt*65535)]
                        pools[pool_idx,9*pos_in_pool:9*pos_in_pool+9]=[pool_nx,\
                                  pool_ny,0,round((1+normal_map_strength*u)/2*65535),round((1+normal_map_strength*(-v))/2*65535),round(s*65535),round(t*65535),\
                                  round(s*65535),round(t*65535)]
                        pools_z_temp[pool_idx,pos_in_pool]=z
                        pools_z_max[pool_idx] = pools_z_max[pool_idx]\
                                        if pools_z_max[pool_idx] >= z else z
                        pools_z_min[pool_idx] = pools_z_min[pool_idx] \
                                        if pools_z_min[pool_idx] <= z else z
                        pools_lengths[pool_idx]+=1
                        if pools_lengths[pool_idx]==pools_pts:
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
    vprint(2,"(",tested_masks,",",skipped_masks,")")
    for _ in range(max_convert_slots):
        download_queue.put('quit')
    os.system(copy_cmd+' "'+Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
             'water_transition.png'+'" "'+build_dir+dir_sep+'textures'+\
              dir_sep+'" '+devnull_rdir) 
    print("  Encoding of the DSF file...")  
    vprint(1,"   Final nbr of points : "+str(len_dico_new_pt))
    vprint(1,"   Final nbr of cross pool tris: "+str(total_cross_pool))
    #for i in range(0,pool_nbr):
        #print(pools_lengths[i])
        #if pools_lengths[i]>=35000 and pool_cols==32:
        #    print("A suspicious number (although non blocking) nbr of points was found\n"+\
        #          "in the zone centered in lat=",pools_params[i,3]+0.5*pools_params[i,2],\
        #          " lon=",pools_params[i,1]+0.5*pools_params[i,0]," : ",pools_lengths[i],".")
        #    print("That could be related to an OSM error, but also to a too large number of")
        #    print("triangles due to a too low value of the parameter curv_tol (cfr log in Step 2).")
    for pool_idx in range(0,4*pool_nbr):
        # BEWARE use the same scal and offset for pools located on the same place but differing only by their number of coordinates
        pool_idx_group=(pool_idx % pool_nbr, pool_idx % pool_nbr + pool_nbr , pool_idx % pool_nbr + 2*pool_nbr, pool_idx % pool_nbr + 3* pool_nbr)
        altmin=min((pools_z_min[gidx] for gidx in pool_idx_group))*100000
        altmax=max((pools_z_max[gidx] for gidx in pool_idx_group))*100000
        if altmax-altmin < 770:
            scale=771   # 65535= 771*85
            inv_stp=85
        elif altmax-altmin < 1284:
            scale=1285 # 66535=1285*51
            inv_stp=51
        elif altmax-altmin < 4368:
            scale=4369 # 65535=4369*15
            inv_stp=15
        else:
            scale=13107
            inv_stp=5
        #scale=4369
        #inv_stp=15
        pools_params[pool_idx,4]=scale
        pools_params[pool_idx,5]=floor(altmin)
        for pos_in_pool in range(0,pools_lengths[pool_idx]):
            pools[pool_idx,pools_planes[pool_idx]*pos_in_pool+2]=int(round((pools_z_temp[pool_idx,\
                    pos_in_pool]*100000-pools_params[pool_idx,5])*inv_stp))

    # Now is time to write our DSF to disk, the exact binary format is described on the wiki
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    if os.path.exists(dest_dir+dir_sep+dsf_file_name+'.dsf'):
        os.system(copy_cmd+' "'+dest_dir+dir_sep+dsf_file+'.dsf'+'" "'+\
         dest_dir+dir_sep+dsf_file+'.dsf.bak" '+devnull_rdir)
    
    if bPROP==b'':
        bPROP=bytes("sim/west\0"+str(lon0)+"\0"+"sim/east\0"+str(lon0+1)+"\0"+\
               "sim/south\0"+str(lat0)+"\0"+"sim/north\0"+str(lat0+1)+"\0"+\
               "sim/creation_agent\0"+"Ortho4XP\0",'ascii')
    else:
        bPROP+=b'sim/creation_agent\0Patched by Ortho4XP\0'
      

    # Computation of intermediate and of total length 
    size_of_head_atom=16+len(bPROP)
    size_of_prop_atom=8+len(bPROP)
    size_of_defn_atom=48+len(bTERT)+len(bOBJT)+len(bPOLY)+len(bNETW)+len(bDEMN)
    size_of_geod_atom=8+len(bGEOD)
    for k in range(0,4*pool_nbr):
        if pools_lengths[k]>0:
            size_of_geod_atom+=21+pools_planes[k]*(9+2*pools_lengths[k])
    vprint(1,"   Size of DEFN atom : "+str(size_of_defn_atom)+" bytes.")    
    vprint(1,"   Size of GEOD atom : "+str(size_of_geod_atom)+" bytes.")    
    f=open(dsf_file_name,'wb')
    f.write(b'XPLNEDSF')
    f.write(struct.pack('<I',1))
    
    # Head super-atom
    f.write(b"DAEH")
    f.write(struct.pack('<I',size_of_head_atom))
    f.write(b"PORP")
    f.write(struct.pack('<I',size_of_prop_atom))
    f.write(bPROP)
    
    # Definitions super-atom
    f.write(b"NFED")
    f.write(struct.pack('<I',size_of_defn_atom))
    f.write(b"TRET")
    f.write(struct.pack('<I',8+len(bTERT)))
    f.write(bTERT)
    f.write(b"TJBO")
    f.write(struct.pack('<I',8+len(bOBJT)))
    f.write(bOBJT)
    f.write(b"YLOP")
    f.write(struct.pack('<I',8+len(bPOLY)))
    f.write(bPOLY)
    f.write(b"WTEN")
    f.write(struct.pack('<I',8+len(bNETW)))
    f.write(bNETW)
    f.write(b"NMED")
    f.write(struct.pack('<I',8+len(bDEMN)))
    f.write(bDEMN)
    
    # Geodata super-atom
    f.write(b"DOEG")
    f.write(struct.pack('<I',size_of_geod_atom))
    f.write(bGEOD)
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
    # Since we possibly skipped some pools, and since we possibly
    # get pools from elsewhere, we rebuild a dico
    # which tells the pool position in the dsf of a pool prior
    # to the stripping :

    dico_new_pool={}
    new_pool_idx=nbr_pools_yet_in
    for k in range(0,4*pool_nbr):
        if pools_lengths[k] != 0:
            dico_new_pool[k]=new_pool_idx
            new_pool_idx+=1

    # DEMS atom
    if bDEMS!=b'':
        f.write(b"SMED")
        f.write(struct.pack('<I',8+len(bDEMS)))
        f.write(bDEMS)

    # Commands atom
    
    # we first compute its size :
    size_of_cmds_atom=8+len(bCMDS)
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
    vprint(1,"   Size of CMDS atom : "+str(size_of_cmds_atom)+" bytes.")
    f.write(b'SDMC')                               # CMDS header 
    f.write(struct.pack('<I',size_of_cmds_atom))   # CMDS length
    f.write(bCMDS)
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
                    flag=2 #overlay
                    break
            else:
                if pools_planes[textures[texture_idx]['cross-pool'][0]]==9:
                    flag=2
                    break
        lod=-1 if flag==1 else overlay_lod
        for pool_idx in textures[texture_idx]:
            #print("  pool_idx = "+str(pool_idx))
            if pool_idx != 'cross-pool':
                f.write(struct.pack('<B',1))                          # POOL SELECT
                f.write(struct.pack('<H',dico_new_pool[pool_idx]))    # POOL INDEX
    
                f.write(struct.pack('<B',18))    # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack('<B',flag))  # FLAG
                f.write(struct.pack('<f',0))     # NEAR LOD
                f.write(struct.pack('<f',lod))    # FAR LOD
                
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
                f.write(struct.pack('<f',lod))  # FAR LOD
                
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
    f=open(dsf_file_name,'rb')
    data=f.read()
    m=hashlib.md5()
    m.update(data)
    #print(str(m.digest_size))
    md5sum=m.digest()
    #print(str(md5sum))
    f.close()
    f=open(dsf_file_name,'ab')
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
    pool_idx=(pool_y)*(pool_cols)+(pool_x)
    pool_nx=int(round((lon-pools_params[pool_idx][1])/\
            pools_params[pool_idx][0]*65535))
    pool_ny=int(round((lat-pools_params[pool_idx][3])/\
            pools_params[pool_idx][2]*65535))
    return [pool_idx,pool_nx,pool_ny]
##############################################################################

####
#Test
####
def build_pools_params(lat0,lon0,pool_cols,pool_rows):
    pool_nbr=pool_rows*pool_cols
    pools_params=numpy.zeros((4*pool_nbr,18),'float32')
    for pool_y in range(0,pool_rows):       
        for pool_x in range(0,pool_cols):  
            pool_idx=(pool_y)*pool_cols+(pool_x)
            pools_params[pool_idx,0]=1/pool_cols*(65536/65535)
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
    return pools_params


def build_tile(lat,lon,build_dir,mesh_file_name,check_for_what_next=True):
    set_flag(0)
    timer=time.time()
    try:
        del(application.dem)
    except:
        pass
    download_queue=queue.Queue()
    convert_queue=queue.Queue()
    download_progress={'bar':application.progress_down,'done':0}
    convert_progress={'bar':application.progress_conv,'done':0}
    initialize_local_combined_providers_dict(lat,lon,ortho_list)
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    if clean_unused_dds_and_ter_files==True:
        print("Purging old .ter files")
        if os.path.exists(build_dir+dir_sep+'terrain'):
            for oldterfile in os.listdir(build_dir+dir_sep+'terrain'):
                os.remove(build_dir+dir_sep+'terrain'+dir_sep+oldterfile)
    fargs_dsf=[lat,lon,ortho_list,\
            water_overlay,ratio_water,mesh_file_name,build_dir,download_queue] 
    build_dsf_thread=threading.Thread(target=build_dsf,args=fargs_dsf)
    fargs_down=[lat,lon,build_dir,download_queue,convert_queue,download_progress]
    download_thread=threading.Thread(target=download_textures,args=fargs_down)
    try:
        application.red_flag.set(0)
        application.progress_attr.set(0) 
        application.progress_down.set(0) 
        application.progress_conv.set(0) 
    except:
        pass
    print("Start of the texture attribution process...")
    build_dsf_thread.start()
    #build_dsf_thread.join()
    if not skip_downloads:
        download_thread.start()
        if not skip_converts:
            if not os.path.exists(os.path.join(build_dir,'textures')):
                os.makedirs(os.path.join(build_dir,'textures'))
            convert_workers=parallel_launch(convert_texture,convert_queue,max_convert_slots,convert_progress)
    build_dsf_thread.join()
    if not skip_downloads:
        download_queue.put('quit')
        download_thread.join()
        if download_progress['done']>=1: print("  Download of textures completed. ")
        if not skip_converts:
            for _ in range(max_convert_slots):
                convert_queue.put('quit')
            parallel_join(convert_workers) 
            if convert_progress['done']>=1: print("  DDS conversion of textures completed. ")
    try:
        if application.red_flag.get()==1:
            return
    except:
        pass
    if clean_unused_dds_and_ter_files and os.path.isdir(build_dir+dir_sep+'textures'):
        print("-> Purging non necessary .dds files")
        for oldfile_name in os.listdir(build_dir+dir_sep+'textures'):
            try:
                [oldfile_namebase,oldfile_nameext]=oldfile_name.split('.')
            except:
                continue
            if oldfile_nameext!='dds':
                    continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfile_namebase+'.ter'):
                continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfile_namebase+'_overlay.ter'):
                continue
            if os.path.isfile(build_dir+dir_sep+'terrain'+dir_sep+oldfile_namebase+'_sea_overlay.ter'):
                continue
            # if we have reached here we are facing a dds which is no longer need and therefore we delete it
            print("  -> removing "+oldfile_name)
            os.remove(build_dir+dir_sep+'textures'+dir_sep+oldfile_name)
    if clean_tmp_files:
        clean_temporary_files(build_dir,['POLY','ELE'])                                                 
    else:
        pass
        #clean_temporary_files(build_dir,['ELE'])
    timings_and_bottom_line(timer)
    try:
        if not check_for_what_next:
            return
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
    terrain_list=[]
    line=f.readline()
    g.write('PROPERTY sim/overlay 1\n')
    while line!='':
        if 'PROPERTY' in line:
            g.write(line)
        elif 'TERRAIN_DEF' in line:
            terrain_list.append(line.split()[1])
        elif 'POLYGON_DEF' in line:
            g.write(line)
        elif 'NETWORK_DEF' in line:
            g.write(line)
        elif 'BEGIN_POLYGON 0' in line:
            while 'END_POLYGON' not in line:
                line=f.readline()
        elif 'BEGIN_POLYGON' in line:
            while 'END_POLYGON' not in line:
                #g.write(line)
                g.write(line)
                line=f.readline()
            #g.write(line)
            g.write(line)
        elif 'BEGIN_SEGMENT' in line:
            while 'END_SEGMENT' not in line:
                g.write(line)
                line=f.readline()
            g.write(line)
        elif 'BEGIN_PATCH' in line:
            items=line.split()
            overlay_flag=True if items[-2]=='2' else False
            terrain_type=int(items[1])
            overlay_flag=True #!!! DISABLED ON PURPOSE !!!
        elif 'BEGIN_PRIMITIVE' in line:
            if overlay_flag: 
                while 'END_PRIMITIVE' not in line:
                    line=f.readline()
            else:
                primitive_type=line.split()[1] 
                if primitive_type=='0':
                    while True:
                        line=f.readline()
                        if 'END_PRIMITIVE' in line: break
                        [lon1,lat1]=line.split()[1:3]
                        line=f.readline()
                        [lon2,lat2]=line.split()[1:3]
                        line=f.readline()
                        [lon3,lat3]=line.split()[1:3]
                        px1=int((float(lon1)-lon)*raster_resolution)
                        px2=int((float(lon2)-lon)*raster_resolution)
                        px3=int((float(lon3)-lon)*raster_resolution)
                        py1=int((lat+1-float(lat1))*raster_resolution)
                        py2=int((lat+1-float(lat2))*raster_resolution)
                        py3=int((lat+1-float(lat3))*raster_resolution)
                        terrain_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill=terrain_type)
                elif primitive_type=='1':
                    line=f.readline()
                    [lon1,lat1]=line.split()[1:3]
                    line=f.readline()
                    [lon2,lat2]=line.split()[1:3]
                    while True:
                        line=f.readline() 
                        if 'END_PRIMITIVE' in line: break
                        [lon3,lat3]=line.split()[1:3]
                        px1=int((float(lon1)-lon)*raster_resolution)
                        px2=int((float(lon2)-lon)*raster_resolution)
                        px3=int((float(lon3)-lon)*raster_resolution)
                        py1=int((lat+1-float(lat1))*raster_resolution)
                        py2=int((lat+1-float(lat2))*raster_resolution)
                        py3=int((lat+1-float(lat3))*raster_resolution)
                        terrain_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill=terrain_type)
                        [lon1,lat1]=[lon2,lat2]
                        [lon2,lat2]=[lon3,lat3]
                else:
                    print("Oscar, you need to encode type 2 primitives as well !!!!!!!!!!!!!!!!!!")
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
    #h=open(dest_dir+dir_sep+'terrain_list_'+strlat+strlon+'.txt','w')
    #for terrain in terrain_list:
    #    h.write(terrain+'\n')
    #h.close()
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
def build_masks(lat,lon,build_dir,mesh_file_name_list,masks_zl=14):
    if legacy_masks:
        build_masks_legacy(lat,lon,build_dir,mesh_file_name_list)
        return 
    t4=time.time()
    try:
        application.red_flag.set(0)
    except:
        pass
    
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    dico_masks={}
    masks_dir=Ortho4XP_dir+dir_sep+"Masks"+dir_sep+strlat+strlon
    if not os.path.exists(masks_dir):
        os.makedirs(masks_dir)
    
    [til_x_min,til_y_min]=wgs84_to_texture(lat+1,lon,masks_zl,'BI')
    [til_x_max,til_y_max]=wgs84_to_texture(lat,lon+1,masks_zl,'BI')
    
    print("Deleting existing masks.")
    for til_x in range(til_x_min,til_x_max+1,16):
        for til_y in range(til_y_min,til_y_max+1,16):
            try:
                os.remove(masks_dir+dir_sep+str(til_y)+'_'+str(til_x)+'.png')
            except:
                pass
            try:
                os.remove(build_dir+dir_sep+'textures'+dir_sep+str(til_y)+'_'+str(til_x)+'.png')
            except:
                pass

    for mesh_file_name in mesh_file_name_list:
        try:
            f_mesh=open(mesh_file_name,"r")
        except:
            print("Mesh file ",mesh_file_name," absent.")
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
        print(" Attribution process of masks buffers to water triangles for "+str(mesh_file_name))
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
            if not (tri_type in ['2','3']) and not(tri_type=='1' and use_masks_for_inland):
            #if not tri_type in ('1','2','3'):
                continue
            [lon1,lat1]=pt_in[5*n1:5*n1+2]
            [lon2,lat2]=pt_in[5*n2:5*n2+2]
            [lon3,lat3]=pt_in[5*n3:5*n3+2]
            bary_lat=(lat1+lat2+lat3)/3
            bary_lon=(lon1+lon2+lon3)/3
            [til_x,til_y]=wgs84_to_texture(bary_lat,bary_lon,masks_zl,'BI')
            if til_x < til_x_min-16 or til_x > til_x_max+16 or til_y < til_y_min-16 or til_y>til_y_max+16:
                continue
            [til_x2,til_y2]=wgs84_to_texture(bary_lat,bary_lon,masks_zl+2,'BI')
            a=(til_x2//16)%4
            b=(til_y2//16)%4
            if str(til_x)+'_'+str(til_y) in dico_masks:
                dico_masks[str(til_x)+'_'+str(til_y)].append([lat1,lon1,lat2,lon2,lat3,lon3])
            else:
                dico_masks[str(til_x)+'_'+str(til_y)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
            if a==0: 
                if str(til_x-16)+'_'+str(til_y) in dico_masks:
                    dico_masks[str(til_x-16)+'_'+str(til_y)].append([lat1,lon1,lat2,lon2,lat3,lon3])
                else:
                    dico_masks[str(til_x-16)+'_'+str(til_y)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
                if b==0: 
                    if str(til_x-16)+'_'+str(til_y-16) in dico_masks:
                        dico_masks[str(til_x-16)+'_'+str(til_y-16)].append([lat1,lon1,lat2,lon2,lat3,lon3])
                    else:
                        dico_masks[str(til_x-16)+'_'+str(til_y-16)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
                elif b==3:
                    if str(til_x-16)+'_'+str(til_y+16) in dico_masks:
                        dico_masks[str(til_x-16)+'_'+str(til_y+16)].append([lat1,lon1,lat2,lon2,lat3,lon3])
                    else:
                        dico_masks[str(til_x-16)+'_'+str(til_y+16)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
            elif a==3:
                if str(til_x+16)+'_'+str(til_y) in dico_masks:
                    dico_masks[str(til_x+16)+'_'+str(til_y)].append([lat1,lon1,lat2,lon2,lat3,lon3])
                else:
                    dico_masks[str(til_x+16)+'_'+str(til_y)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
                if b==0: 
                    if str(til_x+16)+'_'+str(til_y-16) in dico_masks:
                        dico_masks[str(til_x+16)+'_'+str(til_y-16)].append([lat1,lon1,lat2,lon2,lat3,lon3])
                    else:
                        dico_masks[str(til_x+16)+'_'+str(til_y-16)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
                elif b==3:
                    if str(til_x+16)+'_'+str(til_y+16) in dico_masks:
                        dico_masks[str(til_x+16)+'_'+str(til_y+16)].append([lat1,lon1,lat2,lon2,lat3,lon3])
                    else:
                        dico_masks[str(til_x+16)+'_'+str(til_y+16)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
            if b==0: 
                if str(til_x)+'_'+str(til_y-16) in dico_masks:
                    dico_masks[str(til_x)+'_'+str(til_y-16)].append([lat1,lon1,lat2,lon2,lat3,lon3])
                else:
                    dico_masks[str(til_x)+'_'+str(til_y-16)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
            elif b==3:
                if str(til_x)+'_'+str(til_y+16) in dico_masks:
                    dico_masks[str(til_x)+'_'+str(til_y+16)].append([lat1,lon1,lat2,lon2,lat3,lon3])
                else:
                    dico_masks[str(til_x)+'_'+str(til_y+16)]=[[lat1,lon1,lat2,lon2,lat3,lon3]]
        f_mesh.close()
        if not use_masks_for_inland:
            print(" Adding inland water near shoreline")
            f_mesh=open(mesh_file_name,"r")
            for i in range(0,4):
                f_mesh.readline()
            nbr_pt_in=int(f_mesh.readline())
            for i in range(0,nbr_pt_in):
                f_mesh.readline()
            for i in range(0,3):
                f_mesh.readline()
            for i in range(0,nbr_pt_in):
                f_mesh.readline()
            for i in range(0,2): # skip 2 lines
                f_mesh.readline()
            nbr_tri_in=int(f_mesh.readline()) # read nbr of tris
            step_stones=nbr_tri_in//100
            percent=-1
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
                if (not tri_type=='1'):
                    continue
                [lon1,lat1]=pt_in[5*n1:5*n1+2]
                [lon2,lat2]=pt_in[5*n2:5*n2+2]
                [lon3,lat3]=pt_in[5*n3:5*n3+2]
                bary_lat=(lat1+lat2+lat3)/3
                bary_lon=(lon1+lon2+lon3)/3
                [til_x,til_y]=wgs84_to_texture(bary_lat,bary_lon,masks_zl,'BI')
                if til_x < til_x_min-16 or til_x > til_x_max+16 or til_y < til_y_min-16 or til_y>til_y_max+16:
                    continue
                [til_x2,til_y2]=wgs84_to_texture(bary_lat,bary_lon,masks_zl+2,'BI')
                a=(til_x2//16)%4
                b=(til_y2//16)%4
                if str(til_x)+'_'+str(til_y) in dico_masks:
                    dico_masks[str(til_x)+'_'+str(til_y)].append([lat1,lon1,lat2,lon2,lat3,lon3])
            f_mesh.close()
    print(" Construction of the masks")
    if use_DEM_too_for_masks:
        try:
            dem=application.dem
            print('-> Recycling elevation data.')
        except:
            try: 
                print('-> Loading of elevation data.')
                application.dem=DEM(lat,lon,application.cde.get())
                dem=application.dem
            except Exception as e:
                print('  -> failed, reverting to default.')
                vprint(2,e)
                application.dem=DEM(lat,lon)
                dem=application.dem
    
    transin=30
    midzone=30
    transout=80
    shore_level=254
    sea_level=80
    def transition_profile(ratio,ttype):
        if ttype=='spline':
            return 3*ratio**2-2*ratio**3
        elif ttype=='linear':
            return ratio
        elif ttype=='parabolic':
            return 2*ratio-ratio**2
    
    task_len=len(dico_masks)
    task_done=0
    for mask in dico_masks:
        task_done+=1
        try:
            application.progress_attr.set(50+int(49*task_done/task_len))
            if application.red_flag.get()==1:
                print("Masks construction process interrupted.")
                return
        except:
            pass
        [til_x,til_y]=[int(z) for z in mask.split('_')]
        if til_x<til_x_min or til_x>til_x_max or til_y<til_y_min or til_y>til_y_max:
            continue
        [latm0,lonm0]=gtile_to_wgs84(til_x,til_y,masks_zl)
        [px0,py0]=wgs84_to_pix(latm0,lonm0,masks_zl)
        px0-=1024
        py0-=1024
        masks_im=Image.new("1",(4096+2*1024,4096+2*1024),'black')
        masks_draw=ImageDraw.Draw(masks_im)
        for mesh_file_name in mesh_file_name_list:
            latlonstr=mesh_file_name.split('.mes')[-2][-7:]
            lathere=int(latlonstr[0:3])
            lonhere=int(latlonstr[3:7]) 
            print(lathere,lonhere)
            [px1,py1]=wgs84_to_pix(lathere,lonhere,masks_zl)
            [px2,py2]=wgs84_to_pix(lathere,lonhere+1,masks_zl)
            [px3,py3]=wgs84_to_pix(lathere+1,lonhere+1,masks_zl)
            [px4,py4]=wgs84_to_pix(lathere+1,lonhere,masks_zl)
            px1-=px0
            px2-=px0
            px3-=px0
            px4-=px0
            py1-=py0
            py2-=py0
            py3-=py0
            py4-=py0
            try:
                masks_draw.polygon([(px1,py1),(px2,py2),(px3,py3),(px4,py4)],fill='white')
            except:
                print("failed to draw rectangle")
                pass
        for [lat1,lon1,lat2,lon2,lat3,lon3] in dico_masks[mask]:
            [px1,py1]=wgs84_to_pix(lat1,lon1,masks_zl)
            [px2,py2]=wgs84_to_pix(lat2,lon2,masks_zl)
            [px3,py3]=wgs84_to_pix(lat3,lon3,masks_zl)
            px1-=px0
            px2-=px0
            px3-=px0
            py1-=py0
            py2-=py0
            py3-=py0
            try:
                masks_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill='black')
            except:
                pass
        del(masks_draw)
        masks_im=masks_im.convert("L") 
        img_array=numpy.array(masks_im,dtype=numpy.uint8)
        
        if use_DEM_too_for_masks:
            #computing the part of the mask coming from the DEM: 
            (latmax,lonmin)= pix_to_wgs84(px0,py0,masks_zl)
            (latmin,lonmax)= pix_to_wgs84(px0+6144,py0+6144,masks_zl)
            (x03857,y03857)=pyproj.transform(epsg['4326'],epsg['3857'],lonmin,latmax)
            (x13857,y13857)=pyproj.transform(epsg['4326'],epsg['3857'],lonmax,latmin)
            ((lonmin,lonmax,latmin,latmax),demim4326)=dem.super_level_set(1,(lonmin,lonmax,latmin,latmax))  
            s_bbox=(lonmin,latmax,lonmax,latmin)
            t_bbox=(x03857,y03857,x13857,y13857)
            demim3857=gdalwarp_alternative(s_bbox,'4326',demim4326,t_bbox,'3857',(6144,6144))
            demim3857=demim3857.filter(ImageFilter.GaussianBlur(0.3*2**(masks_zl-14))) # slight increase of area
            mask_array=(numpy.array(demim3857,dtype=numpy.uint8)>0).astype(numpy.uint8)*255
            del(demim3857)
            del(demim4326)
            img_array=numpy.maximum(img_array,mask_array)

        
        extent_masks=False
        extent_code='APL_Mont-Saint-Michel'
        mask_array=numpy.zeros((4096,4096),dtype=numpy.uint8)
        if extent_masks:
            (latm1,lonm1)=gtile_to_wgs84(til_x+16,til_y+16,masks_zl)
            bbox_4326=(lonm0,latm0,lonm1,latm1)
            masks_im=has_data(bbox_4326,extent_code,True,mask_size=(4096,4096),is_sharp_resize=False,is_mask_layer=False)
            if masks_im:
                mask_array=(numpy.array(masks_im,dtype=numpy.uint8)*(sea_level/255)).astype(numpy.uint8)

        
        if (img_array.max()==0) and (mask_array.max()==0): # or img_array.min()==255):
            print("   Skipping "+str(til_y)+'_'+str(til_x)+'.png')
            continue
        else:
            print("   Creating "+str(til_y)+'_'+str(til_x)+'.png')
       

        # Blur of the mask
        mask_choice=1
        if mask_choice==1:
            b_img_array=b_mask_array=numpy.array(img_array)
            # First the transition at the shore
            # We go from shore_level to sea_level in transin meters
            stepsin=int(transin*2**(masks_zl-14)/(10*cos(lat*pi/180))/3)
            for i in range(stepsin):
                value=shore_level+transition_profile((i+1)/stepsin,'parabolic')*(sea_level-shore_level)
                b_mask_array=(numpy.array(Image.fromarray(b_mask_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(1)),dtype=numpy.uint8)>0).astype(numpy.uint8)*255
                b_img_array[(b_img_array==0)*(b_mask_array!=0)]=value
                print(value)
            # Next the intermediate zone at constant transparency
            sea_b_radius=(midzone*2**(masks_zl-14)/(10*cos(lat*pi/180)))/3
            sea_b_radius_buffered=(1.5*(midzone+transout)*2**(masks_zl-14)/(10*cos(lat*pi/180)))/3
            b_mask_array=(numpy.array(Image.fromarray(b_mask_array).convert("L").\
                filter(ImageFilter.GaussianBlur(sea_b_radius_buffered)),dtype=numpy.uint8)>0).astype(numpy.uint8)*255
            b_mask_array=(numpy.array(Image.fromarray(b_mask_array).convert("L").\
                filter(ImageFilter.GaussianBlur(sea_b_radius_buffered-sea_b_radius)),dtype=numpy.uint8)==255).astype(numpy.uint8)*255
            b_img_array[(b_img_array==0)*(b_mask_array!=0)]=sea_level
            # Finally the transition to the X-Plane sea
            # We go from sea_level to 0 in transout meters
            stepsout=int(transout*2**(masks_zl-14)/(10*cos(lat*pi/180))/3)  
            for i in range(stepsout):
                value=sea_level*(1-transition_profile((i+1)/stepsout,'linear'))
                b_mask_array=(numpy.array(Image.fromarray(b_mask_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(1)),dtype=numpy.uint8)>0).astype(numpy.uint8)*255
                b_img_array[(b_img_array==0)*(b_mask_array!=0)]=value
                print(value)
            # To smoothen the thresolding introduced above we do a global short extent gaussian blur
            b_img_array=numpy.array(Image.fromarray(b_img_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(2)),dtype=numpy.uint8)
        elif mask_choice==2:
            b_img_array=(numpy.array(Image.fromarray(img_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(masks_width/1.7)),dtype=numpy.uint8)>0).astype(numpy.uint8)*255
            #blur it
            b_img_array=numpy.array(Image.fromarray(b_img_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(masks_width)),dtype=numpy.uint8)
            #nonlinear transform to make the transition quicker at the shore (gaussian is too flat) 
            gamma=2.5
            b_img_array=(((numpy.tan((b_img_array.astype(numpy.float32)-127.5)/128*atan(3))-numpy.tan(-127.5/128*atan(3)))\
                    *254/(2*numpy.tan(127.5/128*atan(3))))**gamma/(255**(gamma-1))).astype(numpy.uint8)
            b_img_array=numpy.minimum(b_img_array,200)
            #still some slight smoothing at the shore
            b_img_array=numpy.maximum(b_img_array,numpy.array(Image.fromarray(img_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(2**(masks_zl-14))),dtype=numpy.uint8))
        elif mask_choice==3:
            kernel=numpy.array(range(1,2*masks_width))
            kernel[masks_width:]=range(masks_width-1,0,-1)
            kernel=kernel/masks_width**2
            for i in range(0,len(img_array)):
                img_array[i]=numpy.convolve(img_array[i],kernel,'same')
            img_array=img_array.transpose() 
            for i in range(0,len(img_array)):
                img_array[i]=numpy.convolve(img_array[i],kernel,'same')
            img_array=img_array.transpose()
            img_array=2*numpy.minimum(img_array,120) #*numpy.ones(img_array.shape)) 
            img_array=numpy.array(img_array,dtype=numpy.uint8)
        
        # Ensure land is kept to 255 on the mask to avoid unecessary ones, crop to final size, and take the
        # max with the possible sea extent mask
        img_array=numpy.maximum(img_array,b_img_array)[1024:4096+1024,1024:4096+1024]
        img_array=numpy.maximum(img_array,mask_array)

        if not (img_array.max()==0 or img_array.min()==255):
            #print("Writing ",str(til_y)+'_'+str(til_x)+'.png')

            masks_im=Image.fromarray(img_array)  #.filter(ImageFilter.GaussianBlur(3))
            #alpha_mask=masks_im.split()[-1]
            masks_im.save(masks_dir+dir_sep+str(til_y)+'_'+str(til_x)+'.png')
            masks_im.save(build_dir+dir_sep+'textures'+dir_sep+str(til_y)+'_'+str(til_x)+'.png')
            #masks_im=Image.new('RGBA',(4096,4096),(0,0,0,0))
            #masks_im.paste(alpha_mask,mask=alpha_mask)
            #masks_im.save(build_dir+dir_sep+"textures"+dir_sep+str(til_y)+'_'+str(til_x)+'.png')
            #os.system(dds_conv_dxt5+" "+build_dir+dir_sep+"textures"+dir_sep+str(til_y)+'_'+str(til_x)+'.png'+" "+build_dir+dir_sep+"textures"+dir_sep+str(til_y)+'_'+str(til_x)+'.dds')
            print("     Done.") 
        else:
            print("     Ends-up being discarded.")        
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

##############################################################################
def build_masks_legacy(lat,lon,build_dir,mesh_file_name_list):
    t4=time.time()
    try:
        application.red_flag.set(0)
    except:
        pass
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    eps=0.00001
    [til_x_min,til_y_min]=wgs84_to_texture(lat+1+eps,lon-eps,14,'BI')
    [til_x_max,til_y_max]=wgs84_to_texture(lat-eps,lon+1+eps,14,'BI')
    nx=(til_x_max-til_x_min)//16+1
    ny=(til_y_max-til_y_min)//16+1
    masks_im=Image.new("1",(nx*4096,ny*4096))
    masks_draw=ImageDraw.Draw(masks_im)
    
    masks_dir=Ortho4XP_dir+dir_sep+"Masks"+dir_sep+strlat+strlon
    if not os.path.exists(masks_dir):
        os.makedirs(masks_dir)
    if not os.path.isfile(masks_dir+dir_sep+'whole_tile.png') or keep_old_pre_mask==False:
        for mesh_file_name in mesh_file_name_list:
            try:
                f_mesh=open(mesh_file_name,"r")
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
            print(" Constructing binary mask for sea water / ground from mesh file "+str(mesh_file_name))
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
        del(masks_im)
    if not use_gimp:
        print(" Blur of size masks_width applied to the binary mask...")
        masks_im=Image.open(masks_dir+dir_sep+'whole_tile.png').convert("L")
        img_array=numpy.array(masks_im,dtype=numpy.uint8)
        #kernel=numpy.ones(int(masks_width))/int(masks_width)
        kernel=numpy.array(range(1,2*masks_width))
        kernel[masks_width:]=range(masks_width-1,0,-1)
        kernel=kernel/masks_width**2
        for i in range(0,len(img_array)):
            img_array[i]=numpy.convolve(img_array[i],kernel,'same')
        img_array=img_array.transpose() 
        for i in range(0,len(img_array)):
            img_array[i]=numpy.convolve(img_array[i],kernel,'same')
        img_array=img_array.transpose()
        img_array=2*numpy.minimum(img_array,127) #*numpy.ones(img_array.shape)) 
        img_array=numpy.array(img_array,dtype=numpy.uint8)
        masks_im=Image.fromarray(img_array)
        masks_im.save(masks_dir+dir_sep+'whole_tile_blured.png')
    else: #use_gimp
        print(" Gaussian blur and level adjustment applied to the binary mask with Gimp...")
        if ('dar' in sys.platform) or ('win' not in sys.platform):   # Mac and Linux
            os.system(gimp_cmd+" -i -c -b '(blurX "+' "'+masks_dir+dir_sep+\
                'whole_tile.png" '+str(masks_width)+' "'+masks_dir+dir_sep+\
                'whole_tile_blured.png")'+"' -b '(gimp-quit 0)' ")
        else: # Windows specific
            tmpf=open('batchgimp.bat','w')
            tmpcmd='"'+gimp_cmd+'" '+\
                   '-i -c -b "(blurX \\\"'+Ortho4XP_dir+'\\\\Masks\\\\'+strlat+strlon+'\\\\whole_tile.png\\\" '+\
                   str(masks_width)+' \\\"'+Ortho4XP_dir+'\\\\Masks\\\\'+strlat+strlon+'\\\\whole_tile_blured.png\\\")"'+\
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
    if not os.path.exists(build_dir+dir_sep+"textures"):
        os.makedirs(build_dir+dir_sep+"textures")
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


##############################################################################
def build_tile_list(tile_list,build_dir_option,read_config,use_existing_mesh,bbmasks,bboverlays):
    global ortho_list,zone_list,default_provider_code,default_zl 
    nbr_tiles=len(tile_list)
    n=1
    for tile in tile_list:
        if application.red_flag.get()==1:
            print("\nBatch build process interrupted.")
            print('_____________________________________________________________'+\
                  '____________________________________')
            return
        [lat,lon]=tile
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if build_dir_option=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            if build_dir_option[-1]=='/':
                build_dir=build_dir_option[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
            else:
                build_dir=build_dir_option
        application.lat.set(lat)
        application.lon.set(lon)
        zone_list=[]
        ortho_list=[]
        if read_config:
            application.read_cfg()
        if not use_existing_mesh:
            print("\nTile "+str(n)+" / "+str(nbr_tiles))
            print("\nStep 1 : Building OSM and patch data for tile "+strlat+strlon+" : ")
            print("--------\n")
            build_poly_file(lat,lon,build_dir)
            if application.red_flag.get()==1:
                print("\nBatch build process interrupted.")
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
            print("\nTile "+str(n)+" / "+str(nbr_tiles))
            print("\nStep 2 : Building mesh for tile "+strlat+strlon+" : ")
            print("--------\n")
            build_mesh(lat,lon,build_dir)
            if application.red_flag.get()==1:
                print("\nBatch build process interrupted.")
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
        mesh_file_name = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
        if os.path.isfile(mesh_file_name)!=True:
            if default_website!='None':
                print("The mesh of Tile "+strlat+strlon+" was not found, skipping that one...")
            else: # Landclass base mesh
                base_sniff_dir=application.sniff_dir_entry.get()
                strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
                strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
                file_to_sniff=base_sniff_dir+dir_sep+"Earth nav data"+dir_sep+\
                      strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'
                if not os.path.isfile(file_to_sniff):
                    print('\nFailure : there is no file to sniff from at the indicated place.')
                    print('_____________________________________________________________'+\
                     '____________________________________')
                else:
                    print("\nTile "+str(n)+" / "+str(nbr_tiles))
                    dem_alternative=application.custom_dem_entry.get()
                    print("\nTranscoding Tile "+strlat+strlon+" : ")
                    print("------------------------\n")
                    re_encode_dsf(lat,lon,build_dir,file_to_sniff,keep_orig_zuv,dem_alternative,seven_zip)
            
            try:
                application.earth_window.canvas.delete(application.earth_window.dico_tiles_todo[str(lat)+'_'+str(lon)]) 
                application.earth_window.dico_tiles_todo.pop(str(lat)+'_'+str(lon),None)
                application.earth_window.refresh()
            except:
                pass
            n+=1 
            continue
        if bbmasks:
            print("\nTile "+str(n)+" / "+str(nbr_tiles))
            print("\nStep 2.5 : Building masks for tile "+strlat+strlon+" : ")
            print("--------\n")
            if complex_masks==False:
                mesh_file_name_list=[mesh_file_name]
            else:
                mesh_file_name_list=[]
                for closelat in [lat-1,lat,lat+1]:
                    for closelon in [lon-1,lon,lon+1]:
                        strcloselat='{:+.0f}'.format(closelat).zfill(3)
                        strcloselon='{:+.0f}'.format(closelon).zfill(4)
                        closemesh_file_name=build_dir+dir_sep+'..'+dir_sep+'zOrtho4XP_'+strcloselat+strcloselon+\
                               dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                        if os.path.isfile(closemesh_file_name):
                            mesh_file_name_list.append(closemesh_file_name)
                            continue
                        # all tiles in the same dir ?, lets try
                        closemesh_file_name=build_dir+dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                        if os.path.isfile(closemesh_file_name):
                            mesh_file_name_list.append(closemesh_file_name)
                            continue
            build_masks(lat,lon,build_dir,mesh_file_name_list,maskszl)
        if application.red_flag.get()==1:
            print("\nBatch build process interrupted.")
            print('_____________________________________________________________'+\
                  '____________________________________')
            return
        ortho_list=zone_list[:]
        if default_website!='None':
            ortho_list.append([[lat,lon,lat,lon+1,lat+1,lon+1,lat+1,lon,lat,lon],\
                    str(default_zl),str(default_website)])
        application.write_cfg()
        print("\nTile "+str(n)+" / "+str(nbr_tiles))
        print("\nStep 3 : Building Tile "+strlat+strlon+" : ")
        print("--------\n")
        build_tile(lat,lon,build_dir,mesh_file_name,False)
        if application.red_flag.get()==1:
            print("\nBatch build process interrupted.")
            print('_____________________________________________________________'+\
                      '____________________________________')
            return
        if bboverlays:
            print("\nIndependent Step  : Building of an Overlay DSF from third party data : ")
            print("-------------------\n")
            base_sniff_dir=application.sniff_dir_entry.get()
            strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
            strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
            file_to_sniff=base_sniff_dir+dir_sep+"Earth nav data"+dir_sep+\
                      strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'
            if not os.path.isfile(file_to_sniff):
                print('\nFailure : there is no file to sniff from at the indicated place.')
                print('_____________________________________________________________'+\
                 '____________________________________')
            else:
                build_overlay(lat,lon,file_to_sniff)
        try:
            application.earth_window.canvas.delete(application.earth_window.dico_tiles_todo[str(lat)+'_'+str(lon)]) 
            application.earth_window.dico_tiles_todo.pop(str(lat)+'_'+str(lon),None)
            application.earth_window.refresh()
        except:
            pass
            #print("I could not update the earth tile window, perhaps you closed it ?")
        n+=1

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
def in_bbox(point,bbox):
    return (point[0] >= bbox[0]) and (point[0] <= bbox[1]) and (point[1]>=bbox[2]) and (point[1]<=bbox[3])
##############################################################################

##############################################################################
def compute_bbox(poly):
    latmin=90
    latmax=-90
    lonmin=180
    lonmax=-180
    for lat,lon in zip(poly[::2],poly[1::2]):
        latmin = lat if lat<latmin else latmin
        latmax = lat if lat>latmax else latmax     
        lonmin = lon if lon<lonmin else lonmin
        lonmax = lon if lon>lonmax else lonmax
    return [latmin-0.02,latmax+0.02,lonmin-0.02,lonmax+0.02]      
##############################################################################

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
def do_overlap(pol1,pol2):
    for x,y in zip(pol1[::2],pol1[1::2]):
        if point_in_polygon([x,y],pol2): return True
    for x,y in zip(pol2[::2],pol2[1::2]):
        if point_in_polygon([x,y],pol1): return True
    for x1,y1,x2,y2 in zip(pol1[:-2:2],pol1[1:-1:2],pol1[2::2],pol1[3::2]):
        for x3,y3,x4,y4 in zip(pol2[:-2:2],pol2[1:-1:2],pol2[2::2],pol2[3::2]):
            if do_intersect_transverse([x1,y1],[x2,y2],[x3,y3],[x4,y4]):
                return True
    return False
##############################################################################
         
##############################################################################
def do_intersect_transverse(a,b,c,d):
    return counterclockwise(a,c,d)!=counterclockwise(b,c,d)\
            and counterclockwise(a,b,c) != counterclockwise(a,b,d)
##############################################################################

##############################################################################
def counterclockwise(a,b,c):
    return (c[1]-a[1])*(b[0]-a[0])>(b[1]-a[1])*(c[0]-a[0])
##############################################################################


##############################################################################
# distance squared from a point "point" to the line through "p1" et "p2"
##############################################################################
def point_to_line_distsquared(point,point1,point2):
    p0=point[0]-point1[0]
    p1=point[1]-point1[1]
    q0=point2[0]-point1[0]
    q1=point2[1]-point1[1]
    n2=q0**2+q1**2
    if n2<1e-12:
        return p0**2+p1**2
    return p0**2+p1**2-(p0*q0+p1*q1)**2/n2 
##############################################################################     



##############################################################################
def ramer_douglas_peucker(polygon,tol):
    dmax2=0
    cut=-1
    for i in range(1,len(polygon)-1):
       d2 = point_to_line_distsquared(polygon[i],polygon[0],polygon[-1])
       if d2 > dmax2:
           cut=i
           dmax2=d2
    if dmax2 > tol**2:
        r1=ramer_douglas_peucker(polygon[:cut+1],tol)
        r2=ramer_douglas_peucker(polygon[cut:],tol)
        return r1[:-1]+r2
    else:
        return [polygon[0],polygon[-1]]
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
class Earth_Preview_window(Toplevel):
    
    dico_old_stuff={}
    earthzl=6 
    resolution=2**earthzl*256
    nx0=0
    ny0=0
    
    def __init__(self):
        Toplevel.__init__(self)
        self.title('Tiles collection')
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
        if self.winfo_screenheight()>=1024:
            self.pady=5
        else:
            self.pady=1
    
        # Constants/Variable
        self.dico_tiles_todo={}
        self.dico_tiles_done={}

        self.latlon         = StringVar()
        self.ptc            = IntVar()
        self.ptc.set(0)
        self.uem            = IntVar()
        self.uem.set(0)
        self.bbm            = IntVar()
        self.bbm.set(0)
        self.bbo            = IntVar()
        self.bbo.set(0)
 
    
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
        self.infotop        =  Label(self.frame_left,text="Four buttons below apply\nto active lat/lon only",bg="light green")
        self.deltile_btn      =  Button(self.frame_left,text='  Delete Tile   ',command=self.delete_tile)
        self.delosm_btn       =  Button(self.frame_left,text='  Delete OSM    ',command=self.delete_osm)
        self.delortho_btn     =  Button(self.frame_left,text='  Delete Ortho  ',command=self.delete_ortho)
        self.delall_btn       =  Button(self.frame_left,text='  Delete All    ',command=self.delete_all)
        self.infomid          =  Label(self.frame_left,text="---------------\nAll = OSM or Ortho or Tiles",bg="light green")
        self.toggle_old_btn   =  Button(self.frame_left,text='Toggle all stuff',command=self.toggle_old_stuff)
        self.infomid2         =  Label(self.frame_left,text="---------------\nBuild multiple tiles at once :",bg="light green")
        self.check1           =  Checkbutton(self.frame_left,text='Per tile config',anchor=W,\
                                   variable=self.ptc,bg="light green",activebackground="light green",highlightthickness=0)
        self.check2           =  Checkbutton(self.frame_left,text='Use existing mesh',anchor=W,\
                                   variable=self.uem,bg="light green",activebackground="light green",highlightthickness=0)
        self.check3           =  Checkbutton(self.frame_left,text='Build masks',anchor=W,\
                                   variable=self.bbm,bg="light green",activebackground="light green",highlightthickness=0)
        self.check4           =  Checkbutton(self.frame_left,text='Build overlays',anchor=W,\
                                   variable=self.bbo,bg="light green",activebackground="light green",highlightthickness=0)
        self.build_btn        =  Button(self.frame_left,text='  Batch Build   ',command=self.batch_build)
        self.refresh_btn      =  Button(self.frame_left,text='     Refresh    ',command=self.refresh)
        self.exit_btn         =  Button(self.frame_left,text='      Exit      ',command=self.save_loc_and_exit)
        self.shortcuts        =  Label(self.frame_left,text="Shortcuts :\n-------------------\nR-Click+hold=move map\nDouble-click=select active lat/lon\nShift+click=add for batch build\nCtrl+click= link in Custom Scenery\n\nActive lat/lon\n---------------------",bg="light green")
        self.latlon_entry     =  Entry(self.frame_left,width=8,bg="white",fg="blue",textvariable=self.latlon)
        self.canvas           =  Canvas(self.frame_right,bd=0)

        # Placement of Widgets
        self.shortcuts.grid(row=13,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.latlon_entry.grid(row=14,column=0,padx=5,pady=self.pady,sticky=N+S)
        self.infotop.grid(row=15,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.deltile_btn.grid(row=16,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.delosm_btn.grid(row=17,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.delortho_btn.grid(row=18,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.delall_btn.grid(row=19,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.infomid.grid(row=20,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.toggle_old_btn.grid(row=21,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.infomid2.grid(row=22,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.check1.grid(row=23,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.check2.grid(row=24,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.check3.grid(row=25,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.check4.grid(row=26,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.build_btn.grid(row=27,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.refresh_btn.grid(row=28,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.exit_btn.grid(row=29,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.canvas.grid(row=0,column=0,sticky=N+S+E+W)     
        
        self.init_canvas()
        self.refresh()
        
    def init_canvas(self):
        self.canvas.config(scrollregion=(1,1,2**self.earthzl*256-1,2**self.earthzl*256-1)) #self.canvas.bbox(ALL))
        try:
            fpos=open("last_map_position.txt","r")
            [x0,y0]=fpos.readline().split()
            x0=float(x0)
            y0=float(y0)
            fpos.close()
            self.canvas.xview_moveto(x0/self.resolution)
            self.canvas.yview_moveto(y0/self.resolution)
        except:
            self.canvas.xview_moveto(0.45)
            self.canvas.yview_moveto(0.3)
            x0=self.canvas.canvasx(0)
            y0=self.canvas.canvasy(0)
        if x0<0: x0=0
        if y0<0: y0=0 
        self.nx0=int((8*x0)//self.resolution)
        self.ny0=int((8*y0)//self.resolution)
        if 'dar' in sys.platform:
            self.canvas.bind("<ButtonPress-2>", self.scroll_start)
            self.canvas.bind("<B2-Motion>", self.scroll_move)
        else:
            self.canvas.bind("<ButtonPress-3>", self.scroll_start)
            self.canvas.bind("<B3-Motion>", self.scroll_move)
        self.canvas.bind("<Double-Button-1>",self.select_tile)
        self.canvas.bind("<Shift-ButtonPress-1>",self.add_tile)
        self.canvas.bind("<Control-ButtonPress-1>",self.toggle_to_custom)
        self.canvas.focus_set()
        self.draw_canvas(self.nx0,self.ny0) 
        return
    
    def set_working_dir(self):
        if application.build_dir_entry.get()=='':
            self.working_dir=Ortho4XP_dir+dir_sep+'Tiles'
            self.working_type='legacy'
        else:
            self.working_dir=application.build_dir_entry.get()
            if self.working_dir[-1]=='/':
                self.working_dir=self.working_dir[:-1]
                self.working_type='legacy'
            else:
                self.working_type='onedir'

    def preview_existing_tiles(self):
        dico_color={11:'blue',12:'blue',13:'blue',14:'blue',15:'cyan',16:'green',17:'yellow',18:'orange',19:'red'}
        if self.dico_tiles_done:
            for tile in self.dico_tiles_done:
                for objid in self.dico_tiles_done[tile]:
                    self.canvas.delete(objid)
            self.dico_tiles_done={}
        if self.working_type=='legacy':
            for dir_name in os.listdir(self.working_dir):
                if "zOrtho4XP_" in dir_name:
                    try:
                        strlat=dir_name[-7:-4]
                        strlon=dir_name[-4:]
                        lat=int(strlat)
                        lon=int(strlon)
                        strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
                        strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
                    except:
                        continue                     
                    [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
                    [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
                    if os.path.isfile(self.working_dir+dir_sep+dir_name+dir_sep+"Earth nav data"+dir_sep+strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'):
                        color='blue'
                        content=''
                        try:
                            tmpf=open(os.path.join(self.working_dir,dir_name,'Ortho4XP_'+short_latlon(lat,lon)+'.cfg'),'r')
                            found_config=True
                        except:
                            try:
                                tmpf=open(os.path.join(self.working_dir,dir_name,'Ortho4XP.cfg'),'r')
                                found_config=True
                            except:
                                found_config=False
                        if found_config:                        
                            prov=zl=''
                            for line in tmpf.readlines():
                                if line[:15]=='default_website':
                                    prov=line.split('=')[1][1:-2]
                                elif line[:10]=='default_zl':
                                    zl=int(line.split('=')[1][:-1])
                                    break
                            tmpf.close()
                            if (prov and zl):
                                color=dico_color[zl]
                                content=prov+'\n'+str(zl)
                        self.dico_tiles_done[(lat,lon)]=(\
                                self.canvas.create_rectangle(x0,y0,x1,y1,fill=color,stipple='gray12'),\
                                self.canvas.create_text((x0+x1)//2,(y0+y1)//2,justify=CENTER,text=content)\
                                )
                        link=Custom_scenery_dir+dir_sep+Custom_scenery_prefix+'zOrtho4XP_'+short_latlon(lat,lon)
                        if os.path.isdir(link):
                            if os.path.samefile(os.path.realpath(link),os.path.realpath(self.working_dir+dir_sep+'zOrtho4XP_'+short_latlon(lat,lon))):
                                self.canvas.itemconfig(self.dico_tiles_done[(lat,lon)][0],stipple='gray50')
        elif self.working_type=='onedir' and os.path.exists(self.working_dir+dir_sep+'Earth nav data'):
            for dir_name in os.listdir(self.working_dir+dir_sep+'Earth nav data'):
                for file_name in os.listdir(self.working_dir+dir_sep+'Earth nav data'+dir_sep+dir_name):
                    try:
                        lat=int(file_name[0:3])   
                        lon=int(file_name[3:7])              
                    except:
                        continue
                    [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
                    [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
                    self.dico_tiles_done[(lat,lon)]=(self.canvas.create_rectangle(x0,y0,x1,y1,fill='blue',stipple='gray12'),)
            link=Custom_scenery_dir+dir_sep+Custom_scenery_prefix+'zOrtho4XP_'+os.path.basename(self.working_dir)
            if os.path.isdir(link):
                if os.path.samefile(os.path.realpath(link),os.path.realpath(self.working_dir)):
                    for tile in self.dico_tiles_done:
                        self.canvas.itemconfig(self.dico_tiles_done[tile][0],stipple='gray50')
        return

   
    def refresh(self):
        self.set_working_dir()
        self.preview_existing_tiles()
        return      

    def toggle_old_stuff(self):
        if not self.dico_old_stuff=={}:
            for tile in self.dico_old_stuff:
                self.canvas.delete(self.dico_old_stuff[tile])
            self.dico_old_stuff={}
            return    
        for dir_name in os.listdir(self.working_dir): 
            if "zOrtho4XP_" in dir_name:
                try:
                    strlat=dir_name[-7:-4]
                    strlon=dir_name[-4:]
                    lat=int(strlat)
                    lon=int(strlon)
                    strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
                    strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
                except:
                    continue                     
                [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
                [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
                if (lat,lon) not in self.dico_tiles_done:
                    self.dico_old_stuff[(lat,lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,outline='red')
        for dir_name in os.listdir(os.path.join(Ortho4XP_dir,"Orthophotos")):
            if dir_name[0] not in ('+','-'): continue
            for sub_dir_name in os.listdir(os.path.join(Ortho4XP_dir,"Orthophotos",dir_name)):
                if sub_dir_name[0] not in ('+','-'): continue
                try:
                    strlat=sub_dir_name[0:3]
                    strlon=sub_dir_name[3:]
                    lat=int(strlat)
                    lon=int(strlon)
                except:
                    continue
                [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
                [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
                if (lat,lon) not in self.dico_tiles_done and (lat,lon) not in self.dico_old_stuff:
                    self.dico_old_stuff[(lat,lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,outline='red')
        for dir_name in os.listdir(os.path.join(Ortho4XP_dir,"OSM_data")):
            if dir_name[0] not in ('+','-'): continue
            for sub_dir_name in os.listdir(os.path.join(Ortho4XP_dir,"OSM_data",dir_name)):
                try:
                    strlat=sub_dir_name[0:3]
                    strlon=sub_dir_name[3:]
                    lat=int(strlat)
                    lon=int(strlon)
                except:
                    continue
                [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
                [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
                if (lat,lon) not in self.dico_tiles_done and (lat,lon) not in self.dico_old_stuff:
                    self.dico_old_stuff[(lat,lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,outline='red')
        return  

    def delete_tile(self):
        if self.working_type=='legacy':
            try:
                shutil.rmtree(os.path.join(self.working_dir,"zOrtho4XP_"+short_latlon(self.active_lat,self.active_lon)))
            except:
                pass
        elif self.working_type=='onedir':
            try:
                os.remove(os.path.join(self.working_dir,"Earth nav data",long_latlon(self.active_lat,self.active_lon)+'.dsf'))
            except:
                pass
        self.preview_existing_tiles()
        self.toggle_old_stuff()
        self.toggle_old_stuff()
        return

    def delete_osm(self):
        try:
            shutil.rmtree(os.path.join(Ortho4XP_dir,"OSM_data",long_latlon(self.active_lat,self.active_lon)))
        except:
            pass
        self.preview_existing_tiles()
        self.toggle_old_stuff()
        self.toggle_old_stuff()
        return
    
    def delete_ortho(self):
        try:
            shutil.rmtree(os.path.join(Ortho4XP_dir,"Orthophotos",long_latlon(self.active_lat,self.active_lon)))
        except:
            pass
        self.preview_existing_tiles()
        self.toggle_old_stuff()
        self.toggle_old_stuff()
        return

    def delete_all(self):
        self.delete_tile()
        self.delete_osm()
        self.delete_ortho()
        return

         
    
    def select_tile(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        [lat,lon]=pix_to_wgs84(x,y,self.earthzl)
        lat=floor(lat)
        lon=floor(lon)
        self.active_lat=lat
        self.active_lon=lon
        self.latlon.set(short_latlon(lat,lon))        
        try:
            self.canvas.delete(self.active_tile)
        except:
            pass
        [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
        [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
        self.active_tile=self.canvas.create_rectangle(x0,y0,x1,y1,fill='',outline='yellow',width=3)
        application.lat.set(lat)
        application.lon.set(lon)
        application.zone_list=[]
        return
    
    def toggle_to_custom(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        [lat,lon]=pix_to_wgs84(x,y,self.earthzl)
        lat=floor(lat)
        lon=floor(lon)
        strlat='{:+.0f}'.format(float(lat)).zfill(3)
        strlon='{:+.0f}'.format(float(lon)).zfill(4)
        if (lat,lon) not in self.dico_tiles_done:
            return
        if self.working_type=='legacy':
            link=Custom_scenery_dir+dir_sep+Custom_scenery_prefix+'zOrtho4XP_'+strlat+strlon
            target=os.path.realpath(self.working_dir+dir_sep+'zOrtho4XP_'+strlat+strlon)
            if os.path.isdir(link):
                os.remove(link)
                self.preview_existing_tiles()
                return 
        elif self.working_type=='onedir': 
            link=Custom_scenery_dir+dir_sep+Custom_scenery_prefix+'zOrtho4XP_'+os.path.basename(self.working_dir)
            target=os.path.realpath(self.working_dir)
            if os.path.isdir(link):
                os.remove(link)
                self.preview_existing_tiles()
                return 
        if ('dar' in sys.platform) or ('win' not in sys.platform): # Mac and Linux
            os.system("ln -s "+' "'+target+'" "'+link+'"')
        else:
            os.system('MKLINK /J "'+link+'" "'+target+'"')
        self.preview_existing_tiles()
        return 


    def add_tile(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        [lat,lon]=pix_to_wgs84(x,y,self.earthzl)
        lat=floor(lat)
        lon=floor(lon)
        if str(lat)+'_'+str(lon) not in self.dico_tiles_todo:
            [x0,y0]=wgs84_to_pix(lat+1,lon,self.earthzl)
            [x1,y1]=wgs84_to_pix(lat,lon+1,self.earthzl)
            self.dico_tiles_todo[str(lat)+'_'+str(lon)]=self.canvas.create_rectangle(x0,y0,x1,y1,fill='red',stipple='gray12') 
        else:
            self.canvas.delete(self.dico_tiles_todo[str(lat)+'_'+str(lon)]) 
            self.dico_tiles_todo.pop(str(lat)+'_'+str(lon),None)
        return

    def batch_build(self):
        tile_list=[]
        if self.ptc.get()==1:
            read_config=True
        else:
            read_config=False    
        if self.uem.get()==1:
            use_existing_mesh=True
        else:
            use_existing_mesh=False    
        if self.bbm.get()==1:
            bbmasks=True
        else:
            bbmasks=False    
        if self.bbo.get()==1:
            bboverlays=True
        else:
            bboverlays=False    
        for tile in self.dico_tiles_todo:
            [stlat,stlon]=tile.split('_')
            lat=int(stlat)
            lon=int(stlon)
            tile_list.append([lat,lon])
        application.build_tile_list_ifc(tile_list,read_config,use_existing_mesh,bbmasks,bboverlays) 
        return
        
    def scroll_start(self,event):
        self.canvas.scan_mark(event.x, event.y)
        return

    def scroll_move(self,event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.redraw_canvas()
        return

    def redraw_canvas(self):
        x0=self.canvas.canvasx(0)
        y0=self.canvas.canvasy(0)
        if x0<0: x0=0
        if y0<0: y0=0
        nx0=int((8*x0)//self.resolution)
        ny0=int((8*y0)//self.resolution)
        if nx0==self.nx0 and ny0==self.ny0:
            return
        else:
           self.nx0=nx0
           self.ny0=ny0 
           self.canvas.delete(self.canv_imgNW)
           self.canvas.delete(self.canv_imgNE)
           self.canvas.delete(self.canv_imgSW)
           self.canvas.delete(self.canv_imgSE)
           fargs_rc=[nx0,ny0]
           self.rc_thread=threading.Thread(target=self.draw_canvas,args=fargs_rc)
           self.rc_thread.start()
           return 
      
    def draw_canvas(self,nx0,ny0):
           fileprefix=Ortho4XP_dir+dir_sep+"Previews"+dir_sep+"Earth"+dir_sep+"Earth2_ZL"+str(self.earthzl)+"_"
           filepreviewNW=fileprefix+str(nx0)+'_'+str(ny0)+".jpg"
           self.imageNW=Image.open(filepreviewNW)
           self.photoNW=ImageTk.PhotoImage(self.imageNW)
           self.canv_imgNW=self.canvas.create_image(nx0*2**self.earthzl*256/8,ny0*2**self.earthzl*256/8,anchor=NW,image=self.photoNW)
           self.canvas.tag_lower(self.canv_imgNW)
           if nx0<2**(self.earthzl-3)-1:
              filepreviewNE=fileprefix+str(nx0+1)+'_'+str(ny0)+".jpg"
              self.imageNE=Image.open(filepreviewNE)
              self.photoNE=ImageTk.PhotoImage(self.imageNE)
              self.canv_imgNE=self.canvas.create_image((nx0+1)*2**self.earthzl*256/8,ny0*2**self.earthzl*256/8,anchor=NW,image=self.photoNE)
              self.canvas.tag_lower(self.canv_imgNE)
           if ny0<2**(self.earthzl-3)-1:
              filepreviewSW=fileprefix+str(nx0)+'_'+str(ny0+1)+".jpg"
              self.imageSW=Image.open(filepreviewSW)
              self.photoSW=ImageTk.PhotoImage(self.imageSW)
              self.canv_imgSW=self.canvas.create_image(nx0*2**self.earthzl*256/8,(ny0+1)*2**self.earthzl*256/8,anchor=NW,image=self.photoSW)
              self.canvas.tag_lower(self.canv_imgSW)
           if nx0<2**(self.earthzl-3)-1 and ny0<2**(self.earthzl-3)-1:
              filepreviewSE=fileprefix+str(nx0+1)+'_'+str(ny0+1)+".jpg"
              self.imageSE=Image.open(filepreviewSE)
              self.photoSE=ImageTk.PhotoImage(self.imageSE)
              self.canv_imgSE=self.canvas.create_image((nx0+1)*2**self.earthzl*256/8,(ny0+1)*2**self.earthzl*256/8,anchor=NW,image=self.photoSE)
              self.canvas.tag_lower(self.canv_imgSE)
           return      

    def save_loc_and_exit(self):
        try:
            fpos=open("last_map_position.txt","w")
            fpos.write(str(self.canvas.canvasx(0))+' '+str(self.canvas.canvasy(0)))
            fpos.close()
        except:
            print("Could not save last map position.")
        self.destroy() 

##############################################################################   


##############################################################################
class Preview_window(Toplevel):

    dico_color={15:'cyan',16:'green',17:'yellow',18:'orange',19:'red'}
    points=[]
    coords=[]
    polygon_list=[]
    polyobj_list=[]

    
    
    def __init__(self,lat,lon):
        self.lat=lat
        self.lon=lon 
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
        if self.winfo_screenheight()>=1024:
            self.pady=5
        else:
            self.pady=1
    
        # Constants

        self.map_list        = sorted(list(providers_dict)+list(combined_providers_dict))
        self.map_list2       = self.map_list
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
                                 values=self.map_list,state='readonly',width=10)
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
                    height=2,indicatoron=0,text='ZL15',variable=self.zlpol,value=15,\
                    command=self.redraw_poly)
        self.B16 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[16],\
                    activebackground=self.dico_color[16],selectcolor=self.dico_color[16],height=2,\
                    indicatoron=0,text='ZL16',variable=self.zlpol,value=16,command=self.redraw_poly)
        self.B17 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[17],\
                    activebackground=self.dico_color[17],selectcolor=self.dico_color[17],height=2,\
                    indicatoron=0,text='ZL17',variable=self.zlpol,value=17,command=self.redraw_poly)
        self.B18 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[18],\
                    activebackground=self.dico_color[18],selectcolor=self.dico_color[18],height=2,\
                    indicatoron=0,text='ZL18',variable=self.zlpol,value=18,command=self.redraw_poly)
        self.B19 =  Radiobutton(self.frame_left,bd=4,bg=self.dico_color[19],\
                    activebackground=self.dico_color[19],selectcolor=self.dico_color[19],height=2,\
                    indicatoron=0,text='ZL19',variable=self.zlpol,value=19,command=self.redraw_poly)
        self.save_zone_btn    =  Button(self.frame_left,text='  Save zone  ',command=self.save_zone_cmd)
        self.del_zone_btn     =  Button(self.frame_left,text=' Delete zone ',command=self.delete_zone_cmd)
        self.save_zones_btn   =  Button(self.frame_left,text='Save and Exit',command=self.save_zone_list)
        self.load_poly_btn    =  Button(self.frame_left,text='  Load Poly  ',command=lambda: self.load_poly(lat,lon))
        self.exit_btn         =  Button(self.frame_left,text='   Abandon   ',command=self.destroy)
        self.geotiff_btn      =  Button(self.frame_left,text='Make GeoTiffs',command=self.build_geotiffs) 
        self.extract_mesh_btn =  Button(self.frame_left,text='Extract Mesh ',command=self.extract_mesh) 
        self.title_gbsize     =  Label(self.frame_left,anchor=W,text="Approx. Add. Size : ",bg="light green") 
        self.gbsize           =  Entry(self.frame_left,width=6,bg="white",fg="blue",textvariable=self.gb)
        self.shortcuts        =  Label(self.frame_left,text="\nShift+click to add polygon points\nCtrl+Shift+click to add points on dds grid\nCtrl+click to add full dds\nCtrl+R_click to delete zone under mouse",bg="light green")
        self.canvas           =  Canvas(self.frame_right,bd=0)

        # Placement of Widgets
        self.label_pp.grid(row=0,column=0,sticky=W+E)
        self.title_src.grid(row=1,column=0,sticky=W,padx=5,pady=self.pady)
        self.map_combo.grid(row=1,column=0,padx=5,pady=self.pady,sticky=E)
        self.title_zl.grid(row=2,column=0,sticky=W,padx=5,pady=self.pady)
        self.zl_combo.grid(row=2,column=0,padx=5,pady=self.pady,sticky=E)
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
        self.title_gbsize.grid(row=15,column=0,padx=5,pady=10,sticky=W)
        self.gbsize.grid(row=15,column=0,padx=5,pady=10,sticky=E)
        self.save_zone_btn.grid(row=16,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.del_zone_btn.grid(row=17,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.load_poly_btn.grid(row=18,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.save_zones_btn.grid(row=19,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.exit_btn.grid(row=20,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.geotiff_btn.grid(row=21,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.extract_mesh_btn.grid(row=22,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.shortcuts.grid(row=23,column=0,padx=5,pady=0,sticky=N+S+E+W)
        self.canvas.grid(row=0,column=0,sticky=N+S+E+W)     
        
        
    def preview_tile(self,lat,lon):
        self.zoomlevel=int(self.zl_combo.get())
        zoomlevel=self.zoomlevel
        provider_code=self.map_combo.get()    
        strlat='{:+.0f}'.format(float(lat)).zfill(3)
        strlon='{:+.0f}'.format(float(lon)).zfill(4)
        [tilxleft,tilytop]=wgs84_to_gtile(lat+1,lon,zoomlevel)
        [self.latmax,self.lonmin]=gtile_to_wgs84(tilxleft,tilytop,zoomlevel)
        [self.xmin,self.ymin]=wgs84_to_pix(self.latmax,self.lonmin,zoomlevel)
        [tilxright,tilybot]=wgs84_to_gtile(lat,lon+1,zoomlevel)
        [self.latmin,self.lonmax]=gtile_to_wgs84(tilxright+1,tilybot+1,zoomlevel)
        [self.xmax,self.ymax]=wgs84_to_pix(self.latmin,self.lonmax,zoomlevel)
        filepreview=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+strlat+strlon+\
                    "_"+provider_code+str(zoomlevel)+".jpg"       
        if os.path.isfile(filepreview) != True:
            fargs_ctp=[int(lat),int(lon),int(zoomlevel),provider_code]
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
        if 'dar' in sys.platform:
            self.canvas.bind("<ButtonPress-2>", self.scroll_start)
            self.canvas.bind("<B2-Motion>", self.scroll_move)
            self.canvas.bind("<Control-ButtonPress-2>",self.delPol)
        else:
            self.canvas.bind("<ButtonPress-3>", self.scroll_start)
            self.canvas.bind("<B3-Motion>", self.scroll_move)
            self.canvas.bind("<Control-ButtonPress-3>",self.delPol)
        self.canvas.bind("<Shift-ButtonPress-1>",self.newPoint)
        self.canvas.bind("<Control-Shift-ButtonPress-1>",self.newPointGrid)
        self.canvas.bind("<Control-ButtonPress-1>",self.newPol)
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
                [x,y]=self.latlon_to_xy(latp,lonp,self.zoomlevel)
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
                [x,y]=self.latlon_to_xy(latp,lonp,self.zoomlevel)
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
            if len(self.points)>=4:
                self.poly_curr=self.canvas.create_polygon(self.points,\
                           outline=color,fill='', width=2)
            else:
                self.poly_curr=self.canvas.create_polygon(self.points,\
                           outline=color,fill='', width=5)
        except:
            pass
        return

    def load_poly(self,lat,lon):
        poly_file=filedialog.askopenfilename()    
        try:
            f=open(poly_file,'r')
        except:
            return
        f.readline()
        array=[]
        for line in f.readlines():
           if 'END' in line:
              break
           [lonp,latp]=line.split()
           lonp=float(lonp)
           latp=float(latp)
           latp=latp if latp > lat-0.001 else lat-0.001
           latp=latp if latp < lat+1.001 else lat+1.001
           lonp=lonp if lonp > lon-0.001 else lon-0.001
           lonp=lonp if lonp < lon+1.001 else lon+1.001
           array.append([float(latp),float(lonp)])
        new_array=ramer_douglas_peucker(array,tol=poly_simplification_tol)
        for point in new_array:
           self.coords+=[point[0],point[1]]
           self.points+=self.latlon_to_xy(point[0],point[1],self.zoomlevel)
        self.redraw_poly()
        self.lift()
        return


    def newPoint(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        self.points+=[x,y]
        [latp,lonp]=self.xy_to_latlon(x,y,self.zoomlevel)
        self.coords+=[latp,lonp]
        self.redraw_poly()
        return
    
    def newPointGrid(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        [latp,lonp]=self.xy_to_latlon(x,y,self.zoomlevel)
        [a,b]=wgs84_to_texture(latp,lonp,self.zlpol.get(),'BI')
        [aa,bb]=wgs84_to_gtile(latp,lonp,self.zlpol.get())
        a=a+16 if aa-a>=8 else a
        b=b+16 if bb-b>=8 else b
        [latp,lonp]=gtile_to_wgs84(a,b,self.zlpol.get())
        self.coords+=[latp,lonp]
        [x,y]=self.latlon_to_xy(latp,lonp,self.zoomlevel)
        self.points+=[int(x),int(y)]
        self.redraw_poly()
        return
    
    def newPol(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        [latp,lonp]=self.xy_to_latlon(x,y,self.zoomlevel)
        [a,b]=wgs84_to_texture(latp,lonp,self.zlpol.get(),'BI')
        [latmax,lonmin]=gtile_to_wgs84(a,b,self.zlpol.get())
        [latmin,lonmax]=gtile_to_wgs84(a+16,b+16,self.zlpol.get())
        self.coords=[latmin,lonmin,latmin,lonmax,latmax,lonmax,latmax,lonmin]
        self.points=[]
        for i in range(4):
            [x,y]=self.latlon_to_xy(self.coords[2*i],self.coords[2*i+1],self.zoomlevel)
            self.points+=[int(x),int(y)]
        self.redraw_poly()
        self.save_zone_cmd()
        return

    def delPol(self,event):
        x=self.canvas.canvasx(event.x)
        y=self.canvas.canvasy(event.y)
        copy=self.polygon_list[:]
        for poly in copy:
            if poly[2]!=self.zlpol.get(): continue
            if point_in_polygon([x,y],poly[0]):
                idx=self.polygon_list.index(poly)
                self.polygon_list.pop(idx)
                self.canvas.delete(self.polyobj_list[idx])
                self.polyobj_list.pop(idx)
        return        


    def xy_to_latlon(self,x,y,zoomlevel):
        pix_x=x+self.xmin
        pix_y=y+self.ymin
        return pix_to_wgs84(pix_x,pix_y,zoomlevel)
        

    def latlon_to_xy(self,lat,lon,zoomlevel):
        [pix_x,pix_y]=wgs84_to_pix(lat,lon,zoomlevel)
        return [pix_x-self.xmin,pix_y-self.ymin]

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

    def build_geotiffs(self):
        for polygon in self.polygon_list:
            lat_bar=(polygon[1][0]+polygon[1][4])/2 
            lon_bar=(polygon[1][1]+polygon[1][3])/2 
            zoomlevel=int(polygon[2])
            provider_code=polygon[3]
            til_x_left,til_y_top=wgs84_to_texture(lat_bar,lon_bar,zoomlevel,'BI')
            (file_dir,file_name)=jpeg_file_name_from_attributes(self.lat,self.lon,til_x_left,til_y_top,zoomlevel,provider_code)
            print(os.path.join(file_dir,file_name))
            #continue
            if not os.path.isfile(os.path.join(file_dir,file_name)):
                vprint(1,"   Downloading missing orthophoto "+file_name)
                build_jpeg_ortho(file_dir,file_name,til_x_left,til_y_top,zoomlevel,provider_code)
            else:
                vprint(1,"   The orthophoto "+file_name+" is already present.")
            (latmax,lonmin)=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
            (latmin,lonmax)=gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
            geotiff_file_name=os.path.join(Ortho4XP_dir,'Geotiffs',file_name.replace('jpg','tif'))	
            os.system('gdal_translate -of Gtiff -co COMPRESS=JPEG -a_ullr '+str(lonmin)+' '+str(latmax)+' '+str(lonmax)+' '+str(latmin)+' -a_srs epsg:4326 "'+os.path.join(file_dir,file_name)+'" "'+geotiff_file_name+'"')      

    
    def extract_mesh(self):
        polygon = self.polygon_list[0]
        lat_bar=(polygon[1][0]+polygon[1][4])/2 
        lon_bar=(polygon[1][1]+polygon[1][3])/2 
        zoomlevel=int(polygon[2])
        provider_code=polygon[3]
        til_x_left,til_y_top=wgs84_to_texture(lat_bar,lon_bar,zoomlevel,'BI')
        (file_dir,file_name)=jpeg_file_name_from_attributes(self.lat,self.lon,til_x_left,til_y_top,zoomlevel,provider_code)
        if not os.path.isfile(os.path.join(file_dir,file_name)):
            vprint(1,"   Downloading missing orthophoto "+file_name)
            build_jpeg_ortho(file_dir,file_name,til_x_left,til_y_top,zoomlevel,provider_code)
        else:
            vprint(1,"   The orthophoto "+file_name+" is already present.")
        (latmax,lonmin)=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        (latmin,lonmax)=gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
        mesh_file_name = os.path.join(build_dir,'Data'+short_latlon(self.lat,self.lon)+'.mesh')
        obj_file_name  = os.path.join(build_dir,file_name.replace('jpg','obj'))
        mesh_to_obj(self.lat,self.lon,mesh_file_name,obj_file_name,latmin,latmax,lonmin,lonmax)
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
                tmp.append(pt) #float('{:.3f}'.format(float(pt))))
            for pt in item[1][0:2]:     # repeat first point for point_in_polygon algo
                tmp.append(pt) #float('{:.3f}'.format(float(pt))))
            zone_list.append([tmp,item[2],item[3]])
        self.destroy()    
        return
############################################################################################

############################################################################################
class Expert_config(Toplevel):

 

    def __init__(self):
        
        Toplevel.__init__(self)
        self.title('Global/Expert config')
        toplevel = self.winfo_toplevel()
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        if self.winfo_screenheight()>=1024:
            self.pady=5
        else:
            self.pady=1
                 
        # Frames
        self.frame_left       =  Frame(self, border=4,\
                                 relief=RIDGE,bg='light green')
        self.frame_lastbtn    =  Frame(self.frame_left,\
                                 border=0,padx=5,pady=self.pady,bg="light green")
        # Frames properties
        self.frame_lastbtn.columnconfigure(0,weight=1)
        self.frame_lastbtn.columnconfigure(1,weight=1)
        self.frame_lastbtn.columnconfigure(2,weight=1)
        self.frame_lastbtn.columnconfigure(3,weight=1)
        self.frame_lastbtn.columnconfigure(4,weight=1)
        self.frame_lastbtn.rowconfigure(0,weight=1)

        # Frames placement
        self.frame_left.grid(row=0,column=0)#,sticky=N+S+W+E)
        self.frame_lastbtn.grid(row=40,column=0,columnspan=6,pady=10)#,sticky=N+S+E+W)
        
        # Variables and widgets and their placement
        self.v_={}
        self.title_={}
        self.entry_={}
        self.explain_={}
        j=0
        l=len(configvars)//2+len(configvars)%2 
        for item in configvars:
            self.title_[item]=Label(self.frame_left,text=item,anchor=W,bg='light green')
            self.entry_[item]=Entry(self.frame_left,width=60,bg='white',fg='blue') 
            self.explain_[item]=Button(self.frame_left,text='?',pady=0,command=lambda: self.popup(item),height=1)
            self.title_[item].grid(row=j%l,column=0+3*(j//l),padx=5,pady=2,sticky=N+S+E+W)  
            self.entry_[item].grid(row=j%l,column=1+3*(j//l),padx=5,pady=2,sticky=N+S+E+W)
            self.explain_[item].grid(row=j%l,column=2+3*(j//l),padx=5,pady=2,sticky=E+W)  
            j+=1
        self.button1= Button(self.frame_lastbtn, text='Load from global cfg',\
                                 command= self.load_from_global_cfg)
        self.button1.grid(row=0,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button2= Button(self.frame_lastbtn, text='Write to global cfg',\
                                 command= self.write_to_global_cfg)
        self.button2.grid(row=0,column=1,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button3= Button(self.frame_lastbtn, text='Load factory default',\
                                 command= self.load_factory_defaults)
        self.button3.grid(row=0,column=2,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button4= Button(self.frame_lastbtn, text='Save and Exit',\
                                 command= self.apply_changes)
        self.button4.grid(row=0,column=3,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.button5= Button(self.frame_lastbtn, text='Cancel',\
                                 command= self.destroy)
        self.button5.grid(row=0,column=4,padx=5,pady=self.pady,sticky=N+S+E+W)

        # Initialize fields
        self.load_from_present_values()
         

    def load_from_present_values(self):
        for item in configvars:
            try:
                self.entry_[item].delete(0,END)
                self.entry_[item].insert(0,str(eval(item)))
            except:
                self.entry_[item].delete(0,END)
                self.entry_[item].insert(0,'')

    def load_factory_defaults(self):
        for item in configvars:
            try:
                self.entry_[item].delete(0,END)
                self.entry_[item].insert(0,str(configvars_defaults[item]))
            except:
                self.entry_[item].delete(0,END)
                self.entry_[item].insert(0,'')
    
    def apply_changes(self):
        for item in configvars:
            try:
                if item not in configvars_strings:
                    globals()[item]=eval(self.entry_[item].get()) 
                else:    
                    globals()[item]=eval("'"+self.entry_[item].get()+"'") 
            except:
                print("I could not set the variable",item,". Perhaps was there a typo ?")
        application.update_interface_with_variables()
        self.destroy()
        return
    
    def write_to_global_cfg(self):
        if os.path.isfile(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg'):
            if os.path.isfile(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg.bak'):
                os.remove(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg.bak')
            os.rename(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg',Ortho4XP_dir+dir_sep+'Ortho4XP.cfg.bak')
        f=open(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg','w')
        for item in configvars:
            try:
                if item not in configvars_strings:
                    f.write(item+"="+self.entry_[item].get()+"\n")
                else:
                    f.write(item+"="+"'"+self.entry_[item].get()+"'"+'\n')
            except:
                print("I could not set the variable",item,". Perhaps was there a typo ?")
        return

    def load_from_global_cfg(self):
        try:
            exec(open(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg').read(),globals())
        except:
            print('\nFailure : the config file is not present or does follow the syntax.')
            print('_____________________________________________________________'+\
                '____________________________________')
        self.load_from_present_values()
        application.update_interface_with_variables()
        return

    def popup(self,item):
        popup = Tk()
        popup.wm_title("")
        label = ttk.Label(popup, text=self.explanation[item])
        label.pack(side="top", fill="x", padx=5,pady=self.pady)
        B1 = ttk.Button(popup, text="Ok", command = popup.destroy)
        B1.pack()
        return
    
    

##############################################################################

############################################################################################
class Ortho4XP_Graphical(Tk):

    def __init__(self):
        
        Tk.__init__(self)
        self.title('Ortho4XP '+version)
        toplevel = self.winfo_toplevel()
        try:
            toplevel.wm_state('zoomed')
        except:
            w = self.winfo_screenwidth()
            h = self.winfo_screenheight() - 60
            geom_string = "%dx%d+0+0" % (w,h)
            toplevel.wm_geometry(geom_string) 

        if self.winfo_screenheight()>=1024:
            self.pady=5
        else:
            self.pady=1

        self.columnconfigure(1,weight=1)
        self.rowconfigure(0,weight=1)
        sys.stdout=self
        
        # Variables
        self.red_flag        = IntVar()
        self.red_flag.set(0)
        self.lat             = IntVar()
        self.lat.set(45)
        self.lat.trace("w", self.clear_hidden_data)
        self.lon             = IntVar()
        self.lon.set(5)
        self.lon.trace("w", self.clear_hidden_data)
        self.bdc             = IntVar()
        self.bdc.set(0)
        self.bd              = StringVar()
        try:
            self.bd.set(default_build_dir)
        except:
            self.bd.set('')
        self.rl              = IntVar()
        self.rl.set(1)
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
        self.complexmasks     = IntVar()
        self.complexmasks.set(0)
        self.masksinland     = IntVar()
        self.masksinland.set(0)
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
        self.zlsea_choice=StringVar()
        self.zlsea_choice.set('')
        self.c_tms_r         = IntVar()
        self.c_tms_r.set(0)
        self.map_choice      = StringVar()
        self.map_choice.set('BI')
        self.seamap_choice      = StringVar()
        self.seamap_choice.set('')
        self.progress_attr   = IntVar()
        self.progress_attr.set(0)
        self.progress_down   = IntVar()
        self.progress_down.set(0)
        self.progress_mont   = IntVar()
        self.progress_mont.set(0)
        self.progress_conv   = IntVar()
        self.progress_conv.set(0)
        self.comp_func       = StringVar()
        self.comp_func.set('Do nothing')

        # Constants
        self.map_list        = ['None']+sorted(list(providers_dict)+list(combined_providers_dict))
        self.zl_list         = ['11','12','13','14','15','16','17','18','19']
        self.comp_func_list  = ['Do nothing','Exit program','Shutdown computer']
        # Frames
        self.frame_left       =  Frame(self, border=4,\
                                 relief=RIDGE,bg='light green')
        self.frame_right      =  Frame(self, border=4,\
                                 relief=RIDGE,bg='light green')
        self.frame_rdbtn      =  Frame(self.frame_left,\
                                 border=0,padx=5,pady=self.pady,bg="light green")
        self.frame_lastbtn    =  Frame(self.frame_left,\
                                 border=0,padx=5,pady=self.pady,bg="light green")
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
        self.frame_lastbtn.grid(row=23,column=0,columnspan=6,sticky=N+S+E+W)

        # Widgets style
        combostyle  = ttk.Style()
        combostyle.theme_create('combostyle', parent='alt',settings = {'TCombobox':\
             {'configure':{'selectbackground': 'white','selectforeground':'blue',\
              'fieldbackground': 'white','foreground': 'blue','background': 'white'}}})
        combostyle.theme_use('combostyle') 
        # Widgets
        self.earth_btn        =  Button(self.frame_left, text='Earth tile map',\
                                 command=self.earth_preview)
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
        self.label_bm         =  Label(self.frame_left,anchor=W,text="Build base mesh",\
                                   fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.title_road_level =  Label(self.frame_left,text='Road cplx :',anchor=W,bg="light green")
        self.road_level       =  Entry(self.frame_left,width=5,bg="white",fg="blue",textvariable=self.rl)
        self.del_osm_btn      =  Button(self.frame_left,text='Purge OSM data',command=self.purge_osm)
        self.get_osm_btn      =  Button(self.frame_left,text='Step 1 : Build vector data',command=self.build_poly_ifc)
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
        self.title_src        =  Label(self.frame_left,anchor=W,text="Imagery :",bg="light green") 
        self.map_combo        =  ttk.Combobox(self.frame_left,textvariable=self.map_choice,\
                                    values=self.map_list,state='readonly',width=10)
        self.title_zl         =  Label(self.frame_left,anchor=W,text="  Base zoomlevel  :",bg="light green")
        self.zl_combo         =  ttk.Combobox(self.frame_left,textvariable=self.zl_choice,\
                                    values=self.zl_list,state='readonly',width=3)
        self.title_seasrc     =  Label(self.frame_left,anchor=W,text="Sea source  :",bg="light green") 
        self.seamap_combo        =  ttk.Combobox(self.frame_left,textvariable=self.seamap_choice,\
                                    values=['']+self.map_list,state='readonly',width=6)
        self.title_zlsea         =  Label(self.frame_left,anchor=W,text="  Sea zoomlevel  :",bg="light green")
        self.zlsea_combo         =  ttk.Combobox(self.frame_left,textvariable=self.zlsea_choice,\
                                    values=self.zl_list,state='readonly',width=3)
        self.preview_btn      =  Button(self.frame_left, text='Choose custom zoomlevel',command=self.preview_tile)
        self.skipdown_check   =  Checkbutton(self.frame_left,text="Skip downloads",\
                                    anchor=W,variable=self.skipd,command=self.set_skip_downloads,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.skipconv_check   =  Checkbutton(self.frame_left,text="Skip converts",\
                                    anchor=W,variable=self.skipc,command=self.set_skip_converts,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.check_response   =  Checkbutton(self.frame_left,text="Check against white textures ",\
                                    anchor=W,variable=self.c_tms_r,command=self.set_c_tms_r,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.verbose_check    =  Checkbutton(self.frame_left,text="Verbose output",\
                                    anchor=W,variable=self.verbose,command=self.set_verbose_output,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.cleantmp_check   =  Checkbutton(self.frame_left,text="Clean tmp files",\
                                    anchor=W,variable=self.cleantmp,command=self.set_cleantmp,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.cleanddster_check=  Checkbutton(self.frame_left,text="Clean unused dds/ter files",\
                                    anchor=W,variable=self.cleanddster,command=self.set_cleanddster,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.complexmasks_check   =  Checkbutton(self.frame_left,text="Complex masks",\
                                    anchor=W,variable=self.complexmasks,command=self.set_complexmasks,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.masksinland_check=  Checkbutton(self.frame_left,text="Use masks for inland",\
                                    anchor=W,variable=self.masksinland,command=self.set_masksinland,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.label_overlay        =  Label(self.frame_left,justify=RIGHT,anchor=W,text="Build Overlays",\
                                    fg = "light green",bg = "dark green",font = "Helvetica 16 bold italic")
        self.sniff_check      =  Checkbutton(self.frame_left,text="Custom overlay dir :",\
                                    anchor=W,variable=self.sniff,command=self.choose_sniff_dir,bg="light green",\
                                    activebackground="light green",highlightthickness=0)                    
        self.sniff_dir_entry  =  Entry(self.frame_left,width=30,bg="white",fg="blue",textvariable=self.sniff_dir)
        self.sniff_btn        =  Button(self.frame_left,text='(Build overlay)',command=self.build_overlay_ifc)
        self.build_tile_btn   =  Button(self.frame_left,text='Step 3 : Build Tile',command=self.build_tile_ifc)
        self.title_masks_width=  Label(self.frame_left,text='Masks_width :',anchor=W,bg="light green")
        self.masks_width_e    =  Entry(self.frame_left,width=5,bg="white",fg="blue",textvariable=self.mw)
        self.build_masks_btn  =  Button(self.frame_left,text='(Step 2.5 : Build Masks)',command=self.build_masks_ifc)
        self.title_ratio_water=  Label(self.frame_left,text='Ratio_water : ',bg="light green")
        self.ratio_water_entry=  Entry(self.frame_left,width=4,bg="white",fg="blue",textvariable=self.rw)
        self.read_cfg_btn     =  Button(self.frame_lastbtn,text='Read tile Cfg ',command=self.read_cfg)
        self.write_cfg_btn    =  Button(self.frame_lastbtn,text='Write tile Cfg',command=self.write_cfg)
        self.expert_cfg_btn   =  Button(self.frame_lastbtn,text='Global Config ',command=self.expert_cfg)
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
        self.earth_btn.grid(row=0,column=0,columnspan=6,padx=5,pady=self.pady,sticky=N+S+E+W)
        self.label_tc.grid(row=1,column=0,columnspan=6,sticky=W+E)
        self.title_lat.grid(row=2,column=0, padx=5, pady=self.pady,sticky=E+W)
        self.latitude.grid(row=2,column=1, padx=5, pady=self.pady,sticky=W)
        self.title_lon.grid(row=2,column=2, padx=5, pady=self.pady,sticky=E+W) 
        self.longitude.grid(row=2,column=3, padx=5, pady=self.pady,sticky=W)
        self.build_dir_check.grid(row=3,column=0,columnspan=2, pady=self.pady,sticky=N+S+E+W) 
        self.build_dir_entry.grid(row=3,column=2,columnspan=4, padx=5, pady=self.pady,sticky=W+E)
        self.label_bm.grid(row=4,column=0,columnspan=6,sticky=W+E)
        self.title_road_level.grid(row=5,column=0, padx=5, pady=self.pady,sticky=W+E) 
        self.road_level.grid(row=5,column=1, padx=5, pady=self.pady,sticky=W)
        self.del_osm_btn.grid(row=5,column=2, columnspan=2, pady=self.pady,sticky=N+S+W)
        self.get_osm_btn.grid(row=5,column=4, columnspan=2,padx=5, pady=self.pady,sticky=N+S+W+E)
        self.title_curv_tol.grid(row=6,column=0, padx=5, pady=self.pady,sticky=W+E) 
        self.curv_tol.grid(row=6,column=1, padx=5, pady=self.pady,sticky=W)
        self.min_angle_check.grid(row=6,column=2, padx=5, pady=self.pady,sticky=W)
        self.min_angle.grid(row=6,column=3, padx=5, pady=self.pady,sticky=W)
        self.build_mesh_btn.grid(row=6,column=4, columnspan=2,padx=5, pady=self.pady,sticky=N+S+W+E)
        self.custom_dem_check.grid(row=7,column=0,columnspan=2, padx=5, pady=self.pady,sticky=W)
        self.custom_dem_entry.grid(row=7,column=2,columnspan=4, padx=5, pady=self.pady,sticky=N+S+E+W)
        self.label_dsf.grid(row=8,column=0,columnspan=6,sticky=W+E)
        self.title_src.grid(row=9,column=0,sticky=E+W,padx=5,pady=self.pady)
        self.map_combo.grid(row=9,column=1,padx=5,pady=self.pady,sticky=W)
        self.title_zl.grid(row=9,column=2,sticky=N+S+E+W,padx=5,pady=self.pady)
        self.zl_combo.grid(row=9,column=3,columnspan=1,padx=5,pady=self.pady,sticky=W)
        self.title_seasrc.grid(row=10,column=0,sticky=E+W,padx=5,pady=self.pady)
        self.seamap_combo.grid(row=10,column=1,padx=5,pady=self.pady,sticky=W)
        self.title_zlsea.grid(row=10,column=2,sticky=N+S+E+W,padx=5,pady=self.pady)
        self.zlsea_combo.grid(row=10,column=3,columnspan=1,padx=5,pady=self.pady,sticky=W)
        self.preview_btn.grid(row=9,column=4, columnspan=2,padx=5, pady=self.pady,sticky=N+S+W+E)
        self.skipdown_check.grid(row=12,column=0,columnspan=2, pady=self.pady,sticky=N+S+E+W)
        self.skipconv_check.grid(row=12,column=2,columnspan=1, pady=self.pady,sticky=N+S+E+W)
        self.check_response.grid(row=12,column=3,columnspan=3,sticky=W)
        self.verbose_check.grid(row=13,column=0,columnspan=2, pady=self.pady,sticky=N+S+W)
        self.cleantmp_check.grid(row=13,column=2,columnspan=1, pady=self.pady,sticky=N+S+W)
        self.cleanddster_check.grid(row=13,column=3,columnspan=2, pady=self.pady,sticky=N+S+W)
        self.complexmasks_check.grid(row=14,column=0,columnspan=2, pady=self.pady,sticky=N+S+W)
        self.masksinland_check.grid(row=14,column=2,columnspan=1, pady=self.pady,sticky=N+S+W)
        self.title_masks_width.grid(row=15,column=0, padx=5, pady=self.pady,sticky=W+E) 
        self.masks_width_e.grid(row=15,column=1, padx=5, pady=self.pady,sticky=W)
        self.title_ratio_water.grid(row=15,column=2,columnspan=1, padx=5, pady=self.pady,sticky=W) 
        self.ratio_water_entry.grid(row=15,column=3, padx=5, pady=self.pady,sticky=W)
        self.build_masks_btn.grid(row=15,column=4,columnspan=2,padx=5,pady=self.pady,sticky=N+S+W+E)
        self.build_tile_btn.grid(row=16,rowspan=3,column=4,columnspan=2,padx=5,sticky=N+S+W+E)
        self.read_cfg_btn.grid(row=0,column=0,padx=5, pady=self.pady,sticky=N+S+W+E)
        self.write_cfg_btn.grid(row=0,column=1,padx=5, pady=self.pady,sticky=N+S+W+E)
        self.expert_cfg_btn.grid(row=0,column=2,padx=5, pady=self.pady,sticky=N+S+W+E)
        self.kill_proc_btn.grid(row=0,column=3,padx=5,pady=self.pady,sticky=N+S+W+E)
        self.exit_btn.grid(row=0,column=4, padx=5, pady=self.pady,sticky=N+S+W+E)
        self.title_progress_a.grid(row=16,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_attr.grid(row=16,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.title_progress_d.grid(row=17,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_down.grid(row=17,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.title_progress_c.grid(row=18,column=0,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.progressbar_conv.grid(row=18,column=2,columnspan=2,padx=5,pady=0,sticky=N+S+E+W)
        self.title_comp_func.grid(row=19,column=0,columnspan=2,padx=5,pady=self.pady,sticky=E+W)
        self.comp_func_combo.grid(row=19,column=2,columnspan=2,padx=5,pady=self.pady,sticky=E+W)
        self.label_overlay.grid(row=20,column=0,columnspan=6,sticky=W+E)
        self.sniff_check.grid(row=21,column=0,columnspan=2, pady=self.pady,sticky=N+S+E+W)
        self.sniff_dir_entry.grid(row=21,column=2,columnspan=3, padx=5, pady=self.pady,sticky=N+S+E+W)
        self.sniff_btn.grid(row=21,column=5,columnspan=1, padx=5, pady=self.pady,sticky=N+S+E+W)
        self.std_out.grid(row=0,column=0,padx=5,pady=self.pady,sticky=N+S+E+W)
        # read default choices from config file 
        self.update_interface_with_variables() 


    def update_interface_with_variables(self):
        try:
            self.water_type.set(water_option)
            self.map_choice.set(default_website)
            self.zl_choice.set(default_zl)
            if sea_texture_params != []:
                self.seamap_choice.set(str(sea_texture_params[0]))
                self.zlsea_choice.set(str(sea_texture_params[1]))
            self.rw.set(ratio_water)
            self.rl.set(road_level)
            self.ct.set(curvature_tol)
            if no_small_angles==True:
                self.minangc.set(1)
                self.minang.set(smallest_angle)
            else:
                self.minangc.set(0)
                self.minang.set('')
            if is_custom_dem==True:
                self.cdc.set(1)
                self.cde.set(custom_dem)
            else:
                self.cdc.set(0)
                self.cde.set('')
            self.skipd.set(skip_downloads)
            self.skipc.set(skip_converts)
            self.cleantmp.set(clean_tmp_files)
            self.cleanddster.set(clean_unused_dds_and_ter_files)
            self.verbose.set(verbose_output)
            self.c_tms_r.set(check_tms_response)
            self.mw.set(masks_width)
            self.sniff_dir.set(default_sniff_dir)
            self.complexmasks.set(complex_masks)
            self.masksinland.set(use_masks_for_inland)
        except:
            print("\nWARNING : the config variables are incomplete or do not follow the syntax,")
            print("I could not initialize all the parameters to your wish.")
            print('_____________________________________________________________'+\
                '____________________________________')
        return 
    
    def check_entry_params(self):
        try:
            test_road_level=int(self.road_level.get())
        except:
            print('\nFailure : parameter Roads cplx wrongly encoded.')
            print('_____________________________________________________________'+\
            '____________________________________')
            return 'error'
        try:
            test_curvature_tol=float(self.curv_tol.get())
            if test_curvature_tol < 0.001 or test_curvature_tol>10000:
                print('\nFailure : curvature_tol exceeds limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return 'error'
        except:
            print('\nFailure : curvature_tol wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return  'error'
        if not self.minangc.get()==0:
            try:
                test_smallest_angle=int(self.minang.get())
            except:
                print('\nFailure : minimum angle wrongly encoded.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return 'error'
            if (test_smallest_angle<0) or (test_smallest_angle>30):
                print('\nFailure : minimum angle larger than 30° not allowed.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return 'error'
        try:
            test_masks_width=int(self.masks_width_e.get())
            if test_masks_width < 1 or test_masks_width>512:
                print('\nFailure : masks_width off limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return 'error'
        except:
            print('\nFailure : masks_width wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
            return 'error'
        if not self.water_type.get()==1:
            try:
                test_ratio_water=float(self.ratio_water_entry.get())
                if test_ratio_water<0 or test_ratio_water>1:
                    print('\nFailure : ratio_water off limits.')
                    print('_____________________________________________________________'+\
                    '____________________________________')
                    return 'error'
            except:
                print("The ratio_water parameter is wrongly encoded.")
                return 'error'
        return 'success'
    
    def update_variables_with_interface(self):
        if self.check_entry_params()!='success':
            print("Test failed, no variable has been updated.\n")
            return  'error'
        globals()['default_website']=self.map_choice.get()
        globals()['default_zl']=self.zl_choice.get()
        if self.seamap_choice.get() != '': 
           globals()['sea_texture_params']=[self.seamap_choice.get(),int(self.zlsea_choice.get())]
        else:
           globals()['sea_texture_params']=[]
        globals()['road_level']=int(self.road_level.get())
        globals()['curvature_tol']=float(self.curv_tol.get())
        if self.minangc.get()==0:
            globals()['no_small_angles']=False
        else:
            globals()['no_small_angles']=True
        if not self.minangc.get()==0:
            globals()['smallest_angle']=int(self.minang.get())
        else: 
            globals()['smallest_angle']=0
        if self.cdc.get()==1:
            globals()['is_custom_dem']=True
        else:
            globals()['is_custom_dem']=False
        globals()['custom_dem']=self.cde.get()
        globals()['masks_width']=int(self.masks_width_e.get())
        if not self.water_type.get()==1:
            globals()['ratio_water']=float(self.ratio_water_entry.get())
        if self.skipd.get()==1:
            self.skipc.set(1)
            globals()['skip_downloads']=True
            globals()['skip_converts']=True
        else:
            globals()['skip_downloads']=False  
        if self.skipc.get()==0:
            globals()['skip_converts']=False
            if self.skipd.get()==1:
                self.skipc.set(1)
                globals()['skip_converts']=True
        else:
            globals()['skip_converts']=True
        if self.c_tms_r.get()==0:
            globals()['check_tms_response']=False
        else:
            globals()['check_tms_response']=True
        if self.verbose.get()==0:
            globals()['verbose_output']=False
        else:
            globals()['verbose_output']=True
        if self.cleantmp.get()==0:
            globals()['clean_tmp_files']=False
        else:
            globals()['clean_tmp_files']=True
        if self.cleanddster.get()==0:
            globals()['clean_unused_dds_and_ter_files']=False
        else:
            globals()['clean_unused_dds_and_ter_files']=True
        if self.complexmasks.get()==0:
            globals()['complex_masks']=False
        else:
            globals()['complex_masks']=True
        if self.masksinland.get()==0:
            globals()['use_masks_for_inland']=False
        else:
            globals()['use_masks_for_inland']=True
        if self.sniff.get()==1:
            globals()['default_sniff_dir']=self.sniff_dir_entry.get()
        return 'success' 
           
    def write(self,text):
        if text=='' or text[-1]!='\r':
            self.std_out.insert('end',str(text))
            self.std_out.see('end')
        else:
            self.std_out.delete('end linestart','end') 
            self.std_out.insert('end',str(text))
            self.std_out.see('end')
        return

    def flush(self):
        return
    
    def clear_hidden_data(self,*args):
        self.zone_list=[]
        try:
            del(self.dem)
        except:
            pass
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
    
    def preview_tile(self):
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        self.preview_window=Preview_window(lat,lon) 
        return
    
    def earth_preview(self):
        self.earth_window=Earth_Preview_window()
        return
    
    def purge_osm(self):
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        osm_dir=os.path.join(Ortho4XP_dir,'OSM_data',long_latlon(lat,lon))
        try:
            shutil.rmtree(osm_dir)
        except:
            print('_____________________________________________________________'+\
            '____________________________________')
        return
    
    def build_poly_ifc(self):
        global build_dir, road_level
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
        strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        provider_code=self.map_choice.get()
        if provider_code!='None':
            try:
                road_level=int(self.road_level.get())
            except:
                print('\nFailure : parameter Roads cplx wrongly encoded.')
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
            print("\nStep 1 : Building vector data for tile "+strlat+strlon+" : ")
            print("--------\n")
            fargs_build_poly_file=[lat,lon,build_dir]
            build_poly_file_thread=threading.Thread(\
                    target=build_poly_file,\
                    args=fargs_build_poly_file)
            build_poly_file_thread.start()
        else:
            print("\nStep 1 : Building landclass and patch data for tile "+strlat+strlon+" : ")
            print("--------\n")
            base_sniff_dir=self.sniff_dir_entry.get()
            file_to_sniff=base_sniff_dir+dir_sep+"Earth nav data"+dir_sep+\
                      strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'
            if not os.path.isfile(file_to_sniff):
                print('\nFailure : there is no file to sniff from at the indicated place.')
                print('_____________________________________________________________'+\
                      '____________________________________')
                return
            dem_alternative=self.custom_dem_entry.get()
            fargs_build_poly=[lat,lon,build_dir,file_to_sniff,dem_alternative]
            build_poly_thread=threading.Thread(target=build_landclass_poly_file,args=fargs_build_poly)
            build_poly_thread.start()
        return

    def build_mesh_ifc(self):
        global build_dir,curvature_tol,no_small_angles,smallest_angle
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        try:
            curvature_tol=float(self.curv_tol.get())
            if curvature_tol < 0.0001 or curvature_tol>1000000:
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
        else:
            smallest_angle=0
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
                clean_tmp_files,dds_or_png,water_overlay,ratio_water,use_masks_for_inland,ortho_list,zone_list,sea_texture_params
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        strlatround='{:+.0f}'.format(floor(lat/10)*10).zfill(3)
        strlonround='{:+.0f}'.format(floor(lon/10)*10).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        mesh_file_name = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
        provider_code=self.map_choice.get()
        if os.path.isfile(mesh_file_name)!=True:
            if provider_code!='None':
                print("You must first construct the mesh !")
                return
            else:
                base_sniff_dir=self.sniff_dir_entry.get()
                file_to_sniff=base_sniff_dir+dir_sep+"Earth nav data"+dir_sep+\
                      strlatround+strlonround+dir_sep+strlat+strlon+'.dsf'
                if not os.path.isfile(file_to_sniff):
                    print('\nFailure : there is no file to sniff from at the indicated place.')
                    print('_____________________________________________________________'+\
                      '____________________________________')
                    return
                dem_alternative=self.custom_dem_entry.get()
                print("\nTranscoding Tile "+strlat+strlon+" : ")
                print("------------------------\n")
                fargs_re_encode_dsf=[lat,lon,build_dir,file_to_sniff,keep_orig_zuv,dem_alternative,seven_zip]
                re_encode_dsf_thread=threading.Thread(target=re_encode_dsf,args=fargs_re_encode_dsf)
                re_encode_dsf_thread.start()
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
        zoomlevel=self.zl_choice.get()
        if self.seamap_choice.get() != '': 
           sea_texture_params=[self.seamap_choice.get(),int(self.zlsea_choice.get())]
        else:
           sea_texture_params=[]
        ortho_list=zone_list[:]
        if provider_code!='None':
            ortho_list.append([[lat,lon,lat,lon+1,lat+1,lon+1,lat+1,lon,lat,lon],\
                        str(zoomlevel),str(provider_code)])
        self.write_cfg()
        print("\nStep 3 : Building Tile "+strlat+strlon+" : ")
        print("--------\n")
        fargs_build_tile=[lat,lon,build_dir,mesh_file_name,True]
        build_tile_thread=threading.Thread(target=build_tile,\
                args=fargs_build_tile)
        build_tile_thread.start()
        return
    
    def build_masks_ifc(self):
        global lat,lon,build_dir,water_overlay,masks_width,complex_masks
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        try:
            masks_width=int(self.masks_width_e.get())
            if masks_width < 1 or masks_width>512:
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
        mesh_file_name = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
        if os.path.isfile(mesh_file_name)!=True:
            print("You must first construct the mesh !")
            return
        print("\nStep 2.5 : Building Masks for Tile "+strlat+strlon+" : ")
        print("----------\n")
        if complex_masks==False:
            mesh_file_name_list=[mesh_file_name]
        else:
            mesh_file_name_list=[]
            for closelat in [lat-1,lat,lat+1]:
                for closelon in [lon-1,lon,lon+1]:
                    strcloselat='{:+.0f}'.format(closelat).zfill(3)
                    strcloselon='{:+.0f}'.format(closelon).zfill(4)
                    if self.build_dir_entry.get()=='' or self.build_dir_entry.get()[-1]=='/':
                        closemesh_file_name=build_dir+dir_sep+'..'+dir_sep+'zOrtho4XP_'+strcloselat+strcloselon+\
                                   dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                    else:
                        closemesh_file_name=build_dir+dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                    if os.path.isfile(closemesh_file_name):
                        mesh_file_name_list.append(closemesh_file_name)
        fargs_build_masks=[lat,lon,build_dir,mesh_file_name_list,maskszl]
        build_masks_thread=threading.Thread(target=build_masks,\
                args=fargs_build_masks)
        build_masks_thread.start()
        return

    def build_tile_list_ifc(self,tile_list,read_config,use_existing_mesh,bbmasks,bboverlays):
        global default_website, default_zl, sea_texture_params, min_area, curvature_tol,\
               no_small_angles, smallest_angle, water_overlay, ratio_water, masks_width
        default_website=self.map_choice.get()
        default_zl=self.zl_choice.get()
        if self.seamap_choice.get() != '': 
           sea_texture_params=[self.seamap_choice.get(),int(self.zlsea_choice.get())]
        else:
           sea_texture_params=[]
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
        else:
            smallest_angle=0 
        try:
            masks_width=int(self.masks_width_e.get())
            if masks_width < 1 or masks_width>512:
                print('\nFailure : masks_width off limits.')
                print('_____________________________________________________________'+\
                '____________________________________')
                return
        except:
            print('\nFailure : masks_width wrongly encoded.')
            print('_____________________________________________________________'+\
                '____________________________________')
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
        build_dir_option=self.build_dir_entry.get()
        fargs_build_tile_list=[tile_list,build_dir_option,read_config,use_existing_mesh,bbmasks,bboverlays]
        build_tile_list_thread=threading.Thread(target=build_tile_list,\
                args=fargs_build_tile_list)
        build_tile_list_thread.start()
        return

    def read_cfg(self):
        global build_dir,water_option,ratio_water,min_area,curvature_tol,\
               no_small_angles,smallest_angle,default_website,default_zl,\
               skip_downloads,skip_converts,verbose_output,clean_tmp_files,\
               dds_or_png,check_tms_response,complex_masks,use_masks_for_inland,zone_list,sea_texture_params, custom_dem
        [lat,lon]=self.load_latlon()
        if lat=='error':
            return
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        try:
            exec(open(build_dir+dir_sep+'Ortho4XP_'+short_latlon(lat,lon)+'.cfg').read(),globals())
        except:
            try:
                exec(open(build_dir+dir_sep+'Ortho4XP.cfg').read(),globals())
            except:
                print('\nFailure : the tile specific config file is not present or does follow the syntax.')
                print('_____________________________________________________________'+\
                    '____________________________________')
                return 
        self.update_interface_with_variables()
        return
      
    def write_cfg(self):
        if self.check_entry_params()!='success':
            print("No config file was written.\n")
            return
        self.update_variables_with_interface()
        [lat,lon]=self.load_latlon()
        if lat=='error':
           return 'error'
        strlat='{:+.0f}'.format(lat).zfill(3)
        strlon='{:+.0f}'.format(lon).zfill(4)
        if self.build_dir_entry.get()=='':
            build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
        else:
            build_dir=self.build_dir_entry.get()
            if build_dir[-1]=='/':
                build_dir=build_dir[:-1]+dir_sep+'zOrtho4XP_'+strlat+strlon
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)
        try:
            fbuild=open(build_dir+dir_sep+'Ortho4XP_'+short_latlon(lat,lon)+'.cfg','w')
        except:
            print("\nI could not open a file for writing at the indicated location.")
            print("\n Failure.")
            print('_____________________________________________________________'+\
                '____________________________________')
            return 'error'
        fbuild.write("# Tile specific config file : lat="+str(lat)+", lon="+str(lon)+"\n")
        for item in configvars:
            if item not in configvars_strings:    
                fbuild.write(str(item)+"="+str(eval(item))+"\n") 
            else:
                fbuild.write(str(item)+"='"+str(eval(item))+"'\n") 
        fbuild.write("zone_list=[]\n")
        for zone in zone_list:
            fbuild.write("zone_list.append("+str(zone)+")\n")
        return
        
    def expert_cfg(self):
        self.update_variables_with_interface()
        self.expert_window=Expert_config() 
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

    def set_skip_downloads(self):
        global skip_downloads,skip_converts
        if self.skipd.get()==1:
            self.skipc.set(1)
            skip_downloads=True
            skip_converts=True
        else:
            skip_downloads=False  
        return
    
    def set_skip_converts(self):
        global skip_downloads, skip_converts
        if self.skipc.get()==0:
            skip_converts=False
            if self.skipd.get()==1:
                self.skipc.set(1)
                skip_converts=True
        else:
            skip_converts=True
        return
    
    def set_c_tms_r(self):
        global check_tms_response
        if self.c_tms_r.get()==0:
            check_tms_response=False
        else:
            check_tms_response=True
        return

    def set_verbose_output(self):
        global verbose_output 
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
    
    def set_complexmasks(self):
        global complex_masks
        if self.complexmasks.get()==0:
            complex_masks=False
        else:
            complex_masks=True
        return
    
    def set_masksinland(self):
        global use_masks_for_inland
        if self.masksinland.get()==0:
            use_masks_for_inland=False
        else:
            use_masks_for_inland=True
        return
    
    def kill_process(self):
        return

##############################################################################




##############################################################################
def build_pools(lat0,lon0,tri_list_kept,terrain,bathdem,nbath,division=landclass_mesh_division): 
    
    strlat='{:+.0f}'.format(lat0).zfill(3)
    strlon='{:+.0f}'.format(lon0).zfill(4)
    strlatround='{:+.0f}'.format(floor(lat0/10)*10).zfill(3)
    strlonround='{:+.0f}'.format(floor(lon0/10)*10).zfill(4)
    pool_cols           = division
    pool_rows           = division
    pool_nbr  = pool_rows*pool_cols
    pools_params=numpy.zeros((2*pool_nbr,18),'float32')
    pools_planes=numpy.zeros(2*pool_nbr,'uint16')
    pools_planes[0:pool_nbr]=5 
    pools_planes[pool_nbr:2*pool_nbr]=7 
    pools_lengths=numpy.zeros((2*pool_nbr),'uint16')
    pools=numpy.zeros((4*pool_nbr,9*pools_max_points),'uint16')
    pools_z_temp=numpy.zeros((2*pool_nbr,pools_max_points),'float32')
    pools_z_max=-9999*numpy.ones(2*pool_nbr,'float32')
    pools_z_min=9999*numpy.ones(2*pool_nbr,'float32')
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

    dico_new_pt={}
    len_dico_new_pt=0
    total_cross_pool=0
    textures={}
    for ter in terrain:
        for i in [1,2]:
            textures[ter+'_'+str(i)]=defaultdict(list)
    #textures['bathymetry_2']=defaultdict(list)


    for key in tri_list_kept:
        for tri in tri_list_kept[key]:
            tri_p=[]
            for i in [0,1,2]:
                [lonp,latp,z,u,v]=tri[i][:5]
                u=round(u*10)/10
                v=round(v*10)/10
                [pool_idx,pool_nx,pool_ny]=point_params(latp,lonp,lat0,lon0,pools_params,pool_cols,pool_rows)
                if key[-1]=='1': #False:
                    key2=str(pool_idx)+'_'+str(pool_nx)+'_'+str(pool_ny)
                else:
                    key2=key[:-2]+'_'+str(pool_idx)+'_'+str(pool_nx)+'_'+str(pool_ny)
                if key2 in dico_new_pt:
                    [pool_idx,pos_in_pool]=dico_new_pt[key2]
                    if key[-1]=='2':
                        pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                            pool_ny,0,round((1+u)/2*65535),round((1+v)/2*65535),round(tri[i][5]*65535),round(tri[i][6]*65535)]
                else:
                    len_dico_new_pt+=1
                    if key[-1]=='2': #True: 
                        pool_idx+=pool_nbr
                    pos_in_pool=pools_lengths[pool_idx]
                    dico_new_pt[key2]=[pool_idx,pos_in_pool]
                    if key[-1]=='1':
                        pools[pool_idx,5*pos_in_pool:5*pos_in_pool+5]=[pool_nx,\
                            pool_ny,0,round((1+u)/2*65535),round((1+v)/2*65535)]
                    else:
                        pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                            pool_ny,0,round((1+u)/2*65535),round((1+v)/2*65535),round(tri[i][5]*65535),round(tri[i][6]*65535)]
                    z=tri[i][2]
                    pools_z_temp[pool_idx,pos_in_pool]=z
                    pools_z_max[pool_idx] = pools_z_max[pool_idx] if pools_z_max[pool_idx] >= z else z
                    pools_z_min[pool_idx] = pools_z_min[pool_idx] if pools_z_min[pool_idx] <= z else z
                    pools_lengths[pool_idx]+=1
                tri_p+=[pool_idx,pos_in_pool]
            if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                pool_idx=tri_p[0]
                textures[key][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]    
            else:
                total_cross_pool+=1
                pool_idx='cross-pool'
                textures[key][pool_idx]+=tri_p
        if True: #key[:-2]!='terrain_Water': 
            continue # !!! disabled bathymetry test here !!!
        for tri in tri_list_kept[key]:
            tri_p=[]
            for i in [0,1,2]:
                [lonp,latp,z,u,v]=tri[i][:5]
                u=0
                v=0
                deep_factor=abs(altitude(lonp-lon0,latp-lat0,bathdem,nbath)-65535)/30
                deep_factor= 1 if deep_factor > 1 else deep_factor
                deep_factor= 0 if deep_factor < 0 else deep_factor
                [pool_idx,pool_nx,pool_ny]=point_params(latp,lonp,lat0,lon0,pools_params,pool_cols,pool_rows)
                if False: #key[-1]=='1':
                    key2=str(pool_idx)+'_'+str(pool_nx)+'_'+str(pool_ny)
                else:
                    key2=key[:-2]+'_'+str(pool_idx)+'_'+str(pool_nx)+'_'+str(pool_ny)
                if key2 in dico_new_pt:
                    [pool_idx,pos_in_pool]=dico_new_pt[key2]
                    #if key[-1]=='2':
                    pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                            pool_ny,0,32768,32768,0,round(deep_factor*65535)]
                else:
                    print("Warum ?")
                    continue 
                    len_dico_new_pt+=1
                    if True: #key[-1]=='2': 
                        pool_idx+=pool_nbr
                    pos_in_pool=pools_lengths[pool_idx]
                    dico_new_pt[key2]=[pool_idx,pos_in_pool]
                    if key[-1]=='1':
                        pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                            pool_ny,0,round((1+u)/2*65535),round((1+v)/2*65535),0,0]
                    else:
                        pools[pool_idx,7*pos_in_pool:7*pos_in_pool+7]=[pool_nx,\
                            pool_ny,0,round((1+u)/2*65535),round((1+v)/2*65535),round(tri[i][5]*65535),round(tri[i][6]*65535)]
                    z=tri[i][2]
                    pools_z_temp[pool_idx,pos_in_pool]=z
                    pools_z_max[pool_idx] = pools_z_max[pool_idx] if pools_z_max[pool_idx] >= z else z
                    pools_z_min[pool_idx] = pools_z_min[pool_idx] if pools_z_min[pool_idx] <= z else z
                    pools_lengths[pool_idx]+=1
                tri_p+=[pool_idx,pos_in_pool]
            if tri_p[0]==tri_p[2] and tri_p[2]==tri_p[4]:
                pool_idx=tri_p[0]
                textures['bathymetry_2'][pool_idx]+=[tri_p[1],tri_p[3],tri_p[5]]    
            else:
                total_cross_pool+=1
                pool_idx='cross-pool'
                textures['bathymetry_2'][pool_idx]+=tri_p

    print("Max pool length : ",max(pools_lengths)," for a limit value of 65535.")

    for pool_idx in range(0,2*pool_nbr):
        altmin=pools_z_min[pool_idx]
        altmax=pools_z_max[pool_idx]
        if altmin < -32000:
            scale=65535
            inv_stp=1
        elif altmax-altmin < 770:
            scale=771   # 65535= 771*85
            inv_stp=85
        elif altmax-altmin < 1284:
            scale=1285 # 66535=1285*51
            inv_stp=51
        elif altmax-altmin < 4368:
            scale=4369 # 65535=4369*15
            inv_stp=15
        else:
            scale=13107
            inv_stp=5
        if snap_to_z_grid:
            scale=65535
            inv_stp=1
        pools_params[pool_idx,4]=scale
        pools_params[pool_idx,5]=floor(altmin) if floor(altmin)>-32000 else -32768
        for pos_in_pool in range(0,pools_lengths[pool_idx]):
            pools[pool_idx,pools_planes[pool_idx]*pos_in_pool+2]=int(round((pools_z_temp[pool_idx,\
                    pos_in_pool]-pools_params[pool_idx,5])*inv_stp))

    return (pool_nbr,pools_params,pools_planes,pools_lengths,pools,textures)
##############################################################################





##############################################################################
def write_geod_atom(f,bGEOD,pool_nbr,pools_params,pools_planes,pools_lengths,pools):
    # f is the file handler we shall write in
    # bGEOD is an external byte string containing pools/scals which we wish to reuse

    # we first compute the size of the GEOD atom :
    size_of_geod_atom=8+len(bGEOD)
    for k in range(0,2*pool_nbr):
        if pools_lengths[k]>0:
            size_of_geod_atom+=21+pools_planes[k]*(9+2*pools_lengths[k])
    vprint(1,"   Size of GEOD atom : "+str(size_of_geod_atom)+" bytes.")   
    # next we encode it 
    f.write(b"DOEG")
    f.write(struct.pack('<I',size_of_geod_atom))
    f.write(bGEOD)
    for k in range(0,2*pool_nbr):
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
    for k in range(0,2*pool_nbr):
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
    return size_of_geod_atom
##############################################################################

##############################################################################
def write_dems_atom(f,bDEMS):
    if bDEMS!=b'':
        vprint(1,"   Size of DEMS atom : "+str(len(bDEMS))+" bytes.")   
        f.write(b"SMED")
        f.write(struct.pack('<I',8+len(bDEMS)))
        f.write(bDEMS)
    return len(bDEMS)
##############################################################################

##############################################################################
def write_cmds_atom(f,bCMDS,textures,dico_textures,dico_new_pool):
    # f is the file handler we shall write in
    # bCMDS is an external byte string contained commands which we wish to reuse
    # textures is the dictionnary for the textured mesh
    # dico_new_pool is the dictionnary for the index of pools after elimination of zero length ones
   
    # we first compute the size of the CMDS atom :
    size_of_cmds_atom=8+len(bCMDS)
    for key in textures:
        if len(textures[key])==0:
            continue
        size_of_cmds_atom+=3
        for pool_idx in textures[key]:
            if pool_idx != 'cross-pool':
                size_of_cmds_atom+= 13+2*(len(textures[key][pool_idx])+\
                        ceil(len(textures[key][pool_idx])/255))
            else:
                size_of_cmds_atom+= 13+2*(len(textures[key][pool_idx])+\
                        ceil(len(textures[key][pool_idx])/510))
    vprint(1,"   Size of CMDS atom : "+str(size_of_cmds_atom)+" bytes.")
    f.write(b'SDMC')                               # CMDS header 
    f.write(struct.pack('<I',size_of_cmds_atom))   # CMDS length
    f.write(bCMDS)
    for key in textures:
        if len(textures[key])==0:
            continue
        texture_idx=dico_textures[key] 
        #print("texture_idx = "+str(texture_idx))
        f.write(struct.pack('<B',4))           # SET DEFINITION 16
        f.write(struct.pack('<H',texture_idx)) # TERRAIN INDEX
        flag=int(key[-1])
        lod=-1 if flag==1 else overlay_lod
        for pool_idx in textures[key]:
            #print("  pool_idx = "+str(pool_idx))
            if pool_idx != 'cross-pool':
                f.write(struct.pack('<B',1))                          # POOL SELECT
                f.write(struct.pack('<H',dico_new_pool[pool_idx]))    # POOL INDEX
    
                f.write(struct.pack('<B',18))    # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack('<B',flag))  # FLAG
                f.write(struct.pack('<f',0))     # NEAR LOD
                f.write(struct.pack('<f',lod))    # FAR LOD
                
                blocks=floor(len(textures[key][pool_idx])/255)
                #print("     "+str(blocks)+" blocks")    
                for j in range(0,blocks):
                    f.write(struct.pack('<B',23))   # PATCH TRIANGLE
                    f.write(struct.pack('<B',255))  # COORDINATE COUNT

                    for k in range(0,255):
                        f.write(struct.pack('<H',textures[key][pool_idx][255*j+k]))  # COORDINATE IDX
                remaining_tri_p=len(textures[key][pool_idx])%255
                if remaining_tri_p != 0:
                    f.write(struct.pack('<B',23))               # PATCH TRIANGLE
                    f.write(struct.pack('<B',remaining_tri_p))  # COORDINATE COUNT
                    for k in range(0,remaining_tri_p):
                        f.write(struct.pack('<H',textures[key][pool_idx][255*blocks+k]))  # COORDINATE IDX
            elif pool_idx == 'cross-pool':
                pool_idx_init=textures[key][pool_idx][0]
                f.write(struct.pack('<B',1))                               # POOL SELECT
                f.write(struct.pack('<H',dico_new_pool[pool_idx_init]))    # POOL INDEX
                f.write(struct.pack('<B',18))    # TERRAIN PATCH FLAGS AND LOD
                f.write(struct.pack('<B',flag))  # FLAG
                f.write(struct.pack('<f',0))     # NEAR LOD
                f.write(struct.pack('<f',lod))  # FAR LOD
                
                blocks=floor(len(textures[key][pool_idx])/510)
                for j in range(0,blocks):
                    f.write(struct.pack('<B',24))   # PATCH TRIANGLE CROSS-POOL
                    f.write(struct.pack('<B',255))  # COORDINATE COUNT
                    for k in range(0,255):
                        f.write(struct.pack('<H',dico_new_pool[textures[key][pool_idx][510*j+2*k]]))    # POOL IDX
                        f.write(struct.pack('<H',textures[key][pool_idx][510*j+2*k+1]))                 # POS_IN_POOL IDX
                remaining_tri_p=int((len(textures[key][pool_idx])%510)/2)
                if remaining_tri_p != 0:
                    f.write(struct.pack('<B',24))               # PATCH TRIANGLE CROSS-POOL
                    f.write(struct.pack('<B',remaining_tri_p))  # COORDINATE COUNT
                    for k in range(0,remaining_tri_p):
                        f.write(struct.pack('<H',dico_new_pool[textures[key][pool_idx][510*blocks+2*k]]))   # POOL IDX
                        f.write(struct.pack('<H',textures[key][pool_idx][510*blocks+2*k+1]))                # POS_IN_PO0L IDX
    try:
        application.progress_attr.set(98)
        if application.red_flag.get()==1:
            print("Attribution process interrupted.")
            return
    except:
        pass
    return size_of_cmds_atom
##############################################################################


##############################################################################
# Indices for making n-2 triangles out of n vertices of a tri strip
class MakeStripIndices(dict):
    def __missing__(self, n):
        a = numpy.concatenate([i%2 and [i, i+2, i+1] or [i, i+1, i+2] for i in range(n-2)])
        self[n] = a
        return a
##############################################################################

##############################################################################
# Indices for making n-2 triangles out of n vertices of a tri fan
class MakeFanIndices(dict):
    def __missing__(self, n):
        a = zeros(3*(n-2), int)
        a[1:n*3:3] += numpy.arange(1,n-1)
        a[2:n*3:3] += numpy.arange(2,n)
        self[n] = a
        return a
##############################################################################


##############################################################################
def progress_bar(nbr,percentage,message=None): 
    dico_progress={1:'attr',2:'down',3:'conv'}
    try:
        eval("application.progress_"+dico_progress[nbr]+".set(percentage)")
        #if application.red_flag.get()==1:
        #    if message: 
        #        print(message)
        #    else:
        #        print("Process interrupted.")
        #    return
    except:
        pass
    return
##############################################################################

##############################################################################
def vprint(verbosity,*args):
    if verbose_output>=verbosity: 
        print(*args)
##############################################################################

##############################################################################
def logprint(*args):
    with open(os.path.join(Ortho4XP_dir,"Ortho4XP.log"),"a") as f:
        f.write(time.strftime("%c")+' | '+' '.join([str(x) for x in args])+"\n")
##############################################################################

##############################################################################
def lvprint(verbosity,*args):
    if verbose_output>=verbosity: 
        print(*args)
    logprint(*args)
##############################################################################

##############################################################################
def check_flag():
    try:
        return application.red_flag.get()
    except:
        return False
##############################################################################

##############################################################################
def set_flag(value):
    try:
        application.red_flag.set(value)
    except:
        pass
##############################################################################
    
##############################################################################
def exit_message_and_bottom_line(message="Process interrupted."):
    logprint(message)
    print(message)
    print('_____________________________________________________________'+\
            '____________________________________')
##############################################################################

##############################################################################
def timings_and_bottom_line(tinit):
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-tinit))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
##############################################################################




##############################################################################
#                                                                            #
#   LE PROGRAMME CHEF, QUI DIRIGE TOUT MAIS QUI NE FAIT RIEN.                #
#                                                                            #
##############################################################################

if __name__ == '__main__':
    initialize_providers_dict()
    initialize_extents_dict()
    initialize_color_filters_dict()
    initialize_combined_providers_dict()
    if len(sys.argv)==1: # switch to the graphical interface
        ortho_list=[]
        zone_list=[]
        try: 
            exec(open(Ortho4XP_dir+dir_sep+'Ortho4XP.cfg').read())
        except:
            print("Global configuration file not found or corrupted, using factory defaults.")
        if not os.path.exists(Ortho4XP_dir+dir_sep+'OSM_data'):
            os.makedirs(Ortho4XP_dir+dir_sep+'OSM_data')
        if not os.path.exists(Ortho4XP_dir+dir_sep+'Tiles'):
            os.makedirs(Ortho4XP_dir+dir_sep+'Tiles')
        os.system(delete_cmd+" "+Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"*.jpg "+devnull_rdir)
        os.system(delete_cmd+" "+Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"*.png "+devnull_rdir)
        application = Ortho4XP_Graphical()
        application.mainloop()	    
        application.quit()
        sys.exit()
    # sequel is only concerned with command line (AND PERHAPS NOT UP TO DATE !!!) 
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
    if build_dir=="default":
        build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
    print("\nStep 1 : Building OSM and patch data for tile "+strlat+strlon+" : ")
    print("--------\n")
    build_poly_file(lat,lon,water_option,build_dir)
    print("\nStep 2 : Building mesh for tile "+strlat+strlon+" : ")
    print("--------\n")
    build_mesh(lat,lon,build_dir)
    print("\nStep 2.5 : Building Masks for Tile "+strlat+strlon+" : ")
    print("----------\n")
    mesh_file_name = build_dir+dir_sep+'Data'+strlat+strlon+".mesh"
    if complex_masks==False:
        mesh_file_name_list=[mesh_file_name]
    else:
        mesh_file_name_list=[]
        for closelat in [lat-1,lat,lat+1]:
            for closelon in [lon-1,lon,lon+1]:
                strcloselat='{:+.0f}'.format(closelat).zfill(3)
                strcloselon='{:+.0f}'.format(closelon).zfill(4)
                closemesh_file_name=build_dir+dir_sep+'..'+'zOrtho4XP_'+strcloselat+strcloselon+\
                               dir_sep+'Data'+strcloselat+strcloselon+".mesh"
                if os.path.isfile(closemesh_file_name):
                    mesh_file_name_list.append(closemesh_file_name)
    build_dir=Ortho4XP_dir+dir_sep+'Tiles'+dir_sep+'zOrtho4XP_'+strlat+strlon
    if not os.path.exists(build_dir+dir_sep+"textures"):
        os.makedirs(build_dir+dir_sep+"textures")
    build_masks(lat,lon,build_dir,mesh_file_name_list,maskszl)
    ortho_list=zone_list[:]
    if default_website!='None':
        ortho_list.append([[lat,lon,lat,lon+1,lat+1,lon+1,lat+1,lon,lat,lon],\
                    str(default_zl),str(default_website)])
    print("\nStep 3 : Building Tile "+strlat+strlon+" : ")
    print("--------\n")
    build_tile(lat,lon,build_dir,mesh_file_name,False)
    print('\nBon vol !')
##############################################################################
#                                                                            #
#                           THAT'S ALL FOLKS                                 #
#                                                                            #
##############################################################################





