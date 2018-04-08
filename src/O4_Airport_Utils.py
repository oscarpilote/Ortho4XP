from math import floor, ceil
import numpy
from shapely import geometry,  affinity,  ops
from PIL import Image, ImageDraw #, ImageFilter
#from matplotlib import pyplot
import O4_UI_Utils as UI
import O4_Vector_Utils as VECT
import O4_Geo_Utils as GEO
import O4_DEM_Utils as DEM
import O4_File_Names as FNAMES

runway_chunks=50

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
            try:
                dico_airports[key]['boundary']=geometry.Polygon(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[osmid]])) if osmtype=='w'\
                                           else ops.cascaded_union([geom for geom in [geometry.Polygon(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in nodelist])) for nodelist in airport_layer.dicosmr[osmid]['outer']]]) if osmtype=='r' else None
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
                if runway_pol.is_valid: 
                    rectangle=numpy.array(VECT.min_bounding_rectangle(runway_pol).exterior.coords)
                    if VECT.length_in_meters(rectangle[0:2])<VECT.length_in_meters(rectangle[1:3]):
                        runway_start=(rectangle[0]+rectangle[1])/2
                        runway_end=(rectangle[2]+rectangle[3])/2
                    else:
                        runway_start=(rectangle[1]+rectangle[2])/2
                        runway_end=(rectangle[0]+rectangle[3])/2
                    runways_as_area.append((runway_pol,runway_start,runway_end))
            else:
                linear.append(airport_layer.dicosmw[wayid])
                try: linear_width.append(float(airport_layer.dicosmtags['w'][wayid]['width']))
                except: linear_width.append(0)  # 0 is just a mark for non existing data, a fictive length will be given later based on the runway length
        ## Line merge runway parts defined as linear features
        runway_parts_are_grouped=False
        while not runway_parts_are_grouped:
            runway_parts_are_grouped=True    
            for i in range(len(linear)-1):
                for j in range(i+1,len(linear)):
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
        ## Grow linear runways into rectangle ones and check wether they are duplicates of existing area ones, in which case they are skipped                
        for (nodeid_list,width) in zip(linear,linear_width):
            runway_start=airport_layer.dicosmn[nodeid_list[0]]
            runway_end  =airport_layer.dicosmn[nodeid_list[-1]]
            runway_length=GEO.dist(runway_start,runway_end)
            runway_start=numpy.array(runway_start)-numpy.array([tile.lon,tile.lat])
            runway_end=numpy.array(runway_end)-numpy.array([tile.lon,tile.lat])
            if width: 
                width+=10
            else:
                width=30+runway_length//1000
            pol=geometry.Polygon(VECT.buffer_simple_way(numpy.vstack((runway_start,runway_end)),width))
            keep_this=True
            for pol2 in runways_as_area[:]:
                if (pol2[0].intersection(pol)).area>0.6*min(pol.area,pol2[0].area):
                    runways_as_area.remove(pol2)
                    #keep_this=False
                    break
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
            pol=geometry.Polygon(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([[tile.lon,tile.lat]]))
            if not pol.is_valid: continue
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
                pol=geometry.Polygon(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([[tile.lon,tile.lat]]))
                if not pol.is_valid: continue
            except:
                continue
            aprons.append(pol)
        aprons=VECT.ensure_MultiPolygon(ops.cascaded_union(aprons))
        dico_airports[airport]['apron']=aprons
    return
####################################################################################################    

####################################################################################################
def build_taxiway_areas(tile,airport_layer,dico_airports):
    for airport in dico_airports:
        wayid_list=dico_airports[airport]['taxiway']
        taxiways=geometry.MultiLineString([geometry.LineString(numpy.array([airport_layer.dicosmn[nodeid] for nodeid in airport_layer.dicosmw[wayid]])-numpy.array([[tile.lon,tile.lat]])) for wayid in wayid_list])
        taxiways=VECT.ensure_MultiPolygon(VECT.improved_buffer(taxiways,15,3,0.5))
        dico_airports[airport]['taxiway']=taxiways
    return
#################################################################################################### 

####################################################################################################
def update_airport_boundaries(tile,dico_airports):
    for airport in dico_airports:
        apt=dico_airports[airport]
        boundary=ops.cascaded_union([apt['taxiway'],apt['apron'],apt['hangar'],apt['runway'][0]])
        if apt['boundary']:
            apt['boundary']=VECT.ensure_MultiPolygon(ops.cascaded_union([affinity.translate(apt['boundary'],-tile.lon,-tile.lat),boundary]).buffer(0).simplify(0.00001))
        else:
            apt['boundary']=VECT.ensure_MultiPolygon(boundary.buffer(0).simplify(0.00001))
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
def smooth_raster_over_airports(tile,dico_airports,preserve_boundary=True):
    pix=tile.apt_smoothing_pix
    if not pix:
        tile.dem.write_to_file(FNAMES.alt_file(tile))
        return
    if preserve_boundary:
        up=numpy.array(tile.dem.alt_dem[:pix])
        down=numpy.array(tile.dem.alt_dem[-pix:])
        left=numpy.array(tile.dem.alt_dem[:,:pix])
        right=numpy.array(tile.dem.alt_dem[:,-pix:])
    x0=tile.dem.x0
    x1=tile.dem.x1
    y0=tile.dem.y0
    y1=tile.dem.y1
    xstep=(x1-x0)/tile.dem.nxdem
    ystep=(y1-y0)/tile.dem.nydem
    upscale=ceil(ystep*GEO.lat_to_m/10) # target 10m of pixel size to avoiding aliasing
    for airport in dico_airports:
        (xmin,ymin,xmax,ymax)=dico_airports[airport]['boundary'].bounds
        colmin=max(floor((xmin-x0)/xstep)-pix,0)
        colmax=min(ceil((xmax-x0)/xstep)+pix,tile.dem.nydem-1)
        rowmin=max(floor((y1-ymax)/ystep)-pix,0)
        rowmax=min(ceil((y1-ymin)/ystep)+pix,tile.dem.nxdem-1)
        X0=x0+colmin*xstep
        Y1=y1-rowmin*ystep
        airport_im=Image.new('L',(upscale*(colmax-colmin+1),upscale*(rowmax-rowmin+1)))
        airport_draw=ImageDraw.Draw(airport_im)
        full_area=VECT.ensure_MultiPolygon(ops.cascaded_union([dico_airports[airport]['boundary'],dico_airports[airport]['runway'][0],dico_airports[airport]['hangar'],dico_airports[airport]['taxiway'],dico_airports[airport]['apron']]))
        for polygon in full_area:
            exterior_pol_pix=[(round(upscale*(X-X0)/xstep),round(upscale*(Y1-Y)/ystep)) for (X,Y) in polygon.exterior.coords]
            airport_draw.polygon(exterior_pol_pix,fill='white')
            for inner_ring in polygon.interiors:
                interior_pol_pix=[(round(upscale*(X-X0)/xstep),round(upscale*(Y1-Y)/ystep)) for (X,Y) in inner_ring.coords]
                airport_draw.polygon(interior_pol_pix,fill='black')
        airport_im=airport_im.resize((colmax-colmin+1,rowmax-rowmin+1),Image.BICUBIC)
        tile.dem.alt_dem[rowmin:rowmax+1,colmin:colmax+1]=DEM.smoothen(tile.dem.alt_dem[rowmin:rowmax+1,colmin:colmax+1],pix,airport_im,preserve_boundary=False)
    if preserve_boundary:
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
def encode_runways(tile,dico_airports,vector_map):
    seeds=[]
    for airport in dico_airports:
        ## We first check for runway intersections and put the intersecting ones in a different container since
        ## they will eventually be treated differently
        isolated_runways_as_area=[]
        isolated_runways_as_line=[]
        crossing_runways=[]
        for runway in dico_airports[airport]['runway'][1]: # runways_as_area = (runway_pol,runway_start,runway_end)
            i1=[t for t in isolated_runways_as_area if runway[0].intersects(t[0])]
            i3=[t for t in crossing_runways if runway[0].intersects(t[0])]
            if i1 or i3:
                    crossing_runways.append(runway)
                    for t in i1:
                        crossing_runways.append(t)
                        isolated_runways_as_area.remove(t)
            else:
                    isolated_runways_as_area.append(runway)
        for runway in dico_airports[airport]['runway'][2]: # runways_as_line
            i1=[t for t in isolated_runways_as_area if runway[0].intersects(t[0])]
            i2=[t for t in isolated_runways_as_line if runway[0].intersects(t[0])]
            i3=[t for t in crossing_runways if runway[0].intersects(t[0])]
            if i1 or i2 or i3:
                    crossing_runways.append(runway[:3]) # drop the width info for uniformness of data in crossing_runways
                    for t in i1:
                        crossing_runways.append(t)
                        isolated_runways_as_area.remove(t)
                    for t in i2:
                        crossing_runways.append(t[:3]) # drop the width info for uniformness of data in crossing_runways
                        isolated_runways_as_line.remove(t)
            else:
                    isolated_runways_as_line.append(runway)            
        ### We are now ready for runway encoding
        ## First isolated_runways_as_line, we encode both the boundary and transversal dummy edges along the runway
        ## Altitude is computed using a least squares regression with degree 5 polynomials for a series of input along the runway center
        ## and forced to be constant in the direction orthogonal to the runway  
        for (runway_pol,runway_start,runway_end,runway_width) in isolated_runways_as_line:
            runway_length=VECT.length_in_meters(numpy.vstack((runway_start,runway_end)))
            refine_size=max(runway_length//runway_chunks,7)
            way=numpy.round(VECT.buffer_simple_way(VECT.refine_way(numpy.vstack((runway_start,runway_end)),refine_size),runway_width),7)
            k=len(way)//2
            center_way=(way[:k]+way[k:-1][::-1])/2
            center_way_alti=tile.dem.alt_vec(center_way)
            interpol=numpy.polyfit(numpy.arange(k)/(k-1),center_way_alti,5)
            (xmin,ymin,xmax,ymax)=runway_pol.bounds
            if xmin>=0 and xmax<=1 and ymin>=0 and ymax<=1:  
                alti_way=numpy.polyval(interpol,numpy.arange(k)/(k-1))
                alti_way=numpy.concatenate((alti_way,alti_way[::-1],alti_way[:1])).reshape((len(way),1))
                way=numpy.hstack([way,alti_way])
                vector_map.insert_way(way,'RUNWAY',check=True) 
                for l in range(1,k-1):
                    vector_map.insert_way(numpy.vstack((way[l],way[-l-2])),'DUMMY',check=True)
                seeds.append(1/3*runway_start+2/3*runway_end)
            else:
                for pol in VECT.ensure_MultiPolygon(VECT.cut_to_tile(runway_pol).simplify(0.000005)):
                    way=VECT.refine_way(numpy.array(pol.exterior.coords),40)
                    linecoords=VECT.projcoords(way,center_way[0],center_way[-1])
                    alti_way=numpy.polyval(interpol,linecoords).reshape((len(way),1))
                    vector_map.insert_way(numpy.hstack([way,alti_way]),'RUNWAY',check=True)
                    seeds.append(numpy.array(pol.representative_point()))
        ## Next isolated_runways_as_area, we encode a refined version of the boundary (length dependent refinement).
        ## Altitude is computed exactly as for runways_as_line.
        for (runway_pol,runway_start,runway_end) in isolated_runways_as_area:  
            runway_length=VECT.length_in_meters(numpy.vstack((runway_start,runway_end)))
            k = int(max(runway_chunks,runway_length//7))
            center_way=numpy.array([runway_start+j/(k-1)*(runway_end-runway_start) for j in range(k)])
            center_way_alti=tile.dem.alt_vec(center_way)
            interpol=numpy.polyfit(numpy.arange(k)/(k-1),center_way_alti,5)
            refine_size=max(runway_length//runway_chunks,7)
            for pol in VECT.ensure_MultiPolygon(VECT.cut_to_tile(runway_pol).simplify(0.000005)):
                way_out=numpy.array(pol.exterior.coords)
                ways_in=[numpy.array(subpol.coords) for subpol in pol.interiors]
                for way in [way_out]+ways_in:
                    way=VECT.refine_way(numpy.array(pol.exterior.coords),refine_size)
                    linecoords=VECT.projcoords(way,runway_start,runway_end)
                    alti_way=numpy.polyval(interpol,linecoords).reshape((len(way),1))
                    vector_map.insert_way(numpy.hstack([way,alti_way]),'RUNWAY',check=True)
                seeds.append(numpy.array(pol.representative_point()))
        ## Finally crossing runways. Here the solution is to compute a least square polyomial approximation for each runway 
        ## individually and then to use a weighted average based on the distance from the point considered for encoding to 
        ## each of these runways. This weighted average is necessary to avoid jumps at runway crossings that would possibly 
        ## arise otherwise, and also to avoid the (related) non uniqueness of the nearest point projection in case of non   
        ## convex projection sets like the union of two segments.
        ## a) Compute the set of polynomial approximations (linked to their corresponding runway end points)
        altitude_generator=[]
        for (runway_pol,runway_start,runway_end) in crossing_runways: 
            runway_length=VECT.length_in_meters(numpy.vstack((runway_start,runway_end)))
            k = int(max(runway_chunks,runway_length//7))
            center_way=numpy.array([runway_start+j/(k-1)*(runway_end-runway_start) for j in range(k)])
            center_way_alti=tile.dem.alt_vec(center_way)
            interpol=numpy.polyfit(numpy.arange(k)/(k-1),center_way_alti,5)
            altitude_generator.append((runway_start,runway_end,interpol))
        crossing_runways=VECT.ensure_MultiPolygon(ops.cascaded_union([rw[0] for rw in crossing_runways]))
        for rw in crossing_runways:
            for pol in VECT.ensure_MultiPolygon(VECT.cut_to_tile(rw).simplify(0.000005)):
                pol=geometry.polygon.orient(pol)
                total_length=0
                total_nodes=0
                way_out=numpy.array(pol.exterior.coords)
                total_length+=VECT.length_in_meters(way_out)
                total_nodes+=len(way_out)
                ways_in=[numpy.array(subpol.coords) for subpol in pol.interiors]
                total_length+=numpy.sum([VECT.length_in_meters(way) for way in ways_in])
                total_nodes+=numpy.sum([len(way) for way in ways_in])
                guess_nbr_runways=(total_nodes-2)//8+1
                refine_size=max(total_length/(guess_nbr_runways*2*runway_chunks),7)
                for way in [way_out]+ways_in:
                    way=VECT.refine_way(way,refine_size)
                    alti_way=numpy.zeros(len(way))
                    alti_weights=numpy.zeros(len(way))
                    for (runway_start,runway_end,interpol) in altitude_generator:
                        linecoords=numpy.maximum(numpy.minimum(VECT.projcoords(way,runway_start,runway_end),1),0)
                        weights=numpy.exp(-VECT.point_to_segment_distance(way,runway_start,runway_end)/60)
                        alti_way+=numpy.polyval(interpol,linecoords)*weights
                        alti_weights+=weights
                    alti_way=(alti_way/alti_weights).reshape((len(way),1))
                    vector_map.insert_way(numpy.hstack([way,alti_way]),'RUNWAY',check=True) 
                seeds.append(numpy.array(pol.representative_point()))
    if seeds:
        if 'RUNWAY' in vector_map.seeds:
            vector_map.seeds['RUNWAY']+=seeds
        else:
            vector_map.seeds['RUNWAY']=seeds  
    return 1    
    
def encode_hangars(tile,dico_airports,vector_map):
    seeds=[]
    for airport in dico_airports:
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
    
def encode_aprons(tile,dico_airports,vector_map):
    seeds=[]
    for airport in dico_airports:
        for pol in VECT.ensure_MultiPolygon(VECT.cut_to_tile(dico_airports[airport]['apron'])):
            way=numpy.array(pol.exterior.coords)
            alti_way=numpy.ones((len(way),1))*numpy.min(tile.dem.alt_vec(way))
            vector_map.insert_way(numpy.hstack([way,alti_way]),'APRON',check=True) 
            seeds.append(numpy.array(pol.representative_point()))
    if seeds:
        if 'APRON' in vector_map.seeds:
            vector_map.seeds['APRON']+=seeds
        else:
            vector_map.seeds['APRON']=seeds  
    return 1  
    
def encode_taxiways(tile,dico_airports,vector_map):
    seeds=[]
    for airport in dico_airports:
        cleaned_taxiway_area=VECT.improved_buffer(dico_airports[airport]['taxiway'].difference(VECT.improved_buffer(dico_airports[airport]['runway'][0].union(dico_airports[airport]['hangar']),35,0,0)),5,3,0.5)
        for pol in VECT.ensure_MultiPolygon(VECT.cut_to_tile(cleaned_taxiway_area)):
            pol=geometry.polygon.orient(pol)
            way=VECT.refine_way(numpy.array(pol.exterior.coords),20)
            alti_way=tile.dem.alt_vec(way).reshape((len(way),1))
            vector_map.insert_way(numpy.hstack([way,alti_way]),'INTERP_ALT',check=True) 
            for subpol in pol.interiors:
                way=VECT.refine_way(numpy.array(subpol.coords),20)
                alti_way=tile.dem.alt_vec(way).reshape((len(way),1))
                vector_map.insert_way(numpy.hstack([way,alti_way]),'INTERP_ALT',check=True)
            seeds.append(numpy.array(pol.representative_point()))
    if seeds:
        if 'INTERP_ALT' in vector_map.seeds:
            vector_map.seeds['INTERP_ALT']+=seeds
        else:
            vector_map.seeds['INTERP_ALT']=seeds  
    return 1  
   
