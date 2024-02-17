import os, sys, subprocess, time
import numpy
from math import cos, pi
import O4_UI_Utils as UI
import O4_File_Names as FNAMES
import O4_OSM_Utils as OSM
import O4_Vector_Utils as VECT
import O4_DEM_Utils as DEM
import O4_Copernicus as COP

from shapely import geometry, ops

if 'dar' in sys.platform:
    unzip_cmd    = "7z "
    dsftool_cmd  = os.path.join(FNAMES.Utils_dir, "mac" ,"DSFTool ")
elif 'win' in sys.platform: 
    unzip_cmd    = os.path.join(FNAMES.Utils_dir, "win", "7z.exe ")
    dsftool_cmd  = os.path.join(FNAMES.Utils_dir, "win", "DSFTool.exe ")
else:
    unzip_cmd    = "7z "
    dsftool_cmd  = os.path.join(FNAMES.Utils_dir, "lin", "DSFTool ")

dico_for={
    'mixed':('vegetation/mixed.for','255 2'),
    'broad':('vegetation/broad.for','255 2'),
    'needle':('vegetation/conifer.for','255 2'),
    'hedge':('vegetation/hedge.for','255 2')
    }

##############################################################################
def forest_classifier(pol, lat, lon, tags_dico, dem, forest_dico):
    if not pol.is_valid: 
        return
    if VECT.length_in_meters(pol.exterior) < 1000 and pol.exterior.length**2 > 80 * geometry.Polygon(pol.exterior).area:
        forest_dico["hedge"].append(pol)
    elif "leaf_type" in tags_dico:
        if "mixed" in tags_dico["leaf_type"]:
            forest_dico["mixed"].append(pol)
        elif "needle" in tags_dico["leaf_type"]:
            forest_dico["needle"].append(pol)
        else:
            forest_dico["broad"].append(pol)
    else:
        ntest = len(pol.exterior.coords)
        for test in range(ntest):
            lonp, latp = pol.exterior.coords[test]
            lonp += lon
            latp += lat
            fty = COP.fty(latp, lonp)
            if fty in ('broad','mixed','needle'):
                print("Thank you Copernicus !!!", fty)
                forest_dico[fty].append(pol)
                return
        alt = dem.alt(pol.exterior.coords[0])
        if alt < 1500:
            print("Low altitude!!!")
            forest_dico["broad"].append(pol)
        else:
            print("High altitude!!!")
            forest_dico["needle"].append(pol)
    return
##############################################################################

##############################################################################
def OSM_to_MultiPolygon_dico(osm_layer, lat, lon, dem, classifier, dico):
    todo=len(osm_layer.dicosmfirst['w'])+len(osm_layer.dicosmfirst['r'])
    step=int(todo/100)+1
    done=0
    for wayid in osm_layer.dicosmfirst['w']:
        if done%step==0: UI.progress_bar(1,int(100*done/todo))
        if osm_layer.dicosmw[wayid][0]!=osm_layer.dicosmw[wayid][-1]: 
            UI.logprint("Non closed way starting at",osm_layer.dicosmn[osm_layer.dicosmw[wayid][0]],", skipped.")
            done+=1
            continue
        way=numpy.round(numpy.array([osm_layer.dicosmn[nodeid] for nodeid in osm_layer.dicosmw[wayid]],dtype=numpy.float64)-numpy.array([[lon,lat]],dtype=numpy.float64),7) 
        try:
            pol=geometry.Polygon(way)
            if not pol.area: continue
            if not pol.is_valid:
                UI.logprint("Invalid OSM way starting at",osm_layer.dicosmn[osm_layer.dicosmw[wayid][0]],", skipped.")
                done+=1
                continue
        except Exception as e:
            UI.vprint(2,e)
            done+=1
            continue
        classifier(pol, lat, lon, osm_layer.dicosmtags['w'][wayid], dem, dico)
        done+=1
    for relid in osm_layer.dicosmfirst['r']:
        if done%step==0: UI.progress_bar(1,int(100*done/todo))
        try:
            multiout=[geometry.Polygon(numpy.round(numpy.array([osm_layer.dicosmn[nodeid] \
                                        for nodeid in nodelist],dtype=numpy.float64)-numpy.array([lon,lat],dtype=numpy.float64),7))\
                                        for nodelist in osm_layer.dicosmr[relid]['outer']]
            # do not check for validity here, let it fail and write a log
            multiout=ops.cascaded_union([geom for geom in multiout])
            multiin=[geometry.Polygon(numpy.round(numpy.array([osm_layer.dicosmn[nodeid]\
                                        for nodeid in nodelist],dtype=numpy.float64)-numpy.array([lon,lat],dtype=numpy.float64),7))\
                                        for nodelist in osm_layer.dicosmr[relid]['inner']]
            # insteand OSM errors in some small inner islands within rel might be ignored and shouldn't make the whole rel to be skipped 
            multiin=ops.cascaded_union([geom for geom in multiin if geom.is_valid])
            multipol = multiout.difference(multiin)
        except Exception as e:
            UI.lvprint(2,"Invalid OSM relation starting at",osm_layer.dicosmn[osm_layer.dicosmr[relid]['outer'][0]],", skipped.")
            UI.vprint(3,e)
            done+=1
            continue
        for pol in multipol.geoms if ('Multi' in multipol.geom_type or 'Collection' in multipol.geom_type) else [multipol]:
            classifier(pol, lat, lon, osm_layer.dicosmtags['r'][relid], dem, dico)
    UI.progress_bar(1,100)
    return 
##############################################################################


##############################################################################
def write_text_dsf(lat,lon, dsf_txt_filename, dico_polygons, dico_polygon_def, shift_latlon = True, exclusions=[]):
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
    for key in sorted(dico_polygons.keys()):
        f.write('POLYGON_DEF '+dico_polygon_def[key][0]+'\n')
    i=0
    for key in sorted(dico_polygons.keys()):
        for pol in dico_polygons[key]:
            if len(pol.interiors) > 255:
                print("Alert ! Too much holes in one forest, skipped.")
                continue
            pol=geometry.polygon.orient(pol)
            f.write('BEGIN_POLYGON '+str(i)+' '+dico_polygon_def[key][1]+'\n')
            f.write('BEGIN_WINDING\n')
            for (x, y) in list(pol.exterior.coords):
                if shift_latlon:
                    f.write('POLYGON_POINT '+'{:7f}'.format(x+lon)+' '+'{:7f}'.format(y+lat)+'\n')
                else:
                    f.write('POLYGON_POINT '+'{:7f}'.format(x)+' '+'{:7f}'.format(y)+'\n')                   
            f.write('END_WINDING\n')
            for wind in pol.interiors:
                f.write('BEGIN_WINDING\n')
                for (x, y) in list(wind.coords):
                    if shift_latlon:
                        f.write('POLYGON_POINT '+'{:7f}'.format(x + lon)+' '+'{:7f}'.format(y + lat)+'\n')
                    else:
                        f.write('POLYGON_POINT '+'{:7f}'.format(x)+' '+'{:7f}'.format(y)+'\n')
                f.write('END_WINDING\n')
            f.write('END_POLYGON\n')
        i+=1
    f.close()
    return 1
##############################################################################

##############################################################################
def build_road_exclusion(lat, lon, road_level):
    buffer_large=12
    buffer_small=7
    if not road_level: return 1
    UI.vprint(0,"    * Building roads multipolygon")
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


##############################################################################
def build_forest(lat, lon, target_scenery_dir, exclude_road_level = 0):
    UI.vprint(0,"-> Dealing with forests")
    timer=time.time()
    # loading elevation data
    dem = DEM.DEM(lat,lon)
    # update the lat/lon scaling factor in VECT
    VECT.scalx = cos((lat + 0.5) * pi / 180)
    forest_layer=OSM.OSM_layer()
    forest_dico = {"broad":[],"needle":[],"mixed":[],"hedge":[]}
    queries=[
        'rel["natural"="wood"]',
        'rel["landuse"="forest"]',
        'way["natural"="wood"]',
        'way["landuse"="forest"]',
        ]
    tags_of_interest=["leaf_type"]
    if not OSM.OSM_queries_to_OSM_layer(queries, forest_layer, lat, lon, tags_of_interest, cached_suffix='forest'):
        return 0
    UI.vprint(1,"    * Building forests multipolygon.")
    OSM_to_MultiPolygon_dico(forest_layer, lat, lon, dem, forest_classifier, forest_dico)
    if exclude_road_level: 
        print("    * Building roads exclusion surface")
        (idx_road, dico_road) = build_road_exclusion(lat, lon, exclude_road_level)    
    for key in forest_dico:
        print("    Dealing with ", key, ": ", len(forest_dico[key]), "polygons")
        print("      Index and merge")
        (idx_pol, dico_pol) = VECT.MultiPolygon_to_Indexed_Polygons(forest_dico[key],
                merge_overlappings = "True")
        if exclude_road_level:
            print("      Indexed difference with roads")
            (idx_pol,dico_pol) = VECT.indexed_difference(idx_pol, dico_pol, idx_road, dico_road)
        print("      Cut to tile boundaries")
        forest_dico[key] = geometry.MultiPolygon([VECT.cut_to_tile(pol, 0, 1, 0, 1) for pol in dico_pol.values() if pol.is_valid])
        print("      Got ", len(forest_dico[key]), "of them.")
    print("    Writing DSF to file")
    dest_dir=os.path.join(target_scenery_dir, "Earth nav data", FNAMES.round_latlon(lat, lon))
    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
        except:
            UI.exit_message_and_bottom_line("   ERROR: could not create destination directory "+str(dest_dir))
            return 0
    write_text_dsf(lat, lon, os.path.join(dest_dir, FNAMES.short_latlon(lat,lon) + '.txt'), forest_dico, dico_for, shift_latlon = True, exclusions=['for'])
    print("    Converting to DSF binary format")
    dsfconvertcmd=[dsftool_cmd.strip(), ' -text2dsf '.strip(), os.path.join(dest_dir, FNAMES.short_latlon(lat,lon) + '.txt'), os.path.join(dest_dir, FNAMES.short_latlon(lat, lon) + '.dsf')] 
    fingers_crossed=subprocess.Popen(dsfconvertcmd, stdout=subprocess.PIPE, bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print('     ' + line.decode("utf-8")[:-1])
    UI.timings_and_bottom_line(timer)
    return 1
##############################################################################

##############################################################################
def syntax():
    print("Syntex: python3 src/O4_Forest.py [lat] [lon] [target_scenery_dir] [exclude_road_level]")
    print("Example for Bamberg: python3 src/O4_Forest.py 49 10 test_forest 4")
    return
##############################################################################

##############################################################################
if __name__ == '__main__':
    try:
        lat = int(sys.argv[1])
        lon = int(sys.argv[2])
        target_scenery_dir = sys.argv[3]
    except:
        syntax()
        sys.exit()
    try:
        exclude_road_level = int(sys.argv[4])
    except:
        exclude_road_level = 4
    build_forest(lat, lon, target_scenery_dir, exclude_road_level )
##############################################################################  
