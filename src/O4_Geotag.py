import os
import pyproj
from math import pi, exp, atan

geographic=pyproj.Proj(init='epsg:4326')
webmercator=pyproj.Proj(init='epsg:3857')

def gtile_to_wgs84(til_x,til_y,zoomlevel):
    rat_x=(til_x/(2**(zoomlevel-1))-1)
    rat_y=(1-til_y/(2**(zoomlevel-1)))
    lon=rat_x*180
    lat=360/pi*atan(exp(pi*rat_y))-90
    return (lat,lon)

for f in os.listdir():
    if not f[-4:]=='.jpg': continue
    items=f.split('_')
    til_y_top=int(items[0])
    til_x_left=int(items[1])
    zoomlevel=int(items[-1][-6:-4])
    (latmax,lonmin)=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
    (latmin,lonmax)=gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
    (xmin,ymin)=pyproj.transform(geographic,webmercator,lonmin,latmin)
    (xmax,ymax)=pyproj.transform(geographic,webmercator,lonmax,latmax)
    os.system("gdal_translate -of Gtiff -co COMPRESS=JPEG -a_ullr "+str(xmin)+" "+str(ymax)+" "+str(xmax)+" "+str(ymin)+" -a_srs epsg:3857 "+f+" "+f.replace(".jpg","_tmp.tif"))
    os.system("gdalwarp -of Gtiff -co COMPRESS=JPEG -s_srs epsg:3857 -t_srs epsg:4326 -ts 4096 4096 -rb "+f.replace(".jpg","_tmp.tif")+" "+f.replace(".jpg",".tif"))
