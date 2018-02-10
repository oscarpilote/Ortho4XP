#!/usr/bin/env python3

import requests
import sys
import io  
import time
from math import pi,log,tan,atan,exp
import random
from PIL import Image, ImageFilter



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
    rat_x=(til_x/(2**(zoomlevel-1))-1)
    rat_y=(1-til_y/(2**(zoomlevel-1)))
    lon=rat_x*180
    lat=360/pi*atan(exp(pi*rat_y))-90
    return [lat,lon]
##############################################################################

##############################################################################
def gtile_to_quadkey(til_x,til_y,zoomlevel):
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
def osmway_to_dicos(osm_content):
    
    pfile=io.StringIO(osm_content.decode('UTF-8'))
    dicosmn={}
    dicosmw={}
    dicosmw_name={}
    dicosmw_icao={}
    dicosmw_ele={}
    finished_with_file=False
    in_way=False
    first_line=pfile.readline()
    if "'" in first_line:
        separator="'"
    else:
        separator='"'
    while not finished_with_file==True:
        items=pfile.readline().split(separator)
        if '<node id=' in items[0]:
            id=items[1]
            for j in range(0,len(items)):
                if items[j]==' lat=':
                    slat=items[j+1]
                elif items[j]==' lon=':
                    slon=items[j+1]
            dicosmn[id]=[slat,slon]
        elif '<way id=' in items[0]:
            in_way=True
            wayid=items[1]
            dicosmw[wayid]=[]  
        elif '<nd ref=' in items[0]:
            dicosmw[wayid].append(dicosmn[items[1]])
        elif '<tag k=' in items[0] and in_way and items[1]=='name':
            dicosmw_name[wayid]=items[3]
        elif '<tag k=' in items[0] and in_way and items[1]=='icao':
            dicosmw_icao[wayid]=items[3]
        elif '<tag k=' in items[0] and in_way and items[1]=='ele':
            dicosmw_ele[wayid]=items[3]
        elif '</osm>' in items[0]:
            finished_with_file=True
    pfile.close()
    return [dicosmw,dicosmw_name,dicosmw_icao,dicosmw_ele]
##############################################################################

##############################################################################
def http_requests_form(til_x_left,til_y_top,zoomlevel,website):
    
    til_x=til_x_left
    til_y=til_y_top
    user_agent_generic="Mozilla/5.0 (X11; Linux x86_64; rv:38.0) "+\
                       "Gecko/20100101 Firefox/38.0 Iceweasel/38.2.1"
    fake_headers_generic={\
            'User-Agent':user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate'\
            }

    ####################################################
    # Bing (restrictive copyright)
    # Viewer on www.bing.com/maps
    ####################################################
    if website=="BI":
        server=random.randint(0,3) # can be quicker with a fixed number between 0 and 3
        url="http://r"+str(server)+".ortho.tiles.virtualearth.net/tiles/a"+\
            gtile_to_quadkey(til_x,til_y,zoomlevel)+".jpeg?g=136"
        fake_headers=fake_headers_generic       

    ####################################################
    # Google (restrictive copyright, version as of 2015)
    # Viewer on maps.google.com
    ####################################################
    elif website == "GO2":
        server=random.randint(0,3) # can be quicker with a fixed number between 0 and 3
        url="http://khms"+str(server)+".google.com/kh/v=700&x="+\
            str(til_x)+"&y="+str(til_y)+"&z="+str(zoomlevel)
        fake_headers={\
            'Host':'khms'+str(server)+'.google.com',\
            'User-Agent': user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Accept-Language':'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',\
            'Accept-Encoding':'gzip,deflate',\
            'Referer':'https://www.google.fr',\
            'Origin':'https://www.google.fr',\
            'Connection':'keep-alive'\
                }
    
    ####################################################
    # Here.com (was asked for, similar to Bing in many places it seems) 
    ####################################################
    elif website=="Here":
        server=random.randint(1,4)
        url="https://"+str(server)+".aerial.maps.api.here.com/"+\
            "maptile/2.1/maptile/2ae1d8fbb0/satellite.day/"+str(zoomlevel)+"/"+\
             str(til_x)+"/"+str(til_y)+"/256/jpg?app_id=xWVIueSv6JL0aJ5xqTxb&app_code=djPZyynKsbTjIUDOBcHZ2g"
        fake_headers=fake_headers_generic       

    
    ####################################################
    # Arcgis Online
    # Copyright is the one of the underlying provider
    # Has an IP ban if download is heavy
    ####################################################
    elif website=="Arc":
        url="http://server.arcgisonline.com/arcgis/rest/"+\
            "services/World_Imagery/MapServer/tile/"+str(zoomlevel)+\
            "/"+str(til_y)+"/"+str(til_x)
        fake_headers=fake_headers_generic       
    
           
    ####################################################
    # Openstreetmap (open data)
    # Viewer on www.openstreetmap.org
    ####################################################
    elif website=="OSM":
        server=random.randint(0,2)
        if server==0:
            letter='a'
        elif server==1:
            letter='b'
        else:
            letter='c'
        url="http://"+letter+".tile.openstreetmap.org/"+str(zoomlevel)+"/"+\
            str(til_x)+"/"+str(til_y)+".png"
        fake_headers=fake_headers_generic       


    ####################################################
    # The Alaska Statewide Orthoimagery Mosaic
    # Permissive copyright
    ####################################################
    elif website=="ASK_1":
       url="http://tiles.gina.alaska.edu/tilesrv/bdl/tile/"+str(til_x_left)+"/"+str(til_y_top)+"/"+str(zoomlevel)
       fake_headers=fake_headers_generic     

    ####################################################
    # The Alaska Statewide Orthoimagery Mosaic
    # Permissive copyright
    ####################################################
    elif website=="ASK_2":
       url="http://tiles.gina.alaska.edu/tiles/SPOT5.SDMI.ORTHO_RGB/tile/"+str(til_x_left)+"/"+str(til_y_top)+"/"+str(zoomlevel)
       fake_headers=fake_headers_generic     

    ####################################################
    # National geographical institute for France
    # Restrictive copyright (should adapt to INSPIRE!)
    ####################################################
    elif  website=="FR":
        url="http://wxs.ign.fr/j5tcdln4ya4xggpdu4j0f0cn"+\
             "/geoportail/wmts?"+\
            "&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER="+\
            "ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&"+\
            "TILEMATRIXSET=PM&TILEMATRIX="+str(zoomlevel)+"&TILEROW="+\
            str(til_y)+"&TILECOL="+str(til_x)

        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate',\
            'Referer':'http://tab.geoportail.fr'\
            }       

    
    ####################################################
    # National geographical institute for Spain
    # Permissive copyright
    ####################################################
    elif website=="SP":
        url="http://www.ign.es/wmts/pnoa-ma/geoserver/gwc/service/wmts?"+\
            "FORMAT=image/jpeg&VERSION=1.0.0&SERVICE=WMTS&REQUEST=GetTile&"+\
            "LAYER=OI.OrthoimageCoverage&TILEMATRIXSET=GoogleMapsCompatible&"+\
            "TILEMATRIX="+str(zoomlevel)+"&TILEROW="+str(til_y)+"&TILECOL="+str(til_x)
        fake_headers=fake_headers_generic       


    ####################################################
    # Sweden Hitta 
    # Unsure about copyright
    ####################################################
    elif website=='Hitta':
        url="http://static.hitta.se/tile/v3/1/"+str(zoomlevel)+"/"+str(til_x)+"/"+str(2**zoomlevel-1-til_y)
        fake_headers=fake_headers_generic       


    ####################################################
    # National geographical institute of Austria 
    ####################################################
    elif website=='OST': 
        server=random.randint(1,4)
        url="http://maps"+str(server)+".wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/"+\
             str(zoomlevel)+"/"+str(til_y_top)+"/"+str(til_x_left)+".jpeg"
        fake_headers=fake_headers_generic

    ####################################################
    # Swiss Federal Geo Portal
    # Restrictive copyright + water marked 
    # (see http://www.swisstopo.admin.ch/internet/swisstopo/en/home/swisstopo/legal_bases/use_without_licence.html
    ####################################################
    elif website=="CH":
        server=random.randint(0,4)
        url="http://wmts1"+str(server)+".geo.admin.ch/"+\
            "1.0.0/ch.swisstopo.swissimage/default/20151231/3857/"+\
            str(zoomlevel)+"/"+str(til_x)+"/"+str(til_y)+".jpeg"
        fake_headers={\
                'User-Agent': user_agent_generic,\
                'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
                'Accept-Language':'en-US,en;q=0.5',\
                'Accept-Encoding':'gzip,deflate',\
                'Referer':'http://map.geo.admin.ch',\
				'Origin':'http://map.geo.admin.ch',\
                'Connection':'keep-alive'\
                }
    
    
    ####################################################
    # Mapy.cz CZ
    # Viewer on mapy.cz (thanks to 'suplere')
    ####################################################
    elif website=="CZ":
        server=random.randint(1,4)
        url="http://m"+str(server)+".mapserver.mapy.cz/ophoto-m/"+\
        	str(zoomlevel)+"-"+str(til_x)+"-"+str(til_y)
        fake_headers=fake_headers_generic
    
    ####################################################
    # Australia South Wester territory : Sixmaps
    # Unsure about copyright
    ####################################################
    elif website=='AU_1':
        server=random.randint(1,4)
        url="http://maps"+str(server)+".six.nsw.gov.au/arcgis/rest/services/"\
               +"sixmaps/LPI_Imagery_Best/MapServer/tile/"+\
               str(zoomlevel)+"/"+str(til_y)+"/"+str(til_x)
        fake_headers=fake_headers_generic       
    
    ####################################################
    # New Zealand (partial but very good in some places)
    # Open data
    ####################################################
    elif website=='NZ':
        server=random.randint(1,4)
        dico_letters={1:"a",2:"b",3:"c",4:"d"}
        url= "https://tiles-"+dico_letters[server]+".data-cdn.linz.govt.nz/services;"+\
             "key=2758b48d7a4446a6a49d2380b0882575/tiles/v4/layer=1934/"+\
             str(zoomlevel)+"/"+str(til_x)+"/"+str(til_y)+".png"
        fake_headers=fake_headers_generic       
    
    ####################################################
    # Japan 2007 imagery (partial but very good in some places)
    # Unsure about copyright
    ####################################################
    elif website=='JP':
        url= "http://cyberjapandata.gsi.go.jp/xyz/ort/"+\
             str(zoomlevel)+"/"+str(til_x)+"/"+str(til_y)+".jpg"
        fake_headers=fake_headers_generic       
    

    ####################################################
    # Kortal.fo (Farao Islands)
    # Unsure about copyright
    ####################################################
    elif website=='FO':
        url="http://www.kortal.fo/background/gwc/service/tms/1.0.0/FDS:Mynd_Verdin@EPSG:900913@jpg/"+\
            str(zoomlevel)+"/"+str(til_x)+"/"+str(2**zoomlevel-1-til_y)+".jpeg"
        fake_headers=fake_headers_generic    
        return [url,fake_headers]
    else:
        print("Unknown imagery provider")
        sys.exit()   
    return [url,fake_headers]
##############################################################################

##############################################################################
if __name__ == '__main__':
    try:
        icao_code=sys.argv[1]
    except:
        print("Syntax: python3 Ortho4WED.py ICAO_CODE ZL IMAGERY_CODE")
        print("Example: python3 Ortho4WED.py LFLJ 17 BI")
        print("Available providers include : Bing (BI) Google (GO2) Here (Here)")
        print("                              Arcgis (Arcg) Openstreetmap (OSM)")
        print("                              (see in the source file for more)") 
        sys.exit()
    try:
        zoomlevel=int(sys.argv[2])
    except:
        zoomlevel=17
    
    try: 
        website=sys.argv[3]
    except:
        website='BI'
    
    s=requests.Session()
    osm_download_ok = False
    tag='way["icao"="'+icao_code+'"]'
    
    while osm_download_ok != True:
       url="http://api.openstreetmap.fr/oapi/interpreter"+"?data=("+tag+"(-90,-180,90,180)"+";);(._;>>;);out meta;"
       r=s.get(url)
       if r.headers['content-type']=='application/osm3s+xml':
           osm_download_ok=True
       else:
           print("      OSM server was busy, new tentative...")
    
    [dicosmw,dicosmw_name,dicosmw_icao,dicosmw_ele]=osmway_to_dicos(r.content)
    
    
    if not dicosmw:
        print("No OSM boundary info found for that airport")
        sys.exit()

    latmin=90
    latmax=-90
    lonmin=180
    lonmax=-180
    
    for wayid in dicosmw:
        for node in dicosmw[wayid]:
            nlat=float(node[0])
            nlon=float(node[1])
            latmax = nlat>latmax and nlat or latmax
            latmin = nlat<latmin and nlat or latmin 
            lonmax = nlon>lonmax and nlon or lonmax
            lonmin = nlon<lonmin and nlon or lonmin 
    
    [til_x_min,til_y_min]=wgs84_to_gtile(latmax+0.0015,lonmin-0.002,zoomlevel)
    [til_x_max,til_y_max]=wgs84_to_gtile(latmin-0.0015,lonmax+0.002,zoomlevel)

    nx=til_x_max-til_x_min+1
    ny=til_y_max-til_y_min+1
    total=nx*ny
    steps=int(total/10.0)
    done=0

    big_image=Image.new('RGB',(256*nx,256*ny))
    
    for til_x in range(til_x_min,til_x_max+1):
        for til_y in range(til_y_min,til_y_max+1):
            successful_download=False
            [url,fake_headers]=http_requests_form(til_x,til_y,zoomlevel,website)
            while successful_download==False:
                try:
                    r=s.get(url, headers=fake_headers)
                    successful_download=True
                except:
                    print("Server error, trying again in 1 sec")
                    time.sleep(1)
                if ('Response [20' in str(r)):
                    small_image=Image.open(io.BytesIO(r.content))
                    big_image.paste(small_image,((til_x-til_x_min)*256,(til_y-til_y_min)*256))
                    done+=1
                    if done%steps==0: 
                        sys.stdout.write('*')  
                        sys.stdout.flush()
                else:
                    small_image=Image.new('RGB',(256,256),'white')
                    big_image.paste(small_image,((til_x-til_x_min)*256,(til_y-til_y_min)*256))
    
    big_image.save(icao_code+"_"+website+"_"+sys.argv[2]+".jpg")
    
    [latmaxphoto,lonminphoto]=gtile_to_wgs84(til_x_min,til_y_min,zoomlevel)
    [latminphoto,lonmaxphoto]=gtile_to_wgs84(til_x_max+1,til_y_max+1,zoomlevel)
    
    fichier = open(icao_code+"_"+website+"_"+sys.argv[2]+".txt", "w")

    print("\nOrthophoto has been saved under "+icao_code+"_"+website+"_"+sys.argv[2]+".jpg")
    fichier.write("Orthophoto has been saved under "+icao_code+"_"+website+"_"+sys.argv[2]+".jpg\n")
    print("You can open it in WED and use the following for anchoring its corners:")
    fichier.write("You can open it in WED and use the following for anchoring its corners:\n")
    print("Upper left  corner is lat="+'{:+.6f}'.format(latmaxphoto)+" lon="+'{:+.6f}'.format(lonminphoto))
    fichier.write("Upper left  corner is lat="+'{:+.6f}'.format(latmaxphoto)+" lon="+'{:+.6f}'.format(lonminphoto)+"\n")
    print("Upper right corner is lat="+'{:+.6f}'.format(latmaxphoto)+" lon="+'{:+.6f}'.format(lonmaxphoto))
    fichier.write("Upper right corner is lat="+'{:+.6f}'.format(latmaxphoto)+" lon="+'{:+.6f}'.format(lonmaxphoto)+"\n")
    print("Lower left  corner is lat="+'{:+.6f}'.format(latminphoto)+" lon="+'{:+.6f}'.format(lonminphoto))
    fichier.write("Lower left  corner is lat="+'{:+.6f}'.format(latminphoto)+" lon="+'{:+.6f}'.format(lonminphoto)+"\n")
    print("Lower right corner is lat="+'{:+.6f}'.format(latminphoto)+" lon="+'{:+.6f}'.format(lonmaxphoto))
    fichier.write("Lower right corner is lat="+'{:+.6f}'.format(latminphoto)+" lon="+'{:+.6f}'.format(lonmaxphoto)+"\n")

    fichier.close()

##############################################################################
    

