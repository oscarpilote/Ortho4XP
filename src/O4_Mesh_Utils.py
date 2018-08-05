import time
import sys
import os
import pickle
import subprocess
import numpy
from math import sqrt, cos, pi
import O4_DEM_Utils as DEM
import O4_UI_Utils as UI
import O4_File_Names as FNAMES
import O4_Geo_Utils as GEO
import O4_Vector_Utils as VECT
import O4_OSM_Utils as OSM
import O4_Version

if 'dar' in sys.platform:
    Triangle4XP_cmd = os.path.join(FNAMES.Utils_dir,"Triangle4XP.app ")
    triangle_cmd    = os.path.join(FNAMES.Utils_dir,"triangle.app ")
    sort_mesh_cmd   = os.path.join(FNAMES.Utils_dir,"moulinette.app ")
elif 'win' in sys.platform: 
    Triangle4XP_cmd = os.path.join(FNAMES.Utils_dir,"Triangle4XP.exe ")
    triangle_cmd    = os.path.join(FNAMES.Utils_dir,"triangle.exe ")
    sort_mesh_cmd   = os.path.join(FNAMES.Utils_dir,"moulinette.exe ")
else:
    Triangle4XP_cmd = os.path.join(FNAMES.Utils_dir,"Triangle4XP ")
    triangle_cmd    = os.path.join(FNAMES.Utils_dir,"triangle ")
    sort_mesh_cmd   = os.path.join(FNAMES.Utils_dir,"moulinette ")


##############################################################################
def is_in_region(lat,lon,latmin,latmax,lonmin,lonmax):
    return lat>=latmin and lat<=latmax and lon>=lonmin and lon<=lonmax
##############################################################################

##############################################################################
def build_curv_tol_weight_map(tile,weight_array):
    if tile.apt_curv_tol!=tile.curvature_tol and tile.apt_curv_tol>0:
        UI.vprint(1,"-> Modifying curv_tol weight map according to runway locations.")
        try:
            f=open(FNAMES.apt_file(tile),'rb')
            dico_airports=pickle.load(f)
            f.close()
        except:
            UI.vprint(1,"   WARNING: File",FNAMES.apt_file(tile),"is missing (erased after Step 1?), cannot check airport info for upgraded zoomlevel.")
            dico_airports={}
        for airport in dico_airports:
            (xmin,ymin,xmax,ymax)=dico_airports[airport]['boundary'].bounds
            x_shift=1000*tile.apt_curv_ext*GEO.m_to_lon(tile.lat) 
            y_shift=1000*tile.apt_curv_ext*GEO.m_to_lat
            colmin=max(round((xmin-x_shift)*1000),0)
            colmax=min(round((xmax+x_shift)*1000),1000)
            rowmax=min(round(((1-ymin)+y_shift)*1000),1000)
            rowmin=max(round(((1-ymax)-y_shift)*1000),0)
            weight_array[rowmin:rowmax+1,colmin:colmax+1]=tile.curvature_tol/tile.apt_curv_tol 
    if tile.coast_curv_tol!=tile.curvature_tol:
        UI.vprint(1,"-> Modifying curv_tol weight map according to coastline location.")
        sea_layer=OSM.OSM_layer()
        queries=['way["natural"="coastline"]']    
        tags_of_interest=[]
        if not OSM.OSM_queries_to_OSM_layer(queries,sea_layer,tile.lat,tile.lon,tags_of_interest,cached_suffix='coastline'):
            return 0
        for nodeid in sea_layer.dicosmn:
            (lonp,latp)=[float(x) for x in sea_layer.dicosmn[nodeid]]
            if lonp<tile.lon or lonp>tile.lon+1 or latp<tile.lat or latp>tile.lat+1: continue
            x_shift=1000*tile.coast_curv_ext*GEO.m_to_lon(tile.lat)
            y_shift=tile.coast_curv_ext/(111.12)
            colmin=max(round((lonp-tile.lon-x_shift)*1000),0)
            colmax=min(round((lonp-tile.lon+x_shift)*1000),1000)
            rowmax=min(round((tile.lat+1-latp+y_shift)*1000),1000)
            rowmin=max(round((tile.lat+1-latp-y_shift)*1000),0)
            weight_array[rowmin:rowmax+1,colmin:colmax+1]=numpy.maximum(weight_array[rowmin:rowmax+1,colmin:colmax+1],tile.curvature_tol/tile.coast_curv_tol) 
        del(sea_layer)
    # It could be of interest to write the weight file as a png for user editing    
    #from PIL import Image
    #Image.fromarray((weight_array!=1).astype(numpy.uint8)*255).save('weight.png')
    return
##############################################################################

##############################################################################
def post_process_nodes_altitudes(tile):
    dico_attributes=VECT.Vector_Map.dico_attributes 
    f_node = open(FNAMES.output_node_file(tile),'r')
    init_line_f_node=f_node.readline()
    nbr_pt=int(init_line_f_node.split()[0])
    vertices=numpy.zeros(6*nbr_pt)   
    UI.vprint(1,"-> Loading of the mesh computed by Triangle4XP.")
    for i in range(0,nbr_pt):
        vertices[6*i:6*i+6]=[float(x) for x in f_node.readline().split()[1:7]]
    end_line_f_node=f_node.readline()
    f_node.close()
    UI.vprint(1,"-> Post processing of altitudes according to vector data")
    f_ele  = open(FNAMES.output_ele_file(tile),'r')
    nbr_tri= int(f_ele.readline().split()[0])
    water_tris=set()
    sea_tris=set()
    interp_alt_tris=set()
    for i in range(nbr_tri):
        line = f_ele.readline()
        # triangle attributes are powers of 2, except for the dummy attributed which doesn't require post-treatment
        if line[-2]=='0': continue  
        (v1,v2,v3,attr)=[int(x)-1 for x in line.split()[1:5]]
        attr+=1
        if attr >= dico_attributes['INTERP_ALT']: 
            interp_alt_tris.add((v1,v2,v3))
        elif attr & dico_attributes['SEA']:
            sea_tris.add((v1,v2,v3))
        elif attr & dico_attributes['WATER'] or attr & dico_attributes['SEA_EQUIV']:
            water_tris.add((v1,v2,v3))
    if tile.water_smoothing:
        UI.vprint(1,"   Smoothing inland water.")
        for j in range(tile.water_smoothing):   
            for (v1,v2,v3) in water_tris:
                    zmean=(vertices[6*v1+2]+vertices[6*v2+2]+vertices[6*v3+2])/3
                    vertices[6*v1+2]=zmean
                    vertices[6*v2+2]=zmean
                    vertices[6*v3+2]=zmean
    UI.vprint(1,"   Smoothing of sea water.")
    for (v1,v2,v3) in sea_tris:
            if tile.sea_smoothing_mode=='zero':
                vertices[6*v1+2]=0
                vertices[6*v2+2]=0
                vertices[6*v3+2]=0
            elif tile.sea_smoothing_mode=='mean':
                zmean=(vertices[6*v1+2]+vertices[6*v2+2]+vertices[6*v3+2])/3
                vertices[6*v1+2]=zmean
                vertices[6*v2+2]=zmean
                vertices[6*v3+2]=zmean
            else:
                vertices[6*v1+2]=max(vertices[6*v1+2],0)
                vertices[6*v2+2]=max(vertices[6*v2+2],0)
                vertices[6*v3+2]=max(vertices[6*v3+2],0)
    UI.vprint(1,"   Treatment of airports, roads and patches.")
    for (v1,v2,v3) in interp_alt_tris:
            vertices[6*v1+2]=vertices[6*v1+5]
            vertices[6*v2+2]=vertices[6*v2+5]
            vertices[6*v3+2]=vertices[6*v3+5]
            vertices[6*v1+3]=0
            vertices[6*v2+3]=0
            vertices[6*v3+3]=0
            vertices[6*v1+4]=0
            vertices[6*v2+4]=0
            vertices[6*v3+4]=0
    UI.vprint(1,"-> Writing output nodes file.")        
    f_node = open(FNAMES.output_node_file(tile),'w')
    f_node.write(init_line_f_node)
    for i in range(0,nbr_pt):
        f_node.write(str(i+1)+" "+' '.join(('{:.15f}'.format(x) for x in vertices[6*i:6*i+6]))+"\n")
    f_node.write(end_line_f_node)
    f_node.close()
    return vertices
##############################################################################

##############################################################################
def write_mesh_file(tile,vertices):
    UI.vprint(1,"-> Writing final mesh to the file "+FNAMES.mesh_file(tile.build_dir,tile.lat,tile.lon))
    f_ele  = open(FNAMES.output_ele_file(tile),'r')
    nbr_vert=len(vertices)//6
    nbr_tri=int(f_ele.readline().split()[0])
    f=open(FNAMES.mesh_file(tile.build_dir,tile.lat,tile.lon),"w")
    f.write("MeshVersionFormatted "+O4_Version.version+"\n")
    f.write("Dimension 3\n\n")
    f.write("Vertices\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[6*i]+tile.lon)+" "+\
                '{:.9f}'.format(vertices[6*i+1]+tile.lat)+" "+\
                '{:.9f}'.format(vertices[6*i+2]/100000)+" 0\n") 
    f.write("\n")
    f.write("Normals\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[6*i+3])+" "+\
                '{:.9f}'.format(vertices[6*i+4])+"\n")
    f.write("\n")
    f.write("Triangles\n")
    f.write(str(nbr_tri)+"\n")
    for i in range(0,nbr_tri):
       f.write(' '.join(f_ele.readline().split()[1:])+"\n")
    f_ele.close()
    f.close()
    return
##############################################################################

##############################################################################
# Build a textured .obj wavefront over the extent of an orthogrid cell
##############################################################################
def extract_mesh_to_obj(mesh_file,til_x_left,til_y_top,zoomlevel,provider_code): 
    UI.red_flag=False
    timer=time.time()
    (latmax,lonmin)=GEO.gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
    (latmin,lonmax)=GEO.gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
    obj_file_name=FNAMES.obj_file(til_x_left,til_y_top,zoomlevel,provider_code)
    mtl_file_name=FNAMES.mtl_file(til_x_left,til_y_top,zoomlevel,provider_code)
    f_mesh=open(mesh_file,"r")
    for i in range(4):
        f_mesh.readline()
    nbr_pt_in=int(f_mesh.readline())
    UI.vprint(1,"    Reading nodes...")
    pt_in=numpy.zeros(5*nbr_pt_in,'float')
    for i in range(nbr_pt_in):
        pt_in[5*i:5*i+3]=[float(x) for x in f_mesh.readline().split()[:3]]
    for i in range(3):
        f_mesh.readline()
    for i in range(nbr_pt_in):
        pt_in[5*i+3:5*i+5]=[float(x) for x in f_mesh.readline().split()[:2]]
    for i in range(0,2): # skip 2 lines
        f_mesh.readline()
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    UI.vprint(1,"    Reading triangles...")
    nbr_tri_in=int(f_mesh.readline()) # read nbr of tris
    textured_nodes={}
    textured_nodes_inv={}
    nodes_st_coord={}
    len_textured_nodes=0
    dico_new_tri={}
    len_dico_new_tri=0
    for i in range(0,nbr_tri_in):
        (n1,n2,n3)=[int(x)-1 for x in f_mesh.readline().split()[:3]]
        (lon1,lat1,z1,u1,v1)=pt_in[5*n1:5*n1+5]
        (lon2,lat2,z2,u2,v2)=pt_in[5*n2:5*n2+5]
        (lon3,lat3,z3,u3,v3)=pt_in[5*n3:5*n3+5]
        if is_in_region((lat1+lat2+lat3)/3.0,(lon1+lon2+lon3)/3.0,latmin,latmax,lonmin,lonmax):
            if n1 not in textured_nodes_inv:
                len_textured_nodes+=1 
                textured_nodes_inv[n1]=len_textured_nodes
                textured_nodes[len_textured_nodes]=n1
                nodes_st_coord[len_textured_nodes]=GEO.st_coord(lat1,lon1,til_x_left,til_y_top,zoomlevel,provider_code)
            n1new=textured_nodes_inv[n1]
            if n2 not in textured_nodes_inv:
                len_textured_nodes+=1 
                textured_nodes_inv[n2]=len_textured_nodes
                textured_nodes[len_textured_nodes]=n2
                nodes_st_coord[len_textured_nodes]=GEO.st_coord(lat2,lon2,til_x_left,til_y_top,zoomlevel,provider_code)
            n2new=textured_nodes_inv[n2]
            if n3 not in textured_nodes_inv:
                len_textured_nodes+=1 
                textured_nodes_inv[n3]=len_textured_nodes
                textured_nodes[len_textured_nodes]=n3
                nodes_st_coord[len_textured_nodes]=GEO.st_coord(lat3,lon3,til_x_left,til_y_top,zoomlevel,provider_code)
            n3new=textured_nodes_inv[n3]
            dico_new_tri[len_dico_new_tri]=(n1new,n2new,n3new)
            len_dico_new_tri+=1
    nbr_vert=len_textured_nodes
    nbr_tri=len_dico_new_tri
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    UI.vprint(1,"    Writing the obj file.")
    # first the obj file
    f=open(obj_file_name,"w")
    for i in range(1,nbr_vert+1):
        j=textured_nodes[i]
        f.write("v "+'{:.9f}'.format(pt_in[5*j]-lonmin)+" "+\
                '{:.9f}'.format(pt_in[5*j+1]-latmin)+" "+\
                '{:.9f}'.format(pt_in[5*j+2])+"\n") 
    f.write("\n")
    for i in range(1,nbr_vert+1):
        j=textured_nodes[i]
        f.write("vn "+'{:.9f}'.format(pt_in[5*j+3])+" "+'{:.9f}'.format(pt_in[5*j+4])+" "+'{:.9f}'.format(sqrt(max(1-pt_in[5*j+3]**2-pt_in[5*j+4]**2,0)))+"\n")
    f.write("\n")
    for i in range(1,nbr_vert+1):
        j=textured_nodes[i]
        f.write("vt "+'{:.9f}'.format(nodes_st_coord[i][0])+" "+\
                '{:.9f}'.format(nodes_st_coord[i][1])+"\n")
    f.write("\n")
    f.write("usemtl orthophoto\n\n")
    for i in range(0,nbr_tri):
        (one,two,three)=dico_new_tri[i]
        f.write("f "+str(one)+"/"+str(one)+"/"+str(one)+" "+str(two)+"/"+str(two)+"/"+str(two)+" "+str(three)+"/"+str(three)+"/"+str(three)+"\n")
    f_mesh.close()
    f.close()
    # then the mtl file
    f=open(mtl_file_name,'w')
    f.write("newmtl orthophoto\nmap_Kd "+FNAMES.geotiff_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)+"\n")
    f.close()
    UI.timings_and_bottom_line(timer)
    return
##############################################################################


##############################################################################
def build_mesh(tile):
    if UI.is_working: return 0
    UI.is_working=1
    UI.red_flag=False  
    VECT.scalx=cos((tile.lat+0.5)*pi/180)  
    UI.logprint("Step 2 for tile lat=",tile.lat,", lon=",tile.lon,": starting.")
    UI.vprint(0,"\nStep 2 : Building mesh tile "+FNAMES.short_latlon(tile.lat,tile.lon)+" : \n--------\n")
    UI.progress_bar(1,0)
    poly_file    = FNAMES.input_poly_file(tile)
    node_file    = FNAMES.input_node_file(tile)
    alt_file     = FNAMES.alt_file(tile)
    weight_file  = FNAMES.weight_file(tile)
    if not os.path.isfile(node_file):
        UI.exit_message_and_bottom_line("\nERROR: Could not find ",node_file)
        return 0
    if not tile.iterate and not os.path.isfile(poly_file):
        UI.exit_message_and_bottom_line("\nERROR: Could not find ",poly_file)
        return 0
    if not tile.iterate:
        if not os.path.isfile(alt_file):
            UI.exit_message_and_bottom_line("\nERROR: Could not find",alt_file,". You must run Step 1 first.")
            return 0
        try:
            fill_nodata = tile.fill_nodata or "to zero"
            source= ((";" in tile.custom_dem) and tile.custom_dem.split(";")[0]) or tile.custom_dem
            tile.dem=DEM.DEM(tile.lat,tile.lon,source,fill_nodata,info_only=True)
            if not  os.path.getsize(alt_file)==4*tile.dem.nxdem*tile.dem.nydem:
                UI.exit_message_and_bottom_line("\nERROR: Cached raster elevation does not match the current custom DEM specs.\n       You must run Step 1 and Step 2 with the same elevation base.")
                return 0
        except Exception as e:
            print(e)
            UI.exit_message_and_bottom_line("\nERROR: Could not determine the appropriate source. Please check your custom_dem entry.")
            return 0
    else:
        try:
            source= ((";" in tile.custom_dem) and tile.custom_dem.split(";")[tile.iterate]) or tile.custom_dem
            tile.dem=DEM.DEM(tile.lat,tile.lon,source,fill_nodata=False,info_only=True)
            if not os.path.isfile(alt_file) or not os.path.getsize(alt_file)==4*tile.dem.nxdem*tile.dem.nydem:
                tile.dem=DEM.DEM(tile.lat,tile.lon,source,fill_nodata=False,info_only=False)
                tile.dem.write_to_file(FNAMES.alt_file(tile))
        except Exception as e:
            print(e)
            UI.exit_message_and_bottom_line("\nERROR: Could not determine the appropriate source. Please check your custom_dem entry.")
            return 0
    try:
        f=open(node_file,'r')
        input_nodes=int(f.readline().split()[0])
        f.close()
    except:
        UI.exit_message_and_bottom_line("\nERROR: In reading ",node_file)
        return 0
        
    timer=time.time()
    tri_verbosity = 'Q' if UI.verbosity<=1 else 'V'
    output_poly   = 'P' if UI.cleaning_level else ''
    do_refine     = 'r' if tile.iterate else 'A'
    limit_tris    = 'S'+str(max(int(tile.limit_tris/1.9-input_nodes),0)) if tile.limit_tris else ''
    Tri_option    = '-p'+do_refine+'uYB'+tri_verbosity+output_poly+limit_tris
    
    
    weight_array=numpy.ones((1001,1001),dtype=numpy.float32)
    build_curv_tol_weight_map(tile,weight_array)
    weight_array.tofile(weight_file)
    del(weight_array)
    
    curv_tol_scaling=sqrt(tile.dem.nxdem/(1000*(tile.dem.x1-tile.dem.x0))) 
    hmin_effective=max(tile.hmin,(tile.dem.y1-tile.dem.y0)*GEO.lat_to_m/tile.dem.nydem/2)
    mesh_cmd=[Triangle4XP_cmd.strip(),
              Tri_option.strip(),
              '{:.9g}'.format(GEO.lon_to_m(tile.lat)),
              '{:.9g}'.format(GEO.lat_to_m),
              '{:n}'.format(tile.dem.nxdem),
              '{:n}'.format(tile.dem.nydem),
              '{:.9g}'.format(tile.dem.x0),
              '{:.9g}'.format(tile.dem.y0),
              '{:.9g}'.format(tile.dem.x1),
              '{:.9g}'.format(tile.dem.y1),
              '{:.9g}'.format(tile.dem.nodata),
              '{:.9g}'.format(tile.curvature_tol*curv_tol_scaling),
              '{:.9g}'.format(tile.min_angle),str(hmin_effective),alt_file,weight_file,poly_file]
    
    del(tile.dem) # for machines with not much RAM, we do not need it anymore
    tile.dem=None
    UI.vprint(1,"-> Start of the mesh algorithm Triangle4XP.")
    UI.vprint(2,'   Mesh command:',' '.join(mesh_cmd))
    fingers_crossed=subprocess.Popen(mesh_cmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print(line.decode("utf-8")[:-1])
    time.sleep(0.3)
    fingers_crossed.poll()        
    if fingers_crossed.returncode:
        UI.exit_message_and_bottom_line("\nERROR: Triangle4XP crashed !\n\n"+\
                                        "If the reason is not due to the limited amount of RAM please\n"+\
                                        "file a bug including the .node and .poly files for that you\n"+\
                                        "will find in "+str(tile.build_dir)+".\n")
        return 0
        
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    
    vertices=post_process_nodes_altitudes(tile)

    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    
    write_mesh_file(tile,vertices)
    #
    if UI.cleaning_level:
        try: os.remove(FNAMES.weight_file(tile))
        except: pass
        try: os.remove(FNAMES.output_node_file(tile))
        except: pass
        try: os.remove(FNAMES.output_ele_file(tile))
        except: pass
    if UI.cleaning_level>2:
        try: os.remove(FNAMES.alt_file(tile))
        except: pass
        try: os.remove(FNAMES.input_node_file(tile))
        except: pass
        try: os.remove(FNAMES.input_poly_file(tile))
        except: pass
    
    UI.timings_and_bottom_line(timer)
    UI.logprint("Step 2 for tile lat=",tile.lat,", lon=",tile.lon,": normal exit.")
    return 1
##############################################################################

##############################################################################
def sort_mesh(tile):
    if UI.is_working: return 0
    UI.is_working=1
    UI.red_flag=False  
    mesh_file = FNAMES.mesh_file(tile.build_dir,tile.lat,tile.lon)
    if not os.path.isfile(mesh_file):
        UI.exit_message_and_bottom_line("\nERROR: Could not find ",mesh_file)
        return 0
    sort_mesh_cmd_list=[sort_mesh_cmd.strip(),str(tile.default_zl),mesh_file]
    UI.vprint(1,"-> Reorganizing mesh triangles.")
    timer=time.time()
    moulinette=subprocess.Popen(sort_mesh_cmd_list,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = moulinette.stdout.readline()
        if not line: 
            break
        else:
            print(line.decode("utf-8")[:-1])
    UI.timings_and_bottom_line(timer)
    UI.logprint("Moulinette applied for tile lat=",tile.lat,", lon=",tile.lon," and ZL",tile.default_zl)
    return 1
##############################################################################

##############################################################################
def triangulate(name,path_to_Ortho4XP_dir):
    Tri_option = ' -pAYPQ '
    mesh_cmd=[os.path.join(path_to_Ortho4XP_dir,triangle_cmd).strip(),Tri_option.strip(),name+'.poly']
    fingers_crossed=subprocess.Popen(mesh_cmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print(line.decode("utf-8")[:-1])
    fingers_crossed.poll()        
    if fingers_crossed.returncode:
        print("\nERROR: triangle crashed, check osm mask data.\n")
        return 0
    return 1
##############################################################################   
