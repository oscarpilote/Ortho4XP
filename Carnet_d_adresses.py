##############################################################################
#                                                                            #
#      The address book for Ortho4XP.                                        #
#      "Norway source hack" based on the version from November 8th 2016      #
#      Courtesy of Jaromaz with minor modifications by Daikan.               #
#      Requires modified version of Ortho4XP.py (v119r2_norway_hack)         #
#                                                                            #
#                                                                            #
#      You can expand it with your preferred providers, the following        #
#      is just a sample one based on prior ideas or queries.                 #
#      Httpfox will help you to make new friends.                            #
#                                                                            #
##############################################################################

try: # pyproj allows to deal with wms which don't accept wgs84 bounds, like 'SE2' below
    import pyproj
    pyproj_loaded=True
    epsg={} 
    epsg['4326']=pyproj.Proj(init='epsg:4326')
    epsg['3006']=pyproj.Proj(init='epsg:3006')
    epsg['32632']=pyproj.Proj(init='epsg:32632')
    epsg['32633']=pyproj.Proj(init='epsg:32633')
    epsg['2056']=pyproj.Proj(init='epsg:2056')
    epsg['25832']=pyproj.Proj(init='epsg:25832')
    epsg['102060']=pyproj.Proj(init='epsg:3912')
    epsg['3301']=pyproj.Proj(init='epsg:3301')
except:
    print("Pyproj is not present, some providers won't be available.")
    pyproj_loaded=False


# When you add a provider you must indicate its code in the appropriate list below
# so that it appears in the interface
# You can also remove the codes you don't want to appear in the interface.

# 1) List of websites that use WGS84 TMS standard with 256x256 pixmaps.
px256_list=['OSM','BI','GO2','Arc','Here','USA_2','FR','FRorth','FRom','FRsat','FRsat2','Top25','SP','CH','OST','SE','Hitta','CZ','AU_1','JP','NZ','ASK_1','ASK_2','F44','FRsatp','FO','g2xpl_8','g2xpl_16']                     
# 2) List of WMS sites accepting 2048x2048 image requests
wms2048_list=['DE','IT','PL','SLO','CRO','SE2','BE_Wa','NE','NE2','DK','USA_1','GE','EST','NO'] 

# If the provider uses a different projection than epsg:4326 indicate it here below
st_proj_coord_dict={'USA_1':'2056','DE':'25832','SE2':'3006','SLO':'102060','GE':'2056','EST':'3301','NO':'32633'}

##############################################################################
# NO ticket ID update task                                                   #
# - Starts a background thread to update the ticket ID every 15 minutes      #
##############################################################################
##############################################################################

# import urllib.request,re,time,threading
import urllib.request,re
endno = 0
ticketno = ''
def ticketgen():

    # Ticket URL
    ticketurl = 'http://www.norgeskart.no/ws/esk.py?wms.nib'
    # Interval in minutes
    tginterval = 15

    global ticketno
    global endno

    if endno == 0:
        threading.Timer((int(tginterval)*60), ticketgen).start()

    ticketget = urllib.request.urlopen(ticketurl)
    if ticketget.getcode() == 200:
        ticketget = ticketget.read()
        ticketget = str(ticketget)
        ticketget = re.sub('"','', ticketget.rstrip())
        ticketget = re.sub("b'",'', ticketget.rstrip())
        ticketget = re.sub("'",'', ticketget.rstrip())
        ticketget = ticketget[:-2];
        ticketno = ticketget
    return
ticketgen()
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
        server=3 #random.randint(0,3) # can be quicker with a fixed number between 0 and 3
        url="http://r"+str(server)+".ortho.tiles.virtualearth.net/tiles/a"+\
            gtile_to_quadkey(til_x,til_y,zoomlevel)+".jpeg?g=136"
        fake_headers=fake_headers_generic       

    ####################################################
    # Google (restrictive copyright, version as of 2015)
    # Viewer on maps.google.com
    ####################################################
    elif website in["GO2","GO",'g2xpl_8','g2xpl_16']:
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
            "maptile/2.1/maptile/3356e3cd65/satellite.day/"+str(zoomlevel)+"/"+\
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
    # The National map (USGS) 1 foot orthoimagery / WMS
    # Permissive copyright
    # Beware that the US territory is not completely in
    ####################################################
    elif website=="USA_1":
        [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        url="http://raster.nationalmap.gov/arcgis/services/Orthoimagery/"+\
            "USGS_EROS_Ortho_1Foot/ImageServer/WMSServer?FORMAT=image/jpeg"+\
            "&VERSION=1.1.1&SERVICE=WMS&REQUEST=GetMap&LAYERS=0&STYLES="+\
            "&SRS=EPSG:4326&WIDTH=2048&HEIGHT=2048&BBOX="+\
            str(lonmin)+','+str(latmin)+','+str(lonmax)+','+str(latmax)
        fake_headers=fake_headers_generic       
    

    ####################################################
    # The National map (USGS) 1 foot orthoimagery / TMS
    # Permissive copyright
    # Same as above but filled with some data where 
    # missing (this is actually 'Arc'...)
    ####################################################
    elif website=="USA_2":
       url="http://services.arcgisonline.com/ArcGIS/rest/services/"+\
           "World_Imagery/MapServer/tile/"+str(zoomlevel)+"/"+str(til_y_top)+\
           "/"+str(til_x_left)
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
    elif  website=="FRorth":
        url="http://wxs.ign.fr/61fs25ymczag0c67naqvvmap"+\
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
    
    elif  website=="FRom":
        url="http://wxs.ign.fr/an7nvfzojv5wa96dsga5nk8w"+\
             "/geoportail/wmts?"+\
            "&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER="+\
            "ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg&"+\
            "TILEMATRIXSET=PM&TILEMATRIX="+str(zoomlevel)+"&TILEROW="+\
            str(til_y)+"&TILECOL="+str(til_x)

        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Host':'wxs.ign.fr',\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate, br',\
            'Referer':'https://www.geoportail.gouv.fr/carte/'\
            }       

    ####################################################
    # National geographical institute for France
    # Restrictive copyright (should adapt to INSPIRE!)
    # Low resolution (visible on geosud.ign.fr)
    ####################################################
    elif  website=="FRsat":
        if zoomlevel>=17:
            return 'error'
        url="http://wxs.ign.fr/61fs25ymczag0c67naqvvmap"+\
             "/geoportail/wmts?"+\
            "&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER="+\
            "ORTHOIMAGERY.ORTHO-SAT.SPOT.2015&STYLE=normal&FORMAT=image/jpeg&"+\
            "TILEMATRIXSET=PM&TILEMATRIX="+str(zoomlevel)+"&TILEROW="+\
            str(til_y)+"&TILECOL="+str(til_x)

        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate',\
            'Referer':'http://geosud.ign.fr/visu.html'\
            }      
 
    elif  website=="FRsat2":
        if zoomlevel>=17:
            return 'error'
        url="http://wxs.ign.fr/61fs25ymczag0c67naqvvmap"+\
             "/geoportail/wmts?"+\
            "&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER="+\
            "ORTHOIMAGERY.ORTHO-SAT.SPOT.2014&STYLE=normal&FORMAT=image/jpeg&"+\
            "TILEMATRIXSET=PM&TILEMATRIX="+str(zoomlevel)+"&TILEROW="+\
            str(til_y)+"&TILECOL="+str(til_x)

        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate',\
            'Referer':'http://geosud.ign.fr/visu.html'\
            }       
    
    elif  website=="FRsatp":  # Pleiades 2014, very limited coverage... but for some specific islands
        if zoomlevel>=18:
            return 'error'
        url="http://wxs.ign.fr/61fs25ymczag0c67naqvvmap"+\
             "/geoportail/wmts?"+\
            "&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER="+\
            "ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2014&STYLE=normal&FORMAT=image/png&"+\
            "TILEMATRIXSET=PM&TILEMATRIX="+str(zoomlevel)+"&TILEROW="+\
            str(til_y)+"&TILECOL="+str(til_x)

        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate',\
            'Referer':'http://geosud.ign.fr/visu.html'\
            }        
    ####################################################
    # National geographical institute for France
    # Restrictive copyright (should adapt to INSPIRE!)
    # Just for fun over topo map
    ####################################################
    elif  website=="Top25":
        if zoomlevel>=16:
            return 'error'
        url="http://wxs.ign.fr/61fs25ymczag0c67naqvvmap"+\
             "/geoportail/wmts?"+\
            "&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER="+\
            "GEOGRAPHICALGRIDSYSTEMS.MAPS&STYLE=normal&FORMAT=image/jpeg&"+\
            "TILEMATRIXSET=PM&TILEMATRIX="+str(zoomlevel)+"&TILEROW="+\
            str(til_y)+"&TILECOL="+str(til_x)

        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate',\
            'Referer':'http://geosud.ign.fr/visu.html'\
            }       
    
    
    ####################################################
    # German Geo Data Centre - DOP Online
    # Copyright is the one of the underlying provider 
    ####################################################
    elif website=="DE":
        if not pyproj_loaded:
            return 'error'
        text_til_x_left=(til_x_left//16)*16
        text_til_y_top=(til_y_top//16)*16
        montx=0 if til_x_left%16==0 else 1
        monty=0 if til_y_top%16==0 else 1
        [latmax,lonmin]=gtile_to_wgs84(text_til_x_left,text_til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(text_til_x_left+16,text_til_y_top+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg['4326'],epsg['25832'],lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg['4326'],epsg['25832'],lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg['4326'],epsg['25832'],lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg['4326'],epsg['25832'],lonmax,latmin)
        text_minx=min(ulx,llx)
        text_maxx=max(urx,lrx)
        text_miny=min(lly,lry)
        text_maxy=max(uly,ury)
        deltax=text_maxx-text_minx
        deltay=text_maxy-text_miny
        minx=text_minx+montx*deltax/2.0
        maxx=minx+deltax/2.0
        miny=text_miny+(1-monty)*deltay/2.0
        maxy=miny+deltay/2.0
        url="http://sg.geodatenzentrum.de/wms_dop40?"+\
            "FORMAT=image%2Fjpeg"+\
            "&TRANSPARENT=FALSE&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&LAYERS=rgb&SRS=EPSG%3A25832&BBOX="+\
            str(minx)+','+str(miny)+','+str(maxx)+','+str(maxy)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate',\
            'Cookie':'DLZBKG=42a227e9-e325-49e3-beb1-a007a0dcc28d; bkg_cookie_test=wp2vcv5e'\
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
    # National geographical institute of Italy
    # Slightly permissive copyright 
    ####################################################
    elif website=='IT': 
        [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        url="http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/"+\
            "ortofoto_colore_06.map&version=1.3.0&service=WMS&request=GetMap&"+\
            "LAYERS=OI.ORTOIMMAGINI.2006.&format=image/jpeg&STYLE=default&"+\
            "CRS=EPSG%3A4326&BBOX="+\
            str(latmin)+','+str(lonmin)+','+str(latmax)+','+str(lonmax)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic
    elif website=='IT2': 
        [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        url="http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/"+\
            "ortofoto_colore_00.map&version=1.3.0&service=WMS&request=GetMap&"+\
            "LAYERS=OI.ORTOIMMAGINI.2000.&format=image/jpeg&STYLE=default&"+\
            "CRS=EPSG%3A4326&BBOX="+\
            str(latmin)+','+str(lonmin)+','+str(latmax)+','+str(lonmax)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic
    
    ####################################################
    # National geographical institute of Sweden (thanks to Magnus1)
    # Permissive copyright
    ####################################################
    elif website=='SE2':
        if not pyproj_loaded:
            return 'error'
        text_til_x_left=(til_x_left//16)*16
        text_til_y_top=(til_y_top//16)*16
        montx=0 if til_x_left%16==0 else 1
        monty=0 if til_y_top%16==0 else 1
        [latmax,lonmin]=gtile_to_wgs84(text_til_x_left,text_til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(text_til_x_left+16,text_til_y_top+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg['4326'],epsg['3006'],lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg['4326'],epsg['3006'],lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg['4326'],epsg['3006'],lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg['4326'],epsg['3006'],lonmax,latmin)
        text_minx=min(ulx,llx)
        text_maxx=max(urx,lrx)
        text_miny=min(lly,lry)
        text_maxy=max(uly,ury)
        deltax=text_maxx-text_minx
        deltay=text_maxy-text_miny
        minx=text_minx+montx*deltax/2.0
        maxx=minx+deltax/2.0
        miny=text_miny+(1-monty)*deltay/2.0
        maxy=miny+deltay/2.0
        url="https://kso.etjanster.lantmateriet.se/karta/ortofoto/wms/v1?"+\
            "LAYERS=orto,orto025&EXCEPTIONS=application%2Fvnd.ogc.se_xml"+\
            "&FORMAT=image%2Fpng"+\
            "&STYLES=default%2Cdefault"+\
            "&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&SRS=EPSG%3A3006&BBOX="+\
            str(minx)+','+str(miny)+','+str(maxx)+','+str(maxy)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Accept':'image/png,image/*;q=0.8,*/*;q=0.5',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate'\
            'Referer: https://kso.etjanster.lantmateriet.se/'\
            }

    ####################################################
    # Sweden Hitta 
    # Unsure about copyright
    ####################################################
    elif website=='Hitta':
        url="http://static.hitta.se/tile/v3/1/"+str(zoomlevel)+"/"+str(til_x)+"/"+str(2**zoomlevel-1-til_y)
        fake_headers=fake_headers_generic       

    ####################################################
    # Sweden Eniro karta (thanks to Durian)
    # Unsure about copyright
    ####################################################
    elif website=='SE':
        url="http://map04.eniro.no/geowebcache/service/tms1.0.0/aerial/"+\
            str(zoomlevel)+"/"+str(til_x)+"/"+str(2**zoomlevel-1-til_y)+".jpeg"
        fake_headers=fake_headers_generic       


    ####################################################
    # National geographical institute of Poland 
    # Unsure about copyright
    ####################################################
    elif website=='PL':
        [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        url="http://mapy.geoportal.gov.pl/wss/service/img/guest/ORTO/MapServer/WMSServer?FORMAT=image%2Fjpeg&"+\
            "VERSION=1.1.1&SERVICE=WMS&REQUEST=GetMap&LAYERS=Raster&STYLES="+\
            "&SRS=EPSG%3A4326&BBOX="+\
            str(lonmin)+','+str(latmin)+','+str(lonmax)+','+str(latmax)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic
   
    ####################################################
    # National geographical institute of Norway 
    # Visible on norgeskart.no 
    # Needs a ticket id which can be generated with
    # http://www.norgeskart.no/ws/esk.py?wms.nib
    # Unsure about copyright
    ####################################################
    elif website in ['NO']: 
        if not pyproj_loaded:
            return 'error'
        text_til_x_left=(til_x_left//16)*16
        text_til_y_top=(til_y_top//16)*16
        montx=0 if til_x_left%16==0 else 1
        monty=0 if til_y_top%16==0 else 1
        [latmax,lonmin]=gtile_to_wgs84(text_til_x_left,text_til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(text_til_x_left+16,text_til_y_top+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg['4326'],epsg['32633'],lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg['4326'],epsg['32633'],lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg['4326'],epsg['32633'],lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg['4326'],epsg['32633'],lonmax,latmin)
        text_minx=min(ulx,llx)
        text_maxx=max(urx,lrx)
        text_miny=min(lly,lry)
        text_maxy=max(uly,ury)
        deltax=text_maxx-text_minx
        deltay=text_maxy-text_miny
        minx=text_minx+montx*deltax/2.0
        maxx=minx+deltax/2.0
        miny=text_miny+(1-monty)*deltay/2.0
        maxy=miny+deltay/2.0
        url="http://wms.geonorge.no/skwms1/wms.nib"+\
            "?LAYERS=ortofoto"+\
            "&TRANSPARENT=FALSE"+\
            "&FORMAT=image%2Fjpeg"+\
            "&SERVICE=WMS"+\
            "&VERSION=1.1.1"+\
            "&REQUEST=GetMap"+\
            "&STYLES="+\
            "&ticket="+ticketno+\
            "&SRS=EPSG%3A32633"+\
            "&BBOX="+\
             str(minx)+','+str(miny)+','+str(maxx)+','+str(maxy)+\
             "&WIDTH=2048&HEIGHT=2048"
        fake_headers={\
            'User-Agent':user_agent_generic,\
            'Accept':'*/*',\
            'Connection':'keep-alive',\
            'Accept-Encoding':'gzip, deflate',\
            'Referer':'http://norgeskart.no/geoportal/'\
            }

    ####################################################
    # National geographical institute of Denmark
    ####################################################
    elif website=='DK': 
        [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        url="http://kortforsyningen.kms.dk/orto_foraar?LAYERS=orto_foraar&FORMAT=image%2Fjpeg"+\
            "&BGCOLOR=0xFFFFFF&TICKET=d4184a234513c2eab77edd8ac68e561b&PROJECTION=EPSG%3A4326"+\
            "&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES=&SRS=EPSG%3A4326&BBOX="+\
            str(lonmin)+','+str(latmin)+','+str(lonmax)+','+str(latmax)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic


    ####################################################
    # National geographical institute of Belgium (Wallonie only)
    # Permissive copyright
    ####################################################
    elif website=='BE_Wa': 
        [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        url="http://geoservices.wallonie.be/arcgis/services/IMAGERIE/ORTHO_2012_2013/"+\
            "MapServer/WMSServer?service=WMS&VERSION=1.3.0&request=GetMap&STYLES="+\
            "&LAYERS=0&FORMAT=image%2Fjpeg&CRS=EPSG%3A4326&BBOX="+\
            str(latmin)+','+str(lonmin)+','+str(latmax)+','+str(lonmax)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic

    ####################################################
    # National geographical institute of the Netherlands (lufoto2005)
    # Permissive copyright
    ####################################################
    elif website=='NE': 
        [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        url="http://gdsc.nlr.nl/wms/lufo2005?"+\
            "service=WMS&VERSION=1.1.1&request=GetMap&STYLES="+\
            "&LAYERS=lufo2005-1m&FORMAT=image%2Fjpeg&SRS=EPSG%3A4326&BBOX="+\
            str(lonmin)+','+str(latmin)+','+str(lonmax)+','+str(latmax)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic
    
    ####################################################
    # National geographical institute of the Netherlands (dlnk2014)
    # Permissive copyright
    ####################################################
    elif website=='NE2': 
        [latmax,lonmin]=gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        url="http://geodata1.nationaalgeoregister.nl/luchtfoto/wms?LAYERS=luchtfoto_png"+\
            "&SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&STYLES="+\
            "&EXCEPTIONS=application%2Fvnd.ogc.se_inimage&FORMAT=image%2Fpng"+\
            "&SRS=EPSG%3A4326&BBOX="+\
            str(lonmin)+','+str(latmin)+','+str(lonmax)+','+str(latmax)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic
    
    ####################################################
    # Geoportal Slovenia
    ####################################################
    elif website=='SLO':
        if not pyproj_loaded:
            return 'error'
        text_til_x_left=(til_x_left//16)*16
        text_til_y_top=(til_y_top//16)*16
        montx=0 if til_x_left%16==0 else 1
        monty=0 if til_y_top%16==0 else 1
        [latmax,lonmin]=gtile_to_wgs84(text_til_x_left,text_til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(text_til_x_left+16,text_til_y_top+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg['4326'],epsg['102060'],lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg['4326'],epsg['102060'],lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg['4326'],epsg['102060'],lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg['4326'],epsg['102060'],lonmax,latmin)
        text_minx=min(ulx,llx)
        text_maxx=max(urx,lrx)
        text_miny=min(lly,lry)
        text_maxy=max(uly,ury)
        deltax=text_maxx-text_minx
        deltay=text_maxy-text_miny
        minx=text_minx+montx*deltax/2.0
        maxx=minx+deltax/2.0
        miny=text_miny+(1-monty)*deltay/2.0
        maxy=miny+deltay/2.0
        url="http://gis.arso.gov.si/arcgis/services/AO_DOF_2009_2011_AG101/"+\
             "MapServer/WMSServer?request=GetMap&service=WMS&VERSION=1.3.0"+\
             "&STYLES=&LAYERS=0,1,2&FORMAT=image/jpeg&CRS=EPSG:102060&BBOX="+\
             str(minx)+','+str(miny)+','+str(maxx)+','+str(maxy)+\
             "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic
   
    ####################################################
    # Geoportal Croatia
    ####################################################
    elif website=='CRO':
        url="http://geoportal.dgu.hr/wms?"+\
            "&version=1.3.0&service=WMS&request=GetMap&"+\
            "LAYERS=DOF&format=image/jpeg&STYLE=default&"+\
            "CRS=EPSG%3A4326&BBOX="+\
            str(latmin)+','+str(lonmin)+','+str(latmax)+','+str(lonmax)+\
            "&WIDTH=2048&HEIGHT=2048" 
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

    ####################################################
    # Estonian Geoportal
    # Visible on http://kaart.delfi.ee
    # Permissive copyright
    ####################################################
    elif website=="EST":
        if not pyproj_loaded:
            return 'error'
        text_til_x_left=(til_x_left//16)*16
        text_til_y_top=(til_y_top//16)*16
        montx=0 if til_x_left%16==0 else 1
        monty=0 if til_y_top%16==0 else 1
        [latmax,lonmin]=gtile_to_wgs84(text_til_x_left,text_til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(text_til_x_left+16,text_til_y_top+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg['4326'],epsg['3301'],lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg['4326'],epsg['3301'],lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg['4326'],epsg['3301'],lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg['4326'],epsg['3301'],lonmax,latmin)
        text_minx=min(ulx,llx)
        text_maxx=max(urx,lrx)
        text_miny=min(lly,lry)
        text_maxy=max(uly,ury)
        deltax=text_maxx-text_minx
        deltay=text_maxy-text_miny
        minx=text_minx+montx*deltax/2.0
        maxx=minx+deltax/2.0
        miny=text_miny+(1-monty)*deltay/2.0
        maxy=miny+deltay/2.0
        url="http://kaart.maaamet.ee/wms/fotokaart?FORMAT=image/jpeg&VERSION=1.1.1&SERVICE=WMS&REQUEST=GetMap"+\
            "&LAYERS=EESTIFOTO&STYLES=&SRS=EPSG%3A3301&WIDTH=2048&HEIGHT=2048&BBOX="+\
            str(minx)+','+str(miny)+','+str(maxx)+','+str(maxy)
        fake_headers=fake_headers_generic       
    

    ####################################################
    # La Loire atlantique vue du ciel
    # Open (and nice) data ! 
    ####################################################
    elif  website=="F44":
        server=random.randint(1,7)
        dico_letters={1:"a",2:"b",3:"c",4:"d",5:"e",6:"f",7:"g"}
        url="http://"+dico_letters[server]+".tiles.cg44.makina-corpus.net/ortho-2012/"\
                +str(zoomlevel)+"/"+str(til_x)+"/"+str(2**zoomlevel-1-til_y)+".jpg"
        fake_headers=fake_headers_generic        
   
    ####################################################
    # Geneva area
    # Visible on ge.ch/sitg
    # Permissive copyright
    ####################################################
    elif website=="GE":
        if not pyproj_loaded:
            return 'error'
        text_til_x_left=(til_x_left//16)*16
        text_til_y_top=(til_y_top//16)*16
        montx=0 if til_x_left%16==0 else 1
        monty=0 if til_y_top%16==0 else 1
        [latmax,lonmin]=gtile_to_wgs84(text_til_x_left,text_til_y_top,zoomlevel)
        [latmin,lonmax]=gtile_to_wgs84(text_til_x_left+16,text_til_y_top+16,zoomlevel)
        [ulx,uly]=pyproj.transform(epsg['4326'],epsg['2056'],lonmin,latmax)
        [urx,ury]=pyproj.transform(epsg['4326'],epsg['2056'],lonmax,latmax)
        [llx,lly]=pyproj.transform(epsg['4326'],epsg['2056'],lonmin,latmin)
        [lrx,lry]=pyproj.transform(epsg['4326'],epsg['2056'],lonmax,latmin)
        text_minx=min(ulx,llx)
        text_maxx=max(urx,lrx)
        text_miny=min(lly,lry)
        text_maxy=max(uly,ury)
        deltax=text_maxx-text_minx
        deltay=text_maxy-text_miny
        minx=text_minx+montx*deltax/2.0
        maxx=minx+deltax/2.0
        miny=text_miny+(1-monty)*deltay/2.0
        maxy=miny+deltay/2.0
        url="http://ge.ch/ags2/services/Orthophotos_2012/"+\
            "MapServer/WMSServer?FORMAT=image/jpeg&VERSION=1.1.1&SERVICE=WMS&REQUEST=GetMap&LAYERS=0&STYLES=&SRS=EPSG%3A2056&BBOX="+\
            str(minx)+','+str(miny)+','+str(maxx)+','+str(maxy)+\
            "&WIDTH=2048&HEIGHT=2048"
        fake_headers=fake_headers_generic       
    else:
        try:
            [url,fake_headers]=APL_request(til_x_left,til_y_top,zoomlevel,website)
        except:
            print("The photo album \'"+website+"\' that you have requested "+\
              "is not or no longer implemented in this release. You will get white tiles !!!")     
            return ['error','']
    return [url,fake_headers]
##############################################################################
