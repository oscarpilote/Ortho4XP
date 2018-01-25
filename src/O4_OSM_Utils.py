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
max_osm_tentatives=10

##############################################################################
class OSM_layer():

    def __init__(self):
        self.dicosmn={}
        self.dicosmw={}
        # rels already sorted out and containing nodeids rather than wayids 
        self.dicosmr={}
        # original rels containing wayids only, not sorted and/or reversed
        self.dicosmrorig={}
        # ids of objects directly queried, not of child or 
        # parent objects pulled indirectly by queries. Since
        # osm ids are only unique per object type we need one for each:
        self.dicosmfirst={'n':[],'w':[],'r':[]}  
        self.dicosmtags={'n':{},'w':{},'r':{}}
        self.dicosm=[self.dicosmn,self.dicosmw,self.dicosmr,self.dicosmrorig,
                     self.dicosmfirst,self.dicosmtags]       
        

    def update_dicosm(self,osm_input,target_tags):
        initnodes=len(self.dicosmn)
        initways=len(self.dicosmfirst['w'])
        initrels=len(self.dicosmfirst['r'])
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
        #finished_with_file=False
        first_line=pfile.readline()
        separator="'" if "'" in first_line else '"'
        normal_exit=False
        for line in pfile:
            #while not finished_with_file==True:
            items=line.split(separator)
            if '<node id=' in items[0]:
                osmtype='n'
                osmid=items[1]
                for j in range(0,len(items)):
                    if items[j]==' lat=':
                        latp=items[j+1]
                    elif items[j]==' lon=':
                        lonp=items[j+1]
                self.dicosmn[osmid]=(lonp,latp)
            elif '<way id=' in items[0]:
                osmtype='w'
                osmid=items[1]
                self.dicosmw[osmid]=[]  
                if target_tags==None: self.dicosmfirst['w'].append(osmid)
            elif '<nd ref=' in items[0]:
                self.dicosmw[osmid].append(items[1])
            elif '<relation id=' in items[0]:
                osmtype='r'
                osmid=items[1]
                self.dicosmr[osmid]={'outer':[],'inner':[]}
                self.dicosmrorig[osmid]={'outer':[],'inner':[]}
                dico_rel_check={'inner':{},'outer':{}}
                if target_tags==None: self.dicosmfirst['r'].append(osmid)
            elif '<member type=' in items[0]:
                role=items[5]
                if items[1]!='way' or role not in ('outer','inner'):
                    if items[1]=='node': continue # not necessary to report these
                    UI.lvprint(2,"Relation id=",osmid,"contains a member of type","'"+items[1]+"'","and role","'"+role+"'","which was not treated (only deal with 'ways' of role 'inner' or 'outer').")
                    continue                
                if items[3] not in self.dicosmw: 
                    continue
                self.dicosmrorig[osmid][role].append(items[3])
                endpt1=self.dicosmw[items[3]][0]
                endpt2=self.dicosmw[items[3]][-1]
                if endpt1==endpt2:
                    self.dicosmr[osmid][role].append(self.dicosmw[items[3]])
                else:
                    if endpt1 in dico_rel_check[role]:
                        dico_rel_check[role][endpt1].append(items[3])
                    else:
                        dico_rel_check[role][endpt1]=[items[3]]
                    if endpt2 in dico_rel_check[role]:
                        dico_rel_check[role][endpt2].append(items[3])
                    else:
                        dico_rel_check[role][endpt2]=[items[3]]
            elif ('<tag k=' in items[0]):
                if target_tags and (not self.dicosmfirst[osmtype] or self.dicosmfirst[osmtype][-1]!=osmid) and (items[1],items[3]) in target_tags[osmtype]:
                    self.dicosmfirst[osmtype].append(osmid)
                if target_tags==None or (('all','') in target_tags[osmtype])\
                                     or ((items[1],'') in target_tags[osmtype])\
                                     or ((items[1],items[3]) in target_tags[osmtype]):
                    if osmid not in self.dicosmtags[osmtype]: 
                        self.dicosmtags[osmtype][osmid]={items[1]:items[3]}
                    else:
                        self.dicosmtags[osmtype][osmid][items[1]]=items[3]
            elif '</way' in items[0]:
                if not self.dicosmw[osmid]: 
                    del(self.dicosmw[osmid]) 
                    if self.dicosmfirst['w'] and self.dicosmfirst['w'][-1]==osmid: del(self.dicosmfirst['w'][-1])
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
                    if self.dicosmfirst['r'] and self.dicosmfirst['r'][-1]==osmid: del(self.dicosmfirst['r'][-1])
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
                if not self.dicosmr[osmid]['outer']: 
                    del(self.dicosmr[osmid])
                    del(self.dicosmrorig[osmid])
                    if self.dicosmfirst['r'] and self.dicosmfirst['r'][-1]==osmid: del(self.dicosmfirst['r'][-1])
                if target_tags==None:
                    for wayid in self.dicosmrorig[osmid]['outer']+self.dicosmrorig[osmid]['inner']:
                        try:
                            self.dicosmfirst['w'].remove(wayid)
                        except:
                           pass
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
        fout.write('<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="Overpass API postprocessed by Ortho4XP">\n')
        for nodeid,(lonp,latp) in self.dicosmn.items():
            fout.write('  <node id="'+nodeid+'" lat="'+latp+'" lon="'+lonp+'" version="1"/>\n')
        for wayid in self.dicosmfirst['w']+list(set(self.dicosmw).difference(set(self.dicosmfirst['w']))):
            fout.write('  <way id="'+wayid+'" version="1">\n')
            for nodeid in self.dicosmw[wayid]:
                fout.write('    <nd ref="'+nodeid+'"/>\n')
            for tag in self.dicosmtags['w'][wayid] if wayid in self.dicosmtags['w'] else []:
                fout.write('    <tag k="'+tag+'" v="'+self.dicosmtags['w'][wayid][tag]+'"/>\n')
            fout.write('  </way>\n')
        for relid in self.dicosmfirst['r']+list(set(self.dicosmrorig).difference(set(self.dicosmfirst['r']))):
            fout.write('  <relation id="'+relid+'" version="1">\n')
            for wayid in self.dicosmrorig[relid]['outer']:
                fout.write('    <member type="way" ref="'+wayid+'" role="outer"/>\n')
            for wayid in self.dicosmrorig[relid]['inner']:
                fout.write('    <member type="way" ref="'+wayid+'" role="inner"/>\n')
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
    for query in queries:
        for tag in [query] if isinstance(query,str) else query:
            items=tag.split('"')
            osm_type=items[0][0]
            target_tags[osm_type].append((items[1],items[3]))
    for tag in tags_of_interest:
        if isinstance(tag,str):
            target_tags['n'].append((tag,''))
            target_tags['w'].append((tag,''))
            target_tags['r'].append((tag,''))
        else:
            target_tags['n'].append(tag)
            target_tags['w'].append(tag)
            target_tags['r'].append(tag)
    cached_data_filename=FNAMES.osm_cached(lat, lon, cached_suffix)
    if cached_suffix and os.path.isfile(cached_data_filename):
        UI.vprint(1,"    * Recycling OSM data from",cached_data_filename)
        return osm_layer.update_dicosm(cached_data_filename,target_tags)
    for query in queries:
        # look first for cached data (old scheme)
        if isinstance(query,str):
            old_cached_data_filename=FNAMES.osm_old_cached(lat, lon, query)
            if os.path.isfile(old_cached_data_filename):
                UI.vprint(1,"    * Recycling OSM data for",query)
                osm_layer.update_dicosm(old_cached_data_filename,target_tags)
                continue
        UI.vprint(1,"    * Downloading OSM data for",query)        
        response=get_overpass_data(query,(lat,lon,lat+1,lon+1),server_code)
        if UI.red_flag: return 0
        if not response: 
           UI.logprint("No valid answer for",query,"after",max_osm_tentatives,", skipping it.") 
           UI.vprint(1,"      No valid answer after",max_osm_tentatives,", skipping it.")
           return 0
        osm_layer.update_dicosm(response,target_tags)
    if cached_suffix: 
        osm_layer.write_to_file(cached_data_filename)
    return 1
##############################################################################

##############################################################################
def OSM_query_to_OSM_layer(query,bbox,osm_layer,tags_of_interest=[],server_code=None,cached_file_name=''):
    # this one is simpler and does not depend on the notion of tile
    target_tags={'n':[],'w':[],'r':[]}
    for tag in [query] if isinstance(query,str) else query:
        items=tag.split('"')
        osm_type=items[0][0]
        target_tags[osm_type].append((items[1],items[3]))
    for tag in tags_of_interest:
        if isinstance(tag,str):
            target_tags['n'].append((tag,''))
            target_tags['w'].append((tag,''))
            target_tags['r'].append((tag,''))
        else:
            target_tags['n'].append(tag)
            target_tags['w'].append(tag)
            target_tags['r'].append(tag)
    if cached_file_name and os.path.isfile(cached_file_name):
        UI.vprint(1,"    * Recycling OSM data from",cached_file_name)
        osm_layer.update_dicosm(cached_file_name,target_tags)
    else:
        response=get_overpass_data(query,bbox,server_code)
        if UI.red_flag: return 0
        if not response: 
            UI.lvprint(1,"      No valid answer for",query,"after",max_osm_tentatives,", skipping it.")
            return 0
        osm_layer.update_dicosm(response,target_tags)
        if cached_file_name: osm_layer.write_to_file(cached_file_name)
    return 1
##############################################################################


##############################################################################
def get_overpass_data(query,bbox,server_code=None):
    tentative=1
    while True:
        s=requests.Session()
        if not server_code:
           true_server_code = random.choice(list(overpass_servers.keys())) if overpass_server_choice=='random' else overpass_server_choice
        base_url=overpass_servers[true_server_code]
        if isinstance(query,str):
            overpass_query=query+str(bbox)
        else: # query is a tuple 
            overpass_query=''.join([x+str(bbox)+";" for x in query])
        url=base_url+"?data=("+overpass_query+");(._;>>;);out meta;"
        UI.vprint(3,url)
        try:
            r=s.get(url,timeout=60)
            UI.vprint(3,"OSM response status :",r)
            if '200' in str(r):
                if b"</osm>" not in r.content[-10:] and b"</OSM>" not in r.content[-10:]:
                    UI.vprint(1,"        OSM server",true_server_code,"sent a corrupted answer (no closing </osm> tag in answer), new tentative in 2sec...")
                elif len(r.content)<=1000 and b"error" in r.content: 
                    UI.vprint(1,"        OSM server",true_server_code,"sent us an error code for the data (data too big ?), new tentative in 2sec...")
                else:
                    break
            else:
                UI.vprint(1,"        OSM server",true_server_code,"rejected our query, new tentative in 2 sec...")
        except:
            UI.vprint(1,"        OSM server",true_server_code,"was too busy, new tentative in 2 sec...")
        if tentative>=max_osm_tentatives:
            return 0
        if UI.red_flag: return 0
        tentative+=1           
        time.sleep(2)
    return r.content
##############################################################################

##############################################################################
def OSM_to_MultiLineString(osm_layer,lat,lon,tags_for_exclusion=set(),filter=None,limit_segs=None):
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
        way=numpy.array([osm_layer.dicosmn[nodeid] for nodeid in osm_layer.dicosmw[wayid]],dtype=numpy.float)-numpy.array([[lon,lat]],dtype=numpy.float) 
        if filter and not filter(way):
            try:
                multiline_reject.append(geometry.LineString(way))
            except:
                pass
            done+=1
            continue
        try:
            multiline.append(geometry.LineString(way))
        except:
            pass
        done+=1
        filtered_segs+=len(way)
        if limit_segs and filtered_segs>=limit_segs: 
            UI.vprint(1,"      (result was stripped due to user defined limit 'max_levelled_segs')")
            UI.vprint(3,"      ",osm_layer.dicosmtags['w'][wayid])
            break
    UI.progress_bar(1,100)
    if not filter:
        return geometry.MultiLineString(multiline)
    else:
        UI.vprint(2,"      Number of filtered segs :",filtered_segs)
        return (geometry.MultiLineString(multiline),geometry.MultiLineString(multiline_reject))
##############################################################################

##############################################################################
def OSM_to_MultiPolygon(osm_layer,lat,lon):
    multilist=[]
    todo=len(osm_layer.dicosmfirst['w'])+len(osm_layer.dicosmfirst['r'])
    step=int(todo/100)+1
    done=0
    for wayid in osm_layer.dicosmfirst['w']:
        if done%step==0: UI.progress_bar(1,int(100*done/todo))
        if osm_layer.dicosmw[wayid][0]!=osm_layer.dicosmw[wayid][-1]: 
            UI.logprint("Non closed way starting at",osm_layer.dicosmn[osm_layer.dicosmw[wayid][0]],", skipped.")
            done+=1
            continue
        way=numpy.array([osm_layer.dicosmn[nodeid] for nodeid in osm_layer.dicosmw[wayid]],dtype=numpy.float)
        way=way-numpy.array([[lon,lat]],dtype=numpy.float) 
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
        multilist.append(pol) 
        done+=1
    for relid in osm_layer.dicosmfirst['r']:
        if done%step==0: UI.progress_bar(1,int(100*done/todo))
        try:
            multiout=[geometry.Polygon(numpy.array([osm_layer.dicosmn[nodeid] \
                                        for nodeid in nodelist],dtype=numpy.float)-numpy.array([lon,lat],dtype=numpy.float)) \
                                        for nodelist in osm_layer.dicosmr[relid]['outer']]
            multiout=ops.cascaded_union([geom for geom in multiout if geom.is_valid])
            multiin=[geometry.Polygon(numpy.array([osm_layer.dicosmn[nodeid] \
                                        for nodeid in nodelist],dtype=numpy.float)-numpy.array([lon,lat],dtype=numpy.float)) \
                                        for nodelist in osm_layer.dicosmr[relid]['inner']]
            multiin=ops.cascaded_union([geom for geom in multiin if geom.is_valid])
        except Exception as e:
            UI.logprint(e)
            done+=1
            continue
        multipol = multiout.difference(multiin)
        for pol in multipol.geoms if ('Multi' in multipol.geom_type or 'Collection' in multipol.geom_type) else [multipol]:
            if not pol.area: 
                done+=1
                continue
            if not pol.is_valid: 
                UI.logprint("Relation",relid,"contains an invalid polygon which was discarded") 
                done+=1
                continue
            multilist.append(pol)  
        done+=1
    ret_val=geometry.MultiPolygon(multilist)
    UI.vprint(2,"    Total number of geometries:",len(ret_val.geoms))
    UI.progress_bar(1,100)
    return ret_val
##############################################################################

