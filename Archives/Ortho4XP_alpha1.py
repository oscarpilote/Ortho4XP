# vim: set nowrap tabstop=4 expandtab shiftwidth=4 softtabstop=4
###############################################################################
# Ortho4XP : Easy set-up of orthophotos for the X-Plane 10 flight simulator.  #
# Version  : alpha_1 released June 6th 2015 - File size : 98192C              #
# Copyright 2015 Oscar Pilote                                                 #
###############################################################################
#                                                                             #
#   LEGAL NOTICE :                                                            #
#                                                                             #
#   This program is free software: you can redistribute it and/or modify      #
#   it under the terms of the GNU General Public License as published by      #
#   the Free Software Foundation, either version 3 of the License, or         #
#   (at your option) any later version.                                       #
#                                                                             #
#   This program is distributed in the hope that it will be useful,           #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#   GNU General Public License for more details.                              #
#                                                                             #
#   You should have received a copy of the GNU General Public License         #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.     #
#                                                                             #
###############################################################################
#                                                                             #
#   MAIN CHARACTERISTICS :                                                    #
#                                                                             #
#   This python module contains tools to use aerial map tiles as textures     #
#   within X-Plane. Its main characteristics are                              #
#                                                                             #
#  1) Free software and cross-platform : its only dependencies are            #
#     Python 3 with a few modules (www.python.org), Image-magick              #
#     version 6.8 or higher (www.imagemagick.org) and Xptools built with      #
#     MAX_TUPLE_LEN=10 (developer.x-plane.com/tools/xptools/ or git repo).    #
#     The three of them are free software and cross-platform. No piece of     #
#     code of these programs is used here, only system calls.                 #
#                                                                             #
#  2) Easy to configure, to adapt and to extend with only basic               #
#     programming skills (at least as basic as the author's ones!). This      #
#     includes the possibility to add new features or orthophotos sources.    #
#     Python is really intuitive and fast learning, and the source code is    #
#     contained in a single text file and a single configuration file.        #
#                                                                             #
#  3) Double screening table for textures reallocation based on               #
#                                                                             #
#     Location : the user provides an ordered list of rectangular regions     #
#                (defined through latitude min max and longitude min max,     #
#                and which may overlap) with possibly separate target         #
#                zoomlevels and  sources for each of them. The order of       #
#                priority for texture allocation is then decreasing top to    #
#                bottom, in the same way as the scenery_packs.ini of          #
#                X-Plane does.                                                #
#                                                                             #
#     Terrain  : the user may decide which terrain types to replace with      #
#                orthophotos and which one to keep as in the input dsf file.  #
#                This may perhaps help users with lower end graphics cards    #
#                (don't expect too much though). One could for example keep   #
#                all original textures except those refered to as 'urban'     #
#                within X-Plane and replace them with high zoomlevel orthos.  #
#                                                                             #
#     Polygon types (which have nothing to do with the base mesh) can also    #
#     be screened to be kept or removed based on your configuration wills.    #
#     This includes in particular beaches and autogen, but actually much more.#
#                                                                             #
#  4) The triangles of the initial base mesh are kept unaffected, which means #
#     that there is not a single triangle recut (this is an important feature #
#     which provides a lot of flexibility).                                   #
#     No complicated patent here : this is made possible by the simplest of   #
#     ideas - a slight overlap of the tile textures (like the tiles on your   #
#     roof). This allows each triangle to be fully contained in at least      #
#     one orthophoto (unless your mesh is too coarse - in which case there is #
#     an easy turn around by decreasing the zoomlevel for that triangle only).#
#     This overlap occurs only at the level of the texture files (where a     #
#     slight part of the information isredundant), NOT in the sim where each  #
#     triangle has its only and proper texture.                               #
#                                                                             #
###############################################################################
#                                                                             #
# IMPORTANT ADDITIONAL REMARKS :                                              #
#                                                                             #
# - The private copy of aerial tiles, even for personal non commercial        #
#   activites, is subject to authorization for most websites, including       #
#   those referenced here.                                                    #
#   Contact the owner of copyright PRIOR to downloading them (some positive   #
#   feedbacks have been reported for limited use).                            #
#                                                                             #
# - The memory footprint of Ortho4XP is reasonable yet not tiny (flexibility  #
#   of Python comes at a cost). Expect something like 500Mb RAM use for a     #
#   stock X-Plane tile, 1 to 2 Gb for an HD mesh, and more than 4 Gb for an   #
#   UHD mesh (Alpilotx's naming). Elapsed time is essentially identical to    #
#   download time, the algorithm in itself runs for a couple of minute at     #
#   most and the texture compression (done by image-magick) are done          #
#   concurrently during file download.  You can expect 1Mb/sec if your        #
#   connection is good (don't expect much more even with very fast internet   #
#   connections though, we have to download tons of small files, not one big  #
#   file -  ping time is an important factor).                                #
#                                                                             #
# - Disk usage may rapidly become large if you download many tiles. A fully   #
#   covered tile with ZL16 orthophotos is roughly 2Gb. A factor 4 applies     #
#   then for each additional zoomlevel (and the other way around going down). #
#   Personal view-point : tayloring your favourite tiles is more fun and      #
#   more rewarding than massive downloads that you will use very rarely!      #
#                                                                             #
# - In addition to the main program the Ortho4XP.py file contains a number    #
#   of potentially helpful functions which won't be commented here, in        #
#   particular a tiny library to manipulate dsf files for other purposes.     #
#                                                                             #
# - The textures that are produced are 4096x4096. This limits the number of   #
#   files but breaks compatibility with X-Plane 9. Yet the code can easily    #
#   be adapted to a framework using 2048x2048 textures.                       #
#                                                                             #
###############################################################################
#                                                                             #
# EXAMPLE OF USE :                                                            #
#                                                                             #
# To build the tile +45+006 with ZL15 from Bing (copyright applies), but      #
# somewhat more detail (ZL17) in the Mont-Blanc area you could :              #
#                                                                             #
# 1) Copy your original +45+006.dsf tile file to your Ortho4XP directory      #
#    (the file can be any dsf containing a base mesh, 7z compressed or not)   #
#                                                                             #
# 2) Edit your Ortho4XP.cfg file so that it looks like the text inside the    #
#    the dashes below (file is case sensitive)                                #
#                                                                             #
#    -------------------------                                                #
#     [Ortho_zone_list]                                                       #
#     45.8 46 6.75 7 17 BI                                                    #
#     45 46 6 7 15 BI                                                         #
#                                                                             #
#     [Terrain_keep_list]                                                     #
#     terrainWater                                                            #
#                                                                             #
#     [Polygon_remove_list]                                                   #
#     beaches                                                                 #
#     autogen                                                                 #
#     --------------------------                                              #
#                                                                             #
# 3) Launch the python3 interpreter in a terminal. On python prompt issue     #
#    the following two commands (one after the other with ENTER key) :        #
#                                                                             #
#    from Ortho4XP_alpha1 import *                                            #
#    Ortho4XP('+45+006')                                                      #
#                                                                             #
#    Remember not to put the .dsf extension in the call.                      #
#                                                                             #
# 4) Step marks are issued on the terminal as operations go along.            #
#    Total time should be around 15min for the above example, depending       #
#    on your setup. After completion you can exit python issuing  :           #
#                                                                             #
#    quit()                                                                   #
#                                                                             #
#    at the command prompt. You can then transfer your newly created tile     #
#    to where needed in X-Plane (or use different folder management strategy) #
#                                                                             #
# 5) Bon vol !                                                                #
#                                                                             #
###############################################################################
       
from math import *
import array
import os, sys, threading, time
import requests, http.client
import random

###############################################################################
# Part 1 : User specific definitions, adapt to your computing setup.           
###############################################################################

dir_sep='/'
delete_command="rm "
copy_command="cp "
devnull_redirection= " >/dev/null 2>&1"


"""
You MUST adapt the following definitions to your setup, or the process
will fail.  All users, even Windows ones, should use '/' as directory
separator in filenames (not '\' for Windows users, since it is evaluated
by the python interpreter. Also, do NOT put a trailing '/' at the end
of directory names.
Contrast, brightness and saturation adjustement should be changed according
to the source and location of orthophotos your are using. Some are already
very contrasted, saturated and dark (like BI), other are lighter and a bit     
dull (FR). 
"""

"""                        
                          !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                          !!!  READ AND ADAPT CAREFULLY  !!!  
                          !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

                                          |  
                                          v 
"""         

Ortho4XP_dir        = "/home/oscarpilote/Ortho4XP"                             # Path to the directory where in particular textures jpegs will be saved. Choose a disk with some free space.
build_dir           = Ortho4XP_dir+"/My_new_tile"                              # Path to the directory where the tile will be built (this directory will not be created if it does not exists (in order to avoid building textures twice if a user just makes a typo).
default_config_file = Ortho4XP_dir+"/Ortho4XP.cfg"                                # Path to the config file for tile generation 
ratio_water         = 0.2                                                      # Use 0 for Orthophoto only, 1 X-Plane default water only, or in between for a mix. 
contrast_adjust     = 5                                                        # Constrast adjustment parameter passed to imagmagick in the process of converting jpeg tiles to dds.
brightness_adjust   = -5                                                       # Same for brightness,
saturation_adjust   = 20                                                       # and saturation.
if 'dar' in sys.platform:
    DSFTool_command     = Ortho4XP_dir+"/Utils/DSFTool.app"
elif 'win' in sys.platform:                                                      # Path for the DSFTool executable 
    DSFTool_command     = Ortho4XP_dir+"/Utils/DSFTool.exe"
else:
    DSFTool_command     = Ortho4XP_dir+"/Utils/DSFTool"
command_7z          = "7z "                                                    # If your dsf files are intially compressed
montage_command     = "montage "                                               # Path for the 'montage' command of imagemagick (used to concatenate small tiles into big textures).
convert_command     = "convert -brightness-contrast "+\
str(brightness_adjust)+"x"+str(contrast_adjust)+\
" -modulate 100,"+str(100+saturation_adjust)+",100 "
"""                        

                                          ^
                                          |

                          !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                          !!!  READ AND ADAPT CAREFULLY  !!!  
                          !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""         


###############################################################################
# Part 2 : Address book definitions : websites and presentation headers           
###############################################################################

###############################################################################
def url_construct(til_x,til_y,zoomlevel,website):
    if website=="BI":
        url="http://r2.ortho.tiles.virtualearth.net/tiles/a"\
+gtile_to_quadkey(til_x,til_y,zoomlevel)+".jpeg?g=136"
    elif website=="GO":
        url="http://khm0.googleapis.com/kh?&v=167&x="\
+str(til_x)+"&y="+str(til_y)+"&z="+str(zoomlevel)
    elif website=='OSM':
        url="http://a.tile.openstreetmap.org/"+str(zoomlevel)+"/"+str(til_x)+\
"/"+str(til_y)+".png"
    elif website=='OTM':  # Opentopomap                                                     
        if zoomlevel > 11:
            pass
        else:
            url="http://opentopomap.org/"+str(zoomlevel)+"/"+str(til_x)+\
"/"+str(til_y)+".png"
    elif  website=="FR": # France
        url=""
    elif website=="SP": # Spain
        url=""    
    elif website=="CH_Vs": # Swtizerland Wallis 
        server=random.randint(1,4)
        url=""
    elif website=="BE_Wa": # Belgium Wallonia
        url="http://geoservices.wallonie.be/arcgis/rest/services/IMAGERIE/\
ORTHO_LAST/MapServer/tile/"+str(zoomlevel)+"/"+str(til_y)+"/"\
+str(til_x)+"?blankTile=false"
    elif website=="IT": # Italy
        url=""
    elif website=="SE": # Sweden, Denmark and Norway 
        url=""
    else:
        print("The photo album \'"+website+"\' that you have requested \
is not implemented in this release.")	   
    return url
###############################################################################


###############################################################################
def fake_headers_construct(website):                                           # It is better to present oneself as a web browser rather than as a python ;-)
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) \
AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A'
    if website in ['BI','GO','OSM','OTM','FR','BE_Wa','SE']:
        fake_headers={'user-agent': user_agent}   
    elif website =='CH_Vs':
        fake_headers={}
    elif website=='IT':
        fake_headers={}
    return fake_headers
###############################################################################

###############################################################################
def filename_from_attributes(til_x_left,til_y_top,zoomlevel,website):
    '''
    This is a personal choice, but it would be wise to follow a common rule
    if files wish to be exchanged between users in the future.
    '''
    file_dir=Ortho4XP_dir+dir_sep+"Orthophotos"+dir_sep+website+dir_sep+"ZL"+\
str(zoomlevel)+dir_sep
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    file_name=str(til_y_top)+"_"+str(til_x_left)+"_"+website+str(zoomlevel)   
    file_ext=".jpg"
    return [file_dir,file_name,file_ext]
###############################################################################


###############################################################################
# Part 3 : A rudimentary library of methods to build python objects reflecting 
#          DSF properties.  
#
# In the following part we define DSF classes, along with Primitive, Patch,
# and Polygons. We build first basic methods for those,
# in particular in order to read from and write to dsf text files.
#
# Refer to http://wiki.x-plane.com/DSFTool_manual for specification 
# about DSF files and their objects.
###############################################################################


###############################################################################
class Primitive:
    
    def load_from(self,iostream,begin_line):
        self.TYPE=begin_line.split()[1]                                        # TYPE is a char which can be '0', '1' or '2'
        self.VERTEX=[]                                                         # VERTEX is a list, whose elements are arrays of doubles
        finished = False 
        while finished != True:
            line=iostream.readline()
            if 'END_PRIMITIVE' in line:
                finished=True
            else:
                vertex=array.array('d',[])        
                for coord in line.split()[1:]:
                    vertex.append(float(coord))
                self.VERTEX.append(vertex)
        return
        
    def write_to(self,iostream):
        iostream.write('BEGIN_PRIMITIVE '+self.TYPE+'\n')
        nbr_coord=len(self.VERTEX[0])
        for vertex in self.VERTEX:
            vertex_string=''
            for k in range(0,nbr_coord):
                if k!=2:    
                    vertex_string+=' '
                    vertex_string+=str('{:.9f}'.format(vertex[k]))
                else:
                    vertex_string+=' '
                    vertex_string+=str(int(vertex[k]))                         # Altitude is recorded (rounded) as int (anyway that way it is in most DEM 
            iostream.write('PATCH_VERTEX'+vertex_string+'\n')                  # files), this avoids issues with DSFTools 
        iostream.write('END_PRIMITIVE\n')
        return
###############################################################################


###############################################################################
class Patch:
    
    def load_from(self,iostream):
        tmp=iostream.readline().split()
        self.TERRAIN=tmp[1]
        self.LOD1=tmp[2]
        self.LOD2=tmp[3]
        self.PHYS=tmp[4]
        self.NBR_COORD=tmp[5]
        self.PRIMITIVE=[]
        finished=False
        while finished != True:
            lastpos=iostream.tell()
            line=iostream.readline()
            if 'BEGIN_PRIMITIVE' in line:
                prim=Primitive()
                prim.load_from(iostream,line)
                self.PRIMITIVE.append(prim)
            else:
                finished=True
                if 'END_PATCH' not in line:                                    # DSFTool does not closes the last BEGIN_PATCH after the last END_PRIMITIVE
                    iostream.seek(lastpos)                                     # so we need verify this
        return                                                                  
    
    def write_to(self,iostream):
        iostream.write('BEGIN_PATCH '+self.TERRAIN+' '+self.LOD1+' '\
                       +self.LOD2+' '+self.PHYS+' '+self.NBR_COORD+'\n')
        for prim in self.PRIMITIVE:
            prim.write_to(iostream)
        iostream.write('END_PATCH\n')
        return

    def simplify_primitives(self):                                             # We need to cut primitives of type 1 and 2 in single triangles because each 
        templist=[]                                                            # may end up in different layers after reallocation.         
        count=0
        for primitive in self.PRIMITIVE:
            if primitive.TYPE=='0':
                for k in range(0,len(primitive.VERTEX),3):
                    newprim=Primitive()
                    newprim.TYPE='0'
                    newprim.VERTEX=[primitive.VERTEX[k][:],\
                                    primitive.VERTEX[k+1][:],\
                                    primitive.VERTEX[k+2][:]]
                    templist.append(newprim)
            elif primitive.TYPE=='1':
                for k in range(0,len(primitive.VERTEX)-2):
                    newprim=Primitive()
                    newprim.TYPE='0'
                    if (k%2)==0:
                        newprim.VERTEX=[primitive.VERTEX[k][:],\
                                        primitive.VERTEX[k+1][:],\
                                        primitive.VERTEX[k+2][:]]
                    else:
                        newprim.VERTEX=[primitive.VERTEX[k+1][:],\
                                        primitive.VERTEX[k][:],\
                                        primitive.VERTEX[k+2][:]]
                    templist.append(newprim)
            elif  primitive.TYPE=='2':
                for k in range(0,len(primitive.VERTEX)-2):
                    newprim=Primitive()
                    newprim.TYPE='0'
                    newprim.VERTEX=[primitive.VERTEX[0][:],\
                                    primitive.VERTEX[k+1][:],\
                                    primitive.VERTEX[k+2][:]]
                    templist.append(newprim)
        self.PRIMITIVE=templist
        return

    def group_primitives_of_type_zero(self):
        templist=[]
        newprim=Primitive()
        newprim.TYPE='0'
        newprim.VERTEX=[]
        for primitive in self.PRIMITIVE:
            if primitive.TYPE=='0':
                for vertex in primitive.VERTEX:
                    newprim.VERTEX.append(vertex)
            else:
                templist.append(primitive)
        if newprim.VERTEX != []:    
            templist.append(newprim)
        self.PRIMITIVE=templist
        return
###############################################################################        


###############################################################################
class Polygon:
    
    def load_from(self,iostream):
        tmp=iostream.readline().split()
        self.TYPE=tmp[1]
        self.PARAMS=' '.join(tmp[2:])
        self.WINDING=[]
        finished_pol=False
        line=iostream.readline()
        while finished_pol != True:
            if 'BEGIN_WINDING' in line:
                winding=array.array('d',[])                                    # A winding for us is an array with an even nbr of coords representing
                finished_wind=False
                while finished_wind != True:                                   # succesive pairs of lat lon        
                    line=iostream.readline()
                    if 'END_WINDING' in line:
                        finished_wind=True
                    else:
                        winding.append(float(line.split()[1]))
                        winding.append(float(line.split()[2]))
                line=iostream.readline()
                self.WINDING.append(winding)
            else:
                finished_pol=True
        return                                                              
    
    def write_to(self,iostream):
        iostream.write('BEGIN_POLYGON '+self.TYPE+' '+self.PARAMS+'\n')
        for winding in self.WINDING:
            iostream.write('BEGIN_WINDING\n')
            for k in range(0,len(winding),2):
                iostream.write('POLYGON_POINT '\
                                +str('{:.9f}'.format(winding[k]))+' '\
                                +str('{:.9f}'.format(winding[k+1]))+'\n')
            iostream.write('END_WINDING\n')
        iostream.write('END_POLYGON\n')
        return

    def belongs_to(self,point):
        '''
        This procedures determines wether the input point belongs to the 
        polygon. The algorithm is based on the computation of the index 
        of the boundary of the polygon with respect to the point.
        '''
        total_winding_nbr=0
        for winding in self.WINDING:
            quadrants=[]
            for j in range(0,len(winding)//2):
                if winding[2*j] >= point[0]:
                    if winding[2*j+1] >= point[1]:
                        quadrants.append(1)
                    else:
                        quadrants.append(4)
                else:
                    if winding[2*j+1] >= point[1]:
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
                    if (winding[2*k]-point[0])*(winding[2*k+3]-point[1])\
-(winding[2*k+1]-point[1])*(winding[2*k+2]-point[0])>=0:
                        winding_nbr+=2
                    else:
                        winding_nbr+=-2
            change=quadrants[0]-quadrants[len(quadrants)-1]
            if change in [1,-1,0]:
                winding_nbr += change
            elif change in [-3,3]:
                winding_nbr += (-1)*change/3
            elif change in [-2,2]:
                if (winding[2*len(quadrants)-2]-point[0])*(winding[1]\
-point[1])-(winding[2*len(quadrants)-1]-point[1])*(winding[0]-point[0])>=0:
                    winding_nbr+=2
                else:
                    winding_nbr+=-2
            total_winding_nbr+=winding_nbr/4
        if total_winding_nbr == 0:
            retval=False
        else:
            retval=True
        return retval
###############################################################################


###############################################################################
class DSF: 
    
    def __init__(self):
        self.BOUNDARIES=[]
        self.PROPERTY=[]
        self.TERRAIN_DEF=[]
        self.OBJECT_DEF=[]
        self.POLYGON_DEF=[]
        self.NETWORK_DEF=[]
        self.RASTER_DEF=[]
        self.PATCH=[]
        self.POLYGON=[]
        self.SEGMENT=[]
        self.OBJECT=[]
        self.RASTER_DATA=[]
    
    def load_from(self,filename):
        t=time.time()
        print('Loading DSF object from file '+filename+' :') 
        
        self.file=open(filename,'r')
        self.PROPERTY=read_up_to('PROPERTY',self.file)                
        self.PROPERTY+=read_tag_zone('PROPERTY',self.file)
        self.BOUNDARIES=[0,0,0,0]
        for line in self.PROPERTY:
            if 'sim/west' in line:
                self.BOUNDARIES[2]=int(line.split()[2])
            elif 'sim/east' in line:
                self.BOUNDARIES[3]=int(line.split()[2])
            if 'sim/north' in line:
                self.BOUNDARIES[1]=int(line.split()[2])
            if 'sim/south' in line:
                self.BOUNDARIES[0]=int(line.split()[2])
        finished=False
        lasttag=''
        counter=0
        while finished != True:
            lastpos=self.file.tell()
            line=self.file.readline()
            self.file.seek(lastpos)
            if line=='':
                finished=True
                continue
            tag=line.split()[0]
            if tag == 'TERRAIN_DEF':
                self.TERRAIN_DEF=read_tag_zone('TERRAIN_DEF',self.file)
                print('   Terrain definitions loaded : '\
                      +str(len(self.TERRAIN_DEF))) 
            elif tag == 'POLYGON_DEF':
                self.POLYGON_DEF=read_tag_zone('POLYGON_DEF',self.file)
                print('   Polygon definitions loaded : '\
                      +str(len(self.POLYGON_DEF)))
            elif tag == 'OBJECT_DEF':
                self.OBJECT_DEF=read_tag_zone('OBJECT_DEF',self.file)
                print('   Object definitions  loaded : '\
                      +str(len(self.OBJECT_DEF)))
            elif tag == 'NETWORK_DEF':
                self.NETWORK_DEF=read_tag_zone('NETWORK_DEF',self.file)
                print('   Network definitions loaded : '\
                      +str(len(self.NETWORK_DEF)))
            elif tag == 'RASTER_DEF':
                self.RASTER_DEF=read_tag_zone('RASTER_DEF',self.file)
                print('   Raster definitions  loaded : '\
                      +str(len(self.RASTER_DEF)))
            elif tag == 'BEGIN_PATCH':
                if lasttag == 'Polygon': 
                    print('   Polygon instances   loaded : '+str(counter))
                    counter=0
                elif lasttag == 'Segment':
                    print('   Segment instances   loaded : '+str(counter))
                    counter=0
                lasttag='Patch'
                counter+=1
                patch=Patch()
                patch.load_from(self.file)
                self.PATCH.append(patch)
            elif tag == 'BEGIN_POLYGON':
                if lasttag == 'Patch': 
                    print('   Patch instances     loaded : '+str(counter))
                    counter=0
                elif lasttag == 'Segment':
                    print('   Segment instances   loaded : '+str(counter))
                    counter=0
                lasttag='Polygon'
                counter+=1
                polygon=Polygon()
                polygon.load_from(self.file)
                self.POLYGON.append(polygon)
            elif tag == 'BEGIN_SEGMENT' or tag == 'BEGIN_SEGMENT_CURVED': 
                if lasttag == 'Patch': 
                    print('   Patch instances     loaded : '+str(counter))
                    counter=0
                elif lasttag == 'Polygon':
                    print('   Polygon instances   loaded : '+str(counter))
                    counter=0
                lasttag='Segment'
                counter+=1
                self.SEGMENT.append(read_up_to('END_SEGMENT',self.file))
            elif tag == 'OBJECT': 
                self.OBJECT=read_tag_zone('OBJECT ',self.file)
                print('   Object definitions  loaded : '\
                      +str(len(self.OBJECT_DEF)))
            elif tag == 'RASTER_DATA':
                if lasttag=='Patch':
                    print('   Patch instances     loaded : '+str(counter))
                elif lasttag=='Segment':
                    print('   Segment instances   loaded : '+str(counter))
                elif lasstag=='Polygon':
                    print('   Polygon instances   loaded : '+str(counter))
                self.RASTER_DATA=read_tag_zone('RASTER_DATA',self.file)
                print('   Raster data         loaded : '\
                      +str(len(self.RASTER_DATA)))
            else:
                self.file.readline()
        self.file.close()
        self.NBR_TRI=0
        for patch in self.PATCH:
            for prim in patch.PRIMITIVE:
                if prim.TYPE=='0':
                    self.NBR_TRI+=len(prim.VERTEX)//3
                else:
                    self.NBR_TRI+=len(prim.VERTEX)-2
        msg=''            
        if self.NBR_TRI==0: msg='  (Probably an Overlay DSF)'            
        print('Total number of triangles : '+str(self.NBR_TRI)+msg)
        print('   --> Done in '+str('{:.2f}'.format(time.time()-t))+'sec')
        time.sleep(1)
        return
   
    def write_to(self,filename):
        print('Writing DSF object to text file '+filename+' :') 
        self.file=open(filename,'w')
        for line in self.PROPERTY:
            if 'creation_agent' in line:
                self.file.write(line)
                self.file.write('PROPERTY sim/creation_agent \
Processed by Ortho4XP\n')
            else:
                self.file.write(line)
        for line in self.TERRAIN_DEF:
            self.file.write(line)
        for line in self.OBJECT_DEF:
            self.file.write(line)
        for line in self.POLYGON_DEF:
            self.file.write(line)
        for line in self.NETWORK_DEF:
            self.file.write(line)
        for line in self.RASTER_DEF:
            self.file.write(line)
        for polygon in self.POLYGON:
            polygon.write_to(self.file)
        for patch in self.PATCH:
            patch.write_to(self.file)
        for line in self.OBJECT:
            self.file.write(line)
        for segment in self.SEGMENT:
            self.file.write(''.join(segment))
        for line in self.RASTER_DATA:
            self.file.write(line)
        self.file.write('# Result code: 0\n')
        self.file.close()
        return
    
    def simplify_primitives(self):
        t=time.time()
        print('Simplifying primitives to single triangles :')
        for patch in self.PATCH:
            patch.simplify_primitives()
        print('   --> Done in '+str('{:.2f}'.format(time.time()-t))+'sec')
        return

    def group_primitives_of_type_zero(self):
        print('Grouping triangles within patches to big primitives of type 0,')
        for patch in self.PATCH:
            patch.group_primitives_of_type_zero()
        return

    def remove_unwanted_polygon_types(self,polygon_remove_list):
        print('Removing unwanted polygon types :')
        for polygon in self.POLYGON:
            for substring in polygon_remove_list:
                if substring in self.POLYGON_DEF[int(polygon.TYPE)]:
                    self.POLYGON.remove(polygon)
        return

    def analyze_mesh(self,with_water=False):
        '''
        Use simplify_primites priori to analyse mesh, it implicitly assumes
        that all primitives are simple.
        '''
        size_min=1000000
        size_max=0
        nbr_triangles=0
        nbr_ZL14=0
        nbr_ZL15=0
        nbr_ZL16=0
        nbr_ZL17=0
        nbr_ZL18=0
        nbr_ZL19=0
        for patch in self.PATCH:
            if (patch.TYPE != '0') or (with_water==True):
                for primitive in patch.PRIMITIVE:
                    cv1=[float(primitive.VERTEX[0]),float(primitive.VERTEX[1])]
                    cv2=[float(primitive.VERTEX[0]),float(primitive.VERTEX[1])]
                    cv3=[float(primitive.VERTEX[0]),float(primitive.VERTEX[1])]
                    approx_l_12 = sqrt(((cv1[0]-cv2[0])*100000*cos(cv1[1]))**2\
+((cv1[1]-cv2[1])*100000)**2)
                    approx_l_13 = sqrt(((cv1[0]-cv3[0])*100000*cos(cv1[1]))**2\
+((cv1[1]-cv3[1])*100000)**2)
                    approx_l_23 = sqrt(((cv3[0]-cv2[0])*100000*cos(cv1[1]))**2\
+((cv3[1]-cv2[1])*100000)**2)
                    size=max(approx_l_12,approx_l_13,approx_l_23)
                    if size < size_min:
                        size_min=size
                    elif size > size_max:
                        size_max = size
                    if size < 100:
                        nbr_ZL19+=1
                    elif size < 200:
                        nbr_ZL18+=1
                    elif size < 400:
                        nbr_ZL17+=1
                    elif size < 800:
                        nbr_ZL16+=1
                    elif size < 1600: 
                        nbr_ZL15+=1
                    elif size < 3200:
                        nbr_ZL14+=1
        print('Your mesh has the following characteristics :')
        if with_water==False:
            print('Largest  non water triangle : '\
+str(round(size_max)).rjust(5)+' m')
            print('Smallest non water triangle : '\
+str(round(size_min)).rjust(5)+' m')
            ZL19_ok=nbr_ZL19
            ZL18_ok=nbr_ZL18+ZL19_ok
            ZL17_ok=nbr_ZL17+ZL18_ok
            ZL16_ok=nbr_ZL16+ZL17_ok
            ZL15_ok=nbr_ZL15+ZL16_ok
            ZL14_ok=nbr_ZL14+ZL15_ok
            print('Total number of non water triangles   : '\
+str(nbr_triangles))
            print('Proportion of safe triangles for ZL14 : '\
                   +str('{:+.3f}'.format(100*ZL14_ok/nbr_triangles))+'#')
            print('Proportion of safe triangles for ZL15 : '\
                   +str('{:+.3f}'.format(100*ZL15_ok/nbr_triangles))+'#')
            print('Proportion of safe triangles for ZL16 : '\
                   +str('{:+.3f}'.format(100*ZL16_ok/nbr_triangles))+'#')
            print('Proportion of safe triangles for ZL17 : '\
                   +str('{:+.3f}'.format(100*ZL17_ok/nbr_triangles))+'#')
            print('Proportion of safe triangles for ZL18 : '\
                   +str('{:+.3f}'.format(100*ZL18_ok/nbr_triangles))+'#')
            print('Proportion of safe triangles for ZL19 : '\
                   +str('{:+.3f}'.format(100*ZL19_ok/nbr_triangles))+'#')
        return
###############################################################################

   
###############################################################################
# Part 4 : Functions related to different coordinate systems (WGS84 - Lambert 
#           - UTM) or tile numbering  (TMS - Quadkey). We call gtile a 256x256 
#           or 512x512 pixel matrix containing an orthophoto, these are the 
#           ones that can be directly downloaded from TMS/WMS services.
###############################################################################

###############################################################################
def wgs84_to_tile_params(lat,lon,zoomlevel,website):
    if website in ['FR','SP','CH_Vs','SE','BI','GO','OSM','OTM']:
        half_meridian=pi*6378137
        ratio_x=lon/180           
        ratio_y=log(tan((90+lat)*pi/360))/pi
        pix_x=(ratio_x+1)*(2**(zoomlevel+7))
        pix_y=(1-ratio_y)*(2**(zoomlevel+7))
        til_x=pix_x//256
        til_y=pix_y//256
        px=pix_x%256
        py=pix_y%256
        retval=[int(til_x),int(til_y),px,py]
    elif website=='BE_Wa':
        retval=wgs84_to_BE_Wa(lat,lon,zoomlevel)
    elif website=='IT':
        retval=wgs84_to_IT(lat,lon,zoomlevel)
    return retval
###############################################################################


###############################################################################
def wgs84_to_gtile(lat,lon,zoomlevel):                                         # Deprecated by wgs84-to_tile_params  
    """
    For a given latitude and longitude, compute the X and Y number
    of the 256x256 google-type tile containing that point at the given zoom 
    level.
    
    One first computes the coordinate pos_x and pos_y in Spherical Mercator 
    Projection EPSG:900913. 
    Cfr. http://en.wikipedia.org/wiki/Mercator_projection
    """  
    half_meridian=pi*6378137
    pos_x=lon/180*half_meridian           
    pos_y=log(tan((90+lat)*pi/360))/pi*half_meridian
    """
    To go from Mercator's infinite strip to a square tiling (Google numbering),
    one first realizes a cut-off of the region abs(latitude)>Latmax (where 
    log(tan(90+Latmax)*pi/360)=pi so that one indeed gets a square with pos_x,
    pos_y \in [-half_meridian,half_meridian]). Then the origin is translated to
    the top left corner of that square, and finally the unit is changed from 
    meters to pixels according to the given zoom level.  
    """
    pix_x=round((pos_x+half_meridian)/(2*half_meridian)*256*(2**zoomlevel))
    pix_y=round((half_meridian-pos_y)/(2*half_meridian)*256*(2**zoomlevel))
    """
    Tile coordinates til_x, til_y are then just the integer parts. Note that
    tile numbering starts at zero, not at one. 
    """
    til_x=pix_x//256
    til_y=pix_y//256
    return [til_x,til_y]
###############################################################################


###############################################################################
def gtile_to_wgs84(til_x,til_y,zoomlevel):
    """
    Returns the latitude and longitude of the bottom left corner of the tile 
    (til_x,til_y) at zoom level zoomlevel, using Google's numbering of tiles 
    (i.e. origin on top left of the earth map)
    """
    half_meridian=pi*6378137
    pos_x=(til_x/(2**(zoomlevel-1))-1)*half_meridian
    pos_y=(1-(til_y+1)/(2**(zoomlevel-1)))*half_meridian
    lon=pos_x*180/half_meridian
    lat=360/pi*atan(exp(pi*pos_y/half_meridian))-90
    return [lat,lon]
###############################################################################

###############################################################################
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
###############################################################################

"""
Some WMS/TMS are not based on the same tiling as above, like the belgian (based 
on a Lambert conical projection) or the italian (based on universal
transverse Mercator projections) public geodata services. We need special 
processes for these.
"""

###############################################################################
def latlon_to_lambert(lat,lon,a,e,lat0,lon0,automec1,automec2,false_x,false_y):# Cfr. Map Projections - A Working Manual, US Geographical survey profesional paper 1395, page 108.
    lat=lat*pi/180
    lon=lon*pi/180
    lat0=lat0*pi/180
    lon0=lon0*pi/180
    lat1=automec1*pi/180
    lat2=automec2*pi/180
    t=tan(pi/4-lat/2)/((1-e*sin(lat))/(1+e*sin(lat)))**(e/2)
    t0=tan(pi/4-lat0/2)/((1-e*sin(lat0))/(1+e*sin(lat0)))**(e/2)
    t1=tan(pi/4-lat1/2)/((1-e*sin(lat1))/(1+e*sin(lat1)))**(e/2)
    t2=tan(pi/4-lat2/2)/((1-e*sin(lat2))/(1+e*sin(lat2)))**(e/2)
    m1=cos(lat1)/sqrt(1-e**2*sin(lat1)**2)
    m2=cos(lat2)/sqrt(1-e**2*sin(lat2)**2)
    n=(log(m1)-log(m2))/(log(t1)-log(t2))
    F=m1/(n*t1**n)
    rho0=a*F*t0**n
    theta=n*(lon-lon0)
    rho=a*F*t**n
    x=rho*sin(theta)+flase_x
    y=rho0-rho*cos(theta)+false_y
    return [x,y]
###############################################################################


###############################################################################
def latlon_to_utm(lat,lon,a,e,lon0,false_x,false_y):                           # Cfr. Map Projections - A Working Manual, US Geographical survey profesional paper 1395, page 60.
    lat=lat*pi/180
    lon=lon*pi/180
    lon0=lon0*pi/180
    e2=e*e
    ep2=e2/(1-e2)
    sin2phi=sin(lat)**2
    cos2phi=1-sin2phi
    tan2phi=sin2phi/cos2phi
    N=a/sqrt(1-e2*sin2phi)
    T=tan2phi
    C=ep2*cos2phi
    A=(lon-lon0)*cos(lat)
    M=a*((1-e2/4-3*e2**2/64-5*e2**3/256)*lat-(3*e2/8+3*e2**2/32+45*e2**3/1024)\
*sin(2*lat)+(15*e2**2/256+45*e2**3/1024)*sin(4*lat)-(35*e2**3/3072)*sin(6*lat))
    k0=0.9996
    x=k0*N*(A+(1-T+C)*A**3/6+(5-18*T*T**2+72*C-58*ep2)*A**5/120)
    y=k0*(M+N*tan(lat)*(A**2/2+(5-T+9*C+4*C**2)*A**4/24+(61-58*T\
+T**2+600*C-330*ep2)*A**6/720))
    x=x+false_x
    y=y+false_y
    return [x,y]
###############################################################################


###############################################################################
def wgs84_to_utm33n(lat,lon):
    a=6378137
    f=1/298.257223563
    e=sqrt(2*f-f**2)
    lon0=15
    false_x=500000
    false_y=0
    return latlon_to_utm(lat,lon,a,e,lon0,false_x,false_y)
###############################################################################


###############################################################################
def utm_to_latlon(x,y,a,e,lon0,false_x,false_y):
    x=x-false_x
    y=y-false_y
    lon0=lon0*pi/180
    e2=e*e
    ep2=e2/(1-e2)
    e1=(1-sqrt(1-e2))/(1+sqrt(1-e2))
    k0=0.9996
    M=y/k0
    mu=M/(a*(1-e2/4-3*e2**2/64-5*e2**3/256))
    lat1=mu+(3*e1/2-27*e1**3/32)*sin(2*mu)+(21*e1**2/16-55*e1**4/32)*sin(4*mu)\
+(151*e1**3/96)*sin(6*mu)+1097*e1**4/512*sin(8*mu)
    T1=tan(lat1)**2
    C1=ep2*cos(lat1)**2
    N1=a/sqrt(1-e2*sin(lat1)**2)
    R1=a*(1-e2)/((1-e2*sin(lat1)**2)**(1.5))
    D=x/(N1*k0)
    lat=lat1-(N1*tan(lat1)/R1)*(D**2/2-(5+3*T1+10*C1-4*C1**2-9*ep2)*D**4/24+\
(61+90*T1+298*C1+45*T1**2-252*ep2-3*C1**2)*D**6/720)
    lon=lon0+(D-(1+2*T1+C1)*D**3/6+\
(5-2*C1+28*T1-3*C1**2+8*ep2+24*T1**2)*D**5/120)/cos(lat1)
    return [180/pi*lat,180/pi*lon]
###############################################################################


###############################################################################
def utm33n_to_wgs84(x,y):
    a=6378137
    f=1/298.257223563
    e=sqrt(2*f-f**2)
    lon0=15
    false_x=500000
    false_y=0
    return utm_to_latlon(x,y,a,e,lon0,false_x,false_y)
###############################################################################


###############################################################################
def wgs84_to_IT(lat,lon,zoomlevel):                                            
    [x,y]=wgs84_to_utm33n(lat,lon)
    if zoomlevel==19:
        resol=0.26458386250105836
    elif zoomlevel==18:
        resol=0.5291677250021167
    elif zoomlevel==17:
        resol=0.7937515875031751
    elif zoomlevel==16: 
        resol=1.0583354500042335
    elif zoomlevel==15:
        resol=1.3229193125052918
    elif zoomlevel==14:
        resol=1.9843789687579376
    elif zoomlevle==13:
        resol=2.6458386250105836
    elif zoomlevel==12:
        resol=3.9687579375158752
    orig_x=-5120900
    orig_y=9998100 
    til_x=(x-orig_x)//(512*resol)
    til_y=-1*(y-orig_y)//(512*resol)
    px=(x-orig_x)/resol-til_x*512
    py=-1*(y-orig_y)/resol-til_y*512
    return [int(til_x),int(til_y),px,py]
###############################################################################


###############################################################################
def IT_to_wgs84(til_x,til_y,zoomlevel):
    if zoomlevel==19:
        resol=0.26458386250105836
    elif zoomlevel==18:
        resol=0.5291677250021167
    elif zoomlevel==17:
        resol=0.7937515875031751
    elif zoomlevel==16: 
        resol=1.0583354500042335
    elif zoomlevel==15:
        resol=1.3229193125052918
    elif zoomlevel==14:
        resol=1.9843789687579376
    elif zoomlevle==13:
        resol=2.6458386250105836
    elif zoomlevel==12:
        resol=3.9687579375158752
    orig_x=-5120900
    orig_y=9998100 
    x=orig_x+512*resol*til_x
    y=orig_y-512*resol*til_y
    [lat,lon]=utm33n_to_wgs84(x,y)
    return [lat,lon]
###############################################################################


###############################################################################
def hayford_to_lambert72(lat,lon):                                             # The reference geoid for Lambert 72 projection is the international 1924 one (determined by Hayford in 1909), not WGS84.
    a=6378388
    f=1/297.0
    e=sqrt(2*f-f**2)
    automec1=49.8333339
    automec2=51.1666672333333333
    lat0=90
    lon0=4.367486666666666666 
    false_x=150000.013                                                         # False easting and northing. 
    false_y=5400088.438
    [x,y]=latlon_to_lambert(lat,lon,a,e,lat0,lon0,automec1,automec2,\
false_x,false_y)
    return [x,y]
##############################################################################


##############################################################################
def wgs84_to_hayford(lat,lon):                                                # Use of Molodensky parameters to jump from one geoid to another (cfr Wiki).  
    lat = (pi / 180) * lat
    lon = (pi / 180) * lon
    sinlat = sin(lat)
    sinlon = sin(lon)
    coslat = cos(lat)
    coslon = cos(lon)
    dx = 125.8
    dy = -79.9
    dz = 100.5
    da = 251.0
    df = 0.000014192702
    f = 1 / 297
    a = 6378388
    b = (1-f)*a
    e2 = (2*f) - (f*f)
    adb = 1/(1-f)
    Rn = a/sqrt(1-e2*sinlat*sinlat)
    Rm = a*(1-e2)/(1-e2*lat*lat)**1.5
    dlat = -dx*sinlat*coslon-dy*sinlat*sinlon+dz*coslat
    dlat = dlat+da*(Rn*e2*sinlat*coslat)/a
    dlat = dlat+df*(Rm*adb+Rn/adb)*sinlat*coslat
    dlat = dlat/Rm 
    dlon = (-dx*sinlon+dy*coslon)/(Rn*coslat)
    dh = dx*coslat*coslon+dy*coslat*sinlon+dz*sinlat
    dh = dh-da*a/Rn+df*Rn*lat*lat/adb
    latint24 = ((lat+dlat)*180)/pi
    lonint24 = ((lon+dlon)*180)/pi
    return [latint24,lonint24]
###############################################################################


###############################################################################
def wgs84_to_lambert72(lat,lon):
    return hayford_to_lambert72(*wgs84_to_hayford(lat,lon))
###############################################################################

###############################################################################
def wgs84_to_BE_Wa(lat,lon,zoomlevel):                                         # Cfr. http://geoservices.wallonie.be/arcgis/rest/services/IMAGERIE/ORTHO_LAST/MapServer.
    [x,y]=wgs84_to_lambert72(lat,lon)
    if zoomlevel==16:
        resol=0.06614596562526459
    elif zoomlevel==15:
        resol=0.13229193125052918
    elif zoomlevel==14:
        resol=0.26458386250105836
    elif zoomlevel==13:
        resol=0.6614596562526459
    elif zoomlevel==12:
        resol=1.3229193125052918
    elif zoomlevel==11: 
        resol=2.6458386250105836
    orig_x=-3.58727E7
    orig_y=4.14227E7 
    til_x=(x-orig_x)//(512*resol)
    til_y=-1*(y-orig_y)//(512*resol)
    px=(x-orig_x)/resol-til_x*512
    py=-1*(y-orig_y)/resol-til_y*512
    return [int(til_x),int(til_y),px,py]
##############################################################################



###############################################################################
# Part 5  :  Functions that relates points to textures.                                                           
#            We call textures 4096x4096 pixel matrices made with 16x16 tiles of
#            size 256x256 or with 8x8 gtiles of size 512x512.
#            They will serve as terrain textures in X-Plane    
###############################################################################



###############################################################################
def wgs84_to_textures(lat,lon,zoomlevel,website):
    """
    For a given point and zoomlevel, returns the list of textures at that given
    zoomlevel which contain that point. A texture is a cluster of 16x16 (resp. 
    8x8) tiles whose top left corner is located at a tile til_x and til_y 
    coordinates which are both multiples of 14 (resp. 7). The texture is 
    recorded as its til_x_left and til_y_top values. Since textures overlap, 
    a point can be in 1, 2 or 4 textures.
    """
    [til_x,til_y,px,py]=wgs84_to_tile_params(lat,lon,zoomlevel,website)
    if website in ['FR','SP','CH_Vs','BI','SE','GO','OSM','OTM']:
        tex_x=(til_x//14)*14
        tex_y=(til_y//14)*14
        px=px+(til_x%14)*256
        py=py+(til_y%14)*256
        if (px >= 512) and (py >= 512):
            retval=[[tex_x,tex_y]]
        elif (px < 512) and (py >= 512):
            retval=[[tex_x,tex_y],[tex_x-14,tex_y]]
        elif (px >= 512) and (py < 512):
            retval=[[tex_x,tex_y],[tex_x,tex_y-14]]
        else:
            retval=[[tex_x,tex_y],[tex_x-14,tex_y],[tex_x,tex_y-14],\
                    [tex_x-14,tex_y-14]]
    elif website in ['BE_Wa','IT']:
        tex_x=(til_x//7)*7
        tex_y=(til_y//7)*7
        px=px+(til_x%7)*512
        py=py+(til_y%7)*512
        if (px >= 512) and (py >= 512):
            retval=[[tex_x,tex_y]]
        elif (px < 512) and (py >= 512):
            retval=[[tex_x,tex_y],[tex_x-7,tex_y]]
        elif (px >= 512) and (py < 512):
            retval=[[tex_x,tex_y],[tex_x,tex_y-7]]
        else:
            retval=[[tex_x,tex_y],[tex_x-7,tex_y],[tex_x,tex_y-7],\
                    [tex_x-7,tex_y-7]]
    return retval
###############################################################################

###############################################################################
def belongs_to_texture(lat,lon,til_x,til_y,zoomlevel,website):
    if website in ['FR','CH_Vs','SP','BI','SE','GO','OSM','OTM']:
        [til_x0,til_y0]=wgs84_to_gtile(lat,lon,zoomlevel)
        if ((til_x <= til_x0) and (til_x0 <= (til_x+15)) and \
(til_y <= til_y0) and (til_y0 <= (til_y+15))):
            retval=True
        else:
            retval=False
    elif website=='BE_Wa':
        [til_x0,til_y0]=wgs84_to_BE_Wa(lat,lon,zoomlevel)
        if ((til_x <= til_x0) and (til_x0 <= (til_x+7)) and \
(til_y <= til_y0) and (til_y0 <= (til_y+7))):
            retval=True
        else:
            retval=False
    elif website=='IT':
        [til_x0,til_y0]=wgs84_to_IT(lat,lon,zoomlevel)
        if ((til_x <= til_x0) and (til_x0 <= (til_x+7)) and \
(til_y <= til_y0) and (til_y0 <= (til_y+7))):
            retval=True
        else:
            retval=False
    return retval
###############################################################################


###############################################################################
def triangle_to_textures(lat1,lon1,lat2,lon2,lat3,lon3,zoomlevel,website):
    """
    List of textures (at given zoomlevel) containing a given triangle. 
    May be empty. 
    """
    retval=[]
    testlist=wgs84_to_textures(lat1,lon1,zoomlevel,website)
    for texture in testlist:
        if ((texture in wgs84_to_textures(lat2,lon2,zoomlevel,website))\
and (texture in wgs84_to_textures(lat3,lon3,zoomlevel,website))): 
            retval=retval+[texture]
    return retval        
###############################################################################


###############################################################################
def st_coordinates(lat,lon,tex_x,tex_y,zoomlevel,website):                     # Cfr. DSFTool manual at wiki.x-plane.com.
    """
    ST coordinates of a point in a texture
    """
    [til_x,til_y,px,py]=wgs84_to_tile_params(lat,lon,zoomlevel,website)
    if website in ['FR','SP','CH_Vs','BI','SE','GO','OSM','OTM']:
        px=px+(til_x-tex_x)*256
        py=py+(til_y-tex_y)*256
        if (px<0 or px>4096 or py<0 or py>4096):
            print('Warning : bad ST coordinates')
            px=max(min(px,4096),0)
            py=max(min(py,4096),0)
    elif website in ['BE_Wa','IT']:
        px=px+(til_x-tex_x)*512
        py=py+(til_y-tex_y)*512
        if (px<0 or px>4096 or py<0 or py>4096):
            print('Warning : bad ST coordinates')
            px=max(min(px,4096),0)
            py=max(min(py,4096),0)
    return [(px/4096),1-(py/4096)]
###############################################################################


###############################################################################
def is_in_region(lat,lon,latmin,latmax,lonmin,lonmax):
    if (lat>=latmin and lat<=latmax and lon>=lonmin and lon<=lonmax):
        retval=True
    else:
        retval=False
    return retval
###############################################################################


###############################################################################
# Part 6 : Methods to download tiles or textures                                                   
###############################################################################


###############################################################################
def obtain_tile(til_x,til_y,zoomlevel,website,filename):
    """
    Obtain the gtile of index (til_x,til_y) at zoom level zoomlevel from your 
    favorite website. Deprecated in favor of the next function for speed 
    purposes.
    """
    url=url_construct(til_x,til_y,zoomlevel,website)
    fake_headers=fake_headers_construct(website)
    s=requests.Session()
    r=s.get(url,headers=fake_headers)
    file=open(filename,"wb")
    if ('Response [20' in str(r)):
            file.write(r.content)
    else:
        os.system(copy_command+' "'+Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
'white.jpg'+'" "'+filename+'"') 
    file.close()
    return
###############################################################################


###############################################################################
def obtain_texture_row(til_x_left,til_y_top,til_y,zoomlevel,website):
    """
    Same as above but 8 or 16 in a row, http transactions take time so better 
    stay in line for a few consecutive tiles. We shall thread these calls in 
    the next function.
    """
    if website in ['FR','SP','CH_Vs','BI','SE','GO','OSM','OTM']:
        rowlength=16
    elif website in ['BE_Wa','IT']:
        rowlength=8
    fake_headers=fake_headers_construct(website)
    s=requests.Session()
    #if not os.path.exists(Ortho4XP_dir+dir_sep+'tmp'):
    #    os.makedirs(Ortho4XP_dir+dir_sep+'tmp') 
    for til_x in range(til_x_left,til_x_left+rowlength):
        url=url_construct(til_x,til_y,zoomlevel,website)
        r=s.get(url, headers=fake_headers)
        filename=Ortho4XP_dir+dir_sep+"tmp"+dir_sep+"image-"+str(til_x_left)+"-"\
+str(til_y_top)+"-"+str(til_y-til_y_top).zfill(2)+"-"\
+str(til_x-til_x_left).zfill(2)+".jpg"
        file=open(filename,"wb")
        if ('Response [20' in str(r)):
            file.write(r.content)
        else:
            os.system(copy_command+' "'+Ortho4XP_dir+dir_sep+'Utils'+dir_sep+\
'white.jpg'+'" "'+filename+'"') 
        file.close()
    return
###############################################################################


###############################################################################
def build_texture(til_x_left,til_y_top,zoomlevel,website):
    '''
    Pack a 16x16 or 8x8 collection of tiles to get a 4096x4096 image that will 
    serve as an X-Plane texture. Use 8 or 16 threads, each of those executing 
    the function obtain_textyure_row for a given row. 
    '''
    [file_dir,file_name,file_ext]=filename_from_attributes(til_x_left,\
                                                           til_y_top,\
                                                           zoomlevel,\
                                                           website)
    if os.path.isfile(file_dir+file_name+file_ext) != True:
        print("   Building missing texture "+file_name+file_ext+"\r")
        jobs=[]
        if website in ['FR','SP','CH_Vs','BI','SE','GO','OSM','OTM']:
            collength=16
        elif website in ['BE_Wa','IT']:
            collength=8
        for til_y in range(til_y_top,til_y_top+collength):
            fargs=[til_x_left,til_y_top,til_y,zoomlevel,website]
            connection_thread=threading.Thread(target=obtain_texture_row,\
args=fargs)
            jobs.append(connection_thread)
        for j in jobs:
            j.start()
        for j in jobs:
            j.join()
        if website in ['FR','SP','CH_Vs','BI','SE','GO','OSM','OTM']:
            os.system(montage_command+' -tile 16x16 -geometry 256x256+0+0 "'+\
Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'image-'+str(til_x_left)+'-'+\
str(til_y_top)+'-*.jpg'+'" "'+file_dir+file_name+file_ext+'" '+devnull_redirection)
        elif website in ['BE_Wa','IT']:
            os.system(montage_command+' -tile 8x8 -geometry 512x512+0+0 "'+\
Ortho4XP_dir+dir_sep+'tmp'+dir_sep+'image-'+str(til_x_left)+'-'+\
str(til_y_top)+'-*.jpg'+'" "'+file_dir+file_name+file_ext+'" '+devnull_redirection)
        os.system(delete_command+' '+Ortho4XP_dir+dir_sep+'tmp'+\
dir_sep+'image-'+str(til_x_left)+'-' +str(til_y_top)+'-*.jpg')
    else:
        print("   Skipping existing texture "+file_name+file_ext+"\r")
    return 
###############################################################################




###############################################################################
def build_texture_region(latmin,latmax,lonmin,lonmax,zoomlevel,website,border_pol_name='None'):
    
    if border_pol_name != 'None':
        border_pol=Polygon()
        file=open(Ortho4XP_dir+dir_sep+'Border_polygons'+dir_sep+border_pol_name+'.pol','r')
        border_pol.load_from(file)
        file.close()

    [til_xmin,til_ymin,px,py]=\
wgs84_to_tile_params(latmax,lonmin,zoomlevel,website)
    [til_xmax,til_ymax,px,py]=\
wgs84_to_tile_params(latmin,lonmax,zoomlevel,website)
    
    if website in ['FR','SP','CH_Vs','BI','SE','GO','OSM','OTM']:
        til_xmax_left=til_xmin-2-(til_xmin-2)%14
        til_xmax_right=til_xmax-til_xmax%14
        til_ymax_top=til_ymin-2-(til_ymin-2)%14
        til_ymax_bottom=til_ymax-til_ymax%14
        print("Number of tiles to download (at most) : "+\
str(((til_ymax_bottom-til_ymax_top)/14+1)*\
((til_xmax_right-til_xmax_left)/14+1)))
        for til_y_top in range(til_ymax_top,til_ymax_bottom+1,14):
            for til_x_left in range(til_xmax_left,til_xmax_right+1,14):
                check_pol=False
                if border_pol_name=='None':
                    check_pol=True
                else:
                    [lat,lon]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
                    if border_pol.belongs_to([lat,lon])==True:
                        check_pol=True
                if check_pol==True:
                    build_texture(til_x_left,til_y_top,zoomlevel,website)
    elif website in ['BE_Wa','IT']:
        til_xmax_left=til_xmin-1-(til_xmin-1)%7
        til_xmax_right=til_xmax-til_xmax%7
        til_ymax_top=til_ymin-1-(til_ymin-1)%7
        til_ymax_bottom=til_ymax-til_ymax%7
        print("Number of tiles to download (at most) : "+\
str(((til_ymax_bottom-til_ymax_top)/7+1)*
((til_xmax_right-til_xmax_left)/7+1)))
        for til_y_top in range(til_ymax_top,til_ymax_bottom+1,7):
            for til_x_left in range(til_xmax_left,til_xmax_right+1,7):
                check_pol=False
                if border_pol_name=='None':
                    check_pol=True
                else:
                    if website =='BE_Wa':
                        [lat,lon]=lambert72_to_wgs84(til_x_left,til_y_top,zoomlevel)
                        if border_pol.belongs_to([lat,lon])==True:
                            check_pol=True
                    elif website=='IT':
                        [lat,lon]=IT_to_wgs84(til_x_left,til_y_top,zoomlevel)
                        if border_pol.belongs_to([lat,lon])==True:
                            check_pol=True
                if check_pol==True:
                    build_texture(til_x_left,til_y_top,zoomlevel,website)
    return   
###############################################################################


###############################################################################
def create_tile_preview(latmin,lonmin,zoomlevel,website):
    strlat='{:+.0f}'.format(latmin).zfill(3)
    strlon='{:+.0f}'.format(lonmin).zfill(4)
    filepreview=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+strlat+\
strlon+"_"+website+str(zoomlevel)+".jpg"       
    if os.path.isfile(filepreview) != True:
        if website in ['FR','SP','CH_Vs','BI','SE','GO','OSM','OTM']:
            [til_x_min,til_y_min]=wgs84_to_gtile(latmin+1,lonmin,zoomlevel)
            [til_x_max,til_y_max]=wgs84_to_gtile(latmin,lonmin+1,zoomlevel)
        elif website=='BE_Wa':
            [til_x_min,til_y_min]=wgs84_to_BE_Wa(latmin+1,lonmin,zoomlevel)
            [til_x_max,til_y_max]=wgs84_to_BE_Wa(latmin,lonmin+1,zoomlevel)
        elif website=='IT':
            [til_x_min,til_y_min]=wgs84_to_IT(latmin+1,lonmin,zoomlevel)
            [til_x_max,til_y_max]=wgs84_to_IT(latmin,lonmin+1,zoomlevel)
        if not os.path.exists(Ortho4XP_dir+dir_sep+'Previews'):
            os.makedirs(Ortho4XP_dir+dir_sep+'Previews') 
        fake_headers=fake_headers_construct(website)
        s=requests.Session()
        for til_x in range(til_x_min,til_x_max+1):
            for til_y in range(til_y_min,til_y_max+1):
                r=s.get(url_construct(til_x,til_y,zoomlevel,website),\
headers=fake_headers)
                filename=Ortho4XP_dir+dir_sep+'Previews'+dir_sep+'image-'\
+str(til_y-til_y_min).zfill(3)+'-'+str(til_x-til_x_min).zfill(3)+'.jpg'
                file=open(filename,"wb")
                if ('Response [20' in str(r)):
                    file.write(r.content)
                else:
                    os.system(copy_command+' "'+Ortho4XP_dir+dir_sep+'Utils'+\
dir_sep+'white.jpg'+'" "'+filename+'"') 
                file.close()
        nx=til_x_max-til_x_min+1
        ny=til_y_max-til_y_min+1
        if website in ['FR','SP','CH_Vs','BI','SE','GO','OSM','OTM']:
            os.system(montage_command+' -tile '+str(nx)+'x'+str(ny)+\
' -geometry 256x256+0+0 "'+Ortho4XP_dir+dir_sep+'Previews'+dir_sep+'image-*.jpg'+\
'" "'+filepreview+'"')
        elif website in ['BE_Wa','IT'] :   
            os.system(montage_command+' -tile '+str(nx)+'x'+str(ny)+\
' -geometry 512x512+0+0 "'+Ortho4XP_dir+dir_sep+'Previews'+dir_sep+\
'image-*.jpg'+'" "'+filepreview+'"')
        os.system(delete_command+' '+Ortho4XP_dir+dir_sep+'Previews'+\
dir_sep+'image-*.jpg')
        return
###############################################################################

    
###############################################################################
# Part 7 : Process of the configuration file in order to build reattribution 
#          rules 
###############################################################################


###############################################################################
def read_ortho_list(configuration_file=default_config_file):
    file=open(configuration_file,'r')
    ortho_list=[]
    if next_tag('[Ortho_zone_list]',file) != 'None':
        file.readline()
        line=file.readline()
        while ((line != '') and (line != '\n')):
            temp=line.split()
            for i in range(4):
                temp[i]=float(temp[i])
            temp[4]=int(temp[4])
            if (temp[4]<10 or temp[4]>20):
                ortho_list=[]
                print('Error in configuration file : zoomlevel out of range. Terminating.')
                break
            ortho_list += [temp]
            line=file.readline()
    return ortho_list  
###############################################################################


###############################################################################
def read_terrain_keep_list(configuration_file=default_config_file):
    file=open(configuration_file,'r')
    terrain_keep_list=[]
    if next_tag('[Terrain_keep_list]',file) != 'None':
        file.readline()
        line=file.readline()
        while ((line != '') and (line != '\n')):
            terrain_keep_list.append(line[:-1])                                # remove the newline character on purpose 
            line=file.readline()
    return terrain_keep_list  
###############################################################################


###############################################################################
def read_polygon_remove_list(configuration_file=default_config_file):
    file=open(configuration_file,'r')
    polygon_remove_list=[]
    if next_tag('[Polygon_remove_list]',file) != 'None':
        file.readline()
        line=file.readline()
        while ((line != '') and (line != '\n')):
            polygon_remove_list.append(line)
            line=file.readline()
    return polygon_remove_list  
###############################################################################


###############################################################################
def attribute_zoomlevel_and_website(lat,lon,ortho_list,border_pol):
    retval=[]
    check_pol=False
    if border_pol == 'None':
        check_pol=True
    else:
        if border_pol.belongs_to([lat,lon]):
            check_pol=True
    if check_pol==True:
        for region in ortho_list:
            if is_in_region(lat,lon,region[0],region[1],region[2],region[3])==True:
                zoomlevel=region[4]
                website=region[5]
                retval.append([zoomlevel,website])
    return retval
###############################################################################


###############################################################################
def attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,ortho_list,border_pol):
    retval='None'
    zplist=attribute_zoomlevel_and_website(lat1,lon1,ortho_list,border_pol)
    for tries in zplist:
        zoomlevel=tries[0]
        website=tries[1]
        texturelist=triangle_to_textures(lat1,lon1,lat2,lon2,lat3,lon3,zoomlevel,website)
        if texturelist != []:
            retval= texturelist[0] + [zoomlevel] + [website]
            break
    return retval
###############################################################################


###############################################################################
# Part 8 : Modify the original dsf by attributing each triangle its devoted 
#          texture                    
###############################################################################


###############################################################################
def analyze_mesh(dsf_text_split):                                              # Not necessary, for testing purposes only.
    filein=open(dsf_text_split,'r')
    eof=False
    size_min=1000000
    size_max=0
    found_non_water_patch=False
    while (found_non_water_patch != True):
        temp=filein.readline()    
        if (("BEGIN_PATCH " in temp) and ("BEGIN_PATCH 0 " not in temp)):
            found_non_water_patch=True
    nbr_triangles=0
    nbr_ZL14=0
    nbr_ZL15=0
    nbr_ZL16=0
    nbr_ZL17=0
    nbr_ZL18=0
    nbr_ZL19=0
    while (eof != True):
        line=filein.readline()
        if "BEGIN_PRIMITIVE" in line:
            nbr_triangles+=1
            line1=filein.readline()
            line2=filein.readline()
            line3=filein.readline()
            vertex1=line1.split()[1:3]
            vertex2=line2.split()[1:3]
            vertex3=line3.split()[1:3]
            cv1=[float(vertex1[0]),float(vertex1[1])]
            cv2=[float(vertex2[0]),float(vertex2[1])]
            cv3=[float(vertex3[0]),float(vertex3[1])]
            approx_l_12 = sqrt(((cv1[0]-cv2[0])*70000)**2\
                                    +((cv1[1]-cv2[1])*100000)**2)
            approx_l_13 = sqrt(((cv1[0]-cv3[0])*70000)**2\
                                    +((cv1[1]-cv3[1])*100000)**2)
            approx_l_23 = sqrt(((cv3[0]-cv2[0])*70000)**2\
                                    +((cv3[1]-cv2[1])*100000)**2)
            size=max(approx_l_12,approx_l_13,approx_l_23)
            if size < size_min:
                size_min=size
            elif size > size_max:
                size_max = size
            if size < 100:
                nbr_ZL19+=1
            elif size < 200:
                nbr_ZL18+=1
            elif size < 400:
                nbr_ZL17+=1
            elif size < 800:
                nbr_ZL16+=1
            elif size < 1600: 
                nbr_ZL15+=1
            elif size < 3200:
                nbr_ZL14+=1
        elif line=='':
            eof=True
    print('Your mesh has the following characteristics :')
    print('Largest  non water triangle : '+str(round(size_max)).rjust(5)+' m')
    print('Smallest non water triangle : '+str(round(size_min)).rjust(5)+' m')
    ZL19_ok=nbr_ZL19
    ZL18_ok=nbr_ZL18+ZL19_ok
    ZL17_ok=nbr_ZL17+ZL18_ok
    ZL16_ok=nbr_ZL16+ZL17_ok
    ZL15_ok=nbr_ZL15+ZL16_ok
    ZL14_ok=nbr_ZL14+ZL15_ok
    print('Total number of non water triangles   : '+str(nbr_triangles))
    print('Proportion of safe triangles for ZL14 : '\
           +str('{:+.3f}'.format(100*ZL14_ok/nbr_triangles))+'#')
    print('Proportion of safe triangles for ZL15 : '\
           +str('{:+.3f}'.format(100*ZL15_ok/nbr_triangles))+'#')
    print('Proportion of safe triangles for ZL16 : '\
           +str('{:+.3f}'.format(100*ZL16_ok/nbr_triangles))+'#')
    print('Proportion of safe triangles for ZL17 : '\
           +str('{:+.3f}'.format(100*ZL17_ok/nbr_triangles))+'#')
    print('Proportion of safe triangles for ZL18 : '\
           +str('{:+.3f}'.format(100*ZL18_ok/nbr_triangles))+'#')
    print('Proportion of safe triangles for ZL19 : '\
           +str('{:+.3f}'.format(100*ZL19_ok/nbr_triangles))+'#')
    return
###############################################################################


###############################################################################
def build_terrain_kept_indices(terrain_keep_list,terrain_list):
    terrain_kept_indices=[]
    for terrain in terrain_list:
        for terrain_substring in terrain_keep_list:
            if terrain_substring in terrain:
                terrain_kept_indices.append(str(terrain_list.index(terrain)))
    return terrain_kept_indices
###############################################################################


###############################################################################
def reorganize_textures(dsforig,dsfnew,ortho_list,border_pol_name,terrain_kept_indices,
                        convert_to_do_list,water_overlay):
    print('Redispatching terrain textures to base mesh triangles :')
    dsfnew.TERRAIN_DEF=[]
    dsfnew.TERRAIN_DEF.append(dsforig.TERRAIN_DEF[0])                          # Initialize dsfnew.TERRAIN_DEF with water_def
    dico_layer={}                                                              # A new dictionnary for layer -> number in dsfnew
    if border_pol_name != 'None':
        border_pol=Polygon()
        file=open(Ortho4XP_dir+dir_sep+'Border_polygons'+dir_sep+border_pol_name+'.pol','r')
        border_pol.load_from(file)
        file.close()
    else:
        border_pol='None'

    waterpatch=0                                                               # Counter for the number of patches of type water if these are kept
    for patch in dsforig.PATCH:
        if patch.TERRAIN in terrain_kept_indices:   
            if patch.TERRAIN=='0':                                             # Water terrain patches are conserved as is if 
                dsfnew.PATCH.append(patch)                                     # requested, and are put at the begining of the
                waterpatch+=1                                                  # new patch list 
            else:
                continue                                                       # Non water patches that are requested to be kept will 
                                                                               # be processed later
        else:                   
            to_be_moved_primitive_list=[]
            for k in range(0,len(patch.PRIMITIVE)): 
            
                primitive=patch.PRIMITIVE[k]
                lon1=float(primitive.VERTEX[0][0])                             # Read the WGS84 coordinates of the three vertices
                lat1=float(primitive.VERTEX[0][1])                             # Note that longitude preceedes latitue in PATCH_VERTEX !
                lon2=float(primitive.VERTEX[1][0]) 
                lat2=float(primitive.VERTEX[1][1]) 
                lon3=float(primitive.VERTEX[2][0]) 
                lat3=float(primitive.VERTEX[2][1]) 

                layer=attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,ortho_list,border_pol)
                
                if layer != 'None':                                            # We first deal with the textures which we reaffect

                    to_be_moved_primitive_list.append(k)
                    
                    [s1,t1]=st_coordinates(lat1,lon1,int(layer[0]),\
int(layer[1]),int(layer[2]),layer[3])
                    [s2,t2]=st_coordinates(lat2,lon2,int(layer[0]),\
int(layer[1]),int(layer[2]),layer[3])
                    [s3,t3]=st_coordinates(lat3,lon3,int(layer[0]),\
int(layer[1]),int(layer[2]),layer[3])
                    if patch.NBR_COORD=='5':
                        primitive.VERTEX[0].append(float(s1))
                        primitive.VERTEX[0].append(float(t1))
                        primitive.VERTEX[1].append(float(s2))
                        primitive.VERTEX[1].append(float(t2))
                        primitive.VERTEX[2].append(float(s3))
                        primitive.VERTEX[2].append(float(t3))
                    else:
                        primitive.VERTEX[0][5]=float(s1)
                        primitive.VERTEX[0][6]=float(t1)
                        primitive.VERTEX[1][5]=float(s2)
                        primitive.VERTEX[1][6]=float(t2)
                        primitive.VERTEX[2][5]=float(s3)
                        primitive.VERTEX[2][6]=float(t3)

                    if str(layer) in dico_layer:                               # If layer already exists, dico_layer(layer) contains the index of 
                                                                               # that layer among the newly created ones.
                       patch_index=dico_layer[str(layer)]+waterpatch-1         # Index of the patch in dsfnew.PATCH wich contains that layer. 
                       dsfnew.PATCH[patch_index].PRIMITIVE.append(primitive)
                    else:
                       nbr_terrain_now=len(dsfnew.TERRAIN_DEF)
                       dico_layer[str(layer)]=nbr_terrain_now                  # Create new layer in dico_layer.
                       newpatch=Patch()                                        # Create a new patch instance...
                       newpatch.TERRAIN=str(nbr_terrain_now)
                       newpatch.LOD1='0'
                       newpatch.LOD2='-1'
                       newpatch.PHYS='1'
                       newpatch.NBR_COORD='7'
                       newpatch.PRIMITIVE=[]
                       newpatch.PRIMITIVE.append(primitive)                    # ... and place the primitive there. 
                       dsfnew.PATCH.append(newpatch)
                       attributes=[int(layer[0]),int(layer[1]),\
                                   int(layer[2]),layer[3]]
                       build_texture(*attributes)
                       [file_dir,file_name,file_ext]=filename_from_attributes(\
                                                     *attributes)
                       convert_to_do_list.append([file_dir,file_name])
                       terrain_def='TERRAIN_DEF terrain/'+file_name+'.ter\n'    
                       dsfnew.TERRAIN_DEF.append(terrain_def)
                       create_terrain_file(file_name,*attributes)
            for j in range(len(to_be_moved_primitive_list)-1,-1,-1):
                patch.PRIMITIVE\
.remove(patch.PRIMITIVE[to_be_moved_primitive_list[j]])                        # Nothing is lost, nothing is created, it is only a matter of transfer...    

    for patch in dsforig.PATCH:                                                # Now we deal with non water patches which were either requested to be kept
                                                                               # or which were not emptied by the attribution of tiles.                                                                   

        if (patch.TERRAIN != '0') and len(patch.PRIMITIVE) != 0:                    
            terrain_def=dsforig.TERRAIN_DEF[int(patch.TERRAIN)]                # We leave what remains of them in the newly created dsf. We only need 
                                                                               # to adapt the terrain number.
            if terrain_def not in dsfnew.TERRAIN_DEF:
                patch.TERRAIN=str(len(dsfnew.TERRAIN_DEF)) 
                dsfnew.TERRAIN_DEF.append(terrain_def)
            else:
                patch.TERRAIN=str(dsfnew.TERRAIN_DEF.index(terrain_def))
            patch.LOD1='0'                                                     # You may comment these                         
            patch.LOD2='-1'                                                    # two lines for keeping original LOD of kept terrains.
            dsfnew.PATCH.append(patch)                   
    dsfnew.PROPERTY+=dsforig.PROPERTY                                          # The base mesh being updated, everything else is straightforwardly copied.
    dsfnew.BOUNDARIES+=dsforig.BOUNDARIES
    dsfnew.POLYGON_DEF+=dsforig.POLYGON_DEF
    dsfnew.RASTER_DEF+=dsforig.RASTER_DEF
    dsfnew.OBJECT_DEF+=dsforig.OBJECT_DEF
    dsfnew.NETWORK_DEF+=dsforig.NETWORK_DEF
    dsfnew.POLYGON+=dsforig.POLYGON
    dsfnew.OBJECT+=dsforig.OBJECT
    dsfnew.SEGMENT+=dsforig.SEGMENT
    dsfnew.RASTER_DATA+=dsforig.RASTER_DATA
    if water_overlay=='False':
        convert_to_do_list.append('finished')                                     # Commented because it is now closed by create_water_overlay below. 
    return 
###############################################################################


###############################################################################
def create_water_overlay(dsfin,dsfout,ratio_water,ortho_list,border_pol_name,convert_to_do_list):
    print('Creating overlay triangles for blending water tiles with orthophotos:')
    dico_layer={}
    if border_pol_name != 'None':
        border_pol=Polygon()
        file=open(Ortho4XP_dir+dir_sep+'Border_polygons'+dir_sep+border_pol_name+'.pol','r')
        border_pol.load_from(file)
        file.close()
    else:
        border_pol='None'
    for patch in dsfin.PATCH:
        if patch.TERRAIN=='0':                                                     
            for primitive in patch.PRIMITIVE:
                lon1=float(primitive.VERTEX[0][0])                             
                lat1=float(primitive.VERTEX[0][1])                             
                lon2=float(primitive.VERTEX[1][0]) 
                lat2=float(primitive.VERTEX[1][1]) 
                lon3=float(primitive.VERTEX[2][0]) 
                lat3=float(primitive.VERTEX[2][1]) 
                
                layer=attribute_texture(lat1,lon1,lat2,lon2,lat3,lon3,ortho_list,border_pol)
                
                if layer != 'None':                                            

                    newprim=Primitive()
                    newprim.TYPE='0'
                    newprim.VERTEX=[]
                    for vertex in primitive.VERTEX:
                        newvertex=array.array('d',[])        
                        for coord in vertex[:]:
                           newvertex.append(float(coord))
                        newprim.VERTEX.append(newvertex)
                    [s1,t1]=st_coordinates(lat1,lon1,int(layer[0]),\
int(layer[1]),int(layer[2]),layer[3])        
                    [s2,t2]=st_coordinates(lat2,lon2,int(layer[0]),\
int(layer[1]),int(layer[2]),layer[3])
                    [s3,t3]=st_coordinates(lat3,lon3,int(layer[0]),\
int(layer[1]),int(layer[2]),layer[3])
                    if patch.NBR_COORD=='5':
                        newprim.VERTEX[0].append(float(s1))
                        newprim.VERTEX[0].append(float(t1))
                        newprim.VERTEX[1].append(float(s2))
                        newprim.VERTEX[1].append(float(t2))
                        newprim.VERTEX[2].append(float(s3))
                        newprim.VERTEX[2].append(float(t3))
                    else:
                        newprim.VERTEX[0][5]=float(s1)
                        newprim.VERTEX[0][6]=float(t1)
                        newprim.VERTEX[1][5]=float(s2)
                        newprim.VERTEX[1][6]=float(t2)
                        newprim.VERTEX[2][5]=float(s3)
                        newprim.VERTEX[2][6]=float(t3)
                    
                    newprim.VERTEX[0].append(0)
                    newprim.VERTEX[0].append(ratio_water)
                    newprim.VERTEX[1].append(0)
                    newprim.VERTEX[1].append(ratio_water)
                    newprim.VERTEX[2].append(0)
                    newprim.VERTEX[2].append(ratio_water)
                    
                    layer.append('overlay') 
                    if str(layer) in dico_layer:                         
                        patch_index=dico_layer[str(layer)]  
                        dsfout.PATCH[patch_index].PRIMITIVE.append(newprim)
                    else:
                        attributes=[int(layer[0]),int(layer[1]),int(layer[2]),layer[3]]
                        build_texture(*attributes)
                        [file_dir,file_name,file_ext]=filename_from_attributes(\
                                                 *attributes)
                        convert_to_do_list.append([file_dir,file_name])
                        terrain_def='TERRAIN_DEF terrain/'+file_name+'_overlay.ter\n'    
                        dsfout.TERRAIN_DEF.append(terrain_def)
                        dico_layer[str(layer)]=len(dsfout.PATCH)                  
                        newpatch=Patch()                                       
                        newpatch.TERRAIN=str(len(dsfout.TERRAIN_DEF)-1)
                        newpatch.LOD1='0'
                        newpatch.LOD2='-1'
                        newpatch.PHYS='2'
                        newpatch.NBR_COORD='9'
                        newpatch.PRIMITIVE=[]
                        newpatch.PRIMITIVE.append(newprim)                    
                        dsfout.PATCH.append(newpatch)
                        create_overlay_file(file_name,*attributes)
    convert_to_do_list.append('finished')
    os.system(copy_command+' "'+Ortho4XP_dir+dir_sep+'Utils'+dir_sep+'water_transition.png'+\
'" "'+build_dir+dir_sep+'textures'+dir_sep+'"') 
###############################################################################


###############################################################################
# Part 9 :   Functions to build the terrain files and to convert the downloaded
#            jpg texture to dds format                       
###############################################################################


###############################################################################
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
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.dds\n')              
    file.close()
    return
###############################################################################


###############################################################################
def create_overlay_file(file_name,til_x_left,til_y_top,zoomlevel,website):
    if not os.path.exists(build_dir+dir_sep+'terrain'):
        os.makedirs(build_+dir_sep+'terrain') 
    file=open(build_dir+dir_sep+'terrain'+dir_sep+file_name+'_overlay.ter','w')
    file.write('A\n800\nTERRAIN\n\n')
    [lat_med,lon_med]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
    half_meridian=pi*6378137
    texture_approx_size=int(2*half_meridian/2**(zoomlevel-4)*\
                            cos(lat_med*pi/180))
    file.write('LOAD_CENTER '+'{:.5f}'.format(lat_med)+' '\
               +'{:.5f}'.format(lon_med)+' '\
               +str(texture_approx_size)+' 4096\n')
    file.write('BASE_TEX_NOWRAP ../textures/'+file_name+'.dds\n')    
    file.write('WET\n')
    file.write('BORDER_TEX ../textures/water_transition.png\n')
    file.close()
    return
###############################################################################


###############################################################################
def convert_textures(convert_to_do_list):
    if not os.path.exists(build_dir+dir_sep+'textures'):
            os.makedirs(build_dir+dir_sep+'textures')
    finished = False
    while finished != True:
        if convert_to_do_list == []:
            time.sleep(0.1)
        elif convert_to_do_list[0] != 'finished':
            file_dir=convert_to_do_list[0][0]
            file_name=convert_to_do_list[0][1]
            if os.path.isfile(build_dir+dir_sep+'textures'+dir_sep+\
file_name+'.dds') != True:
                conv_cmd = convert_command+' "'+file_dir+file_name+\
'.jpg'+'" "'+build_dir+dir_sep+'textures'+dir_sep+file_name+'.dds"' 
                print('   Converting jpeg to build '+build_dir+dir_sep+\
'textures'+dir_sep+file_name+'.dds')
                os.system(conv_cmd)
            else:
                print('   Texture  '+build_dir+dir_sep+'textures'\
+dir_sep+file_name+'.dds already present')
            convert_to_do_list.remove(convert_to_do_list[0])
        else:
            finished=True
    return
###############################################################################

###############################################################################
# Part 10 : The main program
###############################################################################

###############################################################################
def Ortho4XP(dsf_file,water_overlay='True',border_pol_name='None',configuration_file=default_config_file):
    t=time.time()
    print('\nStep 1/10')
    print('---------')
    print('DSFTool converts the binary dsf to its text version :')
    os.system(command_7z+' -y e "'+dsf_file+'.dsf" '+devnull_redirection) 
    dsf_to_text(dsf_file+'.dsf',dsf_file+'.txt')
    dsfin=DSF()
    dsfout=DSF()
    print('\nStep 2/10') 
    print('---------')
    dsfin.load_from(dsf_file+'.txt')
    print('\nStep 3/10')
    print('---------')
    ortho_list=read_ortho_list(configuration_file)
    terrain_keep_list=read_terrain_keep_list(configuration_file)
    terrain_kept_indices=build_terrain_kept_indices(terrain_keep_list,\
                                                    dsfin.TERRAIN_DEF)
    dsfin.simplify_primitives()
    print('\nSteps 4-6/10  (in parallel)')
    print('---------------------------')
    t2=time.time()
    convert_to_do_list=[]
    fargs0=[dsfin,dsfout,ortho_list,border_pol_name,terrain_kept_indices,convert_to_do_list,water_overlay]
    reorganize_thread=threading.Thread(target=reorganize_textures,args=fargs0)
    if water_overlay=='True':
        fargs0bis=[dsfin,dsfout,ratio_water,ortho_list,border_pol_name,convert_to_do_list]
        create_water_overlay_thread=threading.Thread(target=\
create_water_overlay,args=fargs0bis)
    fargs1=[convert_to_do_list]
    convert_thread=threading.Thread(target=convert_textures,args=fargs1)
    reorganize_thread.start()
    convert_thread.start()
    reorganize_thread.join()
    if water_overlay=='True':
        create_water_overlay_thread.start()
        create_water_overlay_thread.join()
    convert_thread.join()
    print('   --> Done in '+str('{:.2f}'.format(time.time()-t2))+'sec')
    print('\nStep 7/10')
    print('---------')
    t3=time.time()
    dsfout.group_primitives_of_type_zero()
    polygon_remove_list=read_polygon_remove_list()
    dsfout.remove_unwanted_polygon_types(polygon_remove_list)
    print('   --> Done in '+str('{:.2f}'.format(time.time()-t3))+'sec')
    print('\nStep 8/10')
    print('---------')
    dsfout.write_to(dsf_file+'.txt.new')
    print('\nStep 9/10')
    print('---------')
    strlatround='{:+.0f}'.format(floor(int(dsfout.BOUNDARIES[0])/10)*10).zfill(3)
    strlonround='{:+.0f}'.format(floor(int(dsfout.BOUNDARIES[2])/10)*10).zfill(4)
    dest_dir=build_dir+dir_sep+'Earth nav data'+dir_sep+strlatround+strlonround
    print('Creating directory '+dest_dir+' if it does not yet exists')
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    print('DSFTool now converts back the newly created dsf to binary format :')
    if os.path.exists(dest_dir+dir_sep+dsf_file+'.dsf'):
        os.system(copy_command+' "'+dest_dir+dir_sep+dsf_file+'.dsf'+'" "'+\
dest_dir+dir_sep+dsf_file+'.dsf.bak"')
    text_2_dsf(dsf_file+'.txt.new',dsf_file+'.dsf.new')
    os.system(copy_command+dsf_file+'.dsf.new "'+dest_dir+dir_sep+dsf_file+'.dsf"') 
    print('\nStep 10/10')
    print('----------')
    print('Cleaning directories :')
    os.system(delete_command+' '+dsf_file+'.txt '+dsf_file+'.txt.* '+\
dsf_file+'.dsf.new')                                                           # Uncomment if you want to look into your dsf with a text editor
    print('Done.')
    print('\nTotal processing time : '\
           +str('{:.2f}'.format(time.time()-t))+'sec.')
    print('\nBon vol !')
    return
###############################################################################

###############################################################################
# Part 11 : Additional stuff and housekeeping
###############################################################################

###############################################################################
def dsf_to_text(dsf,dsf_text):
    os.system(DSFTool_command+ ' --dsf2text '+'"'+dsf+'" "'+dsf_text+'"')
    return
###############################################################################

###############################################################################
def text_2_dsf(dsf_text_new,dsf_new): 
    os.system(DSFTool_command+ ' --text2dsf '+'"'+dsf_text_new+'" "'+dsf_new+'"')
    return
###############################################################################


###############################################################################
def next_tag(tag,iostream,limit='no limit'):
    '''
    Find the next line of iostream containing an occurence of tag and advance 
    just before that line. Do not search beyond any line containing on 
    occurence of limit. Return 'None' if no tag were found and in that case go
    back to where we were initially in iostream.
    '''
    finished=False
    initpos=iostream.tell()
    while finished != True:
        lastpos=iostream.tell()
        line=iostream.readline()
        if line=='' or (limit in line):
            finished=True
            iostream.seek(initpos)
            retval='None'
        elif tag in line:
            finished=True
            iostream.seek(lastpos)
            retval=lastpos
    return retval
###############################################################################

###############################################################################
def read_tag_zone(tag,iostream):
    '''
    Advance in iostream as long as next line contains tag. Return a list whose
    elements are the lines we jumped over. 
    '''
    tag_zone=[]
    finished=False
    lastpos=iostream.tell()
    while finished != True:
        line=iostream.readline()
        if tag in line:
            tag_zone.append(line)
            lastpos=iostream.tell()
        else:
            finished=True
            iostream.seek(lastpos)
    return tag_zone
###############################################################################

###############################################################################
def read_up_to(tag,iostream):
    ret_list=[]
    finished=False
    initpos=iostream.tell()
    while finished != True:
        line=iostream.readline()
        if line=='':
            print('Error while using function read_up_to : file ended before \
                   pattern '+tag+' was found')
            iostream.seek(initpos)
            ret_list='Error'
            continue
        if tag in line:
            finished=True
        ret_list.append(line)
    return ret_list
###############################################################################
# vim: set nowrap tabstop=4 expandtab shiftwidth=4 softtabstop=4


