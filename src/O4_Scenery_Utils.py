import os
from shapely import geometry
import O4_UI_Utils as UI

def write_text_dsf(lat, lon, dsf_txt_filename, dico_polygons, dico_polygon_def):
    if not os.path.isdir(os.path.dirname(dsf_txt_filename)):
        try:
            os.makedirs(os.path.dirname(dsf_txt_filename))
        except:
            UI.exit_message_and_bottom_line("   ERROR: could not create destination directory " + str(os.path.dirname(dsf_txt_filename)))
            return 0
    try:
        f=open(dsf_txt_filename, 'w')
    except:
        UI.exit_message_and_bottom_line("   ERROR: could not open file", dsf_txt_filename, "for writing.")
        return 0
    f.write('PROPERTY sim/planet earth\n')
    f.write('PROPERTY sim/overlay 1\n')
    f.write('PROPERTY sim/west '+str(lon)+'\n')
    f.write('PROPERTY sim/east '+str(lon+1)+'\n')
    f.write('PROPERTY sim/south '+str(lat)+'\n')
    f.write('PROPERTY sim/north '+str(lat+1)+'\n')
    for key in sorted(dico_polygons.keys()):
        f.write('POLYGON_DEF '+dico_polygon_def[key][0]+'\n')
    i=0
    for key in sorted(dico_polygons.keys()):
        for pol in dico_polygons[key]:
            pol=geometry.polygon.orient(pol)
            f.write('BEGIN_POLYGON '+str(i)+' '+dico_polygon_def[key][1]+'\n')
            f.write('BEGIN_WINDING\n')
            for (lon, lat) in list(pol.exterior.coords):
                f.write('POLYGON_POINT '+'{:7f}'.format(lon)+' '+'{:7f}'.format(lat)+'\n')
            f.write('END_WINDING\n')
            for wind in pol.interiors:
                f.write('BEGIN_WINDING\n')
                for (lon, lat) in list(wind.coords):
                    f.write('POLYGON_POINT '+'{:7f}'.format(lon)+' '+'{:7f}'.format(lat)+'\n')
                f.write('END_WINDING\n')
            f.write('END_POLYGON\n')
        i+=1
    f.close()
    return 1   
