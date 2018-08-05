import pickle
from math import floor, ceil, pi, cos, sin
import numpy
from shapely import geometry,  affinity,  ops
from PIL import Image, ImageDraw 
from rtree import index
import O4_UI_Utils as UI
import O4_Vector_Utils as VECT
import O4_Geo_Utils as GEO
import O4_DEM_Utils as DEM
import O4_File_Names as FNAMES

runway_chunks=100   # how much chunks to split a runway longitudinally, ... 
chunk_min_size=10   # as long as the chunks do not get smaller than this (in meters) .

def discover_airport_names(airport_layer,dico_airports): 
    for osmtype in ('r','w','n'):
        for osmid in (x for x in airport_layer.dicosmtags[osmtype] if 'aerodrome' in airport_layer.dicosmtags[osmtype][x].values() or 'airstrip' in airport_layer.dicosmtags[osmtype][x].values()): 
            key=None
            if 'icao' in   airport_layer.dicosmtags[osmtype][osmid]:
                key=airport_layer.dicosmtags[osmtype][osmid]['icao'][:4]
                if key in dico_airports: continue 
                dico_airports[key]={'key_type':'icao'}
            elif 'iata' in airport_layer.dicosmtags[osmtype][osmid]:
                key=airport_layer.dicosmtags[osmtype][osmid]['iata'][:3]
                if key in dico_airports: continue 
                dico_airports[key]={'key_type':'iata'}
            elif 'local_ref' in airport_layer.dicosmtags[osmtype][osmid]:
                key=airport_layer.dicosmtags[osmtype][osmid]['local_ref']
                if key in dico_airports: continue
                dico_airports[key]={'key_type':'local_ref'}
            if 'name:en' in airport_layer.dicosmtags[osmtype][osmid]:
                name=airport_layer.dicosmtags[osmtype][osmid]['name:en'].replace("&quot;",'"').replace("&apos;","'")
            elif 'name:alt' in airport_layer.dicosmtags[osmtype][osmid]:
                name=airport_layer.dicosmtags[osmtype][osmid]['name:alt'].replace("&quot;",'"').replace("&apos;","'")
            elif 'name' in airport_layer.dicosmtags[osmtype][osmid]:
                name=airport_layer.dicosmtags[osmtype][osmid]['name'].replace("&quot;",'"').replace("&apos;","'")
            else:
                name='****'
            if len(name)>=60: name=name[:57]+'...'
            repr_node=airport_layer.dicosmn[osmid] if osmtype=='n' else \
                      tuple(numpy.mean(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[osmid]]),axis=0)) if  osmtype=='w' else \
                      tuple(numpy.mean(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmr[osmid]['outer'][0]]),axis=0))
            if not key:
                if name in dico_airports: continue
                if name!='****':
                    key=name
                    dico_airports[key]={'key_type':'name'}
                else:
                    key=repr_node
                    if key in dico_airports: continue
                    dico_airports[key]={'key_type':'repr_node'}
            dico_airports[key]['name']=name    
            dico_airports[key]['runway']=[]
            dico_airports[key]['runway_width']=[]
            dico_airports[key]['taxiway']=[]
            dico_airports[key]['apron']=[]
            dico_airports[key]['hangar']=[]
            dico_airports[key]['repr_node']=repr_node
            if 'smoothing_pix' in airport_layer.dicosmtags[osmtype][osmid]:
                try:
                    dico_airports[key]['smoothing_pix']=int(airport_layer.dicosmtags[osmtype][osmid]['smoothing_pix'])
                except:
                    pass
            try:
                dico_airports[key]['boundary']=geometry.Polygon(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[osmid]])) if osmtype=='w'\
                                           else ops.cascaded_union([geom for geom in [geometry.Polygon(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in nodelist])) for nodelist in airport_layer.dicosmr[osmid]['outer']]]) if osmtype=='r'\
                                           else None
                if dico_airports[key]['boundary'] and not dico_airports[key]['boundary'].is_valid: 
                    UI.lvprint(2,"Airport ",dico_airports[key],"OSM boundary is an invalid polygon, boundary set to None.")
                    dico_airports[key]['boundary']=None
            except:
                UI.lvprint(2,"WARNING:  A presumably erroneous tag marked aerodrome was found and skipped close to the point",repr_node,".\n          You might wish to check and correct it online in OSM.")  
                dico_airports.pop(key,None)
####################################################################################################

####################################################################################################    
def attach_surfaces_to_airports(airport_layer,dico_airports):
    ### We link surfaces to airports (this information is unfortunately not in OSM)
    for  surface_type in ('runway','taxiway','apron','hangar'):
        for wayid in (x for x in airport_layer.dicosmw if x in airport_layer.dicosmtags['w'] and 'aeroway' in airport_layer.dicosmtags['w'][x] and airport_layer.dicosmtags['w'][x]['aeroway']==surface_type):
            linestring=geometry.LineString(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]]))
            found_apt=False
            for airport in (x for x in dico_airports if dico_airports[x]['boundary']):
                if linestring.intersects(dico_airports[airport]['boundary']):
                    dico_airports[airport][surface_type].append(wayid)
                    found_apt=True
                    break
            if  found_apt: continue
            closest_dist=99999
            closest_apt=None
            pt_check=tuple(numpy.mean(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]]),axis=0))
            for airport in dico_airports:
                dist=GEO.dist(pt_check,dico_airports[airport]['repr_node'])
                if dist<closest_dist:
                    closest_dist=dist
                    closest_apt=airport
            if closest_apt and closest_dist<3500: 
                dico_airports[closest_apt][surface_type].append(wayid)
            else:
                try: 
                    name=airport_layer.dicosmtags['w'][wayid]['name']
                    dico_airports[name]={'key_type':'name','repr_node':pt_check,'name':name,'runway':[],'runway_width':[],'taxiway':[],'apron':[],'hangar':[],'boundary':None}
                    dico_airports[name][surface_type].append(wayid)
                except: 
                    dico_airports[pt_check]={'key_type':'repr_node','repr_node':pt_check,'name':'****','runway':[],'runway_width':[],'taxiway':[],'apron':[],'hangar':[],'boundary':None}
                    dico_airports[pt_check][surface_type].append(wayid)
    return
#################################################################################################### 

#################################################################################################### 
def sort_and_reconstruct_runways(tile,airport_layer,dico_airports):
     ### Runways in OSM are either encoded as linear features or as area features, and sometimes both for the same runway. Here we identify them and
     ### remove duplicates. Runways of linear type are also often split in OSM between multiple parts (displaced threshold etc), we also group them 
     ### together in this funcion.
    for airport in dico_airports:
        ## Distinction between linear and area runways
        runways_as_area=[]  # runways that are encoded in OSM as a polygon around their boundary
        runways_as_line=[]  # runways that are encoded in OSM as a linestrings 
        linear=[]           # temporary list containing parts (displaced threshold, etc) of OSM runways as linestrings
        linear_width=[]     # whenever the width tag appears for runways that are linear features, if not we'll try to guess the width from the length
        for wayid in dico_airports[airport]['runway']:
            if airport_layer.dicosmw[wayid][0]==airport_layer.dicosmw[wayid][-1]:
                runway_pol=geometry.Polygon(numpy.round(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([tile.lon,tile.lat]),7))
                if not runway_pol.is_empty and runway_pol.is_valid and runway_pol.area>1e-7:
                    runway_pol_rect=VECT.min_bounding_rectangle(runway_pol)
                    if wayid not in airport_layer.dicosmtags['w'] or 'custom' not in  airport_layer.dicosmtags['w'][wayid]:
                        discrep=runway_pol_rect.hausdorff_distance(runway_pol)
                        if discrep>0.0008:
                            UI.logprint("Bad runway (geometry too far from a rectangle) close to",airport,"at",dico_airports[airport]['repr_node'])
                            UI.vprint(1,"   !Bad runway (geometry too far from a rectangle) close to",airport,"at",dico_airports[airport]['repr_node'])
                            UI.vprint(1,"   !You may correct it editing the file ",FNAMES.osm_cached(tile.lat, tile.lon, 'airports'),"in JOSM.")
                            continue    
                    rectangle=numpy.array(VECT.min_bounding_rectangle(runway_pol).exterior.coords)
                    if VECT.length_in_meters(rectangle[0:2])<VECT.length_in_meters(rectangle[1:3]):
                        runway_start=(rectangle[0]+rectangle[1])/2
                        runway_end=(rectangle[2]+rectangle[3])/2
                        runway_width=VECT.length_in_meters(rectangle[0:2])
                    else:
                        runway_start=(rectangle[1]+rectangle[2])/2
                        runway_end=(rectangle[0]+rectangle[3])/2
                        runway_width=VECT.length_in_meters(rectangle[1:3])
                    runways_as_area.append((runway_pol,runway_start,runway_end,runway_width))
                else:
                    UI.logprint(1,"Bad runway (geometry invalid or going back over itself) close to",airport,"at",dico_airports[airport]['repr_node'])
                    UI.vprint(1,"   !Bad runway (geometry invalid or going back over itself) close to",airport,"at",dico_airports[airport]['repr_node'])
                    UI.vprint(1,"   !You may correct it editing the file ",FNAMES.osm_cached(tile.lat, tile.lon, 'airports'),"in JOSM.")
                    continue   
            else:
                linear.append(airport_layer.dicosmw[wayid])
                try: linear_width.append(float(airport_layer.dicosmtags['w'][wayid]['width']))
                except: linear_width.append(0)  # 0 is just a mark for non existing data, a fictive length will be given later based on the runway length
        ## Line merge runway parts defined as linear features
        runway_parts_are_grouped=False
        while not runway_parts_are_grouped:
            runway_parts_are_grouped=True    
            for i in range(len(linear)-1):
                dir_i=numpy.arctan2(*(numpy.array(airport_layer.dicosmn[linear[i][-1]])-numpy.array(airport_layer.dicosmn[linear[i][0]])))
                for j in range(i+1,len(linear)):
                    dir_j=numpy.arctan2(*(numpy.array(airport_layer.dicosmn[linear[j][-1]])-numpy.array(airport_layer.dicosmn[linear[j][0]])))
                    # Some different runways may share a common end-point in OSM, in this case we don't want to group them into a single one
                    if not numpy.min(numpy.abs(numpy.array([-2*pi,-pi,0,pi,2*pi])-(dir_i-dir_j)))<0.2: 
                            continue
                    if linear[i][-1]==linear[j][0]:
                        linear=[linear[k] for k in range(len(linear)) if k not in (i,j)]+[linear[i]+linear[j][1:]]
                        linear_width=[linear_width[k] for k in range(len(linear_width)) if k not in (i,j)]+[max(linear_width[i],linear_width[j])]
                        runway_parts_are_grouped=False
                        break
                    elif linear[i][-1]==linear[j][-1]:
                        linear=[linear[k] for k in range(len(linear)) if k not in (i,j)]+[linear[i]+linear[j][-2::-1]]
                        linear_width=[linear_width[k] for k in range(len(linear_width)) if k not in (i,j)]+[max(linear_width[i],linear_width[j])]
                        runway_parts_are_grouped=False
                        break
                    elif linear[i][0]==linear[j][0]:
                        linear=[linear[k] for k in range(len(linear)) if k not in (i,j)]+[linear[i][-1::-1]+linear[j][1:]]
                        linear_width=[linear_width[k] for k in range(len(linear_width)) if k not in (i,j)]+[max(linear_width[i],linear_width[j])]
                        runway_parts_are_grouped=False
                        break
                    elif linear[i][0]==linear[j][-1]:
                        linear=[linear[k] for k in range(len(linear)) if k not in (i,j)]+[linear[j]+linear[i][1:]]
                        linear_width=[linear_width[k] for k in range(len(linear_width)) if k not in (i,j)]+[max(linear_width[i],linear_width[j])]
                        runway_parts_are_grouped=False
                        break
                if not runway_parts_are_grouped: break
        ## Grow linear runways into rectangle ones and check wether they are duplicates of existing area ones, in which case they are skipped                
        for (nodeid_list,width) in zip(linear,linear_width):
            runway_start=airport_layer.dicosmn[nodeid_list[0]]
            runway_end  =airport_layer.dicosmn[nodeid_list[-1]]
            runway_length=GEO.dist(runway_start,runway_end)
            runway_start=numpy.round(numpy.array(runway_start)-numpy.array([tile.lon,tile.lat]),7)
            runway_end=numpy.round(numpy.array(runway_end)-numpy.array([tile.lon,tile.lat]),7)
            if width: 
                width+=10
            else:
                width=30+runway_length//1000
            pol=geometry.Polygon(VECT.buffer_simple_way(numpy.vstack((runway_start,runway_end)),width))
            keep_this=True
            i=0
            for pol2 in runways_as_area:
                if (pol2[0].intersection(pol)).area>0.6*min(pol.area,pol2[0].area):
                    # update area one with start end and width from linear one
                    runways_as_area[i]=(pol2[0],runway_start,runway_end,width)
                    # and then skip the linear one
                    keep_this=False
                    break
                i+=1
            if keep_this: runways_as_line.append((pol, runway_start,runway_end,width))
        ##  Save this into the dico_airport dictionnary
        runway=VECT.ensure_MultiPolygon(ops.cascaded_union([item[0] for item in runways_as_area+runways_as_line]))
        dico_airports[airport]['runway']=(runway,runways_as_area,runways_as_line)   
    return
####################################################################################################

####################################################################################################
def discard_unwanted_airports(tile,dico_airports):
    # A bit of cleaning (aeromodelism, helipads, should be removed here)
    for airport in list(dico_airports.keys()):
        apt=dico_airports[airport]
        #if apt['key_type'] in ('icao','iata','local_ref'): continue
        if apt['boundary']:
            if apt['boundary'].area<5000*GEO.m_to_lat*GEO.m_to_lon(tile.lat):
                # too small, skip it
                dico_airports.pop(airport,None)
            continue
        if apt['runway'][0].area<2500*GEO.m_to_lat*GEO.m_to_lon(tile.lat):
            # too small, skip it
            dico_airports.pop(airport,None)
            continue
####################################################################################################

####################################################################################################
def build_hangar_areas(tile,airport_layer,dico_airports):
    for airport in dico_airports:
        wayid_list=dico_airports[airport]['hangar']
        hangars=[]
        for wayid in wayid_list: 
            try:
                pol=geometry.Polygon(numpy.round(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([[tile.lon,tile.lat]]),7))
                if not pol.is_valid: continue
            except:
                UI.vprint(2,"Unable to turn hangar area to polygon, close to",airport_layer.dicosmn[airport_layer.dicosmw[wayid][0]]) 
                continue
            hangars.append(pol)
        hangars=VECT.ensure_MultiPolygon(VECT.improved_buffer(ops.cascaded_union(hangars),2,1,0.5))
        dico_airports[airport]['hangar']=hangars
####################################################################################################    

####################################################################################################
def build_apron_areas(tile,airport_layer,dico_airports):
    for airport in dico_airports:
        wayid_list=dico_airports[airport]['apron']
        aprons=[]
        for wayid in wayid_list: 
            try:
                pol=geometry.Polygon(numpy.round(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([[tile.lon,tile.lat]]),7))
                if not pol.is_valid: 
                    UI.vprint(2,"Unable to turn apron area to polygon, close to",airport_layer.dicosmn[airport_layer.dicosmw[wayid][0]]) 
                    continue
            except:
                UI.vprint(2,"Unable to turn apron area to polygon, close to",airport_layer.dicosmn[airport_layer.dicosmw[wayid][0]]) 
                continue
            aprons.append(pol)
        aprons=VECT.ensure_MultiPolygon(ops.cascaded_union(aprons))
        dico_airports[airport]['apron']=(aprons,dico_airports[airport]['apron'])
    return
####################################################################################################    

####################################################################################################
def build_taxiway_areas(tile,airport_layer,dico_airports):
    for airport in dico_airports:
        wayid_list=dico_airports[airport]['taxiway']
        taxiways=geometry.MultiLineString([geometry.LineString(numpy.round(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([[tile.lon,tile.lat]]),7)) for wayid in wayid_list])
        taxiways=VECT.ensure_MultiPolygon(VECT.improved_buffer(taxiways,15,3,0.5))
        dico_airports[airport]['taxiway']=(taxiways,dico_airports[airport]['taxiway'])
    return
#################################################################################################### 

####################################################################################################
def update_airport_boundaries(tile,dico_airports):
    for airport in dico_airports:
        apt=dico_airports[airport]
        boundary=ops.cascaded_union([apt['taxiway'][0],apt['apron'][0],apt['hangar'],apt['runway'][0]])
        if apt['boundary']:
            apt['boundary']=VECT.ensure_MultiPolygon(ops.cascaded_union([affinity.translate(apt['boundary'],-tile.lon,-tile.lat),boundary]).buffer(0).simplify(0.00001))
        else:
            apt['boundary']=VECT.ensure_MultiPolygon(boundary.buffer(0).simplify(0.00001))
    # pickle dico_airports for later use in Step 2 (apt_curv_tol) and Step 3 (cover_airports_with_high_res)
    try:
        with open(FNAMES.apt_file(tile),'wb') as outf:
            pickle.dump(dico_airports,outf)
    except:
        UI.vprint(1,"WARNING: Could not save airport info to file",FNAMES.apt_file(tile)) 
    return
#################################################################################################### 
 
####################################################################################################
def list_airports_and_runways(dico_airports):
    # Sorting for easier reading of the output
    airport_list= sorted([x for x in dico_airports if dico_airports[x]['key_type']=='icao'])+\
                  sorted([x for x in dico_airports if dico_airports[x]['key_type']=='iata'])+\
                  sorted([x for x in dico_airports if dico_airports[x]['key_type']=='local_ref'])+\
                  sorted([x for x in dico_airports if dico_airports[x]['key_type']=='name'])+\
                  sorted([x for x in dico_airports if dico_airports[x]['key_type']=='repr_node'])
    for airport in airport_list:
        l=len(dico_airports[airport]['runway'][1])+len(dico_airports[airport]['runway'][2])
        runway_str=str(l)+(' runways,' if l>1 else ' runway ,') if l else 'boundary ,'
        if dico_airports[airport]['key_type'] in ('icao','iata','local_ref'):
            UI.vprint(1,'  ','{:6s}'.format(airport),'{:60s}'.format(dico_airports[airport]['name']),runway_str,'lat=','{:.2f}'.format(dico_airports[airport]['repr_node'][1])+',','lon=','{:.2f}'.format(dico_airports[airport]['repr_node'][0]))
        else:
            UI.vprint(1,'  ','{:6s}'.format('****'),'{:60s}'.format(dico_airports[airport]['name']),runway_str,'lat=','{:.2f}'.format(dico_airports[airport]['repr_node'][1])+',','lon=','{:.2f}'.format(dico_airports[airport]['repr_node'][0]))
    return
####################################################################################################

####################################################################################################
def build_airport_array(tile,dico_airports):
    airport_array=numpy.zeros((1001,1001),dtype=numpy.bool)
    for airport in dico_airports:
        (xmin,ymin,xmax,ymax)=dico_airports[airport]['boundary'].bounds
        x_shift=1500*GEO.m_to_lon(tile.lat) 
        y_shift=1500*GEO.m_to_lat
        colmin=max(round((xmin-x_shift)*1000),0)
        colmax=min(round((xmax+x_shift)*1000),1000)
        rowmax=min(round(((1-ymin)+y_shift)*1000),1000)
        rowmin=max(round(((1-ymax)-y_shift)*1000),0)
        airport_array[rowmin:rowmax+1,colmin:colmax+1]=True 
    return airport_array
####################################################################################################

####################################################################################################
def smooth_raster_over_airports(tile,dico_airports,preserve_boundary=True):
    max_pix=tile.apt_smoothing_pix
    for airport in dico_airports:
        if 'smoothing_pix' in dico_airports[airport]:
            try:
                max_pix=max(int(dico_airports[airport]['smoothing_pix']),max_pix)
            except:
                pass
    if not max_pix:
        tile.dem.write_to_file(FNAMES.alt_file(tile))
        return
    if preserve_boundary:
        up=numpy.array(tile.dem.alt_dem[:max_pix])
        down=numpy.array(tile.dem.alt_dem[-max_pix:])
        left=numpy.array(tile.dem.alt_dem[:,:max_pix])
        right=numpy.array(tile.dem.alt_dem[:,-max_pix:])
    x0=tile.dem.x0
    x1=tile.dem.x1
    y0=tile.dem.y0
    y1=tile.dem.y1
    xstep=(x1-x0)/tile.dem.nxdem
    ystep=(y1-y0)/tile.dem.nydem
    upscale=max(ceil(ystep*GEO.lat_to_m/10),1) # target 10m of pixel size at most to avoiding aliasing
    for airport in dico_airports:
        try:
            pix= int(dico_airports[airport]['smoothing_pix']) if 'smoothing_pix' in dico_airports[airport] else tile.apt_smoothing_pix
        except:
            pix = tile.apt_smoothing_pix
        if not pix: continue
        (xmin,ymin,xmax,ymax)=dico_airports[airport]['boundary'].bounds
        colmin=max(floor((xmin-x0)/xstep)-pix,0)
        colmax=min(ceil((xmax-x0)/xstep)+pix,tile.dem.nxdem-1)
        rowmin=max(floor((y1-ymax)/ystep)-pix,0)
        rowmax=min(ceil((y1-ymin)/ystep)+pix,tile.dem.nydem-1)
        if colmin>=colmax or rowmin>=rowmax: continue
        X0=x0+colmin*xstep
        Y1=y1-rowmin*ystep
        airport_im=Image.new('L',(upscale*(colmax-colmin+1),upscale*(rowmax-rowmin+1)))
        airport_draw=ImageDraw.Draw(airport_im)
        full_area=VECT.ensure_MultiPolygon(ops.cascaded_union([dico_airports[airport]['boundary'],dico_airports[airport]['runway'][0],dico_airports[airport]['hangar'],dico_airports[airport]['taxiway'][0],dico_airports[airport]['apron'][0]]))
        for polygon in full_area:
            exterior_pol_pix=[(round(upscale*(X-X0)/xstep),round(upscale*(Y1-Y)/ystep)) for (X,Y) in polygon.exterior.coords]
            airport_draw.polygon(exterior_pol_pix,fill='white')
            for inner_ring in polygon.interiors:
                interior_pol_pix=[(round(upscale*(X-X0)/xstep),round(upscale*(Y1-Y)/ystep)) for (X,Y) in inner_ring.coords]
                airport_draw.polygon(interior_pol_pix,fill='black')
        airport_im=airport_im.resize((colmax-colmin+1,rowmax-rowmin+1),Image.BICUBIC)
        tile.dem.alt_dem[rowmin:rowmax+1,colmin:colmax+1]=DEM.smoothen(tile.dem.alt_dem[rowmin:rowmax+1,colmin:colmax+1],pix,airport_im,preserve_boundary=False)
    if preserve_boundary:
        pix=max_pix
        for i in range(pix):
            tile.dem.alt_dem[i]=i/pix*tile.dem.alt_dem[i]+(pix-i)/pix*up[i]
            tile.dem.alt_dem[-i-1]=i/pix*tile.dem.alt_dem[-i-1]+(pix-i)/pix*down[-i-1]
        for i in range(pix):
            tile.dem.alt_dem[:,i]=i/pix*tile.dem.alt_dem[:,i]+(pix-i)/pix*left[:,i]
            tile.dem.alt_dem[:,-i-1]=i/pix*tile.dem.alt_dem[:,-i-1]+(pix-i)/pix*right[:,-i-1]
    tile.dem.write_to_file(FNAMES.alt_file(tile))
    return
####################################################################################################

####################################################################################################
def encode_runways_taxiways_and_aprons(tile,airport_layer,dico_airports,vector_map,patches_list):
    seeds={'RUNWAY':[],'TAXIWAY':[],'APRON':[]}
    total_rwy=0
    total_taxi=0
    for airport in dico_airports:
        if airport in patches_list: 
            continue
        apt=dico_airports[airport]
        total_rwy+=len(apt['runway'][1]+apt['runway'][2])
        total_taxi+=len(apt['taxiway'][1])
        # First build the altitude generator function : that is a number of least square polynomial 
        # approximations of altitudes along ways (runways, taxiways, etc). These will be used later
        # approriately weighted all together in order to give altitudes to any node in a runway or 
        # taxiway (this weighting is highly important to avoid steppint effects close to intersections)
        alt_idx=index.Index()
        alt_dico={}
        id=0
        for (runway_pol,runway_start,runway_end,runway_width) in apt['runway'][1]+apt['runway'][2]:
            center_way=numpy.vstack((runway_start,runway_end))
            runway_length=VECT.length_in_meters(center_way)
            steps = int(max(runway_chunks,runway_length//7))
            (linestring,polyfit)=VECT.least_square_fit_altitude_along_way(center_way,steps,tile.dem,weights=True)
            #(linestring,polyfit)=VECT.spline_fit_altitude_along_way(center_way,steps,tile.dem)#,weights=True)
            alt_idx.insert(id,linestring.bounds)
            alt_dico[id]=(linestring,polyfit,runway_width)
            id+=1
        for wayid in apt['taxiway'][1]:
            taxiway=numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([[tile.lon,tile.lat]])
            taxiway_length=VECT.length_in_meters(taxiway)
            steps = int(max(runway_chunks,taxiway_length//7))
            (linestring,polyfit)=VECT.least_square_fit_altitude_along_way(taxiway,steps,tile.dem)
            #(linestring,polyfit)=VECT.spline_fit_altitude_along_way(taxiway,steps,tile.dem)
            alt_idx.insert(id,linestring.bounds)
            alt_dico[id]=(linestring,polyfit,15)
            id+=1
        # Now that alt_gen is filled, we may proceed to encoding
        pols=[]  # we keep track of encoded pols to later plant seeds inside crossings etc
        ## First runways
        for (runway_pol,runway_start,runway_end,runway_width) in apt['runway'][1]+apt['runway'][2]:
            runway_length=VECT.length_in_meters(numpy.vstack((runway_start,runway_end)))
            refine_size=max(runway_length//runway_chunks,chunk_min_size)
            for pol in VECT.ensure_MultiPolygon(VECT.cut_to_tile(runway_pol)):
                way=numpy.round(VECT.refine_way(numpy.array(pol.exterior.coords),refine_size),7)
                alti_way=numpy.array([VECT.weighted_alt(node,alt_idx,alt_dico,tile.dem) for node in way]).reshape((len(way),1))
                vector_map.insert_way(numpy.hstack([way,alti_way]),'RUNWAY',check=True)
                pols.append(pol)
        for pol in pols:
            for subpol in VECT.ensure_MultiPolygon(pol.difference(ops.cascaded_union([pol2 for pol2 in pols if pol2!=pol]))):
                seeds['RUNWAY'].append(numpy.array(subpol.representative_point()))
            for subpol in VECT.ensure_MultiPolygon(pol.intersection(ops.cascaded_union([pol2 for pol2 in pols if pol2!=pol]))):
                seeds['RUNWAY'].append(numpy.array(subpol.representative_point()))   
        ## Then taxiways
        ## Not sure if it is best to separate them from the runway or not...  
        cleaned_taxiway_area=VECT.improved_buffer(apt['taxiway'][0].difference(VECT.improved_buffer(apt['runway'][0],5,0,0).union(VECT.improved_buffer(apt['hangar'],20,0,0))),3,2,0.5)
        #cleaned_taxiway_area=VECT.improved_buffer(apt['taxiway'][0].difference(VECT.improved_buffer(apt['hangar'],20,0,0)),0,1,0.5)
        for pol in VECT.ensure_MultiPolygon(VECT.cut_to_tile(cleaned_taxiway_area)):
            if not pol.is_valid or pol.is_empty or pol.area<1e-9: 
                continue
            way=numpy.round(VECT.refine_way(numpy.array(pol.exterior),20),7)
            alti_way=numpy.array([VECT.weighted_alt(node,alt_idx,alt_dico,tile.dem) for node in way]).reshape((len(way),1))
            vector_map.insert_way(numpy.hstack([way,alti_way]),'TAXIWAY',check=True) 
            for subpol in pol.interiors:
                way=numpy.round(VECT.refine_way(numpy.array(subpol),20),7)
                alti_way=numpy.array([VECT.weighted_alt(node,alt_idx,alt_dico,tile.dem) for node in way]).reshape((len(way),1))
                vector_map.insert_way(numpy.hstack([way,alti_way]),'TAXIWAY',check=True)
            seeds['TAXIWAY'].append(numpy.array(pol.representative_point()))
        ## Try to bring some aprons with, we are looking for the small ones along runways, you just need to add the 'include' tag to that apron in JOSM (local copy)
        for wayid in apt['apron'][1]: 
            if wayid not in airport_layer.dicosmtags['w'] or 'include' not in airport_layer.dicosmtags['w'][wayid]: continue
            try:
                way=numpy.round(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([tile.lon,tile.lat]),7)
                way=numpy.round(VECT.refine_way(way,15),7)
                apron_pol=geometry.Polygon(way)
                if not apron_pol.is_empty and runway_pol.is_valid:    
                    alti_way=numpy.array([VECT.weighted_alt(node,alt_idx,alt_dico,tile.dem) for node in way]).reshape((len(way),1))
                    vector_map.insert_way(numpy.hstack([way,alti_way]),'APRON',check=True) 
                    seeds['APRON'].append(numpy.array(apron_pol.representative_point()))
            except:
                pass
    for surface in ('RUNWAY','TAXIWAY','APRON'):
        if seeds[surface]:
            if surface in vector_map.seeds:
                vector_map.seeds[surface]+=seeds[surface]
            else:
                vector_map.seeds[surface]=seeds[surface]
    plural_rwy='s' if total_rwy>1 else ''
    plural_taxi='s' if total_taxi>1 else ''    
    UI.vprint(1,"   Auto-patched",total_rwy,"runway"+plural_rwy+" and",total_taxi,"piece"+plural_taxi+" of taxiway.")
    return ops.cascaded_union([dico_airports[airport]['runway'][0] for airport in dico_airports]+\
                              [dico_airports[airport]['taxiway'][0] for airport in dico_airports]+\
                              [dico_airports[airport]['apron'][0] for airport in dico_airports])       
####################################################################################################        

####################################################################################################    
def encode_hangars(tile,dico_airports,vector_map,patches_list):
    seeds=[]
    for airport in dico_airports:
        if airport in patches_list: continue
        for pol in VECT.ensure_MultiPolygon(VECT.cut_to_tile(dico_airports[airport]['hangar'])):
            way=numpy.array(pol.exterior.coords)
            alti_way=numpy.ones((len(way),1))*numpy.min(tile.dem.alt_vec(way))
            vector_map.insert_way(numpy.hstack([way,alti_way]),'HANGAR',check=True) 
            seeds.append(numpy.array(pol.representative_point()))
    if seeds:
        if 'HANGAR' in vector_map.seeds:
            vector_map.seeds['HANGAR']+=seeds
        else:
            vector_map.seeds['HANGAR']=seeds  
    return 1    
####################################################################################################    
    
####################################################################################################    
def flatten_helipads(airport_layer,vector_map,tile, patches_area):
    multipol=[]
    seeds=[]
    total=0
    # helipads whose boundary is encoded in OSM
    for wayid in (x for x in airport_layer.dicosmw if x in airport_layer.dicosmtags['w'] and 'aeroway' in airport_layer.dicosmtags['w'][x] and airport_layer.dicosmtags['w'][x]['aeroway']=='helipad'):
        if airport_layer.dicosmw[wayid][0]!=airport_layer.dicosmw[wayid][-1]: continue
        way=numpy.round(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([[tile.lon,tile.lat]]),7)
        pol=geometry.Polygon(way)
        if (pol.is_empty) or (not pol.is_valid) or (not pol.area) or (pol.intersects(patches_area)): continue
        multipol.append(pol)
        alti_way=numpy.ones((len(way),1))*numpy.mean(tile.dem.alt_vec(way))
        vector_map.insert_way(numpy.hstack([way,alti_way]),'INTERP_ALT',check=True) 
        seeds.append(numpy.array(pol.representative_point()))
        total+=1
    helipad_area=ops.cascaded_union(multipol)
    # helipads that are only encoded as nodes, they will be grown into hexagons
    for nodeid in (x for x in airport_layer.dicosmn if x in airport_layer.dicosmtags['n'] and 'aeroway' in airport_layer.dicosmtags['n'][x] and airport_layer.dicosmtags['n'][x]['aeroway']=='helipad'):
        center=numpy.round(numpy.array(airport_layer.dicosmn[nodeid])-numpy.array([tile.lon,tile.lat]),7)
        if geometry.Point(center).intersects(helipad_area) or geometry.Point(center).intersects(patches_area): 
            continue
        way=numpy.round(center+numpy.array([[cos(k*pi/3)*7*GEO.m_to_lon(tile.lat),sin(k*pi/3)*7*GEO.m_to_lat] for k in range(7)]),7)
        alti_way=numpy.ones((len(way),1))*numpy.mean(tile.dem.alt_vec(way))
        vector_map.insert_way(numpy.hstack([way,alti_way]),'INTERP_ALT',check=True) 
        seeds.append(center)
        total+=1
    if seeds:
        if 'INTERP_ALT' in vector_map.seeds:
            vector_map.seeds['INTERP_ALT']+=seeds
        else:
            vector_map.seeds['INTERP_ALT']=seeds  
    if total:
        UI.vprint(1,"   Flattened", total,"helipads.")
####################################################################################################
