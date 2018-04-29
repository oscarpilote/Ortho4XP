import time 
import os
import sys
import subprocess
import io
import requests
import queue
import random
from math import ceil, log, tan, pi
import numpy
from PIL import Image, ImageFilter, ImageEnhance,  ImageOps
Image.MAX_IMAGE_PIXELS = 1000000000 # Not a decompression bomb attack!
import O4_UI_Utils as UI
try:
    import O4_Custom_URL as URL
    has_URL=True
except:
    has_URL=False
import O4_Geo_Utils as GEO
import O4_File_Names as FNAMES
from O4_Parallel_Utils import parallel_execute

http_timeout=10
check_tms_response=False
max_connect_retries=10
max_baddata_retries=10

user_agent_generic="Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0"
request_headers_generic={
            'User-Agent':user_agent_generic,
            'Accept':'*/*',
            'Connection':'keep-alive',
            'Accept-Encoding':'gzip, deflate'
            }

if 'dar' in sys.platform:
    dds_convert_cmd = os.path.join(UI.Ortho4XP_dir,"Utils","nvcompress","nvcompress.app") 
    gdal_transl_cmd = 'gdal_translate'
    devnull_rdir    = " >/dev/null 2>&1"
elif 'win' in sys.platform: 
    dds_convert_cmd = os.path.join(UI.Ortho4XP_dir, "Utils", "nvcompress", "nvcompress.exe") 
    gdal_transl_cmd = 'gdal_translate'
    devnull_rdir    = " > nul  2>&1"
else:
    dds_convert_cmd = "nvcompress" 
    gdal_transl_cmd = 'gdal_translate'
    devnull_rdir    = " >/dev/null 2>&1 "
    
###############################################################################################################################
#
#  PART I : Initialization of providers, extents, and color filters
#
###############################################################################################################################
   
providers_dict={}
combined_providers_dict={}
local_combined_providers_dict={}
extents_dict={'global':{}}
color_filters_dict={'none':[]}

def initialize_extents_dict():
    for dir_name in os.listdir(FNAMES.Extent_dir):
        if not os.path.isdir(os.path.join(FNAMES.Extent_dir,dir_name)):
            continue
        for file_name in os.listdir(os.path.join(FNAMES.Extent_dir,dir_name)):
            if '.' not in file_name or file_name.split('.')[-1]!='ext': continue
            extent_code=file_name.split('.')[0]
            extent={}
            f=open(os.path.join(FNAMES.Extent_dir,dir_name,file_name),'r')
            valid_extent=True
            for line in f.readlines():
                line=line[:-1]
                if "#" in line: line=line.split('#')[0]
                if ("=" not in line): continue
                try:
                    key=line.split("=")[0]
                    value=line[len(key)+1:]
                    extent[key]=value
                except:
                    print("Error for extent",extent_code,"in line",line)
                    continue
                # structuring data
                if key=='epsg_code':
                    try:
                        GEO.epsg[value]=GEO.pyproj.Proj(init='epsg:'+value)
                    except:
                        print("Error in epsg code for extent",extent_code)
                        valid_extent=False
                elif key=='mask_bounds':
                    try:
                        extent[key]=[float(x) for x in value.split(",")]
                    except:
                        print("Error in reading mask bounds for extent",extent_code)
                        valid_extent=False
            if valid_extent:
                extent['code']=extent_code
                extent['dir']=dir_name
                extents_dict[extent_code]=extent
            else:
                print("Error in reading extent definition file for",file_name)
                pass
            f.close()

def initialize_color_filters_dict():
    for file_name in os.listdir(FNAMES.Filter_dir):
            if '.' not in file_name or file_name.split('.')[-1]!='flt': continue
            color_code=file_name.split('.')[0]
            f=open(os.path.join(FNAMES.Filter_dir,file_name),'r')
            valid_color_filters=True
            color_filters=[]
            for line in f.readlines():
                line=line[:-1]
                if "#" in line: line=line.split('#')[0]
                if not line: continue
                try:
                    items=line.split()            
                    color_filters.append([items[0]]+[float(x) for x in items[1:]])
                except:
                    valid_color_filters=False
            if valid_color_filters:
                color_filters_dict[color_code]=color_filters
            else:
                print("Could not understand color filter ",color_code,", skipping it.") 
                pass
            f.close()

# Look for lay files
def initialize_providers_dict():
    for dir_name in os.listdir(FNAMES.Provider_dir):
        if not os.path.isdir(os.path.join(FNAMES.Provider_dir,dir_name)):
            continue
        for file_name in os.listdir(os.path.join(FNAMES.Provider_dir,dir_name)):
            if '.' not in file_name or file_name.split('.')[-1]!='lay': continue
            provider_code=file_name.split('.')[0]
            provider={}
            f=open(os.path.join(FNAMES.Provider_dir,dir_name,file_name),'r')
            valid_provider=True
            for line in f.readlines():
                line=line[:-1]
                if "#" in line:
                    if line[0]=="#": 
                        continue
                    else:
                        line=line.split('#')[0]
                if ("=" not in line): continue
                try:
                    key=line.split("=")[0]
                    value=line[len(key)+1:]
                    provider[key]=value
                except:
                    UI.vprint(0,"Error for provider",provider_code,"in line",line)
                    continue
                # structuring data
                if key=='request_type' and value not in ['wms','wmts','tms','local_tms']:
                    UI.vprint(0,"Unknown request_type field for provider",provider_code,":",value)
                    valid_provider=False
                if key=='grid_type' and value not in ['webmercator']:
                    UI.vprint(0,"Unknown grid_type field for provider",provider_code,":",value)
                    valid_provider=False
                elif key=='fake_headers':
                    try:
                        provider[key]=eval(value)
                        if type(provider[key]) is not dict:
                            print("Definition of fake headers for provider",provider_code,"not valid.")
                            valid_provider=False
                    except:
                        print("Definition of fake headers for provider",provider_code,"not valid.")
                        valid_provider=False
                elif key=='epsg_code':
                    try:
                        GEO.epsg[value]=GEO.pyproj.Proj(init='epsg:'+value)
                    except:
                        UI.vprint(0,"Error in epsg code for provider",provider_code)
                        valid_provider=False
                elif key=='image_type':
                    pass
                elif key=='url_prefix':
                    pass
                elif key=='url_template':
                    pass
                elif key=='layers':
                    pass
                elif key in ['wms_size','tile_size']:
                    try:
                        provider[key]=int(value)
                        if provider[key]<100 or provider[key]>10000:
                            print("Wm(t)s size for provider ",provider_code,"seems off limits, provider skipped.")
                    except:
                        print("Error in reading wms size for provider",provider_code)
                        valid_provider=False
                elif key in ['wms_version','wmts_version']:
                    if len(value.split('.'))<2: 
                        print("Error in reading wms version for provider",provider_code)
                        valid_provider=False
                elif key=='top_left_corner':
                    try:
                        provider[key]=[numpy.array([float(x) for x in value.split()]) for _ in range(40)]
                    except:
                        print("Error in reading top left corner for provider",provider_code)
                        valid_provider=False
                elif key=='scaledenominator':
                    try:
                        provider[key]=numpy.array([float(x) for x in value.split()])
                    except:
                        print("Error in reading scaledenominator for provider",provider_code)
                        valid_provider=False
                elif key == 'tilematrixset':
                    pass
                elif key=='resolutions':
                    try:
                        provider[key]=numpy.array([float(x) for x in value.split()])
                    except:
                        print("Error in reading resolutions for provider",provider_code)
                        valid_provider=False
                elif key=='max_threads':
                    try:
                        provider[key]=int(value)
                    except:
                        pass            
                elif key=='extent':
                    pass
                elif key=='color_filters':
                    pass
                elif key=='imagery_dir':
                   pass
            if 'request_type' in provider and provider['request_type']=='wmts':
                try: 
                    tilematrixsets=read_tilematrixsets(os.path.join(FNAMES.Provider_dir,dir_name,'capabilities.xml'))
                    tms_found=False
                    for tilematrixset in tilematrixsets:
                        if tilematrixset['identifier']==provider['tilematrixset']:
                            provider['tilematrixset']=tilematrixset
                            tms_found=True
                            break
                    if tms_found: 
                        provider['scaledenominator']=numpy.array([float(x['ScaleDenominator']) for x in provider['tilematrixset']['tilematrices']]) 
                        provider['top_left_corner']=[[float(x) for x in y['TopLeftCorner'].split()] for y in provider['tilematrixset']['tilematrices']] 
                    else:
                        print("no tilematrixset found")  
                        valid_provider=False
                except:
                    print("Error in reading capabilities for provider",provider_code) 
            if valid_provider:
                provider['code']=provider_code
                provider['directory']=dir_name
                if 'image_type' not in provider: 
                    provider['image_type']='jpeg'
                if 'extent' not in provider: 
                    provider['extent']='global'
                if 'color_filters' not in provider: 
                    provider['color_filters']='none'
                if 'imagery_dir' not in provider:
                    provider['imagery_dir']='grouped'
                if 'scaledenominator' in provider:
                    units_per_pix=0.00028 if provider['epsg_code'] not in ['4326'] else 2.5152827955e-09 
                    provider['resolutions']=units_per_pix*provider['scaledenominator']
                if 'grid_type' in provider and provider['grid_type']=='webmercator':
                    provider['request_type']='tms'
                    provider['tile_size']=256
                    provider['epsg_code']='3857'
                    provider['top_left_corner']=[[-20037508.34, 20037508.34] for i in range(0,21)]
                    provider['resolutions']=numpy.array([20037508.34/(128*2**i) for i in range(0,21)])
                providers_dict[provider_code]=provider
            else:
                UI.vprint("Error in reading provider definition file for",file_name)
                pass
            f.close()

def initialize_combined_providers_dict():   
    for file_name in os.listdir(FNAMES.Provider_dir):
        if '.' not in file_name or file_name.split('.')[-1]!='comb': continue
        provider_code=file_name.split('.')[0]
        try:
            comb_list=[]
            f=open(os.path.join(FNAMES.Provider_dir,file_name),'r')
            for line in f.readlines():
                if '#' in line: line=line.split('#')[0]
                if not line[:-1]: continue
                layer_code,extent_code,color_code,priority=line[:-1].split()
                if layer_code not in providers_dict:
                    print("Unknown provider in combined provider",provider_code,":",layer_code)
                    continue
                if extent_code=='default':
                    extent_code=providers_dict[layer_code]['extent']
                if extent_code not in extents_dict:
                    print("Unknown extent in combined provider",provider_code,":",extent_code)
                    continue
                if color_code=='default':
                    color_code=providers_dict[layer_code]['color_filters']
                if color_code not in color_filters_dict:
                    print("Unknown color filter in combined provider",provider_code,":",color_code)
                    continue
                if priority not in ['low','medium','high','mask']:
                    print("Unknown priority in combined provider",provider_code,":",priority)
                    continue
                comb_list.append({'layer_code':layer_code,'extent_code':extent_code,'color_code':color_code,'priority':priority})
            f.close()
            if comb_list:
                combined_providers_dict[provider_code]=comb_list
            else:
                print("Combined provider",provider_code,"did not contained valid providers, skipped.")
        except:
            print("Error reading definition of combined provider",provider_code)
                

def initialize_local_combined_providers_dict(tile):
    # This function will select from list of providers the only
    # ones whose coverage intersect the given tile.
    global local_combined_providers_dict
    UI.vprint(1,"-> Initializing providers with potential data on this tile.")
    local_combined_providers_dict={} 
    test_set=set([tile.default_website])
    for region in tile.zone_list[:]:
        test_set.add(region[2])
    for provider_code in test_set.intersection(combined_providers_dict):
            comb_list=[]
            for rlayer in combined_providers_dict[provider_code]:
                if has_data((tile.lon,tile.lat+1,tile.lon+1,tile.lat),rlayer['extent_code'],is_mask_layer=(tile.lat,tile.lon,tile.mask_zl) if rlayer['priority']=='mask' else False):
                    comb_list.append(rlayer)
            if comb_list:
                local_combined_providers_dict[provider_code]=comb_list
            else:
                UI.vprint(1,"Combined provider",provider_code,"did not contained data for this tile, skipping it.")
                tile.zone_list.remove(region)
    UI.vprint(2,"     Done.")
    return
    
def read_tilematrixsets(file_name):
    f=open(file_name,'r')
    def xml_decode(line):
        field=line.split('<')[1].split('>')[0]
        str_value=line.split('>')[1].split('<')[0]
        return [field,str_value]
    tilematrixsets=[]
    line=f.readline()
    while line:
        if line.strip()=='<TileMatrixSet>':
            tilematrixset={}
            tilematrixset['tilematrices']=[]
            line=f.readline()
            while not line.strip()=='</TileMatrixSet>':
                if line.strip()=='<TileMatrix>':
                    tilematrix={}
                    line=f.readline()
                    while not line.strip()=='</TileMatrix>':
                        field,str_value=xml_decode(line)
                        if 'Identifier' in field: field='identifier'
                        tilematrix[field]=str_value
                        line=f.readline()
                    tilematrixset['tilematrices'].append(tilematrix)
                elif 'Identifier' in line:
                    field,str_value=xml_decode(line)
                    tilematrixset['identifier']=str_value
                line=f.readline()
            tilematrixsets.append(tilematrixset)
        else:
            pass
        line=f.readline()
    f.close()
    return tilematrixsets

def has_data(bbox,extent_code,return_mask=False,mask_size=(4096,4096),is_sharp_resize=False,is_mask_layer=False):
    # This function checks wether a given provider has data instersecting the given bbox. 
    # IMPORTANT : THE EXTENT AND THE BBOX NEED TO BE USING THE SAME REFERENCE FRAME (e.g. ESPG CODE) 
    # It returns either False or True or (in the latter case) the mask image over the bbox and properly resized accroding to input parameter.
    # is_sharp_resize determined if the upsamplique of the extent mask is nearest (good when sharp transitions are ) or bicubic (good in all other cases)
    # is_mask_layer (assuming EPSG:4326) allows to "multiply" extent masks with water masks, this is a smooth alternative for the old sea_texture_params. 
    # IMPORTANT TOO : (x0,y0) is the top-left corner, (x1,y1) is the bottom-right
    (x0,y0,x1,y1)=bbox
    try:
        # global layers need special treatment 
        if extent_code=='global' and (not is_mask_layer or (x1-x0)==1):
            return (not return_mask) or Image.new('L',mask_size,'white')
        if extent_code[0]=='!': 
            extent_code=extent_code[1:]
            negative=True 
        else:
            negative=False 
        (xmin,ymin,xmax,ymax)=extents_dict[extent_code]['mask_bounds'] if extent_code!='global' else (-180,-90,180,90)
        if x0>xmax or x1<xmin or y0<ymin or y1>ymax:
            return negative
        if not is_mask_layer:
            mask_im=Image.open(os.path.join(FNAMES.Extent_dir,extents_dict[extent_code]['dir'],extents_dict[extent_code]['code']+".png")).convert("L")
            (sizex,sizey)=mask_im.size
            pxx0=int((x0-xmin)/(xmax-xmin)*sizex)
            pxx1=int((x1-xmin)/(xmax-xmin)*sizex)
            pxy0=int((ymax-y0)/(ymax-ymin)*sizey)
            pxy1=int((ymax-y1)/(ymax-ymin)*sizey)
            mask_im=mask_im.crop((pxx0,pxy0,pxx1,pxy1))
            if negative: mask_im=ImageOps.invert(mask_im)
            if not mask_im.getbbox():
                return False
            if not return_mask:
                return True
            if is_sharp_resize:
                return mask_im.resize(mask_size)
            else:
                return mask_im.resize(mask_size,Image.BICUBIC)
        else:
            # following code only visited when is_mask_layer is True
            # in which case it is passed as (lat,lon)
            # check if sea mask file exists
            (lat,lon, mask_zl)=is_mask_layer
            (m_tilx,m_tily)=GEO.wgs84_to_orthogrid((y0+y1)/2,(x0+x1)/2,mask_zl)
            if not os.path.isfile(os.path.join(FNAMES.mask_dir(lat,lon),FNAMES.legacy_mask(m_tilx,m_tily))):
                return False
            # build extent mask_im
            if extent_code!='global':
                mask_im=Image.open(os.path.join(FNAMES.Extent_dir,extents_dict[extent_code]['dir'],extents_dict[extent_code]['code']+".png")).convert("L")
                (sizex,sizey)=mask_im.size
                pxx0=int((x0-xmin)/(xmax-xmin)*sizex)
                pxx1=int((x1-xmin)/(xmax-xmin)*sizex)
                pxy0=int((ymax-y0)/(ymax-ymin)*sizey)
                pxy1=int((ymax-y1)/(ymax-ymin)*sizey)
                mask_im=mask_im.crop((pxx0,pxy0,pxx1,pxy1))
                if negative: mask_im=ImageOps.invert(mask_im)
                if not mask_im.getbbox():
                    return False
                if is_sharp_resize:
                    mask_im=mask_im.resize(mask_size)
                else:
                    mask_im=mask_im.resize(mask_size,Image.BICUBIC)
            else:
                mask_im=Image.new('L',mask_size,'white')
            # build sea mask_im2    
            (ymax,xmin)=GEO.gtile_to_wgs84(m_tilx,m_tily,mask_zl)
            (ymin,xmax)=GEO.gtile_to_wgs84(m_tilx+16,m_tily+16,mask_zl)
            mask_im2=Image.open(os.path.join(FNAMES.mask_dir(lat,lon),FNAMES.legacy_mask(m_tilx,m_tily))).convert("L")
            (sizex,sizey)=mask_im2.size
            pxx0=int((x0-xmin)/(xmax-xmin)*sizex)
            pxx1=int((x1-xmin)/(xmax-xmin)*sizex)
            pxy0=int((ymax-y0)/(ymax-ymin)*sizey)
            pxy1=int((ymax-y1)/(ymax-ymin)*sizey)
            mask_im2=mask_im2.crop((pxx0,pxy0,pxx1,pxy1)).resize(mask_size,Image.BICUBIC)
            # invert it 
            mask_array2=255-numpy.array(mask_im2,dtype=numpy.uint8)
            # let full sea down (if you wish to...)
            # mask_array2[mask_array2==255]=0
            # combine (multiply) both
            mask_array=numpy.array(mask_im,dtype=numpy.uint16)
            mask_array=(mask_array*mask_array2/255).astype(numpy.uint8)
            mask_im = Image.fromarray(mask_array).convert('L')
            if not mask_im.getbbox():
                return False
            if not return_mask:
                return True
            return mask_im
    except Exception as e:
        UI.vprint(1,"Could not test coverage of ",extent_code," !!!")
        UI.vprint(2,e)
        return False


###############################################################################################################################
#
#  PART II : Methods to download and build textures
#
###############################################################################################################################

###############################################################################################################################
def http_request_to_image(width,height,url,request_headers,http_session):
    UI.vprint(3,"HTTP request issued :",url)
    tentative_request=0
    tentative_image=0
    r=False
    while True:
        try:
            if request_headers:
                r=http_session.get(url, timeout=http_timeout,headers=request_headers) 
            else:
                r=http_session.get(url, timeout=http_timeout) 
            status_code = str(r)   
            if ('[200]' in status_code) and ('image' in r.headers['Content-Type']):
                try:
                    small_image=Image.open(io.BytesIO(r.content))
                    return (1,small_image)
                except:
                    UI.vprint(2,"Server said 'OK', but the received image was corrupted.")
                    UI.vprint(3,url,r.headers)
            elif ('[404]' in status_code):
                UI.vprint(2,"Server said 'Not Found'")
                UI.vprint(3,url,r.headers)
                break
            elif ('[200]' in status_code):
                UI.vprint(2,"Server said 'OK' but sent us the wrong Content-Type.")
                UI.vprint(3,url,r.headers,r.content)
                break
            elif ('[403]' in status_code):
                UI.vprint(2,"Server said 'Forbidden' ! (IP banned?)")
                UI.vprint(3,url,r.headers,r.content)
                break
            elif ('[5' in status_code):      
                UI.vprint(2,"Server said 'Internal Error'.",status_code)
                if not check_tms_response:
                    break 
                time.sleep(2)
            else:
                UI.vprint(2,"Unmanaged Server answer:",status_code)
                UI.vprint(3,url,r.headers)
                break
            if UI.red_flag: return (0,'Stopped')
            tentative_image+=1  
        except requests.exceptions.RequestException as e: 
            status_code='Connection failure'   
            UI.vprint(2,"Server could not be connected, retrying in 2 secs")
            UI.vprint(3,e)
            if not check_tms_response:
                break
            # trying a new session ? 
            http_session=requests.Session()
            time.sleep(2)
            if UI.red_flag: return (0,'Stopped')
            tentative_request+=1
        if tentative_request==max_connect_retries or tentative_image==max_baddata_retries: 
            break 
    return (0,status_code)
###############################################################################################################################

###############################################################################################################################
def get_wms_image(bbox,width,height,provider,http_session):
    if has_URL and provider['code'] in URL.custom_url_list:
        url=URL.custom_url_request(bbox,width,height,provider)
    else:
        (minx,maxy,maxx,miny)=bbox
        if provider['wms_version'].split('.')[1]=="3":
            bbox_string=str(miny)+','+str(minx)+','+str(maxy)+','+str(maxx)
            _RS='CRS'
        else:
            bbox_string=str(minx)+','+str(miny)+','+str(maxx)+','+str(maxy) 
            _RS='SRS' 
        url=provider['url_prefix']+"SERVICE=WMS&VERSION="+provider['wms_version']+"&FORMAT=image/"+provider['image_type']+\
                "&REQUEST=GetMap&LAYERS="+provider['layers']+"&STYLES=&"+_RS+"=EPSG:"+str(provider['epsg_code'])+\
                "&WIDTH="+str(width)+"&HEIGHT="+str(height)+\
                "&BBOX="+bbox_string 
    if 'fake_headers' in provider:
        request_headers=provider['fake_headers']
    else:
        request_headers=request_headers_generic 
    (success,data)=http_request_to_image(width,height,url,request_headers,http_session)
    if success: 
        return (1,data) 
    else:
        return (0,Image.new('RGB',(width,height),'white'))
###############################################################################################################################

###############################################################################################################################
def get_wmts_image(tilematrix,til_x,til_y,provider,http_session):
  til_x_orig,til_y_orig=til_x,til_y
  down_sample=0
  while True:   
    if provider['request_type']=='tms': # TMS
        url=provider['url_template'].replace('{zoom}',str(tilematrix))
        url=url.replace('{x}',str(til_x)) 
        url=url.replace('{y}',str(til_y))
        url=url.replace('{|y|}',str(abs(til_y)-1))
        url=url.replace('{-y}',str(2**tilematrix-1-til_y))
        url=url.replace('{quadkey}',GEO.gtile_to_quadkey(til_x,til_y,tilematrix))
        url=url.replace('{xcenter}',str((til_x+0.5)*provider['resolutions'][tilematrix]*provider['tile_size']+provider['top_left_corner'][tilematrix][0]))
        url=url.replace('{ycenter}',str(-1*(til_y+0.5)*provider['resolutions'][tilematrix]*provider['tile_size']+provider['top_left_corner'][tilematrix][1]))
        url=url.replace('{size}',str(int(provider['resolutions'][tilematrix]*provider['tile_size'])))
        if '{switch:' in url:
            (url_0,tmp)=url.split('{switch:')
            (tmp,url_2)=tmp.split('}')
            server_list=tmp.split(',')
            url_1=random.choice(server_list).strip()
            url=url_0+url_1+url_2 
    elif provider['request_type']=='wmts': # WMTS
        url=provider['url_prefix']+"&SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetTile&LAYER="+\
            provider['layers']+"&STYLE=&FORMAT=image/"+provider['image_type']+"&TILEMATRIXSET="+provider['tilematrixset']['identifier']+\
            "&TILEMATRIX="+provider['tilematrixset']['tilematrices'][tilematrix]['identifier']+"&TILEROW="+str(til_y)+"&TILECOL="+str(til_x)
    elif provider['request_type']=='local_tms':  # LOCAL TMS
        url_local=provider['url_template'].replace('{x}',str(5*til_x).zfill(4)) # ! Too much specific, needs to be changed by a x,y-> file_name lambda fct
        url_local=url_local.replace('{y}',str(-5*til_y).zfill(4))
        if os.path.isfile(url_local):
            return (1,Image.open(url_local))
        else:
            UI.vprint(2,"! File ",url_local,"absent, using white texture instead !")
            return (0,Image.new('RGB',(provider['tile_size'],provider['tile_size']),'white'))
    if 'fake_headers' in provider:
        request_headers=provider['fake_headers']
    else:
        request_headers=request_headers_generic
    width=height=provider['tile_size'] 
    (success,data)=http_request_to_image(width,height,url,request_headers,http_session)
    if success and not down_sample: 
        return (success,data) 
    elif success and down_sample:
        x0=(til_x_orig-2**down_sample*til_x)*width//(2**down_sample)
        y0=(til_y_orig-2**down_sample*til_y)*height//(2**down_sample)
        x1=x0+width//(2**down_sample)
        y1=y0+height//(2**down_sample)
        return (success,data.crop((x0,y0,x1,y1)).resize((width,height),Image.BICUBIC)) 
    elif '[404]' in data:
        til_x=til_x//2
        til_y=til_y//2
        tilematrix-=1
        down_sample+=1 
        if down_sample>=6:
            return (0,Image.new('RGB',(width,height),'white'))
    else:
        return (0,Image.new('RGB',(width,height),'white'))
###############################################################################################################################

###############################################################################################################################
def get_and_paste_wms_part(bbox,width,height,provider,big_image,x0,y0,http_session):
    (success,small_image)=get_wms_image(bbox,width,height,provider,http_session)
    big_image.paste(small_image,(x0,y0))
    return success
###############################################################################################################################

###############################################################################################################################
def get_and_paste_wmts_part(tilematrix,til_x,til_y,provider,big_image,x0,y0,http_session,subt_size=None):
    (success,small_image)=get_wmts_image(tilematrix,til_x,til_y,provider,http_session)
    if not subt_size:
        big_image.paste(small_image,(x0,y0))
    else:
        big_image.paste(small_image.resize(subt_size,Image.BICUBIC),(x0,y0))
    return success
###############################################################################################################################

###############################################################################################################################
def build_texture_from_tilbox(tilbox,zoomlevel,provider,progress=None):
    # less general than the next build_texture_from_bbox_and_size but probably slightly quicker
    (til_x_min,til_y_min,til_x_max,til_y_max)=tilbox
    parts_x=til_x_max-til_x_min
    parts_y=til_y_max-til_y_min
    width=height=provider['tile_size']
    big_image=Image.new('RGB',(width*parts_x,height*parts_y)) 
    # we set-up the queue of downloads
    http_session=requests.Session() 
    download_queue=queue.Queue()
    for monty in range(0,parts_y):
        for montx in range(0,parts_x):
            x0=montx*width
            y0=monty*height
            fargs=(zoomlevel,til_x_min+montx,til_y_min+monty,provider,big_image,x0,y0,http_session)
            download_queue.put(fargs)
    # then the number of workers
    if 'max_threads' in provider: 
        max_threads=int(provider['max_threads'])
    else:
        max_threads=16
    # and finally activate them
    success=parallel_execute(get_and_paste_wmts_part,download_queue,max_threads,progress)
    # once out big_image has been filled and we return it
    return (success,big_image)
###############################################################################################################################

###############################################################################################################################
def build_texture_from_bbox_and_size(t_bbox,t_epsg,t_size,provider):
    # warp will be needed for projections not parallel to 3857
    # if warp is not needed, crop could still be needed if the grids do not match
    warp_needed=crop_needed=False
    (ulx,uly,lrx,lry)=t_bbox
    (t_sizex,t_sizey)=t_size 
    [s_ulx,s_uly]=GEO.transform(t_epsg,provider['epsg_code'],ulx,uly)
    [s_urx,s_ury]=GEO.transform(t_epsg,provider['epsg_code'],lrx,uly)
    [s_llx,s_lly]=GEO.transform(t_epsg,provider['epsg_code'],ulx,lry)
    [s_lrx,s_lry]=GEO.transform(t_epsg,provider['epsg_code'],lrx,lry)
    if s_ulx!=s_llx or s_uly!=s_ury or s_lrx!=s_urx or s_lly!=s_lry:
        s_ulx=min(s_ulx,s_llx)
        s_uly=max(s_uly,s_ury)
        s_lrx=max(s_urx,s_lrx)
        s_lry=min(s_lly,s_lry)
        warp_needed=True
    x_range=s_lrx-s_ulx
    y_range=s_uly-s_lry
    if provider['request_type']=='wms':
        wms_size=int(provider['wms_size'])
        parts_x=int(ceil(t_sizex/wms_size))
        width=wms_size
        parts_y=int(ceil(t_sizey/wms_size))
        height=wms_size
    elif provider['request_type'] in ('wmts','tms','local_tms'):
        asked_resol=max(x_range/t_sizex,y_range/t_sizey)
        wmts_tilematrix=numpy.argmax(provider['resolutions']<=asked_resol*1.1)
        wmts_resol=provider['resolutions'][wmts_tilematrix]   # in s_epsg unit per pix !
        UI.vprint(3,"Asked resol:",asked_resol,"WMTS resol:",wmts_resol)
        width=height=provider['tile_size']
        cell_size=wmts_resol*width
        [wmts_x0,wmts_y0]=provider['top_left_corner'][wmts_tilematrix]  
        til_x_min=int((s_ulx-wmts_x0)//cell_size)
        til_x_max=int((s_lrx-wmts_x0)//cell_size)
        til_y_min=int((wmts_y0-s_uly)//cell_size)
        til_y_max=int((wmts_y0-s_lry)//cell_size)
        parts_x=til_x_max-til_x_min+1
        parts_y=til_y_max-til_y_min+1
        s_box_ulx=wmts_x0+cell_size*til_x_min
        s_box_uly=wmts_y0-cell_size*til_y_min
        s_box_lrx=wmts_x0+cell_size*(til_x_max+1)
        s_box_lry=wmts_y0-cell_size*(til_y_max+1)
        if s_box_ulx!=s_ulx or s_box_uly!=s_uly or s_box_lrx!=s_lrx or s_box_lry!=s_lry:
            crop_x0=int(round((s_ulx-s_box_ulx)/wmts_resol))
            crop_y0=int(round((s_box_uly-s_uly)/wmts_resol))
            crop_x1=int(round((s_lrx-s_box_ulx)/wmts_resol))
            crop_y1=int(round((s_box_uly-s_lry)/wmts_resol))
            s_ulx=s_box_ulx    
            s_uly=s_box_uly    
            s_lrx=s_box_lrx
            s_lry=s_box_lry
            crop_needed=True
        downscale=int(min(log(width*parts_x/t_sizex),log(height/t_sizey))/log(2))-1
        if downscale>=1:
            width/=2**downscale
            height/=2**downscale
            subt_size=(width,height) 
        else:
            subt_size=None
    big_image=Image.new('RGB',(width*parts_x,height*parts_y)) 
    http_session=requests.Session()
    download_queue=queue.Queue()
    for monty in range(0,parts_y):
        for montx in range(0,parts_x):
            x0=montx*width
            y0=monty*height
            if provider['request_type']=='wms':
                p_ulx=s_ulx+montx*x_range/parts_x
                p_uly=s_uly-monty*y_range/parts_y
                p_lrx=p_ulx+x_range/parts_x
                p_lry=p_uly-y_range/parts_y
                p_bbox=[p_ulx,p_uly,p_lrx,p_lry]
                fargs=[p_bbox[:],width,height,provider,big_image,x0,y0,http_session]
            elif provider['request_type'] in ['wmts','tms','local_tms']:
                fargs=[wmts_tilematrix,til_x_min+montx,til_y_min+monty,provider,big_image,x0,y0,http_session,subt_size]
            download_queue.put(fargs)
    # We execute the downloads and subimage pastes
    if 'max_threads' in provider: 
        max_threads=int(provider['max_threads'])
    else:
        max_threads=16
    if provider['request_type']=='wms':
        success=parallel_execute(get_and_paste_wms_part,download_queue,max_threads)
    elif provider['request_type'] in ['wmts','tms','local_tms']:
        success=parallel_execute(get_and_paste_wmts_part,download_queue,max_threads)
    # We modify big_image if necessary
    if warp_needed:
        UI.vprint(3,"Warp needed")
        big_image=gdalwarp_alternative((s_ulx,s_uly,s_lrx,s_lry),provider['epsg_code'],big_image,t_bbox,t_epsg,t_size)
    elif crop_needed:
        UI.vprint(3,"Crop needed")
        big_image=big_image.crop((crop_x0,crop_y0,crop_x1,crop_y1))
    if big_image.size!=t_size:
        UI.vprint(3,"Resize needed:"+str(t_size[0]/big_image.size[0])+" "+str(t_size[1]/big_image.size[1]))
        big_image=big_image.resize(t_size,Image.BICUBIC)
    return (success,big_image)
###############################################################################################################################

###############################################################################################################################
def download_jpeg_ortho(file_dir,file_name,til_x_left,til_y_top,zoomlevel,provider_code,super_resol_factor=1):
    provider=providers_dict[provider_code]
    if 'super_resol_factor' in provider and super_resol_factor==1: super_resol_factor=int(provider['super_resol_factor'])
    width=height=int(4096*super_resol_factor)
    # we treat first the case of webmercator grid type servers
    if 'grid_type' in provider and provider['grid_type']=='webmercator':
        tilbox=[til_x_left,til_y_top,til_x_left+16,til_y_top+16] 
        tilbox_mod=[int(round(p*super_resol_factor)) for p in tilbox]
        zoom_shift=round(log(super_resol_factor)/log(2))
        (success,big_image)=build_texture_from_tilbox(tilbox_mod,zoomlevel+zoom_shift,provider)
    # if not we are in the world of epsg:3857 bboxes
    else:
        [latmax,lonmin]=GEO.gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        [latmin,lonmax]=GEO.gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
        [xmin,ymax]=GEO.transform('4326','3857',lonmin,latmax)
        [xmax,ymin]=GEO.transform('4326','3857',lonmax,latmin)
        (success,big_image)=build_texture_from_bbox_and_size([xmin,ymax,xmax,ymin],'3857',(width,height),provider)
    # if stop flag we do not wish to imprint a white texture
    if UI.red_flag: return 0
    if not success:
        UI.lvprint(1,"Part of image",file_name,"could not be obtained (even at lower ZL), it was filled with white there.")  
    if not os.path.exists(file_dir):
        os.makedirs(file_dir)
    try:
        if super_resol_factor==1:
            big_image.save(os.path.join(file_dir,file_name))
        else:
            big_image.resize((int(width/super_resol_factor),int(height/super_resol_factor)),Image.BICUBIC).save(os.path.join(file_dir,file_name))
    except Exception as e:
        UI.lvprint(0,"OS Error : could not save orthophoto on disk, received message :",e)
        return 0
    return 1
###############################################################################################################################

###############################################################################################################################
def build_jpeg_ortho(tile, til_x_left,til_y_top,zoomlevel,provider_code,out_file_name=''):
    texture_attributes=(til_x_left,til_y_top,zoomlevel,provider_code)
    if provider_code in local_combined_providers_dict:
        data_found=False
        for rlayer in local_combined_providers_dict[provider_code]:
            (y0,x0)=GEO.gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
            (y1,x1)=GEO.gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
            if has_data((x0,y0,x1,y1),rlayer['extent_code'],is_mask_layer= (tile.lat,tile.lon, tile.mask_zl) if rlayer['priority']=='mask' else False):
                data_found=True
                true_til_x_left=til_x_left
                true_til_y_top=til_y_top
                true_zl=zoomlevel
                if 'max_zl' in providers_dict[rlayer['layer_code']]:
                    max_zl=int(providers_dict[rlayer['layer_code']]['max_zl'])
                    if max_zl<zoomlevel:
                        (latmed,lonmed)=GEO.gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
                        (true_til_x_left,true_til_y_top)=GEO.wgs84_to_orthogrid(latmed,lonmed,max_zl)
                        true_zl=max_zl
                true_texture_attributes=(true_til_x_left,true_til_y_top,true_zl,rlayer['layer_code'])
                true_file_name=FNAMES.jpeg_file_name_from_attributes(true_til_x_left, true_til_y_top, true_zl,rlayer['layer_code'])
                true_file_dir=FNAMES.jpeg_file_dir_from_attributes(tile.lat, tile.lon,true_zl,providers_dict[rlayer['layer_code']])
                if not os.path.isfile(os.path.join(true_file_dir,true_file_name)):
                    UI.vprint(1,"   Downloading missing orthophoto "+true_file_name+" (for combining in "+provider_code+")")
                    if not download_jpeg_ortho(true_file_dir,true_file_name,*true_texture_attributes):
                        return 0
                else:
                    UI.vprint(1,"   The orthophoto "+true_file_name+" (for combining in "+provider_code+") is already present.")
        if not data_found: 
            UI.lvprint(1,"     -> !!! Warning : No data found for building the combined texture",\
                    FNAMES.dds_file_name_from_attributes(*texture_attributes)," !!!")
            return 0
        if out_file_name:
            big_img=combine_textures(tile,til_x_left,til_y_top,zoomlevel,provider_code)
            big_img.convert('RGB').save(out_file_name)
    elif provider_code in providers_dict:  
        file_name=FNAMES.jpeg_file_name_from_attributes(til_x_left, til_y_top, zoomlevel,provider_code)
        file_dir=FNAMES.jpeg_file_dir_from_attributes(tile.lat, tile.lon,zoomlevel,providers_dict[provider_code])
        if not os.path.isfile(os.path.join(file_dir,file_name)):
            UI.vprint(1,"   Downloading missing orthophoto "+file_name)
            if not download_jpeg_ortho(file_dir,file_name,*texture_attributes):
                return 0
        else:
            UI.vprint(1,"   The orthophoto "+file_name+" is already present.")
    else:
        (tlat,tlon)=GEO.gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
        UI.vprint(1,"   Unknown provider",provider_code,"or it has no data around",tlat,tlon,".")
        return 0
    return 1
###############################################################################################################################

###############################################################################################################################
# Not used in Ortho4XP itself but useful for testing combined color filters at low zl
###############################################################################################################################
def build_combined_ortho(tile, latp,lonp,zoomlevel,provider_code,mask_zl,filename='test.png'):
    initialize_color_filters_dict()
    initialize_extents_dict()
    initialize_providers_dict()
    initialize_combined_providers_dict()
    (til_x_left,til_y_top)=GEO.wgs84_to_orthogrid(latp,lonp,zoomlevel)
    for rlayer in combined_providers_dict[provider_code]:
        (y0,x0)=GEO.gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        (y1,x1)=GEO.gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
        if has_data((x0,y0,x1,y1),rlayer['extent_code']):
            true_til_x_left=til_x_left
            true_til_y_top=til_y_top
            true_zl=zoomlevel
            if 'max_zl' in providers_dict[rlayer['layer_code']]:
                max_zl=int(providers_dict[rlayer['layer_code']]['max_zl'])
                if max_zl<zoomlevel:
                    (latmed,lonmed)=GEO.gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
                    (true_til_x_left,true_til_y_top)=GEO.wgs84_to_orthogrid(latmed,lonmed,max_zl)
                    true_zl=max_zl
            true_texture_attributes=(true_til_x_left,true_til_y_top,true_zl,rlayer['layer_code'])
            true_file_name=FNAMES.jpeg_file_name_from_attributes(true_til_x_left, true_til_y_top, true_zl, provider_code)
            true_file_dir=FNAMES.jpeg_file_dir_from_attributes(tile.lat, tile.lon, true_zl, providers_dict[provider_code])
            if not os.path.isfile(os.path.join(true_file_dir,true_file_name)):
                UI.vprint(1,"   Downloading missing orthophoto "+true_file_name+" (for combining in "+provider_code+")\n")
                download_jpeg_ortho(true_file_dir,true_file_name,*true_texture_attributes)
            else:
                UI.vprint(1,"   The orthophoto "+true_file_name+" (for combining in "+provider_code+") is already present.\n")
    big_img=combine_textures(tile,til_x_left,til_y_top,zoomlevel,provider_code)
    big_img.save(filename)
###############################################################################################################################

###############################################################################################################################
def build_geotiffs(tile,texture_attributes_list):
    UI.red_flag=False
    timer=time.time()
    done=0
    todo=len(texture_attributes_list)
    for texture_attributes in texture_attributes_list:
        (til_x_left,til_y_top,zoomlevel,provider_code)=texture_attributes
        if build_jpeg_ortho(tile,til_x_left,til_y_top,zoomlevel,provider_code):
            convert_texture(tile,til_x_left,til_y_top,zoomlevel,provider_code,type='tif')
        done+=1
        UI.progress_bar(1,int(100*done/todo))
        if UI.red_flag: UI.exit_message_and_bottom_line() 
    UI.timings_and_bottom_line(timer)
    return
###############################################################################################################################

###############################################################################################################################
def build_texture_region(dest_dir,latmin,latmax,lonmin,lonmax,zoomlevel,provider_code):
    [til_xmin,til_ymin]=GEO.wgs84_to_orthogrid(latmax,lonmin,zoomlevel)
    [til_xmax,til_ymax]=GEO.wgs84_to_orthogrid(latmin,lonmax,zoomlevel)
    nbr_to_do=((til_ymax-til_ymin)/16+1)*((til_xmax-til_xmin)/16+1)
    print("Number of tiles to download at most : ",nbr_to_do)
    for til_y_top in range(til_ymin,til_ymax+1,16):
        for til_x_left in range(til_xmin,til_xmax+1,16):
            (y0,x0)=GEO.gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
            (y1,x1)=GEO.gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
            bbox_4326=(x0,y0,x1,y1)
            if has_data(bbox_4326,providers_dict[provider_code]['extent'],return_mask=False,mask_size=(4096,4096)):
                file_name=FNAMES.jpeg_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)
                if os.path.isfile(os.path.join(dest_dir,file_name)):
                    print("recycling one")
                    nbr_to_do-=1
                    continue 
                print("building one")
                download_jpeg_ortho(dest_dir,file_name,til_x_left,til_y_top,zoomlevel,provider_code,super_resol_factor=1)
            else:
                print("skipping one")
            nbr_to_do-=1
            print(nbr_to_do)
    return   
###############################################################################################################################

###############################################################################################################################
def build_provider_texture(dest_dir,provider_code,zoomlevel):
    (lonmin,latmin,lonmax,latmax)=extents_dict[providers_dict[provider_code]['extent']]['mask_bounds']
    build_texture_region(dest_dir,latmin,latmax,lonmin,lonmax,zoomlevel,provider_code)
    return   
###############################################################################################################################

###############################################################################################################################
def create_tile_preview(lat,lon,zoomlevel,provider_code):
    UI.red_flag=False
    if not os.path.exists(FNAMES.Preview_dir):
        os.makedirs(FNAMES.Preview_dir) 
    filepreview=FNAMES.preview(lat, lon, zoomlevel, provider_code)     
    if not os.path.isfile(filepreview):
        provider=providers_dict[provider_code]
        (til_x_min,til_y_min)=GEO.wgs84_to_gtile(lat+1,lon,zoomlevel)
        (til_x_max,til_y_max)=GEO.wgs84_to_gtile(lat,lon+1,zoomlevel)
        width=(til_x_max+1-til_x_min)*256
        height=(til_y_max+1-til_y_min)*256
        if 'grid_type' in provider and provider['grid_type']=='webmercator':
            tilbox=(til_x_min,til_y_min,til_x_max+1,til_y_max+1)
            dico_progress={'done':0,'bar':1}
            (success,big_image)=build_texture_from_tilbox(tilbox,zoomlevel,provider,progress=dico_progress)
        # if not we are in the world of epsg:3857 bboxes
        else:
            (latmax,lonmin)=GEO.gtile_to_wgs84(til_x_min,til_y_min,zoomlevel)
            (latmin,lonmax)=GEO.gtile_to_wgs84(til_x_max+1,til_y_max+1,zoomlevel)
            (xmin,ymax)=GEO.transform('4326','3857',lonmin,latmax)
            (xmax,ymin)=GEO.transform('4326','3857',lonmax,latmin)
            (success,big_image)=build_texture_from_bbox_and_size((xmin,ymax,xmax,ymin),'3857',(width,height),provider)
        if success: 
            big_image.save(filepreview)
            return 1
        else:
            try: big_image.save(filepreview)
            except: pass
            return 0
    return 1
###############################################################################################################################


###############################################################################################################################
#
#  PART II : Methods to transform textures (warp, color transform, combine)
#
###############################################################################################################################

###############################################################################################################################
def gdalwarp_alternative(s_bbox,s_epsg,s_im,t_bbox,t_epsg,t_size):
        [s_ulx,s_uly,s_lrx,s_lry]=s_bbox
        [t_ulx,t_uly,t_lrx,t_lry]=t_bbox
        (s_w,s_h)=s_im.size
        (t_w,t_h)=t_size
        t_quad = (0, 0, t_w, t_h)
        meshes = []
        def cut_quad_into_grid(quad, steps):
            w = quad[2]-quad[0]
            h = quad[3]-quad[1]
            x_step = w / float(steps)
            y_step = h / float(steps)
            y = quad[1]
            for k in range(steps):
                x = quad[0]
                for l in range(steps):
                    yield (int(x), int(y), int(x+x_step), int(y+y_step))
                    x += x_step
                y += y_step
        for quad in cut_quad_into_grid(t_quad,8):
            s_quad=[]
            for (t_pixx,t_pixy) in [(quad[0],quad[1]),(quad[0],quad[3]),(quad[2],quad[3]),(quad[2],quad[1])]:
                t_x=t_ulx+t_pixx/t_w*(t_lrx-t_ulx)
                t_y=t_uly-t_pixy/t_h*(t_uly-t_lry)
                (s_x,s_y)=GEO.transform(t_epsg,s_epsg,t_x,t_y)
                s_pixx=int(round((s_x-s_ulx)/(s_lrx-s_ulx)*s_w))    
                s_pixy=int(round((s_uly-s_y)/(s_uly-s_lry)*s_h))
                s_quad.extend((s_pixx,s_pixy))
            meshes.append((quad,s_quad))    
        return s_im.transform(t_size,Image.MESH,meshes,Image.BICUBIC)
###############################################################################################################################

###############################################################################################################################
def color_transform(im,color_code):
    for color_filter in color_filters_dict[color_code]:
        if color_filter[0]=='brightness-contrast': #both range from -127 to 127, http://gimp.sourcearchive.com/documentation/2.6.1/gimpbrightnesscontrastconfig_8c-source.html
            (brightness,contrast)=color_filter[1:3]
            if brightness>=0:  
                im=im.point(lambda i: 128+tan(pi/4*(1+contrast/128))*(brightness+(255-brightness)/255*i-128))
            else:
                im=im.point(lambda i: 128+tan(pi/4*(1+contrast/128))*((255+brightness)/255*i-128))
        elif color_filter[0]=='saturation':  
            saturation=color_filter[1]   
            im=ImageEnhance.Color(im).enhance(1+saturation/100)
        elif color_filter[0]=='sharpness':
            im=ImageEnhance.Sharpness(im).enhance(color_filter[1])
        elif color_filter[0]=='blur':
            im=im.filter(ImageFilter.GaussianBlur(color_filter[1]))
        elif color_filter[0]=='levels': # levels range between 0 and 255, gamma is neutral at 1 / https://pippin.gimp.org/image-processing/chap_point.html
            bands=im.split()
            for j in [0,1,2]:
               in_min,gamma,in_max,out_min,out_max=color_filter[5*j+1:5*j+6]
               bands[j].paste(bands[j].point(lambda i: out_min+(out_max-out_min)*((max(in_min,min(i,in_max))-in_min)/(in_max-in_min))**(1/gamma)))
            im=Image.merge(im.mode,bands)
    return im
###############################################################################################################################

###############################################################################################################################
def combine_textures(tile,til_x_left,til_y_top,zoomlevel,provider_code):
    big_image=Image.new('RGBA',(4096,4096))
    (y0,x0)=GEO.gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
    (y1,x1)=GEO.gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
    mask_weight_below=numpy.zeros((4096,4096),dtype=numpy.uint16)
    for rlayer in local_combined_providers_dict[provider_code][::-1]:
        mask=has_data((x0,y0,x1,y1),rlayer['extent_code'],return_mask=True,is_mask_layer=(tile.lat,tile.lon, tile.mask_zl) if rlayer['priority']=='mask' else False)
        if not mask: continue
        # we turn the image mask into an array 
        mask=numpy.array(mask,dtype=numpy.uint16)
        true_til_x_left=til_x_left
        true_til_y_top=til_y_top
        true_zl=zoomlevel
        crop=False
        if 'max_zl' in providers_dict[rlayer['layer_code']]:
            max_zl=int(providers_dict[rlayer['layer_code']]['max_zl'])
            if max_zl<zoomlevel:
                (latmed,lonmed)=GEO.gtile_to_wgs84(til_x_left+8,til_y_top+8,zoomlevel)
                (true_til_x_left,true_til_y_top)=GEO.wgs84_to_orthogrid(latmed,lonmed,max_zl)
                true_zl=max_zl
                crop=True
                pixx0=round(256*(til_x_left*2**(max_zl-zoomlevel)-true_til_x_left))
                pixy0=round(256*(til_y_top*2**(max_zl-zoomlevel)-true_til_y_top))
                pixx1=round(pixx0+2**(12-zoomlevel+max_zl))
                pixy1=round(pixy0+2**(12-zoomlevel+max_zl))
        true_file_name=FNAMES.jpeg_file_name_from_attributes(true_til_x_left, true_til_y_top, true_zl,rlayer['layer_code'])
        true_file_dir=FNAMES.jpeg_file_dir_from_attributes(tile.lat, tile.lon, true_zl,providers_dict[rlayer['layer_code']])
        true_im=Image.open(os.path.join(true_file_dir,true_file_name))
        UI.vprint(2,"Imprinting for provider",rlayer,til_x_left,til_y_top) 
        true_im=color_transform(true_im,rlayer['color_code'])  
        if rlayer['priority']=='mask' and tile.sea_texture_blur:
            UI.vprint(2,"Blur of a mask !")
            true_im=true_im.filter(ImageFilter.GaussianBlur(tile.sea_texture_blur*2**(true_zl-17)))
        if crop: 
            true_im=true_im.crop((pixx0,pixy0,pixx1,pixy1)).resize((4096,4096),Image.BICUBIC)
        # in case the smoothing of the extent mask was too strong we remove the
        # the mask (where it is nor 0 nor 255) the pixels for which the true_im
        # is all white
        # true_arr=numpy.array(true_im).astype(numpy.uint16)
        # mask[(numpy.sum(true_arr,axis=2)>=715)*(mask>=1)*(mask<=253)]=0
        # mask[(numpy.sum(true_arr,axis=2)<=15)*(mask>=1)*(mask<=253)]=0
        if rlayer['priority']=='low':
            # low priority layers, do not increase mask_weight_below
            wasnt_zero=(mask_weight_below+mask)!=0
            mask[wasnt_zero]=255*mask[wasnt_zero]/(mask_weight_below+mask)[wasnt_zero]
        elif rlayer['priority'] in ['high','mask']:
            mask_weight_below+=mask
        elif rlayer['priority']=='medium':
            not_zero=mask!=0
            mask_weight_below+=mask
            mask[not_zero]=255*mask[not_zero]/mask_weight_below[not_zero]
            # undecided about the next two lines
            # was_zero=mask_weight_below==0
            # mask[was_zero]=255 
        # we turn back the array mask into an image
        mask=Image.fromarray(mask.astype(numpy.uint8))
        big_image=Image.composite(true_im,big_image,mask)
    UI.vprint(2,"Finished imprinting",til_x_left,til_y_top)
    return big_image
###############################################################################################################################

###############################################################################################################################
def convert_texture(tile,til_x_left,til_y_top,zoomlevel,provider_code,type='dds'):
    if type=='dds':
        out_file_name=FNAMES.dds_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)
        png_file_name=out_file_name.replace('dds','png')
    elif type=='tif':
        out_file_name=FNAMES.geotiff_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)
        png_file_name=out_file_name.replace('tif','png')
    UI.vprint(1,"   Converting orthophoto(s) to build texture "+out_file_name+".")
    
    if provider_code in local_combined_providers_dict:
        big_image=combine_textures(tile,til_x_left,til_y_top,zoomlevel,provider_code)
        file_to_convert=os.path.join(UI.Ortho4XP_dir,'tmp',png_file_name)
        big_image.save(file_to_convert) 
        # If one wanted to distribute jpegs instead of dds, uncomment the next line
        # big_image.convert('RGB').save(os.path.join(tile.build_dir,'textures',out_file_name.replace('dds','jpg')),quality=70)
    # now if provider_code was not in local_combined_providers_dict but color correction is required
    elif providers_dict[provider_code]['color_filters']!='none':
        jpeg_file_name=FNAMES.jpeg_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)
        file_dir=FNAMES.jpeg_file_dir_from_attributes(tile.lat,tile.lon, zoomlevel, providers_dict[provider_code])
        big_image=Image.open(os.path.join(file_dir,jpeg_file_name),'r').convert('RGB')
        big_image=color_transform(big_image,providers_dict[provider_code]['color_filters'])
        file_to_convert=os.path.join(UI.Ortho4XP_dir,'tmp',png_file_name)
        big_image.save(file_to_convert) 
    # finally if nothing needs to be done prior to the conversion
    else:
        jpeg_file_name=FNAMES.jpeg_file_name_from_attributes(til_x_left,til_y_top,zoomlevel,provider_code)
        file_dir=FNAMES.jpeg_file_dir_from_attributes(tile.lat, tile.lon, zoomlevel, providers_dict[provider_code])
        file_to_convert=os.path.join(file_dir,jpeg_file_name)
    # eventually the dds conversion
    if type=='dds':
        conv_cmd=[dds_convert_cmd,'-bc1','-fast',file_to_convert,os.path.join(tile.build_dir,'textures',out_file_name),devnull_rdir]
    else:
        (latmax,lonmin)=GEO.gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
        (latmin,lonmax)=GEO.gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
        conv_cmd=[gdal_transl_cmd,'-of','Gtiff','-co','COMPRESS=JPEG','-a_ullr',str(lonmin),str(latmax),str(lonmax),str(latmin),'-a_srs','epsg:4326',file_to_convert,os.path.join(FNAMES.Geotiff_dir,out_file_name)] 
    tentative=0
    while True:
        if not subprocess.call(conv_cmd):
            break
        tentative+=1
        if tentative==10:
            UI.lvprint(1,"ERROR: Could not convert texture",os.path.join(tile.build_dir,'textures',out_file_name),"(10 tries)")
            break
        UI.lvprint(1,"WARNING: Could not convert texture",os.path.join(tile.build_dir,'textures',out_file_name))
        time.sleep(1)
    try: os.remove(os.path.join(UI.Ortho4XP_dir,'tmp',png_file_name))
    except: pass  
    return 
###############################################################################################################################

def geotag(input_file_name):
    suffix=input_file_name.split('.')[-1]
    out_file_name=input_file_name.replace(suffix,'tiff')
    items=input_file_name.split('_')
    til_y_top=int(items[0])
    til_x_left=int(items[1])
    zoomlevel=int(items[-1][-6:-4])
    (latmax,lonmin)=GEO.gtile_to_wgs84(til_x_left,til_y_top,zoomlevel)
    (latmin,lonmax)=GEO.gtile_to_wgs84(til_x_left+16,til_y_top+16,zoomlevel)
    conv_cmd=[gdal_transl_cmd,'-of','Gtiff','-co','COMPRESS=JPEG','-a_ullr',str(lonmin),str(latmax),str(lonmax),str(latmin),'-a_srs','epsg:4326',input_file_name,out_file_name] 
    tentative=0
    while True:
        if not subprocess.call(conv_cmd):
            break
        tentative+=1
        if tentative==10:
            print("ERROR: Could not convert texture",out_file_name,"(10 tries)")
            break
        print("WARNING: Could not convert texture",out_file_name)
        time.sleep(1)
