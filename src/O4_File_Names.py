import os
import sys
from math import floor

g2xpl_16_prefix=''
g2xpl_16_suffix=''

Ortho4XP_dir  =  '..' if getattr(sys,'frozen',False) else '.'
Preview_dir   =  os.path.join(Ortho4XP_dir, 'Previews')
Provider_dir  =  os.path.join(Ortho4XP_dir, 'Providers')
Extent_dir    =  os.path.join(Ortho4XP_dir, 'Extents')
Filter_dir    =  os.path.join(Ortho4XP_dir, 'Filters')
OSM_dir       =  os.path.join(Ortho4XP_dir, 'OSM_data')
Mask_dir      =  os.path.join(Ortho4XP_dir, 'Masks')
Imagery_dir   =  os.path.join(Ortho4XP_dir, 'Orthophotos')
Elevation_dir =  os.path.join(Ortho4XP_dir, 'Elevation_data')
Geotiff_dir   =  os.path.join(Ortho4XP_dir, 'Geotiffs')
Patch_dir     =  os.path.join(Ortho4XP_dir, 'Patches')
Utils_dir     =  os.path.join(Ortho4XP_dir, 'Utils')
Tile_dir      =  os.path.join(Ortho4XP_dir, 'Tiles')
Tmp_dir       =  os.path.join(Ortho4XP_dir, 'tmp')
Overlay_dir  =   os.path.join(Ortho4XP_dir, 'yOrtho4XP_Overlays')
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
##############################################################################

def tile_dir(lat,lon):
    return "zOrtho4XP_"+short_latlon(lat,lon)
def build_dir(lat,lon,custom_build_dir):
    if not custom_build_dir:
        return os.path.join(Tile_dir,tile_dir(lat,lon))
    elif custom_build_dir[-1]=='/':
            return os.path.join(custom_build_dir[:-1],tile_dir(lat,lon))
    else:
        return custom_build_dir
def osm_dir(lat,lon):
    return os.path.join(OSM_dir,long_latlon(lat,lon))
def mask_dir(lat, lon):
    return os.path.join(Mask_dir, long_latlon(lat, lon))
def patch_dir(lat, lon):
    return os.path.join(Patch_dir, long_latlon(lat, lon))

def input_node_file(tile):
    if tile.iterate:
        return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.'+str(tile.iterate)+'.node')
    else:
        return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.node')
def input_poly_file(tile):
    if tile.iterate:
        return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.'+str(tile.iterate)+'.poly')
    else:
        return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.poly')
def input_ele_file(tile):
    if tile.iterate:
        return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.'+str(tile.iterate)+'.ele')
    else:
        return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.ele')
def output_node_file(tile):
    return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.'+str(tile.iterate+1)+'.node')
def output_poly_file(tile):
    return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.'+str(tile.iterate+1)+'.poly')
def output_ele_file(tile):
    return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.'+str(tile.iterate+1)+'.ele')
def alt_file(tile):
    return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.alt')
def apt_file(tile):
    return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.apt')
def weight_file(tile):
    return os.path.join(tile.build_dir,'Data'+short_latlon(tile.lat,tile.lon)+'.weight')
def mesh_file(build_dir,lat,lon):
    return os.path.join(build_dir,'Data'+short_latlon(lat,lon)+'.mesh')
def obj_file(til_x_left,til_y_top,zoomlevel,provider_code):    
    return os.path.join(Geotiff_dir,str(til_y_top)+"_"+str(til_x_left)+"_"+provider_code+str(zoomlevel)+'.obj')
def mtl_file(til_x_left,til_y_top,zoomlevel,provider_code):    
    return os.path.join(Geotiff_dir,str(til_y_top)+"_"+str(til_x_left)+"_"+provider_code+str(zoomlevel)+'.mtl') 
##############################################################################

##############################################################################
def preview(lat, lon, zoomlevel, provider_code):
    return os.path.join(Preview_dir,short_latlon(lat,lon)+"_"+provider_code+str(zoomlevel)+".jpg")  
##############################################################################

##############################################################################
def custom_coastline(lat, lon):
    return os.path.join(OSM_dir,long_latlon(lat,lon),short_latlon(lat,lon)+'_custom_coastline.osm.bz2')
def custom_water(lat, lon):
    return os.path.join(OSM_dir,long_latlon(lat,lon),short_latlon(lat,lon)+'_custom_water.osm.bz2')
def osm_cached(lat, lon, cached_suffix):
    return os.path.join(OSM_dir,long_latlon(lat,lon),short_latlon(lat,lon)+'_'+cached_suffix+'.osm.bz2')
def osm_old_cached(lat, lon, query):
    subtags=query.split('"')
    return os.path.join(OSM_dir,long_latlon(lat,lon),short_latlon(lat,lon)+'_'+\
                    subtags[0][0:-1]+'_'+subtags[1]+'_'+subtags[3]+'.osm')

##############################################################################
def base_file_name(lat, lon):
    hemisphere='N' if lat>=0 else 'S'
    greenwichside='E' if lon>=0 else 'W'
    file_name=hemisphere+'{:.0f}'.format(abs(lat)).zfill(2)+greenwichside+'{:.0f}'.format(abs(lon)).zfill(3)
    return os.path.join(Elevation_dir,round_latlon(lat,lon),file_name)
##############################################################################

##############################################################################
def elevation_data(source,lat, lon):
    if source=='View':
        return base_file_name(lat,lon)+'.hgt'
    elif source=='SRTM':
        return base_file_name(lat,lon)+'_SRTMv3.hgt'
    elif source=='ALOS':
        return base_file_name(lat,lon)+'_ALOS3W30.tif'
    elif source=='NED1/3':
        return base_file_name(lat,lon)+'_NED13.img'
    elif source=='NED1':
        return os.path.join(Elevation_dir,long_latlon(lat,lon)+'_NED1','w001001.adf') 
##############################################################################


##############################################################################
def generic_tif(lat, lon):
    return base_file_name(lat,lon)+'.tif'
##############################################################################

##############################################################################
def viewfinderpanorama(lat, lon):
    return base_file_name(lat,lon)+'.hgt'
##############################################################################

##############################################################################
def SRTM_1sec(lat, lon):
    return base_file_name(lat,lon)+'_SRTM_1sec.hgt'
##############################################################################

##############################################################################
def legacy_mask(m_til_x_left,m_til_y_top):
    return str(m_til_y_top)+'_'+str(m_til_x_left)+'.png'
def mask_file(til_x_left,til_y_top,zoomlevel,provider_code):
    return str(til_y_top)+"_"+str(til_x_left)+"_ZL"+str(zoomlevel)+".png"   
##############################################################################

##############################################################################
def jpeg_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code):
    if provider_code=='g2xpl_16':
        file_name=g2xpl_16_prefix+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
                str(2**zoomlevel-16-til_y_top)+g2xpl_16_suffix+".jpg"
    else:
        file_name=str(til_y_top)+"_"+str(til_x_left)+"_"+provider_code+str(zoomlevel)+".jpg"   
    return file_name
##############################################################################
    
##############################################################################
def jpeg_file_dir_from_attributes(lat, lon, zoomlevel,provider): 
    if not provider:
        file_dir='.'
    elif provider['imagery_dir']=='normal':
        file_dir=os.path.join(Imagery_dir,short_latlon(lat,lon),provider['code']+'_'+str(zoomlevel))
    elif provider['imagery_dir']=='grouped':
        file_dir=os.path.join(Imagery_dir,long_latlon(lat,lon),provider['code']+'_'+str(zoomlevel))
    elif provider['imagery_dir']=='code':
        file_dir=os.path.join(Imagery_dir,provider['code'],provider['code']+'_'+str(zoomlevel))
    else:
        file_dir=os.path.join(Imagery_dir,provider['imagery_dir'],provider['code']+'_'+str(zoomlevel))
    return file_dir
##############################################################################

##############################################################################
def dds_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code,file_ext='dds'):
    if provider_code=='g2xpl_16':
        file_name=g2xpl_16_prefix+str(zoomlevel)+'_'+str(til_x_left)+'_'+\
                str(2**zoomlevel-16-til_y_top)+g2xpl_16_suffix+"."+file_ext
    else:
        file_name=str(til_y_top)+"_"+str(til_x_left)+"_"+provider_code+str(zoomlevel)+"."+file_ext   
    return file_name
##############################################################################

##############################################################################
def geotiff_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code):
    return str(til_y_top)+"_"+str(til_x_left)+"_"+provider_code+str(zoomlevel)+'-WGS84.tif'
##############################################################################
