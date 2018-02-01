import os
import time
from math import pi, cos, sqrt, atan, exp
import numpy
from shapely import geometry,  ops
import O4_UI_Utils as UI
import O4_OSM_Utils as OSM
import O4_Vector_Utils as VECT
import O4_File_Names as FNAMES
import O4_Geo_Utils as GEO

##############################################################################
def build_poly_file(tile):
    UI.red_flag=0
    UI.logprint("Step 1 for tile lat=",tile.lat,", lon=",tile.lon,": starting.")
    UI.vprint(0,"\nStep 1 : Building vector data for tile "+FNAMES.short_latlon(tile.lat,tile.lon)+" : \n--------\n")
    timer=time.time()
    
    if not os.path.exists(tile.build_dir):
        os.makedirs(tile.build_dir)
    if not os.path.exists(FNAMES.osm_dir(tile.lat,tile.lon)):
        os.makedirs(FNAMES.osm_dir(tile.lat,tile.lon))
    node_file =  FNAMES.input_node_file(tile) 
    poly_file =  FNAMES.input_poly_file(tile) 
    vector_map=VECT.Vector_Map()
    
    tile.ensure_elevation_data()
    
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0

    # Patches
    patches_area=include_patches(vector_map,tile)
    UI.vprint(1,"    Number of edges at this point:",len(vector_map.dico_edges))

    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0

    # Airports
    include_airports(vector_map,tile,patches_area)
    UI.vprint(1,"    Number of edges at this point:",len(vector_map.dico_edges))
    
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0

    # Roads
    include_roads(vector_map,tile)
    UI.vprint(1,"    Number of edges at this point:",len(vector_map.dico_edges))
    
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0

    # Sea
    include_sea(vector_map,tile)
    UI.vprint(1,"    Number of edges at this point:",len(vector_map.dico_edges))
 
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0

    # Water 
    include_water(vector_map,tile)
    UI.vprint(1,"    Number of edges at this point:",len(vector_map.dico_edges))

    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0

    # Buildings 
    # include_buildings(vector_map)
    # if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    
    # Orthogrid
    UI.vprint(0,"-> Inserting edges related to the orthophotos grid")
    xgrid=set()  # x coordinates of vertical grid lines
    ygrid=set()  # y coordinates of horizontal grid lines
    (til_xul,til_yul) = GEO.wgs84_to_orthogrid(tile.lat+1,tile.lon,tile.mesh_zl)
    (til_xlr,til_ylr) = GEO.wgs84_to_orthogrid(tile.lat,tile.lon+1,tile.mesh_zl)
    for til_x in range(til_xul+16,til_xlr+1,16):
        pos_x=(til_x/(2**(tile.mesh_zl-1))-1)
        xgrid.add(pos_x*180-tile.lon)
    for til_y in range(til_yul+16,til_ylr+1,16):
        pos_y=(1-(til_y)/(2**(tile.mesh_zl-1)))
        ygrid.add(360/pi*atan(exp(pi*pos_y))-90-tile.lat)
    xgrid.add(0); xgrid.add(1); ygrid.add(0); ygrid.add(1)
    xgrid=list(sorted(xgrid))
    ygrid=list(sorted(ygrid))
    ortho_network=geometry.MultiLineString([geometry.LineString([(x,0),(x,1)]) for x in xgrid]+[geometry.LineString([(0,y),(1,y)]) for y in ygrid])
    vector_map.encode_MultiLineString(ortho_network,tile.dem.alt_vec,'DUMMY',check=True,skip_cut=True)
    
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    
    # Gluing edges
    UI.vprint(0,"-> Inserting additional boundary edges for gluing")
    segs=2500
    gluing_network=geometry.MultiLineString([\
        geometry.LineString([(x,0) for x in numpy.arange(0,segs+1)/segs]),\
        geometry.LineString([(x,1) for x in numpy.arange(0,segs+1)/segs]),\
        geometry.LineString([(0,y) for y in numpy.arange(0,segs+1)/segs]),\
        geometry.LineString([(1,y) for y in numpy.arange(0,segs+1)/segs])])
    vector_map.encode_MultiLineString(gluing_network,tile.dem.alt_vec,'DUMMY',check=True,skip_cut=True)
    
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    UI.vprint(0,"-> Transcription to the files ",poly_file,"and .node")
    if not vector_map.seeds:
        if tile.dem.alt_dem.max()>=1:
            vector_map.seeds['SEA']=[numpy.array([1000,1000])]
        else:
            vector_map.seeds['SEA']=[numpy.array([0.5,0.5])]
    vector_map.write_node_file(node_file)
    vector_map.write_poly_file(poly_file)
    
    UI.vprint(1,"\nFinal number of constrained edges :",len(vector_map.dico_edges))
    UI.timings_and_bottom_line(timer)
    UI.logprint("Step 1 for tile lat=",tile.lat,", lon=",tile.lon,": normal exit.")
    return 1
##############################################################################

##############################################################################
def include_patches(vector_map,tile):
    UI.vprint(0,"-> Dealing with patches")
    patch_dir     =  FNAMES.patch_dir(tile.lat,tile.lon)
    if not os.path.exists(patch_dir): 
        return geometry.Polygon()
    patch_layer = OSM.OSM_layer()
    for pfile_name in os.listdir(patch_dir):
        if pfile_name[-10:]!='.patch.osm':
            continue
        UI.vprint(1,"    "+pfile_name)
        try:
            patch_layer.update_dicosm(os.path.join(patch_dir,pfile_name),target_tags=None)
        except:
            UI.vprint(1,"     Error in treating",pfile_name," , skipped.")
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
        way=way-numpy.array([[tile.lon,tile.lat]]) 
        alti_way_orig=tile.dem.alt_vec(way)
        cplx_patch=False
        if wayid in dt['w']:
            wtags=dt['w'][wayid]
            if 'cst_alt_abs' in wtags:
                alti_way=numpy.ones((len(way),1))*float(wtags['cst_alt_abs'])
            elif 'cst_alt_rel' in wtags:
                alti_way=tile.dem.alt_vec_mean(way)+float(wtags['cst_alt_rel'])
            elif 'var_alt_rel' in wtags:
                alti_way=alti_way_orig+float(wtags['var_alt_rel'])
            elif 'altitude' in wtags:    # deprecated : for backward compatibility only
                try:
                    alti_way=numpy.ones((len(way),1))*float(wtags['altitude'])
                except:
                    alti_way=tile.dem.alt_vec_mean(way)    
            elif 'altitude_high' in wtags:
                cplx_patch=True
                if len(way)!=5 or (way[0]!=way[-1]).all():
                    UI.vprint(1,"    Wrong number of nodes or non closed way for a altitude_high/altitude_low polygon, skipped.")
                    continue
                short_high = way[-2:]
                short_low  = way[1:3]
                try:
                    altitude_high=float(wtags['altitude_high'])
                    altitude_low =float(wtags['altitude_low'])
                except:
                    altitude_high=tile.dem.alt_vec(short_high).mean()
                    altitude_low =tile.dem.alt_vec(short_low).mean()
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
                if 'tanh' in rnw_profile: 
                    rnw_profile= lambda x:tanh_profile(alpha,x)
                elif rnw_profile=='spline':
                    rnw_profile=spline_profile
                else:
                    rnw_profile=plane_profile
                rnw_vect=(short_high[0]+short_high[1]-short_low[0]-short_low[1])/2
                rnw_length=sqrt(rnw_vect[0]**2*cos(tile.lat*pi/180)**2+rnw_vect[1]**2)*111120
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
                    vector_map.insert_way(numpy.hstack([way,alti_way]),'INTERP_ALT',check=True)
                    seed=numpy.array(pol.representative_point())
                    if 'INTERP_ALT' in vector_map.seeds:
                        vector_map.seeds['INTERP_ALT'].append(seed)
                    else:
                        vector_map.seeds['INTERP_ALT']=[seed]
                else:
                    UI.vprint(2,"Skipping invalid patch polygon.")
            except:
                UI.vprint(2,"Skipping invalid patch polygon.")
        else:
            vector_map.insert_way(numpy.hstack([way,alti_way]),'DUMMY',check=True)
    return patches_area
##############################################################################

##############################################################################
def include_airports(vector_map,tile,patches_area):
    # patches_area if not None is the extent to substract from runway_area
    # we enlarge it (local copy) slightly for security
    patches_area=patches_area.buffer(0.00002)
    UI.vprint(0,"-> Dealing with airports")
    airport_layer=OSM.OSM_layer()
    queries=[('rel["aeroway"="runway"]','rel["aeroway"="taxiway"]','rel["aeroway"="apron"]',
          'way["aeroway"="runway"]','way["aeroway"="taxiway"]','way["aeroway"="apron"]')]
    tags_of_interest=["all"]
    if not OSM.OSM_queries_to_OSM_layer(queries,airport_layer,tile.lat,tile.lon,tags_of_interest,cached_suffix='airports'): 
        return 0
    # Runway and taxiway center lines (they will be incorporated to ensure triangles
    # are not too badly aligned with these lines (improves removal of bumpiness)
    runway_network=OSM.OSM_to_MultiLineString(airport_layer,tile.lat,tile.lon,[])
    # Buffer these for later smoothing
    runway_area=VECT.improved_buffer(runway_network,0.0003,0.0001,0.00001)
    if not runway_area: return 0
    runway_area=runway_area.difference(patches_area).buffer(0).simplify(0.00001)
    runway_network=runway_network.difference(patches_area)
    # Now we encode in vector_map
    vector_map.encode_MultiLineString(runway_network,tile.dem.alt_vec,'DUMMY',check=True,refine=20)
    vector_map.encode_MultiPolygon(runway_area,tile.dem.alt_vec,'SMOOTHED_ALT',check=True,refine=50)
    return 1
##############################################################################

##############################################################################
def include_roads(vector_map,tile):    
    if not tile.road_level: return
    UI.vprint(0,"-> Dealing with roads")
    tags_of_interest=["bridge","tunnel"]
    #Need to evaluate if including bridges is better or worse
    tags_for_exclusion=set(["bridge","tunnel"]) 
    #tags_for_exclusion=set(["tunnel"]) 
    road_layer=OSM.OSM_layer()
    queries=[
           'way["highway"="motorway"]',
           'way["highway"="trunk"]',
           'way["highway"="primary"]',
           'way["highway"="secondary"]',
           'way["railway"="rail"]',
           'way["railway"="narrow_gauge"]'
         ]
    if not OSM.OSM_queries_to_OSM_layer(queries,road_layer,tile.lat,tile.lon,tags_of_interest,cached_suffix='big_roads'):
        return 0
    UI.vprint(1,"    * Checking which large roads need levelling.")
    (road_network_banked,road_network_flat)=OSM.OSM_to_MultiLineString(
            road_layer,tile.lat,tile.lon,tags_for_exclusion,lambda way: tile.dem.way_is_too_much_banked(way,tile.road_banking_limit))
    if UI.red_flag: return 0
    if tile.road_level>=2:
        road_layer=OSM.OSM_layer()
        queries=[\
           'way["highway"="tertiary"]']
        if tile.road_level>=3:
            queries+=[
               'way["highway"="unclassified"]',
               'way["highway"="residential"]']
        if tile.road_level>=4:
            queries+=['way["highway"="service"]']
        if tile.road_level>=5:
            queries+=['way["highway"="track"]']
        if not OSM.OSM_queries_to_OSM_layer(queries,road_layer,tile.lat,tile.lon,tags_of_interest,cached_suffix='small_roads'):
            return 0
        UI.vprint(1,"    * Checking which smaller roads need levelling.") 
        timer=time.time()
        (road_network_banked_2,road_network_flat_2)=OSM.OSM_to_MultiLineString(road_layer,\
                tile.lat,tile.lon,tags_for_exclusion,lambda way: tile.dem.way_is_too_much_banked(way,tile.road_banking_limit),limit_segs=tile.max_levelled_segs)
        UI.vprint(3,"Time for check :",time.time()-timer)
        road_network_banked=geometry.MultiLineString(list(road_network_banked)+list(road_network_banked_2)).simplify(0.000005)
    if not road_network_banked.is_empty:
        UI.vprint(1,"    * Buffering banked road network as multipolygon.")
        timer=time.time()
        road_area=VECT.improved_buffer(road_network_banked,0.00004,0.00002,0.000005)
        UI.vprint(3,"Time for improved buffering:",time.time()-timer)
        if UI.red_flag: return 0 
        UI.vprint(1,"      Encoding it.")
        vector_map.encode_MultiPolygon(road_area,tile.dem.alt_vec_road,'INTERP_ALT',check=True,refine=False)
        if UI.red_flag: return 0 
    if not road_network_flat.is_empty:
        road_network_flat=road_network_flat.simplify(0.00001) #.difference(road_area)
        UI.vprint(1,"    * Encoding the remaining primary road network as linestrings.")
        vector_map.encode_MultiLineString(road_network_flat,tile.dem.alt_vec_road,'DUMMY',check=True)
    return 1
##############################################################################

##############################################################################
def include_sea(vector_map,tile):
    UI.vprint(0,"-> Dealing with coastline")
    sea_layer=OSM.OSM_layer()
    custom_coastline=FNAMES.custom_coastline(tile.lat, tile.lon)
    if os.path.isfile(custom_coastline):
        sea_layer.update_dicosm(custom_coastline,target_tags=None)
    else:
        queries=['way["natural"="coastline"]']    
        tags_of_interest=[]
        if not OSM.OSM_queries_to_OSM_layer(queries,sea_layer,tile.lat,tile.lon,tags_of_interest,cached_suffix='coastline'):
            return 0
    coastline=OSM.OSM_to_MultiLineString(sea_layer,tile.lat,tile.lon,None)
    if not coastline.is_empty:
        # 1) encoding the coastline
        UI.vprint(1,"    * Encoding coastline.")
        vector_map.encode_MultiLineString(VECT.cut_to_tile(coastline,strictly_inside=True),tile.dem.alt_vec,'SEA',check=True,refine=False)
        UI.vprint(3,"...done.")
        # 2) finding seeds (transform multilinestring coastline to polygon coastline 
        # linemerge being expensive we first set aside what is already known to be closed loops
        UI.vprint(1,"    * Reconstructing its topology.")
        loops=geometry.MultiLineString([line for line in coastline.geoms if line.is_ring])
        remainder=VECT.ensure_MultiLineString(VECT.cut_to_tile(geometry.MultiLineString([line for line in coastline.geoms if not line.is_ring]),strictly_inside=True))
        UI.vprint(3,"Linemerge...")
        if not remainder.is_empty: 
            remainder=VECT.ensure_MultiLineString(ops.linemerge(remainder))
        UI.vprint(3,"...done.")
        coastline=geometry.MultiLineString([line for line in remainder]+[line for line in loops])
        sea_area=VECT.ensure_MultiPolygon(VECT.coastline_to_MultiPolygon(coastline,tile.lat,tile.lon)) 
        if sea_area.geoms: UI.vprint(1,"      Found ",len(sea_area.geoms),"contiguous patch(es).")
        for polygon in sea_area.geoms:
            seed=numpy.array(polygon.representative_point()) 
            if 'SEA' in vector_map.seeds:
                vector_map.seeds['SEA'].append(seed)
            else:
                vector_map.seeds['SEA']=[seed]
##############################################################################

##############################################################################
def include_water(vector_map,tile):
    UI.vprint(0,"-> Dealing with inland water")
    water_layer=OSM.OSM_layer()
    custom_water=FNAMES.custom_water(tile.lat, tile.lon)
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
        tags_of_interest=["name"]
        if not OSM.OSM_queries_to_OSM_layer(queries,water_layer,tile.lat,tile.lon,tags_of_interest,cached_suffix='water'):
            return 0
    UI.vprint(1,"    * Building water multipolygon.")
    water_area=OSM.OSM_to_MultiPolygon(water_layer,tile.lat,tile.lon)
    if not water_area.is_empty: 
        UI.vprint(1,"      Cleaning it.")
        try:
            (idx_water,dico_water)=VECT.MultiPolygon_to_Indexed_Polygons(water_area,merge_overlappings=tile.clean_bad_geometries,limit=VECT.max_pols_for_merge)
        except:
            return 0
        UI.vprint(2,"      Number of water Multipolygons : "+str(len(dico_water)))  
        UI.vprint(1,"      Encoding it.")
        vector_map.encode_MultiPolygon(dico_water,tile.dem.alt_vec,'WATER',area_limit=tile.min_area/10000,simplify=0.00001,check=True)
    return 1
##############################################################################

##############################################################################
#def include_buildings(vector_map, tile):
    # should be all revisited
    #UI.vprint(0,"-> Dealing with buildings")
    #building_layer=OSM.OSM_layer()
    #queries=[]#'way["building"="yes"]']
    #tags_of_interest=[]
    #if not OSM.OSM_queries_to_OSM_layer(queries,building_layer,tile.lat,tile.lon,tags_of_interest,cached_suffix='buildings'):
    #    return 0
    #for (i,j) in itertools.product(range(1),range(1)):
    #    print("    Obtaining part ",4*i+j," of OSM data for "+tag)
    #    response=get_overpass_data(tag,(lat+i/4,lon+j/4,lat+(i+1)/4,lon+(j+1)/4),"FR")
    #    if UI.red_flag: return 0
    #    if response[0]!='ok': 
    #       print("    Error while trying to obtain ",query,", exiting.")
    #       return 0
    #    building_layer.update_dicosm(response[1],tags_of_interest)
    #building_area=OSM.OSM_to_MultiPolygon(building_layer,lat,lon)
    #try:
    #    (idx_building,dico_building)=MultiPolygon_to_Indexed_Polygons(building_area,merge_overlappings=True)
    #except:
    #    return 0
    #UI.vprint(2,"Number of building Multipolygons :",len(dico_pol_building))  
    #vector_map.encode_MultiPolygon(dico_building,dem.alt_vec,'WATER',area_limit=min_area/10000,check=True)
    #return 1
##############################################################################

