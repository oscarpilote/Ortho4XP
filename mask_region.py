#!/usr/bin/env python3
import os, sys, time
import requests
import numpy
import pyproj
import subprocess
from math import *
from PIL import Image,ImageFilter,ImageDraw,ImageOps

overpass_server_list={"1":"http://api.openstreetmap.fr/oapi/interpreter", "2":"http://overpass-api.de/api/interpreter","3":"http://overpass.osm.rambler.ru/cgi/interpreter"}
overpass_server_choice="1" #str(random.randint(1,2)) # replace with "1" or "2" if you really wish a specific one, default is now to split the burden between "1" and "2" ("3" seems problematic)
dico_edge_markers   = {'outer':'1','inner':'1','coastline':'2',\
                       'tileboundary':'3','orthogrid':'3',\
                       'airport':'4','runway':'5','patch':'6'}
dico_tri_markers    = {'water':'1','sea':'2','sea_equiv':'3','altitude':'4'} 

##############################################################################
def build_image(maskxmin,maskmax,maskymin,maskymax,pixel_size,mesh_filename):
    t4=time.time()
    masks_im=Image.new("1",(int((maskxmax-maskxmin)/pixel_size),int((maskymax-maskymin)/pixel_size)))
    masks_draw=ImageDraw.Draw(masks_im)
    f_mesh=open(mesh_filename,"r")
    for i in range(0,4):
        f_mesh.readline()
    nbr_pt_in=int(f_mesh.readline())
    pt_in=numpy.zeros(2*nbr_pt_in,'float')
    for i in range(0,nbr_pt_in):
        tmplist=f_mesh.readline().split()
        pt_in[2*i]=float(tmplist[0])
        pt_in[2*i+1]=float(tmplist[1])
    for i in range(0,2): # skip 2 lines
        f_mesh.readline()
    nbr_tri_in=int(f_mesh.readline()) # read nbr of tris

    step_stones=nbr_tri_in//100
    percent=-1
    print(" Constructing binary mask for sea water / ground from mesh file "+str(mesh_filename))
    for i in range(0,nbr_tri_in):
        tmplist=f_mesh.readline().split()
        # look for the texture that will possibly cover the tri
        n1=int(tmplist[0])-1
        n2=int(tmplist[1])-1
        n3=int(tmplist[2])-1
        tri_type=tmplist[3] 
        [x1,y1]=pt_in[2*n1:2*n1+2]
        [x2,y2]=pt_in[2*n2:2*n2+2]
        [x3,y3]=pt_in[2*n3:2*n3+2]
        [px1,py1]=[round((x1-maskxmin)/pixel_size),round((y1-maskymin)/pixel_size)]
        [px2,py2]=[round((x2-maskxmin)/pixel_size),round((y2-maskymin)/pixel_size)]
        [px3,py3]=[round((x3-maskxmin)/pixel_size),round((y3-maskymin)/pixel_size)]
        try:
            masks_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill='white')
        except:
            pass
    f_mesh.close()
    masks_im=ImageOps.flip(masks_im)
    masks_im.save(name+'.png')
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t4))+\
              'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    return
##############################################################################

##############################################################################
def wgs84_to_texture(lat,lon,zoomlevel,website):
    ratio_x=lon/180           
    ratio_y=log(tan((90+lat)*pi/360))/pi
    if website=='g2xpl_8':
        mult=2**(zoomlevel-4)
        til_x=int((ratio_x+1)*mult)*8
        til_y=int((1-ratio_y)*mult)*8
    else:
        mult=2**(zoomlevel-5)
        til_x=int((ratio_x+1)*mult)*16
        til_y=int((1-ratio_y)*mult)*16
    return [til_x,til_y]
##############################################################################

##############################################################################
def st_coord(lat,lon,tex_x,tex_y,zoomlevel,website):                        
    """
    ST coordinates of a point in a texture
    """
    ratio_x=lon/180           
    ratio_y=log(tan((90+lat)*pi/360))/pi
    mult=2**(zoomlevel-5)
    s=(ratio_x+1)*mult-(tex_x//16)
    t=1-((1-ratio_y)*mult-tex_y//16)
    s = s if s>=0 else 0
    s = s if s<=1 else 1
    t = t if t>=0 else 0
    t = t if t<=1 else 1
    return [s,t]
##############################################################################

#############################################################################
def area(way):
   area=0
   x1=float(way[0][1])
   y1=float(way[0][0])
   for node in way[1:]:
       x2=float(node[1])
       y2=float(node[0])
       area+=(x2-x1)*(y2+y1)
       x1=x2
       y1=y2
   return area/2 
#############################################################################

#############################################################################
def pick_point(way,side):
   if side=='left':
       sign=1
   elif side=='right':
       sign=-1
   dmin =0.00001 
   l=0
   ptin=False
   i=0
   while (l<dmin) or (ptin==False):
       if len(way)==i+1:
           break
       x1=float(way[i][1])
       y1=float(way[i][0])
       x2=float(way[i+1][1])
       y2=float(way[i+1][0])
       l=sqrt((x2-x1)**2+(y2-y1)**2)
       ptin=True
       i+=1
   if ptin==True:
       dperp=0.000001
       x=0.5*x1+0.5*x2+(y1-y2)/l*dperp*sign
       y=0.5*y1+0.5*y2+(x2-x1)/l*dperp*sign
       return [[x,y]]
   else:
       return [[1000,1000]]
#############################################################################


##############################################################################
def build_poly_file(name,tags_or_osm_file,epsg_code): 
    t1=time.time()
    poly_file =  name+'.poly'
    dico_nodes={}
    dico_edges={}
    region_seeds=[]
    init_nodes=0
    if not tags_or_osm_file[-4:]=='.osm':
        print("-> Downloading region boundary data on Openstreetmap")
        tag=''
        for char in tags_or_osm_file:
            if char=='[':
                tag+='["'
            elif char==']':
                tag+='"]'
            elif char in['=','~']:
                tag+='"'+char+'"'
            else:
                tag+=char
        #tags.append('rel["admin_level"="'+boundary_level+'"]["name:fr"="'+name+'"]')                                         
        osm_filename=name+'.osm'
        #osm_errors_filename=name+'_detected_errors.txt'
        osm_errors_filename='/dev/null'
        if not os.path.isfile(osm_filename):
            print("    Obtaining OSM data for "+tag)
            s=requests.Session()
            osm_download_ok = False
            while osm_download_ok != True:
                url=overpass_server_list[overpass_server_choice]+"?data=("+tag+";);(._;>>;);out meta;"
                print(url)
                r=s.get(url)
                if r.headers['content-type']=='application/osm3s+xml':
                    osm_download_ok=True
                else:
                    print(r.content)
                    time.sleep(5)
                    print("      OSM server was busy, new tentative...")
            osmfile=open(osm_filename,'wb')
            osmfile.write(r.content)
            osmfile.close()
            print("     Done.")
        else:
            print("    Recycling OSM data for "+tag)
    else:
        osm_filename=tags_or_osm_file
    #if 'way[' in tag:
    #    [dicosmw,dicosmw_name,dicosmw_icao,dicosmw_ele]=osmway_to_dicos(osm_filename)
    #elif 'rel[' in tag:
    [dicosmr,dicosmrinner,dicosmrouter,dicosmr_name,dicosmr_icao,dicosmr_ele]=osmrel_to_dicos(osm_filename,osm_errors_filename)

    for relid in dicosmr:
        for waypts in dicosmrinner[relid]:
            keep_way(waypts,1,'inner',dico_nodes,\
                                dico_edges)
        for waypts in dicosmrouter[relid]:
            signed_area=area(waypts)
            if signed_area<0:
                side='left'
            else:
                side='right'
            keep_way(waypts,1,'outer',dico_nodes,\
                            dico_edges)
            points_checked=pick_point(waypts,side)
            region_seeds+=points_checked
    treated_nodes=len(dico_nodes)-init_nodes
    init_nodes=len(dico_nodes)
    if treated_nodes>0:
        strtmp=str(treated_nodes)+" new nodes."
    else:
        strtmp="no new node."
    print("   -> process of the associated data completed : "+strtmp)
    print("     Removal of obsolete edges,")
    dico_edges_tmp={}
    for edge in dico_edges:
        [initpt,endpt]=edge.split('|')
        if initpt != endpt:
            dico_edges_tmp[edge]=dico_edges[edge]
        #else:
        #    print("one removed edge : "+str(initpt))
    dico_edges=dico_edges_tmp
    print("     Removal of obsolete nodes,")
    final_nodes={}
    for edge in dico_edges:
        #print(edge)
        [initpt,endpt]=edge.split('|')
        final_nodes[initpt]=dico_nodes[initpt]
        final_nodes[endpt]=dico_nodes[endpt]
    dico_nodes=final_nodes
    print("-> Transcription of the updated data to the file "+poly_file)
    write_poly_file(poly_file,dico_nodes,dico_edges,region_seeds,epsg_code)
    
    print('\nCompleted in '+str('{:.2f}'.format(time.time()-t1))+\
                'sec.')
    print('_____________________________________________________________'+\
            '____________________________________')
    
    return 
#############################################################################

#############################################################################
def write_poly_file(poly_file,dico_nodes,dico_edges,region_seeds,epsg_code):
    total_nodes=len(dico_nodes)
    f=open(poly_file,'w')
    f.write(str(total_nodes)+' 2 1 0\n')
    dico_node_pos={}
    idx=1
    epsg4326=pyproj.Proj(init='epsg:4326')
    mask_proj=pyproj.Proj(init='epsg:'+epsg_code)
    for key in dico_nodes:
        dico_node_pos[key]=idx
        [lon,lat]=xycoords(key)
        [x,y]=pyproj.transform(epsg4326,mask_proj,lon,lat)
        f.write(str(idx)+' '+str(x)+' '+\
          str(y)+' '+str(dico_nodes[key])+'\n')        
        idx+=1
    f.write('\n')
    idx=1
    total_edges=len(dico_edges)
    f.write(str(total_edges)+' 1\n')
    for edge in dico_edges:
        [code1,code2]=edge.split('|')
        idx1=dico_node_pos[code1]
        idx2=dico_node_pos[code2]
        f.write(str(idx)+' '+str(idx1)+' '+str(idx2)+' '+\
                dico_edge_markers[dico_edges[edge]]+'\n')
        idx+=1
    f.write('\n0\n')
    total_seeds=len(region_seeds)
    f.write('\n'+str(total_seeds)+' 1\n')
    idx=1
    for seed in region_seeds:
        f.write(str(idx)+' '+str(seed[0])+' '+str(seed[1])+' 1\n')
        idx+=1
    print("   Remain " + str(len(dico_edges))+\
          " edges in total.") 
    f.close()
    return 
##############################################################################

##############################################################################
def osmway_to_dicos(osm_filename):
    pfile=open(osm_filename,'r',encoding="utf-8")
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
  
   # (Thanks Tony Wroblewski) Remove ways with no nodes (Can happen when editing in JOSM or from bad data)
    for wayid in list(dicosmw.keys()):
        if not dicosmw[wayid]:
            del dicosmw[wayid]


    print("     A total of "+str(len(dicosmn))+" node(s) and "+str(len(dicosmw))+" way(s).")
    return [dicosmw,dicosmw_name,dicosmw_icao,dicosmw_ele]
##############################################################################


##############################################################################
def osmrel_to_dicos(osm_filename,osm_errors_filename):
    pfile=open(osm_filename,'r',encoding="utf-8")
    efile=open(osm_errors_filename,'w')
    osm_errors_found=False
    dicosmn={}
    dicosmw={}
    dicosmr={}
    dicosmrinner={}
    dicosmrouter={}
    dicosmr_name={}
    dicosmr_icao={}
    dicosmr_ele={}
    dicoendpt={}
    finished_with_file=False
    in_rel=False
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
            wayid=items[1]
            dicosmw[wayid]=[]  
        elif '<nd ref=' in items[0]:
            dicosmw[wayid].append(items[1])
        elif '<relation id=' in items[0]:
            relid=items[1]
            in_rel=True
            dicosmr[relid]=[]
            dicosmrinner[relid]=[]
            dicosmrouter[relid]=[]
            dicoendpt={}
        elif '<member type=' in items[0]:
            if items[1]!='way':
                efile.write("Relation id="+str(relid)+" contains member "+items[1]+" which was not treated because it is not a way.\n")
                osm_errors_found=True
                continue
            role=items[5]
            if role=='inner':
                waytmp=[]
                for nodeid in dicosmw[items[3]]:
                    waytmp.append(dicosmn[nodeid])
                dicosmrinner[relid].append(waytmp)
            elif role=='outer':
                endpt1=dicosmw[items[3]][0]
                endpt2=dicosmw[items[3]][-1]
                if endpt1==endpt2:
                    waytmp=[]
                    for nodeid in dicosmw[items[3]]:
                        waytmp.append(dicosmn[nodeid])
                    dicosmrouter[relid].append(waytmp)
                else:
                    if endpt1 in dicoendpt:
                        dicoendpt[endpt1].append(items[3])
                    else:
                        dicoendpt[endpt1]=[items[3]]
                    if endpt2 in dicoendpt:
                        dicoendpt[endpt2].append(items[3])
                    else:
                        dicoendpt[endpt2]=[items[3]]
            else:
                efile.write("Relation id="+str(relid)+" contains a member with role different from inner or outer, it was not treated.\n")
                osm_errors_found=True
                continue
            dicosmr[relid].append(items[3]) 
        elif '<tag k=' in items[0] and in_rel and items[1]=='name':
            dicosmr_name[relid]=items[3]
        elif '<tag k=' in items[0] and in_rel and items[1]=='icao':
            dicosmr_icao[relid]=items[3]
        elif '<tag k=' in items[0] and in_rel and items[1]=='ele':
            dicosmr_ele[relid]=items[3]
        elif '</relation>' in items[0]:
            bad_rel=False
            for endpt in dicoendpt:
                if len(dicoendpt[endpt])!=2:
                    bad_rel=True
                    break
            if bad_rel==True:
                efile.write("Relation id="+str(relid)+" is ill formed and was not treated.\n")
                osm_errors_found=True
                dicosmr.pop(relid,'None')
                dicosmrinner.pop(relid,'None')
                dicosmrouter.pop(relid,'None')
                continue
            while dicoendpt:
                waypts=[]
                endpt=next(iter(dicoendpt))
                way=dicoendpt[endpt][0]
                endptinit=dicosmw[way][0]
                endpt1=endptinit
                endpt2=dicosmw[way][-1]
                for node in dicosmw[way][:-1]:
                    waypts.append(dicosmn[node])
                while endpt2!=endptinit:
                    if dicoendpt[endpt2][0]==way:
                            way=dicoendpt[endpt2][1]
                    else:
                            way=dicoendpt[endpt2][0]
                    endpt1=endpt2
                    if dicosmw[way][0]==endpt1:
                        endpt2=dicosmw[way][-1]
                        for node in dicosmw[way][:-1]:
                            waypts.append(dicosmn[node])
                    else:
                        endpt2=dicosmw[way][0]
                        for node in dicosmw[way][-1:0:-1]:
                            waypts.append(dicosmn[node])
                    dicoendpt.pop(endpt1,'None')
                waypts.append(dicosmn[endptinit])
                dicosmrouter[relid].append(waypts)
                dicoendpt.pop(endptinit,'None')
            dicoendpt={}
        elif '</osm>' in items[0]:
            finished_with_file=True
    pfile.close()
    efile.close()
    print("     A total of "+str(len(dicosmn))+" node(s) and "+str(len(dicosmr))+" relation(s).")
    #if osm_errors_found:
    #    print("     !!!Some OSM errors were detected!!!\n        They are listed in "+str(osm_errors_filename))
    #else:
    #    os.remove(osm_errors_filename)
    return [dicosmr,dicosmrinner,dicosmrouter,dicosmr_name,dicosmr_icao,dicosmr_ele]
##############################################################################

#############################################################################
def strcode(node):
    return '{:.9f}'.format(float(node[0]))+'_'+'{:.9f}'.format(float(node[1]))
#############################################################################


#############################################################################
def keep_node(node,dico_nodes,attribute=-32768):
    dico_nodes[strcode(node)]=attribute
    return
#############################################################################
   
#############################################################################
def keep_edge(node0,node,marker,dico_edges):
    if strcode(node0) != strcode(node):
        if strcode(node)+'|'+strcode(node0) in dico_edges:
            dico_edges[strcode(node)+'|'+strcode(node0)]=marker
        else:
            dico_edges[strcode(node0)+'|'+strcode(node)]=marker
    return
#############################################################################

#############################################################################
def keep_edge_unique(node0,node,marker,dico_edges):
   if strcode(node0) == strcode(node):
       return
   if strcode(node0)+'|'+strcode(node) in dico_edges:
       dico_edges.pop(strcode(node0)+'|'+strcode(node),None)
       return
   if strcode(node)+'|'+strcode(node0) in dico_edges:
       dico_edges.pop(strcode(node)+'|'+strcode(node0),None)
       return
   dico_edges[strcode(node0)+'|'+strcode(node)]=marker
   return
#############################################################################

#############################################################################
def keep_edge_str(strcode1,strcode2,marker,dico_edges,overwrite=True):
    if overwrite:
        if strcode2+'|'+strcode1 in dico_edges:
            dico_edges[strcode2+'|'+strcode1]=marker  
        else:
            dico_edges[strcode1+'|'+strcode2]=marker  
    elif (strcode2+'|'+strcode1 not in dico_edges) and (strcode1+'|'+strcode2 not in dico_edges):
        dico_edges[strcode1+'|'+strcode2]=marker  
    return
#############################################################################



#############################################################################
def keep_way(way,sign,marker,dico_nodes,dico_edges,attribute=-32768):
   if sign==1:
       node0=way[0]
       keep_node(node0,dico_nodes,attribute)
       for node in way[1:]:
           keep_node(node,dico_nodes,attribute)
           keep_edge(node0,node,marker,dico_edges)
           node0=node
   elif sign==-1:
       node0=way[-1]
       keep_node(node0,dico_nodes,attribute)
       for node in way[-1:-len(way)-1:-1]:
           keep_node(node,dico_nodes,attribute)
           keep_edge(node0,node,marker,dico_edges)
           node0=node
   return
#############################################################################
   
#############################################################################
def strxy(x,y):
    return '{:.9f}'.format(y)+'_'+'{:.9f}'.format(x)
    #return str(y+lat0)+'_'+str(x+lon0)
#############################################################################

#############################################################################
def keep_node_xy(x,y,dico_nodes,attribute=-32768):
   dico_nodes[strxy(x,y)]=attribute
   return
#############################################################################

#############################################################################
def xycoords(strcode):
    [slat,slon]=strcode.split('_')
    return [float('{:.9f}'.format(float(slon))),float('{:.9f}'.format(float(slat)))]
#############################################################################



#############################################################################
def keep_edge_str_tmp(strcode1,strcode2,marker,dico_edges_tmp):
   dico_edges_tmp[strcode1+'|'+strcode2]=marker
   return
#############################################################################

#############################################################################
def build_mesh_file(name,vertices,mesh_filename):
    print("-> Writing of the final mesh to the file "+mesh_filename)
    ele_filename  = name+'.1.ele'
    f_ele  = open(ele_filename,'r')
    nbr_vert=len(vertices)//2
    nbr_tri=int(f_ele.readline().split()[0])
    f=open(mesh_filename,"w")
    f.write("MeshVersionFormatted 1\n")
    f.write("Dimension 2\n\n")
    f.write("Vertices\n")
    f.write(str(nbr_vert)+"\n")
    for i in range(0,nbr_vert):
        f.write('{:.9f}'.format(vertices[2*i])+" "+\
                '{:.9f}'.format(vertices[2*i+1])+" 0\n") 
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
def build_vertex_array(name):
    node_filename = name+'.1.node'
    f_node = open(node_filename,'r')
    nbr_pt=int(f_node.readline().split()[0])
    vertices=numpy.zeros(2*nbr_pt)
    print("-> Loading of the mesh computed by Triangle4XP.")
    for i in range(0,nbr_pt):
        coordlist=f_node.readline().split()
        vertices[2*i]=float(coordlist[1])
        vertices[2*i+1]=float(coordlist[2])
    f_node.close()
    return vertices
##############################################################################

if __name__ == '__main__':
    print(sys.argv)
    name=sys.argv[1]
    tags_or_osm_file=sys.argv[2]
    epsg_code=sys.argv[3]
    pixel_size=float(sys.argv[4])
    gridsize=float(sys.argv[5])
    masks_width=int(sys.argv[6])
    build_poly_file(name,tags_or_osm_file,epsg_code)
    Tri_option = ' -pAYPQ '
    mesh_cmd=["../Utils/triangle".strip(),Tri_option.strip(),name+'.poly']
    fingers_crossed=subprocess.Popen(mesh_cmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print(line.decode("utf-8")[:-1])
    vertices=build_vertex_array(name)
    xmin=vertices[::2].min()
    xmax=vertices[::2].max()
    ymin=vertices[1::2].min()
    ymax=vertices[1::2].max()
    print(xmin,xmax,ymin,ymax)
    mesh_filename=name+'.mesh'
    build_mesh_file(name,vertices,mesh_filename)
    maskxmin=xmin-gridsize #int(floor(floor(xmin/gridsize)*gridsize))
    maskxmax=xmax+gridsize #int(ceil(ceil(xmax/gridsize)*gridsize))
    maskymin=ymin-gridsize #int(floor(floor(ymin/gridsize)*gridsize))
    maskymax=ymax+gridsize #int(ceil(ceil(ymax/gridsize)*gridsize))
    build_image(maskxmin,maskxmax,maskymin,maskymax,pixel_size,mesh_filename)
    buffer=''
    try:
        f=open(name+'.ext','r')
        for line in f.readlines():
            if "#" in line:
                buffer+="#"+line
        f.close()
    except:
        pass
    buffer+="# Created with : "+' '.join(sys.argv)+'\n'
    buffer+="mask_bounds="+str(maskxmin)+","+str(maskymin)+","+str(maskxmax)+","+str(maskymax)+"\n"
    buffer+="blur_radius="+str(masks_width)+'\n'
    f=open(name+'.ext','w')
    f.write(buffer)
    f.close()
    if masks_width:
        print(" Blur of the mask...")
        masks_im=Image.open(name+'.png').convert("L")
        img_array=numpy.array(masks_im,dtype=numpy.uint8)
        #kernel=numpy.ones(int(masks_width))/int(masks_width)
        kernel=numpy.array(range(1,2*masks_width))
        kernel[masks_width:]=range(masks_width-1,0,-1)
        kernel=kernel/masks_width**2
        for i in range(0,len(img_array)):
            img_array[i]=numpy.convolve(img_array[i],kernel,'same')
        img_array=img_array.transpose() 
        for i in range(0,len(img_array)):
            img_array[i]=numpy.convolve(img_array[i],kernel,'same')
        img_array=img_array.transpose()
        img_array=2*numpy.minimum(img_array,127) #*numpy.ones(img_array.shape)) 
        img_array=numpy.array(img_array,dtype=numpy.uint8)
        masks_im=Image.fromarray(img_array)
        masks_im.save(name+".png")
        #masks_im.save(name+'_'+epsg_code+'_'+str(maskxmin)+"_"+str(maskymax)+"_"+str(maskxmax)+"_"+str(maskymin)+"_.png")
    for f in [name+'.poly',name+'.1.node',name+'.mesh',name+'.1.ele']:
        try:
            os.remove(f)
        except:
            pass
