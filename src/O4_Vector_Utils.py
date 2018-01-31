from math import sqrt, ceil
import numpy
from shapely import geometry
from shapely import ops
from rtree import index
import O4_UI_Utils as UI

max_pols_for_merge=20

##############################################################################
class Vector_Map():
    
    nodata=-32768
    dico_attributes = {'DUMMY':0,'WATER':1,'SEA':2,'INTERP_ALT':4,'SMOOTHED_ALT':8}
    def __init__(self):
        self.dico_nodes={}  # keys are tuples of 2 floats (in our case (lon-base_lon), lat-base_lat) and values are ints (ids)  
        self.dico_edges={}  # keys are tuples of 2 ints (end-points ids) and values are ints (ids). An egde id is needed for the index (bbox)
        self.nodes_dico={}  # inverse of dico_nodes : ids to 2-uples (coordinates)
        self.edges_dico={}  # inverse of dico_edges : ids to 2-uples (end-points ids)
        self.ebbox=index.Index()
        self.data_nodes={}  # keys are ints (ids) and values are floats (vector altitude)  # could easily be upgraded to arrays if necessary  
        self.data_edges={}  # keys are ints (ids) and values are ints (attribute)
        self.next_node_id=1
        self.next_edge_id=1
        self.holes=[]
        self.seeds={} 

    def insert_node(self,x,y,z):
        if (x,y) in self.dico_nodes:
            node_id=self.dico_nodes[(x,y)]
            if self.data_nodes[node_id]==self.nodata: self.data_nodes[node_id]=z
        else:
            node_id=self.next_node_id
            self.dico_nodes[(x,y)]=node_id 
            self.nodes_dico[node_id]=(x,y)
            self.data_nodes[node_id]=z
            self.next_node_id+=1
        return node_id

    def interp_nodes(self,node0_id,node1_id,weight):
        x=(1-weight)*self.nodes_dico[node0_id][0]+weight*self.nodes_dico[node1_id][0]
        y=(1-weight)*self.nodes_dico[node0_id][1]+weight*self.nodes_dico[node1_id][1]
        if self.data_nodes[node0_id]!=self.nodata and self.data_nodes[node1_id]!=self.nodata:
            z=(1-weight)*self.data_nodes[node0_id]+weight*self.data_nodes[node1_id]
        else:
            z=self.nodata
        return (x,y,z)
    
    
    def update_edge(self,nodeid0,nodeid1,marker):
        if nodeid0==nodeid1: return 1
        if (nodeid0,nodeid1) in self.dico_edges:
            edge_id=self.dico_edges[(nodeid0,nodeid1)]
            self.data_edges[edge_id]=  self.data_edges[edge_id] | marker # bitwise add new marker if necessary
            return 1 
        if (nodeid1,nodeid0) in self.dico_edges:
            edge_id=self.dico_edges[(nodeid1,nodeid0)]
            self.data_edges[edge_id]=  self.data_edges[edge_id] | marker # bitwise add new marker if necessary
            return 1
        return 0


    def create_edge(self,nodeid0,nodeid1,marker):
        if self.update_edge(nodeid0,nodeid1,marker): return
        edge_id=self.next_edge_id
        self.next_edge_id+=1
        self.dico_edges[(nodeid0,nodeid1)]=edge_id
        self.edges_dico[edge_id]=(nodeid0,nodeid1)
        self.data_edges[edge_id]=marker
        self.ebbox.insert(edge_id,self.bbox_from_node_ids(nodeid0,nodeid1))
        return

    
    def insert_edge(self,id0,id1,marker,check=True):
        #UI.vprint(2,"Inserting :",self.nodes_dico[id0],self.nodes_dico[id1])
        if not check:
            self.create_edge(id0,id1,marker)
            return
        if self.update_edge(id0,id1,marker): 
            #UI.vprint(2,"  -> only updated")
            return
        weight_list=[]
        id_list=[]
        task=self.ebbox.intersection(self.bbox_from_node_ids(id0,id1),objects=True)
        for hits in task:
            edge_id=hits.id
            edge_bbox=hits.bbox 
            (id2,id3)=self.edges_dico[edge_id]
            c_marker=self.data_edges[edge_id]
            #UI.vprint(2,"  checking against:",self.nodes_dico[id2],self.nodes_dico[id3])
            coeffs=self.are_encroached(numpy.array(self.nodes_dico[id0]),\
                    numpy.array(self.nodes_dico[id1]),\
                    numpy.array(self.nodes_dico[id2]),\
                    numpy.array(self.nodes_dico[id3]))
            if not coeffs: 
                #UI.vprint(2,"    -> not encroached")
                continue
            if len(coeffs)==2:
                (alpha,beta)=coeffs  
                #UI.vprint(2,"    encroached transverse",alpha,beta)  
                (c_x,c_y,c_z)=self.interp_nodes(id2,id3,beta)  # ! important to choose id2 id3 beta and not id0 id1 alpha for the c_z component !
                c_id=self.insert_node(c_x,c_y,c_z)
                #print("      new vertex",self.nodes_dico[c_id])
                weight_list.append(alpha)
                id_list.append(c_id)
                # destroy edge
                del(self.dico_edges[(id2,id3)])
                del(self.edges_dico[edge_id])
                del(self.data_edges[edge_id])
                self.ebbox.delete(edge_id,edge_bbox)
                #
                self.create_edge(id2,c_id,c_marker)
                self.create_edge(c_id,id3,c_marker)
            else:
                (alpha0,alpha1,beta0,beta1)=coeffs
                ordered_data=sorted(zip((beta0,beta1,0,1),(id0,id1,id2,id3)))     
                #UI.vprint(2,"    encroached colinear:",ordered_data)
                for i in range(1,3):
                    if ordered_data[i][0]>0 and ordered_data[i][0]<1:
                        # destroy edge
                        #UI.vprint(2,"delete:",id2,id3)
                        del(self.dico_edges[(id2,id3)])
                        del(self.edges_dico[edge_id])
                        del(self.data_edges[edge_id])
                        self.ebbox.delete(edge_id,edge_bbox)
                        #
                        self.create_edge(ordered_data[i-1][1],ordered_data[i][1],c_marker)  
                        self.create_edge(ordered_data[i][1],ordered_data[i+1][1],c_marker)  
                        if ordered_data[i+1][0]<1:
                           self.create_edge(ordered_data[i+1][1],ordered_data[i+2][1],c_marker)  
                        break
                if alpha0>0 and alpha0<1: 
                    weight_list.append(alpha0)
                    #UI.vprint(2,"encode cut :",alpha0,id2) 
                    id_list.append(id2)
                if alpha1>0 and alpha1<1: 
                    weight_list.append(alpha1)
                    #UI.vprint(2,"encode cut :",alpha1,id3) 
                    id_list.append(id3)
        for alpha,cut_id in zip(weight_list,id_list):
            if self.data_nodes[cut_id]==self.nodata: self.data_nodes[cut_id]=self.interp_nodes(id1,id0,alpha)[2]  
        id_list = list(zip(*([(0,id0)]+sorted(zip(weight_list,id_list)) +[(1,id1)])))[1]
        for i in range(0,len(id_list)-1):
            if (id_list[i],id_list[i+1]) in self.dico_edges: 
                #UI.vprint(1,"update edge:",id_list[i],id_list[i+1])
                edge_id=self.dico_edges[(id_list[i],id_list[i+1])] 
                self.data_edges[edge_id]= self.data_edges[edge_id] | marker
            elif (id_list[i+1],id_list[i]) in self.dico_edges:
                #UI.vprint(1,"update edge:",id_list[i+1],id_list[i])
                edge_id=self.dico_edges[(id_list[i+1],id_list[i])] 
                self.data_edges[edge_id]= self.data_edges[edge_id] | marker
            else: 
                #UI.vprint(1,"create edge:",id_list[i],id_list[i+1])
                self.create_edge(id_list[i],id_list[i+1],marker)
        #print(self.nodes_dico)
        #print(self.edges_dico)
                                  
    def insert_way(self,way,marker,check=True):
        if isinstance(marker,str):
            marker=self.dico_attributes[marker] 
        node0_id=self.insert_node(*way[0])
        for node_array in way[1:]:
            node1_id=self.insert_node(*node_array)
            self.insert_edge(node0_id,node1_id,marker,check)
            node0_id=node1_id     
                                  
    def bbox_from_node_ids(self,id0,id1):
        # takes the ids of two nodes
        # returns a 4-uple of the form (xmin,ymin,xmax,ymax) taken from the nodes coords
        (xmin,xmax,ymin,ymax) = (self.nodes_dico[id0][0]<=self.nodes_dico[id1][0] and \
                                (self.nodes_dico[id0][0],self.nodes_dico[id1][0]) or \
                                (self.nodes_dico[id1][0],self.nodes_dico[id0][0])) + \
                                (self.nodes_dico[id0][1]<=self.nodes_dico[id1][1] and \
                                (self.nodes_dico[id0][1],self.nodes_dico[id1][1]) or \
                                (self.nodes_dico[id1][1],self.nodes_dico[id0][1]))
        return (xmin,ymin,xmax,ymax)
                                  
    def are_encroached(self,a,b,c,d): 
        # A crucial one !
        # returns False if the only mutual points of the closed segments a->b and c->d are in {a,b,c,d}
        # returns [alpha,beta] where (1-alpha)*a * alpha*b = (1-beta)*c+beta*d otherwise and 
        #    if the segments otherwise cut each other transversally (possibly only in one point)
        # returns [alpha0,alpha1,beta0,beta1] where alpha0*(a-b)=(a-c), alpha1*(a-b)=(a-d), 
        #    beta0*(c-d)=(c-a), beta1*(c-d)=(c-b) otherwise and if the segments are colinear.
        # In the last case we hence have : c=(1-alpha0)*a+alpha0*b, d=(1-alpha1)*a+alpha1*b, 
        # a=(1-beta0)*c+beta0*d, b=(1-beta1)*c+beta1*d
        eps=1e-12               
        A=numpy.column_stack((b-a,c-d))
        F=c-a                     
        if abs(numpy.linalg.det(A))>eps:
            [alpha,beta]=numpy.linalg.solve(A,F)
            enc_lim=1e-7
            return (alpha>=0 and alpha<=1) and (beta>=0 and beta<=1) and ((alpha>enc_lim and alpha<1-enc_lim)\
                    or (beta>enc_lim and beta<1-enc_lim)) and [alpha,beta] 
        elif abs(numpy.linalg.det(numpy.column_stack((b-a,c-a))))>eps:
            return False          
        else:
            g_idx = numpy.argmax(abs(a-b))
            d_idx = numpy.argmax(abs(c-d))
            alpha0,alpha1=(a-c)[g_idx]/(a-b)[g_idx],(a-d)[g_idx]/(a-b)[g_idx]
            beta0,beta1=(c-a)[d_idx]/(c-d)[d_idx],(c-b)[d_idx]/(c-d)[d_idx]
            return (alpha0>0 or alpha1>0) and (alpha0<1 or alpha1<1) and [alpha0,alpha1,beta0,beta1]

    def encode_MultiPolygon(self,multipol,pol_to_alt,marker,area_limit=1e-10,check=True,simplify=False,refine=False,cut=True): 
        UI.progress_bar(1,0)
        if isinstance(multipol,dict):
            iterloop=multipol.values()
            todo=len(multipol)
        else:
            iterloop=ensure_MultiPolygon(multipol)
            todo=len(iterloop)
        step=int(todo/100)+1
        done=0
        for pol in iterloop:
            if cut: pol=cut_to_tile(pol)
            if simplify:
                pol=pol.simplify(simplify)  
            for polygon in ensure_MultiPolygon(pol):
                if polygon.area<=area_limit:
                    continue
                try:
                    polygon=geometry.polygon.orient(polygon)  # important for certain pol_to_alt instances
                except:
                    continue
                way=numpy.array(polygon.exterior)
                if refine: way=refine_way(way,refine)
                alti_way=pol_to_alt(way).reshape((len(way),1))
                self.insert_way(numpy.hstack([way,alti_way]),marker,check)
                for linestring in polygon.interiors:
                    if linestring.is_empty: 
                        continue
                    way=numpy.array(linestring)
                    if refine: way=refine_way(way,refine)
                    alti_way=pol_to_alt(way).reshape((len(way),1))
                    self.insert_way(numpy.hstack([way,alti_way]),marker,check)
                try:
                    if marker in self.seeds:
                        self.seeds[marker].append(numpy.array(polygon.representative_point()))
                    else:
                        self.seeds[marker]=[numpy.array(polygon.representative_point())]
                except Exception as e:
                    UI.vprint(2,e+str(list(polygon.exterior.coords))) 
            done+=1
            if done%step==0: 
                UI.progress_bar(1,int(100*done/todo))
                if UI.red_flag: return 0
        return 1

    def encode_MultiLineString(self,multilinestring,line_to_alt,marker,check=True,refine=False,skip_cut=False): 
        UI.progress_bar(1,0)
        multilinestring=ensure_MultiLineString(multilinestring)
        todo=len(multilinestring)
        step=int(todo/100)+1
        done=0
        for line in multilinestring:
            if not skip_cut: line=cut_to_tile(line)
            for linestring in ensure_MultiLineString(line):
                if linestring.is_empty: 
                    continue
                way=numpy.array(linestring)
                if refine: way=refine_way(way,refine)
                alti_way=line_to_alt(way).reshape((len(way),1))
                self.insert_way(numpy.hstack([way,alti_way]),marker,check)
            done+=1
            if done%step==0: 
                UI.progress_bar(1,int(100*done/todo))
                if UI.red_flag: return 0
        return 1
        
    

    def write_node_file(self,node_file_name): 
        # note that Triangle4XP too is writing a(nother) node file, which as more node attributes
        total_nodes=len(self.dico_nodes)
        f= open(node_file_name,'w')
        f.write(str(total_nodes)+' 2 1 0\n')
        for idx in sorted(list(self.nodes_dico.keys())):
            f.write(str(idx)+' '+' '.join(['{:.15f}'.format(x) for x in (self.nodes_dico[idx][0],self.nodes_dico[idx][1],self.data_nodes[idx])])+'\n')
        f.close() 
    
    def write_poly_file(self,poly_file_name): 
        f=open(poly_file_name,'w')
        f.write('0 2 1 0\n')
        f.write('\n')
        total_edges=len(self.edges_dico)
        f.write(str(total_edges)+' 1\n')
        idx=1
        for edge_id in self.edges_dico:
            f.write(str(idx)+' '+str(self.edges_dico[edge_id][0])+' '+str(self.edges_dico[edge_id][1])+' '+str(self.data_edges[edge_id])+'\n')
            idx+=1
        f.write('\n'+str(len(self.holes))+'\n')
        idx=1
        for hole in self.holes:        
            f.write(str(idx)+' '+' '.join(['{:.15f}'.format(h) for h in hole])+'\n')
            idx+=1
        total_seeds=numpy.sum([len(self.seeds[key]) for key in self.seeds])
        if total_seeds==0:
            f.write('\n0\n')
        else: 
            f.write('\n'+str(total_seeds)+'\n')
            idx=1
            for long_key in sorted(self.dico_attributes.items(),key=lambda item:item[1]):
                (key,marker)=long_key
                if key not in self.seeds: continue
                for seed in self.seeds[key]:
                    f.write(str(idx)+' '+' '.join(['{:.15f}'.format(s) for s in seed])+' '+str(marker)+'\n')
                    idx+=1
        f.close()
        return 
##############################################################################

##############################################################################
def is_multipart(input_geometry):
    return 'Multi' in input_geometry.geom_type or 'Collection' in input_geometry.geom_type   
##############################################################################

##############################################################################
def split_polygon(input_pol, max_size):
    (xmin,ymin,xmax,ymax) = input_pol.bounds
    if xmax-xmin <= max_size and ymax-ymin <= max_size:
        return [input_pol]
    ret_val=[]
    if xmax-xmin >= ymax-ymin:
        subpols1 = input_pol.intersection(geometry.box(xmin,ymin,(xmin+xmax)/2,ymax))
        subpols2 = input_pol.intersection(geometry.box((xmin+xmax)/2,ymin,xmax,ymax))
    else:
        subpols1 = input_pol.intersection(geometry.box(xmin,ymin,xmax,(ymin+ymax)/2))
        subpols2 = input_pol.intersection(geometry.box(xmin,(ymin+ymax)/2,xmax,ymax))
    for subpol in subpols1 if is_multipart(subpols1) else [subpols1]:
        if isinstance(subpol,geometry.Polygon): 
            ret_val.extend(split_polygon(subpol,max_size))
    for subpol in subpols2 if is_multipart(subpols2) else [subpols2]:
        if isinstance(subpol,geometry.Polygon): 
            ret_val.extend(split_polygon(subpol,max_size))
    return ret_val
##############################################################################


##############################################################################
def MultiPolygon_to_Indexed_Polygons(multipol,merge_overlappings=True,limit=10):
    ########################################################################
    def merge_pol(pol,id_pol):
        todo_list=list(idx_pol.intersection(pol.bounds))
        if limit and len(todo_list)>limit: 
            UI.vprint(2,"    Skipping some too complex merging process (based on max_pols_for_merge)")
            return add_pol(pol,id_pol)
        ids_to_merge=[]
        for polid in todo_list:
            if pol.intersects(dico_pol[polid]):
                ids_to_merge.append(polid)
        #if ids_to_merge: print("Number to be merged :",len(ids_to_merge))        
        #timer=time.time()
        try:
            merged_pols=ops.cascaded_union([dico_pol[polid] for polid in ids_to_merge]+[pol])
        except Exception as e:
            UI.vprint(2,e)
            return
        #print("merge:                 ",time.time()-timer)
        #timer=time.time()
        for polid in ids_to_merge:
            idx_pol.delete(polid,dico_pol[polid].bounds)
            dico_pol.pop(polid,None)
        for pol in merged_pols.geoms if 'Multi' in merged_pols.geom_type else [merged_pols]:
            for subpol in split_polygon(pol,0.1):
                idx_pol.insert(id_pol,subpol.bounds)
                dico_pol[id_pol]=subpol
                id_pol+=1
        #print("update:",time.time()-timer)
        return id_pol
    def add_pol(pol,id_pol):
        dico_pol[id_pol]=pol
        id_pol+=1
        return id_pol   
    ########################################################################
    UI.progress_bar(1,0)
    idx_pol=index.Index() 
    dico_pol={} 
    id_pol=0
    todo=len(multipol.geoms) if 'Multi' in multipol.geom_type else 1
    step=int(todo/100)+1 
    done=0 
    # we sort the geometries according to the area of their bounding box, larger first
    # since it is probably more efficient this way
    iterloop=sorted(multipol.geoms, key=lambda geom:geometry.box(*geom.bounds).area, reverse=True) if 'Multi' in multipol.geom_type else [multipol]
    for pol in iterloop:
        if not pol.area: 
            done+=1
            continue
        if not pol.is_valid: 
            UI.logprint("Invalid polygon detected at",list(pol.exterior.coords)[0]) 
            done+=1
            continue
        if merge_overlappings:
            id_pol=merge_pol(pol,id_pol)
        else:
            id_pol=add_pol(pol,id_pol)
        done+=1
        if done%step==0: 
            UI.progress_bar(1,int(100*done/todo))
            if UI.red_flag: return 0
    return (idx_pol,dico_pol)
##############################################################################

##############################################################################
def cut_to_tile(input_geometry, xmin=0, xmax=1, ymin=0, ymax=1,strictly_inside=False):
    if not strictly_inside:
        return input_geometry.intersection(geometry.Polygon(
            [(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax),(xmin,ymin)]))
    else:
        return input_geometry.intersection(geometry.Polygon(
            [(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax),(xmin,ymin)])).difference(
            geometry.LineString([(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax),(xmin,ymin)]))


##############################################################################

##############################################################################
def ensure_MultiPolygon(input_geometry):
    if input_geometry.is_empty: 
        return geometry.MultiPolygon()
    elif input_geometry.geom_type=='MultiPolygon':
        return input_geometry
    elif input_geometry.geom_type=='Polygon':
        return geometry.MultiPolygon([input_geometry])
    elif 'Collection' in input_geometry.geom_type: 
        return geometry.MultiPolygon([pol for pol in input_geometry.geoms if pol.geom_type=='Polygon'])
    else:
        return geometry.MultiPolygon()
##############################################################################

##############################################################################
def ensure_MultiLineString(input_geometry):
    if input_geometry.is_empty: 
        return geometry.MultiLineString()
    elif input_geometry.geom_type=='MultiLineString':
        return input_geometry
    elif input_geometry.geom_type in ['LineString','LinearRing']:
        return geometry.MultiLineString([input_geometry])
    elif 'Collection' in input_geometry.geom_type: 
        return geometry.MultiLineString([line for line in input_geometry.geoms if line.geom_type in ['LineString','LinearRing']])
    else:
        return geometry.MultiLineString()
##############################################################################
    
##############################################################################
def ensure_ccw(input_geometry):
    if input_geometry.is_empty: 
        return geometry.MultiLineString()
    geometries=[]
    for line in input_geometry.geoms if 'Multi' in input_geometry.geom_type else [input_geometry]:
        if line.is_ring and not geometry.LinearRing(line).is_ccw:
            line.coords = list(line.coords)[::-1]
        geometries.append(line)
    return geometry.MultiLineString(geometries)
##############################################################################

##############################################################################
def indexed_difference(idx_pol1,dico_pol1,idx_pol2,dico_pol2):
    idx_out=index.Index()
    dico_out={}
    idnew=0
    for polid1,pol1 in dico_pol1.items():
        for polid2 in idx_pol2.intersection(pol1.bounds):
            if pol1.intersects(dico_pol2[polid2]):
                pol1=pol1.difference(dico_pol2[polid2])
        if pol1.area:
            for pol in pol1 if 'Multi' in pol1.geom_type else [pol1]: 
                idx_out.insert(idnew,pol.bounds)
                dico_out[idnew]=pol
                idnew+=1 
    return idx_out,dico_out
##############################################################################

##############################################################################
def improved_buffer(input_geometry,buffer_width,separation_width,simplify_length):
    UI.progress_bar(1,0)
    output_geometry=input_geometry.buffer(buffer_width+separation_width,join_style=2,mitre_limit=1.5,resolution=1)
    UI.progress_bar(1,40)
    if UI.red_flag: return 0
    output_geometry=output_geometry.buffer(-1*separation_width,join_style=2,mitre_limit=1.5,resolution=1)
    UI.progress_bar(1,80)
    if UI.red_flag: return 0
    output_geometry=output_geometry.simplify(simplify_length)
    UI.progress_bar(1,100)
    if UI.red_flag: return 0
    return output_geometry
##############################################################################

##############################################################################
def coastline_to_MultiPolygon(coastline,lat,lon):
    ######################################################################
    def encode_to_next(coord,new_way,remove_coords):
        if coord in inits:
            idx=inits.index(coord)
            new_way+=segments[idx][2]
            UI.vprint(3,segments[idx][2][0],segments[idx][2][-1])
            next_coord=segments[idx][1]
            remove_coords.append(coord)
            remove_coords.append(next_coord)
        else:
            idx=bdcoords.index(coord)                
            if idx<len(bdcoords)-1: 
               next_coord=bdcoords[idx+1] 
               next_coord_loop=next_coord
            else:
               next_coord=bdcoords[0]
               next_coord_loop=next_coord+4  
            interp_coord=ceil(coord)
            while interp_coord<next_coord_loop:
                new_way+=bd_point(interp_coord) 
                UI.vprint(3,bd_point(interp_coord))
                interp_coord+=1
        return next_coord               
    ######################################################################
    # code starts here :
    coastline=ensure_MultiLineString(coastline)
    islands=[]
    interior_seas=[]
    segments=[]
    bdpolys=[]
    ends=[]
    inits=[]
    osm_error=False
    osm_badpoints=[]
    for line in coastline.geoms:
        if line.is_ring:
            if geometry.LinearRing(line).is_ccw:
                islands.append(list(line.coords)) 
            else:
                interior_seas.append(list(line.coords)) 
        else:
            tmp=list(line.coords)
            if numpy.min(numpy.abs([tmp[0][0]-int(tmp[0][0]),tmp[0][1]-int(tmp[0][1])]))>0.00001: 
                osm_error=True  
                osm_badpoints.append((tmp[0][1]+lat,tmp[0][0]+lon))
            if numpy.min(numpy.abs([tmp[-1][0]-int(tmp[-1][0]),tmp[-1][1]-int(tmp[-1][1])]))>0.00001:
                osm_error=True  
                osm_badpoints.append((tmp[-1][1]+lat,tmp[-1][0]+lon))
            segments.append([bd_coord(tmp[0]),bd_coord(tmp[-1]),tmp])
            ends.append(bd_coord(tmp[-1]))
            inits.append(bd_coord(tmp[0]))
    if osm_error:
        UI.lvprint(1,"ERROR is OSM coastline data. Coastline abruptly stops at",osm_badpoints)
        return geometry.MultiPolygon()
    bdcoords=sorted(ends+inits)
    UI.vprint(3,bdcoords)
    while bdcoords:
        UI.vprint(3,"new loop")
        new_way=[]
        remove_coords=[]
        first_coord=bdcoords[0]
        next_coord=encode_to_next(first_coord,new_way,remove_coords) 
        count=0
        while next_coord!=first_coord:
           count+=1
           next_coord=encode_to_next(next_coord,new_way,remove_coords)  
           if count==1000: # dead loop caused by faulty osm coastline data   
               UI.lvprint(1,"ERROR is OSM coastline data, probably caused by a coastline way with wrong orientation.")
               return geometry.MultiPolygon()
        bdpolys.append(new_way)
        UI.vprint(3,new_way)
        for coord in remove_coords:
            try:
                bdcoords.remove(coord)
            except:
               (x,y)=bd_point(coord)
               UI.lvprint(1,"ERROR is OSM coastline data, probably caused by a triple junction around lat=",str(y+lat)," lon=",str(x+lon))
               return geometry.MultiPolygon()
    if not bdpolys: # and islands: 
        bdpolys.append([(0,0),(0,1),(1,1),(1,0)])
    outpol=ops.cascaded_union([geometry.Polygon(bdpoly).buffer(0) for bdpoly in bdpolys])
    inpol=ensure_MultiPolygon(cut_to_tile(ops.cascaded_union([geometry.Polygon(loop).buffer(0) for loop in islands+interior_seas]))) 
    return ensure_MultiPolygon(outpol.symmetric_difference(inpol))
##############################################################################


##############################################################################
def bd_coord(pt):
    # distance along the boundary of the unit square in cw direction starting
    # from (0,0)  
    return geometry.LineString([(0,0),(0,1),(1,1),(1,0),(0,0)]).project(geometry.Point(pt))
##############################################################################

##############################################################################
def bd_point(coord):
    # point a coord distance along the boundary of the unit square in cw direction starting
    # from (0,0)  
    return list(geometry.LineString([(0,0),(0,1),(1,1),(1,0),(0,0)]).interpolate(coord%4).coords)
##############################################################################

##############################################################################
def grow_or_shrink_loops(multilinestring,extent):
   coords_list=[] 
   for line in multilinestring.geoms:
       if line.is_ring:
           tmp=geometry.polygon.orient(geometry.Polygon(line).buffer(extent/111120,resolution=1)).exterior 
           coords_list.append(list(tmp.coords))
       else:
           coords_list.append(list(line.coords))
   return geometry.MultiLineString(coords_list)
##############################################################################

#############################################################################
def refine_way(way,max_length):
    new_way=[]
    for i in range(len(way)-1):
        new_way.append(way[i]) 
        l=sqrt((way[i][0]-way[i+1][0])**2+(way[i][1]-way[i+1][1])**2)
        ins=int(l//(max_length/111120))
        for j in range(1,ins+1):
            new_way.append((j/(ins+1)*way[i+1][0]+(ins+1-j)/(ins+1)*way[i][0],j/(ins+1)*way[i+1][1]+(ins+1-j)/(ins+1)*way[i][1]))
    new_way.append(way[-1])
    return numpy.array(new_way)
    
##############################################################################
def point_in_polygon(point,polygon):
    '''
    This procedures determines wether the input point belongs to the 
    polygon. The algorithm is based on the computation of the index 
    of the boundary of the polygon with respect to the point.
    A point is a list of 2 floats and a polygon is a list of 2N floats, N>=3,   
    and the first two floats equal the last two ones.  
    '''
    total_winding_nbr=0
    quadrants=[]
    for j in range(0,len(polygon)//2):
        if polygon[2*j] >= point[0]:
            if polygon[2*j+1] >= point[1]:
                quadrants.append(1)
            else:
                quadrants.append(4)
        else:
            if polygon[2*j+1] >= point[1]:
                quadrants.append(2)
            else:
                quadrants.append(3)
    winding_nbr=0
    for k in range(0,len(quadrants)-1):
        change=quadrants[k+1]-quadrants[k]
        if change in [1,-1,0]:
            winding_nbr += change
        elif change in [-3,3]:
            winding_nbr += (-1)*change/3
        elif change in [-2,2]:
            if (polygon[2*k]-point[0])*(polygon[2*k+3]-point[1])\
-(polygon[2*k+1]-point[1])*(polygon[2*k+2]-point[0])>=0:
                winding_nbr+=2
            else:
                winding_nbr+=-2
    change=quadrants[0]-quadrants[len(quadrants)-1]
    if change in [1,-1,0]:
        winding_nbr += change
    elif change in [-3,3]:
        winding_nbr += (-1)*change/3
    elif change in [-2,2]:
        if (polygon[2*len(quadrants)-2]-point[0])*(polygon[1]\
-point[1])-(polygon[2*len(quadrants)-1]-point[1])*(polygon[0]-point[0])>=0:
            winding_nbr+=2
        else:
            winding_nbr+=-2
    total_winding_nbr+=winding_nbr/4
    if total_winding_nbr == 0:
        return False
    else:
        return True
##############################################################################

#############################################################################
def dummy_alt(way):
        return numpy.zeros(way.shape[0])
#############################################################################
