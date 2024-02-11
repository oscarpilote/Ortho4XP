import os
from shapely import geometry
import O4_UI_Utils as UI
import O4_OSM_Utils as OSM
import O4_Vector_Utils as VECT

def write_text_dsf(lat,lon, dsf_txt_filename, dico_overlay, shift_latlon = True, exclusions=[]):
    if not os.path.isdir(os.path.dirname(dsf_txt_filename)):
        try:
            os.makedirs(os.path.dirname(dsf_txt_filename))
        except:
            UI.exit_message_and_bottom_line("   ERROR: could not create destination directory "+str(os.path.dirname(dsf_txt_filename)))
            return 0
    try:
        f=open(dsf_txt_filename, 'w')
    except:
        UI.exit_message_and_bottom_line("   ERROR: could not open file",dsf_txt_filename,"for writing.")
        return 0
    f.write('PROPERTY sim/planet earth\n')
    f.write('PROPERTY sim/overlay 1\n')
    f.write('PROPERTY sim/west '+str(lon)+'\n')
    f.write('PROPERTY sim/east '+str(lon+1)+'\n')
    f.write('PROPERTY sim/south '+str(lat)+'\n')
    f.write('PROPERTY sim/north '+str(lat+1)+'\n')
    for exclusion in exclusions:
        f.write('PROPERTY sim/exclude_'+exclusion+' '+str(lon)+'/'+str(lat)+'/'+str(lon+1)+'/'+str(lat+1)+'\n')
    for key in sorted([x for x in dico_overlay.keys() if dico_overlay[x]['type']=='polygon']):
        f.write('POLYGON_DEF '+dico_overlay[key]['def']+'\n')
    for key in sorted([x for x in dico_overlay.keys() if dico_overlay[x]['type']=='linestring']):
        f.write('POLYGON_DEF '+dico_overlay[key]['def']+'\n')
    for key in sorted([x for x in dico_overlay.keys() if dico_overlay[x]['type']=='point']):
        f.write('OBJECT_DEF '+dico_overlay[key]['def']+'\n')
    polyidx = 0
    objectidx = 0
    for key in sorted([x for x in dico_overlay.keys() if dico_overlay[x]['type']=='polygon']):
        is_facade = '.fac' in dico_overlay[key]['def']
        for j in range(len(dico_overlay[key]['geoms'])):
            pol = dico_overlay[key]['geoms'][j]
            dsf_param = dico_overlay[key]['dsf_param'] if 'dsf_param' in dico_overlay[key] else dico_overlay[key]['dsf_params'][j]
            windings=0
            pol=geometry.polygon.orient(pol)
            f.write('BEGIN_POLYGON '+str(polyidx)+' ' + str(dsf_param)+' 2\n')
            f.write('BEGIN_WINDING\n')
            for (x, y) in list(pol.exterior.coords)[:-1]:
                if shift_latlon:
                    f.write('POLYGON_POINT '+'{:7f}'.format(x+lon)+' '+'{:7f}'.format(y+lat)+'\n')
                else:
                    f.write('POLYGON_POINT '+'{:7f}'.format(x)+' '+'{:7f}'.format(y)+'\n')                   
            f.write('END_WINDING\n')
            if not is_facade:
                for wind in pol.interiors:
                    windings += 1
                    f.write('BEGIN_WINDING\n')
                    for (x, y) in list(wind.coords)[:-1]:
                        if shift_latlon:
                            f.write('POLYGON_POINT '+'{:7f}'.format(x + lon)+' '+'{:7f}'.format(y + lat)+'\n')
                        else:
                            f.write('POLYGON_POINT '+'{:7f}'.format(x)+' '+'{:7f}'.format(y)+'\n')
                    f.write('END_WINDING\n')
            f.write('END_POLYGON\n')
            if windings > 255: print("Alert ! Too much holes :",windings)
        polyidx+=1
    for key in sorted([x for x in dico_overlay.keys() if dico_overlay[x]['type']=='linestring']):
        for linestring in dico_overlay[key]['geoms']:
            f.write('BEGIN_POLYGON '+str(polyidx)+' ' + dico_overlay[key]['dsf_param']+'\n')
            f.write('BEGIN_WINDING\n')
            for (x, y) in list(linestring.coords):
                if shift_latlon:
                    f.write('POLYGON_POINT '+'{:7f}'.format(x+lon)+' '+'{:7f}'.format(y+lat)+'\n')
                else:
                    f.write('POLYGON_POINT '+'{:7f}'.format(x)+' '+'{:7f}'.format(y)+'\n')                   
            f.write('END_WINDING\n')
            f.write('END_POLYGON\n')
        polyidx+=1
    for key in sorted([x for x in dico_overlay.keys() if dico_overlay[x]['type']=='point']):
        print("Key : ",key)
        for j in range(len(dico_overlay[key]['geoms'])):
            point = dico_overlay[key]['geoms'][j]
            rot = dico_overlay[key]['rots'][j]
            print(rot)
            f.write('OBJECT '+str(objectidx)+' ')
            if shift_latlon:
                f.write('{:7f}'.format(point.coords[0][0]+lon)+' '+'{:7f}'.format(point.coords[0][1]+lat))
            else:
                f.write('{:7f}'.format(point.coords[0][0])+' '+'{:7f}'.format(point.coords[0][1]))
            f.write(' '+str(rot)+'\n')
        objectidx+=1
    f.close()
    return 1
 
##############################################################################
def build_road_exclusion(lat, lon, road_level):
    buffer_large=12
    buffer_small=7
    if not road_level: return 1
    UI.vprint(0,"Building roads multipolygon")
    tags_of_interest=["bridge","tunnel"]
    tags_for_exclusion=set(["tunnel"]) 
    road_layer=OSM.OSM_layer()
    queries=[
           'way["highway"="motorway"]',
           'way["highway"="motorway_link"]',
           'way["highway"="trunk"]',
           'way["highway"="primary"]',
           'way["highway"="secondary"]',
           'way["railway"="rail"]',
           'way["railway"="narrow_gauge"]'
         ]
    if not OSM.OSM_queries_to_OSM_layer(queries,road_layer,lat,lon,tags_of_interest,cached_suffix='big_roads'):
        return 0
    road_network=OSM.OSM_to_MultiLineString(road_layer, lat, lon, tags_for_exclusion) 
    road_surface=[VECT.improved_buffer(linestring, buffer_large, 0, 0, show_progress=False) for linestring in road_network]
    if road_level>=2:
        road_layer=OSM.OSM_layer()
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
        if not OSM.OSM_queries_to_OSM_layer(queries,road_layer, lat, lon, tags_of_interest, cached_suffix='small_roads'):
            return 0
        road_network=OSM.OSM_to_MultiLineString(road_layer,0,0,tags_for_exclusion)
        road_surface=geometry.MultiPolygon(road_surface+[VECT.improved_buffer(linestring, buffer_small, 0, 0,show_progress=False) for linestring in road_network])
    del(road_network)
    (idx_road,dico_road)=VECT.MultiPolygon_to_Indexed_Polygons(road_surface,merge_overlappings=False)
    return (idx_road,dico_road)
############################################################################## 
