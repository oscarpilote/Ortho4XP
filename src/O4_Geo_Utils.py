from math import log, tan, pi, atan, exp, cos, sin, sqrt, atan2
import pyproj

earth_radius = 6378137
lat_to_m      = pi*earth_radius/180
m_to_lat      = 1/lat_to_m
def lon_to_m(lat):
    return lat_to_m*cos(pi*lat/180)
def m_to_lon(lat):
    return m_to_lat/cos(pi*lat/180) 

def dist(A,B):
    # A=(lona,lata), B=(lonb,latb)
    # returns the great circle distance between A and B over the earth surface
    a=sin((A[1]-B[1])*pi/360)**2+cos(A[1]*pi/180)*cos(B[1]*pi/180)*sin((A[0]-B[0])*pi/360)**2
    return 2*earth_radius*atan2(sqrt(a),sqrt(1-a))

epsg={}
epsg['4326']=pyproj.Proj(init='epsg:4326')
epsg['3857']=pyproj.Proj(init='epsg:3857')
    

##############################################################################
def webmercator_pixel_size(lat,zoomlevel):
    return 2*pi*earth_radius*cos(pi*lat/180)/(2**(zoomlevel+8))
##############################################################################

##############################################################################
def transform(s_epsg, t_epsg, s_x, s_y):
    return pyproj.transform(epsg[s_epsg], epsg[t_epsg], s_x, s_y)
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
def wgs84_to_orthogrid(lat,lon,zoomlevel):
    ratio_x=lon/180           
    ratio_y=log(tan((90+lat)*pi/360))/pi
    mult=2**(zoomlevel-5)
    til_x=int((ratio_x+1)*mult)*16
    til_y=int((1-ratio_y)*mult)*16
    return (til_x,til_y)
##############################################################################

##############################################################################
def st_coord(lat,lon,tex_x,tex_y,zoomlevel,provider_code):                        
    """
    ST coordinates of a point in a texture
    """
    ratio_x=lon/180           
    ratio_y=log(tan((90+lat)*pi/360))/pi
    mult=2**(zoomlevel-5)
    s=(ratio_x+1)*mult-(tex_x//16)
    t=1-((1-ratio_y)*mult-tex_y//16)
    s = s if s>=0 else 0
    s = s if s<=1 else 1
    t = t if t>=0 else 0
    t = t if t<=1 else 1
    return (s,t)
##############################################################################
