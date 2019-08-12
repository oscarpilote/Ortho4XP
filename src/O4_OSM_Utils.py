import os
import time
import io
import bz2
import random
import requests
import numpy
from shapely import geometry, ops
import O4_UI_Utils as UI
import O4_File_Names as FNAMES

overpass_servers={
        "DE":"http://overpass-api.de/api/interpreter",
        "FR":"http://api.openstreetmap.fr/oapi/interpreter",
        "KU":"https://overpass.kumi.systems/api/interpreter", 
        "RU":"http://overpass.osm.rambler.ru/cgi/interpreter"
        }
overpass_server_choice="DE"
max_osm_tentatives=8

##############################################################################
class OSM_layer():

    def __init__(self):
        self.dicosmn={}      # keys are ints (ids) and values are tuple of (lat,lon)
        self.dicosmn_reverse={} # reverese of the previous one
        self.dicosmw={}
        self.next_node_id=-1
        self.next_way_id=-1
        self.next_rel_id=-1
        # rels already sorted out and containing nodeids rather than wayids 
        self.dicosmr={}
        # original rels containing wayids only, not sorted and/or reversed
        self.dicosmrorig={}
        # ids of objects directly queried, not of child or 
        # parent objects pulled indirectly by queries. Since
        # osm ids are only unique per object type we need one for each:
        self.dicosmfirst={'n':set(),'w':set(),'r':set()}  
        self.dicosmtags={'n':{},'w':{},'r':{}}
        self.dicosm=[self.dicosmn,self.dicosmw,self.dicosmr,self.dicosmrorig,
                     self.dicosmfirst,self.dicosmtags]       
        

    def update_dicosm(self,osm_input,input_tags=None,target_tags=None):
        # input_tags (dict or None) are the input query tags (per osm type)
        # target_tags (dict or None) are the the tags which should be kept (per osm type)
        # It is expected that if not None the target_tags contains the input_tags
        initnodes=len(self.dicosmn)
        initways=len(self.dicosmfirst['w'])
        initrels=len(self.dicosmfirst['r'])
        dicosmn_id_map={}
        dicosmw_id_map={}
        # osm_input may either refer to an osm filename (e.g. cached data) or 
        # to a xml bytestring (direct download) 
        if isinstance(osm_input,str):
            osm_file_name=osm_input 
            try:
                if osm_file_name[-4:]=='.bz2':
                    pfile=bz2.open(osm_file_name,'rt',encoding="utf-8")
                else:
                    pfile=open(osm_file_name,'r',encoding="utf-8")
            except:
                UI.vprint(1,"    Could not open",osm_file_name,"for reading (corrupted ?).")
                return 0    
        elif isinstance(osm_input,bytes):
            pfile=io.StringIO(osm_input.decode(encoding="utf-8"))
        first_line=pfile.readline()
        if "<osm " not in first_line:
            first_line=pfile.readline()
        separator="'" if "'" in first_line else '"'
        normal_exit=False
        for line in pfile:
            items=line.split(separator)
            if '<node id=' in items[0]:
                osmtype='n'
                osmid=items[1]
                for j in range(0,len(items)):
                    if items[j]==' lat=':
                        latp=float(items[j+1])
                    elif items[j]==' lon=':
                        lonp=float(items[j+1])
                if (lonp,latp) in self.dicosmn_reverse:
                    true_osmid=self.dicosmn_reverse[(lonp,latp)]
                    dicosmn_id_map[osmid]=true_osmid
                    osmid=true_osmid
                else:
                    true_osmid=self.next_node_id
                    dicosmn_id_map[osmid]=true_osmid
                    osmid=true_osmid
                    self.dicosmn_reverse[(lonp,latp)]=osmid
                    self.dicosmn[osmid]=(lonp,latp)
                    self.next_node_id-=1
            elif '<way id=' in items[0]:
                osmtype='w'
                osmid=items[1]
                true_osmid=self.next_way_id
                self.next_way_id-=1
                dicosmw_id_map[osmid]=true_osmid
                osmid=true_osmid
                self.dicosmw[osmid]=[]  
                if not input_tags: self.dicosmfirst['w'].add(osmid)
            elif '<nd ref=' in items[0]:
                self.dicosmw[osmid].append(dicosmn_id_map[items[1]])
            elif '<relation id=' in items[0]:
                osmtype='r'
                osmid=items[1]
                true_osmid=self.next_rel_id
                self.next_rel_id-=1
                osmid=true_osmid
                self.dicosmr[osmid]={'outer':[],'inner':[]}
                self.dicosmrorig[osmid]={'outer':[],'inner':[]}
                dico_rel_check={'inner':{},'outer':{}}
                if not input_tags: 
                    self.dicosmfirst['r'].add(osmid)
            elif '<member type=' in items[0]:
                role=items[5]
                if items[1]!='way' or role not in ('outer','inner'):
                    if items[1]=='node': continue # not necessary to report these
                    UI.lvprint(2,"Relation id=",osmid,"contains a member of type","'"+items[1]+"'","and role","'"+role+"'","which was not treated (only deal with 'ways' of role 'inner' or 'outer').")
                    continue                
                try:
                    wayid=dicosmw_id_map[items[3]]
                except:
                    continue
                self.dicosmrorig[osmid][role].append(wayid)
                endpt1=self.dicosmw[wayid][0]
                endpt2=self.dicosmw[wayid][-1]
                if endpt1==endpt2:
                    self.dicosmr[osmid][role].append(self.dicosmw[wayid])
                else:
                    if endpt1 in dico_rel_check[role]:
                        dico_rel_check[role][endpt1].append(wayid)
                    else:
                        dico_rel_check[role][endpt1]=[wayid]
                    if endpt2 in dico_rel_check[role]:
                        dico_rel_check[role][endpt2].append(wayid)
                    else:
                        dico_rel_check[role][endpt2]=[wayid]
            elif ('<tag k=' in items[0]):
                # Do we need to catch that tag ?
                if (not input_tags) or (('all','') in target_tags[osmtype])\
                                     or ((items[1],'') in target_tags[osmtype])\
                                     or ((items[1],items[3]) in target_tags[osmtype]):
                    if osmid not in self.dicosmtags[osmtype]: 
                        self.dicosmtags[osmtype][osmid]={items[1]:items[3]}
                    else:
                        self.dicosmtags[osmtype][osmid][items[1]]=items[3]                     
                    # If so, do we need to declare this osmid as a first catch, not one only brought with as a child    
                    if input_tags and (((items[1],'') in input_tags[osmtype]) or ((items[1],items[3]) in input_tags[osmtype])):
                        self.dicosmfirst[osmtype].add(osmid)                         
            elif '</way' in items[0]:
                if not self.dicosmw[osmid]:
                    del(self.dicosmw[osmid]) 
                    self.next_way_id+=1
                    if osmid in self.dicosmfirst['w']: self.dicosmfirst['w'].remove(osmid)
                    if osmid in self.dicosmtags['w']: del(self.dicosmtags[osmtype][osmid])
            elif '</relation>' in items[0]:
                bad_rel=False
                for role,endpt in ((r,e) for r in ['outer','inner'] for e in dico_rel_check[r]):
                    if len(dico_rel_check[role][endpt])!=2:
                        bad_rel=True
                        break
                if bad_rel==True:
                    UI.lvprint(2,"Relation id=",osmid,"is ill formed and was not treated.")
                    del(self.dicosmr[osmid])
                    del(self.dicosmrorig[osmid])
                    del(dico_rel_check)
                    self.next_rel_id+=1
                    if osmid in self.dicosmfirst['r']: self.dicosmfirst['r'].remove(osmid)
                    if osmid in self.dicosmtags['r']: del(self.dicosmtags['r'][osmid])
                    continue
                for role in ['outer','inner']:
                    while dico_rel_check[role]:
                        nodeids=[]
                        endpt=next(iter(dico_rel_check[role]))
                        wayid=dico_rel_check[role][endpt][0]
                        endptinit=self.dicosmw[wayid][0]
                        endpt1=endptinit
                        endpt2=self.dicosmw[wayid][-1]
                        for nodeid in self.dicosmw[wayid][:-1]:
                            nodeids.append(nodeid)
                        while endpt2!=endptinit:
                            if dico_rel_check[role][endpt2][0]==wayid:
                                    wayid=dico_rel_check[role][endpt2][1]
                            else:
                                    wayid=dico_rel_check[role][endpt2][0]
                            endpt1=endpt2
                            if self.dicosmw[wayid][0]==endpt1:
                                endpt2=self.dicosmw[wayid][-1]
                                for nodeid in self.dicosmw[wayid][:-1]:
                                    nodeids.append(nodeid)
                            else:
                                endpt2=self.dicosmw[wayid][0]
                                for nodeid in self.dicosmw[wayid][-1:0:-1]:
                                    nodeids.append(nodeid)
                            del(dico_rel_check[role][endpt1])
                        nodeids.append(endptinit)
                        self.dicosmr[osmid][role].append(nodeids)
                        del(dico_rel_check[role][endptinit])
                if target_tags==None:
                    for wayid in self.dicosmrorig[osmid]['outer']+self.dicosmrorig[osmid]['inner']:
                        try:
                            self.dicosmfirst['w'].remove(wayid)
                        except:
                           pass
                if not self.dicosmr[osmid]['outer']: 
                    del(self.dicosmr[osmid])
                    del(self.dicosmrorig[osmid])
                    self.next_rel_id+=1
                    if osmid in self.dicosmfirst['r']: self.dicosmfirst['r'].remove(osmid)
                    if osmid in self.dicosmtags['r']: del(self.dicosmtags['r'][osmid])
                del(dico_rel_check)
            elif '</osm>' in items[0]:
                normal_exit=True
        pfile.close()
        if not normal_exit:
            UI.lvprint(0,"ERROR: OSM overpass server answer was corrupted (no ending </OSM> tag)")
            return 0 
        UI.vprint(2,"      A total of "+str(len(self.dicosmn)-initnodes)+" new node(s), "+\
               str(len(self.dicosmfirst['w'])-initways)+" new ways and "+str(len(self.dicosmfirst['r'])-initrels)+" new relation(s).")
        return 1

    def write_to_file(self,filename):
        try:
            if filename[-4:]=='.bz2':
                fout=bz2.open(filename,'wt',encoding="utf-8")
            else:
                fout=open(filename,'w',encoding="utf-8")
        except:
            UI.vprint(1,"    Could not open",filename,"for writing.")
            return 0
        fout.write('<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="Ortho4XP">\n')
        if not len(self.dicosmfirst['n']):
            for nodeid,(lonp,latp) in self.dicosmn.items():
                fout.write('  <node id="'+str(nodeid)+'" lat="'+'{:.7f}'.format(latp)+'" lon="'+'{:.7f}'.format(lonp)+'" version="1"/>\n')
        else:
            for nodeid,(lonp,latp) in self.dicosmn.items():
                if nodeid not in self.dicosmtags['n']:
                    fout.write('  <node id="'+str(nodeid)+'" lat="'+'{:.7f}'.format(latp)+'" lon="'+'{:.7f}'.format(lonp)+'" version="1"/>\n')
                else:
                    fout.write('  <node id="'+str(nodeid)+'" lat="'+'{:.7f}'.format(latp)+'" lon="'+'{:.7f}'.format(lonp)+'" version="1">\n')
                    for tag in self.dicosmtags['n'][nodeid]:
                        fout.write('    <tag k="'+tag+'" v="'+self.dicosmtags['n'][nodeid][tag]+'"/>\n')
                    fout.write('  </node>\n')
        for wayid in tuple(self.dicosmfirst['w'])+tuple(set(self.dicosmw).difference(self.dicosmfirst['w'])):
            fout.write('  <way id="'+str(wayid)+'" version="1">\n')
            for nodeid in self.dicosmw[wayid]:
                fout.write('    <nd ref="'+str(nodeid)+'"/>\n')
            for tag in self.dicosmtags['w'][wayid] if wayid in self.dicosmtags['w'] else []:
                fout.write('    <tag k="'+tag+'" v="'+self.dicosmtags['w'][wayid][tag]+'"/>\n')
            fout.write('  </way>\n')
        for relid in tuple(self.dicosmfirst['r'])+tuple(set(self.dicosmrorig).difference(self.dicosmfirst['r'])):
            fout.write('  <relation id="'+str(relid)+'" version="1">\n')
            for wayid in self.dicosmrorig[relid]['outer']:
                fout.write('    <member type="way" ref="'+str(wayid)+'" role="outer"/>\n')
            for wayid in self.dicosmrorig[relid]['inner']:
                fout.write('    <member type="way" ref="'+str(wayid)+'" role="inner"/>\n')
            for tag in self.dicosmtags['r'][relid] if relid in self.dicosmtags['r'] else []:
                fout.write('    <tag k="'+tag+'" v="'+self.dicosmtags['r'][relid][tag]+'"/>\n')
            fout.write('  </relation>\n')
        fout.write('</osm>')
        fout.close()    
        return 1
##############################################################################

##############################################################################
def OSM_queries_to_OSM_layer(queries,osm_layer,lat,lon,tags_of_interest=[],server_code=None,cached_suffix=''):
    # this one is a bit complicated by a few checks of existing cached data which had different filenames
    # is versions prior to 1.30
    target_tags={'n':[],'w':[],'r':[]}
    input_tags={'n':[],'w':[],'r':[]}
    for query in queries:
        for tag in [query] if isinstance(query,str) else query:
            items=tag.split('"')
            osm_type=items[0][0]
            try: 
                target_tags[osm_type].append((items[1],items[3]))
                input_tags[osm_type].append((items[1],items[3]))
            except: 
                target_tags[osm_type].append((items[1],''))
                input_tags[osm_type].append((items[1],''))
            for tag in tags_of_interest:
                if isinstance(tag,str):
                    if (tag,'') not in target_tags[osm_type]: target_tags[osm_type].append((tag,''))
                else:
                    if tag not in target_tags[osm_type]:target_tags[osm_type].append(tag)
    cached_data_filename=FNAMES.osm_cached(lat, lon, cached_suffix)
    if cached_suffix and os.path.isfile(cached_data_filename):
        UI.vprint(1,"    * Recycling OSM data from",cached_data_filename)
        return osm_layer.update_dicosm(cached_data_filename,input_tags,target_tags)
    for query in queries:
        # look first for cached data (old scheme)
        if isinstance(query,str):
            old_cached_data_filename=FNAMES.osm_old_cached(lat, lon, query)
            if os.path.isfile(old_cached_data_filename):
                UI.vprint(1,"    * Recycling OSM data for",query)
                osm_layer.update_dicosm(old_cached_data_filename,input_tags,target_tags)
                continue
        UI.vprint(1,"    * Downloading OSM data for",query)        
        response=get_overpass_data(query,(lat,lon,lat+1,lon+1),server_code)
        if UI.red_flag: return 0
        if not response: 
           UI.logprint("No valid answer for",query,"after",max_osm_tentatives,", skipping it.") 
           UI.vprint(1,"      No valid answer after",max_osm_tentatives,", skipping it.")
           return 0
        osm_layer.update_dicosm(response,input_tags,target_tags)
    if cached_suffix: 
        osm_layer.write_to_file(cached_data_filename)
    return 1
##############################################################################

##############################################################################
def OSM_query_to_OSM_layer(query,bbox,osm_layer,tags_of_interest=[],server_code=None,cached_file_name=''):
    # this one is simpler and does not depend on the notion of tile
    target_tags={'n':[],'w':[],'r':[]}
    input_tags={'n':[],'w':[],'r':[]}
    for tag in [query] if isinstance(query,str) else query:
        items=tag.split('"')
        osm_type=items[0][0]
        try: 
            target_tags[osm_type].append((items[1],items[3]))
            input_tags[osm_type].append((items[1],items[3]))
        except: 
            target_tags[osm_type].append((items[1],''))
            input_tags[osm_type].append((items[1],''))
        for tag in tags_of_interest:
            if isinstance(tag,str):
                target_tags[osm_type].append((tag,''))
            else:
                target_tags[osm_type].append(tag)
    if cached_file_name and os.path.isfile(cached_file_name):
        UI.vprint(1,"    * Recycling OSM data from",cached_file_name)
        osm_layer.update_dicosm(cached_file_name,input_tags,target_tags)
    else:
        response=get_overpass_data(query,bbox,server_code)
        if UI.red_flag: return 0
        if not response: 
            UI.lvprint(1,"      No valid answer for",query,"after",max_osm_tentatives,", skipping it.")
            return 0
        osm_layer.update_dicosm(response,input_tags,target_tags)
        if cached_file_name: osm_layer.write_to_file(cached_file_name)
    return 1
##############################################################################


##############################################################################
def get_overpass_data(query,bbox,server_code=None):
    tentative=1
    while True:
        s=requests.Session()
        true_server_code = server_code
        if not server_code:
           true_server_code = random.choice(list(overpass_servers.keys())) if overpass_server_choice=='random' else overpass_server_choice
        base_url=overpass_servers[true_server_code]
        if isinstance(query,str):
            overpass_query=query+str(bbox)+";"
        else: # query is a tuple 
            overpass_query=''.join([x+str(bbox)+";" for x in query])
        url=base_url+"?data=("+overpass_query+");(._;>>;);out meta;"
        UI.vprint(3,url)
        try:
            r=s.get(url,timeout=60)
            UI.vprint(3,"OSM response status :",r)
            if '200' in str(r):
                if b"</osm>" not in r.content[-10:] and b"</OSM>" not in r.content[-10:]:
                    UI.vprint(1,"        OSM server",true_server_code,"sent a corrupted answer (no closing </osm> tag in answer), new tentative in",2**tentative,"sec...")
                elif len(r.content)<=1000 and b"error" in r.content: 
                    UI.vprint(1,"        OSM server",true_server_code,"sent us an error code for the data (data too big ?), new tentative in",2**tentative,"sec...")
                else:
                    break
            else:
                UI.vprint(1,"        OSM server",true_server_code,"rejected our query, new tentative in",2**tentative,"sec...")
        except:
            UI.vprint(1,"        OSM server",true_server_code,"was too busy, new tentative in",2**tentative,"sec...")
        if tentative>=max_osm_tentatives:
            return 0
        if UI.red_flag: return 0
        time.sleep(2**tentative)
        tentative+=1           
    return r.content
##############################################################################

##############################################################################
def OSM_to_MultiLineString(osm_layer,lat,lon,tags_for_exclusion=set(),filter=None):
    multiline=[]
    multiline_reject=[]
    todo=len(osm_layer.dicosmfirst['w'])
    step=int(todo/100)+1
    done=0
    filtered_segs=0
    for wayid in osm_layer.dicosmfirst['w']:
        if done%step==0: UI.progress_bar(1,int(100*done/todo))
        if tags_for_exclusion and wayid in osm_layer.dicosmtags['w'] \
          and not set(osm_layer.dicosmtags['w'][wayid].keys()).isdisjoint(tags_for_exclusion):
            done+=1
            continue  
        way=numpy.round(numpy.array([osm_layer.dicosmn[nodeid] for nodeid in osm_layer.dicosmw[wayid]],dtype=numpy.float64)-numpy.array([[lon,lat]],dtype=numpy.float64),7) 
        if filter and not filter(way,filtered_segs):
            try:
                multiline_reject.append(geometry.LineString(way))
            except:
                pass
            done+=1
            continue
        try:
            multiline.append(geometry.LineString(way))
            filtered_segs+=len(way)
        except:
            pass
        done+=1
    UI.progress_bar(1,100)
    if not filter:
        return geometry.MultiLineString(multiline)
    else:
        UI.vprint(2,"      Number of filtered segs :",filtered_segs)
        return (geometry.MultiLineString(multiline),geometry.MultiLineString(multiline_reject))
##############################################################################

##############################################################################
def OSM_to_MultiPolygon(osm_layer,lat,lon,filter=None):
    multilist=[]
    excludelist=[]
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
        if filter and filter(pol,wayid,osm_layer.dicosmtags['w']):
            excludelist.append(pol)
        else:
            multilist.append(pol) 
        done+=1
    for relid in osm_layer.dicosmfirst['r']:
        if done%step==0: UI.progress_bar(1,int(100*done/todo))
        try:
            multiout=[geometry.Polygon(numpy.round(numpy.array([osm_layer.dicosmn[nodeid] \
                                        for nodeid in nodelist],dtype=numpy.float64)-numpy.array([lon,lat],dtype=numpy.float64),7))\
                                        for nodelist in osm_layer.dicosmr[relid]['outer']]
            multiout=ops.cascaded_union([geom for geom in multiout if geom.is_valid])
            multiin=[geometry.Polygon(numpy.round(numpy.array([osm_layer.dicosmn[nodeid]\
                                        for nodeid in nodelist],dtype=numpy.float64)-numpy.array([lon,lat],dtype=numpy.float64),7))\
                                        for nodelist in osm_layer.dicosmr[relid]['inner']]
            multiin=ops.cascaded_union([geom for geom in multiin if geom.is_valid])
        except Exception as e:
            UI.logprint(e)
            done+=1
            continue
        multipol = multiout.difference(multiin)
        if filter and filter(multipol,relid,osm_layer.dicosmtags['r']):
            targetlist=excludelist
        else:
            targetlist=multilist 
        for pol in multipol.geoms if ('Multi' in multipol.geom_type or 'Collection' in multipol.geom_type) else [multipol]:
            if not pol.area: 
                done+=1
                continue
            if not pol.is_valid: 
                UI.logprint("Relation",relid,"contains an invalid polygon which was discarded") 
                done+=1
                continue
            targetlist.append(pol)  
        done+=1
    if filter:
        ret_val=(geometry.MultiPolygon(multilist),geometry.MultiPolygon(excludelist))
        UI.vprint(2,"    Total number of geometries:",len(ret_val[0].geoms),len(ret_val[1].geoms))
    else:
        ret_val=geometry.MultiPolygon(multilist)
        UI.vprint(2,"    Total number of geometries:",len(ret_val.geoms))
    UI.progress_bar(1,100)
    return ret_val
##############################################################################

