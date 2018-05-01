import os
import time
import shutil
import queue
import threading
import O4_UI_Utils as UI
import O4_File_Names as FNAMES
import O4_Imagery_Utils as IMG
import O4_Vector_Map as VMAP
import O4_Mesh_Utils as MESH
import O4_Mask_Utils as MASK
import O4_DSF_Utils as DSF
import O4_Overlay_Utils as OVL
from O4_Parallel_Utils import parallel_launch, parallel_join

max_convert_slots=4 
skip_downloads=False
skip_converts=False

##############################################################################
def download_textures(tile,download_queue,convert_queue):
    UI.vprint(1,"-> Opening download queue.")
    done=0
    while True:
        texture_attributes=download_queue.get()
        if isinstance(texture_attributes,str) and texture_attributes=='quit':
            UI.progress_bar(2,100)
            break
        if IMG.build_jpeg_ortho(tile,*texture_attributes):
            done+=1
            UI.progress_bar(2,int(100*done/(done+download_queue.qsize()))) 
            convert_queue.put((tile,*texture_attributes))
        if UI.red_flag: UI.vprint(1,"Download process interrupted."); return 0
    if done: UI.vprint(1," *Download of textures completed.") 
    return 1
##############################################################################


##############################################################################
def build_tile(tile):
    if UI.is_working: return 0
    UI.is_working=1
    UI.red_flag=False
    UI.logprint("Step 3 for tile lat=",tile.lat,", lon=",tile.lon,": starting.")
    UI.vprint(0,"\nStep 3 : Building DSF/Imagery for tile "+FNAMES.short_latlon(tile.lat,tile.lon)+" : \n--------\n")
    
    if not os.path.isfile(FNAMES.mesh_file(tile.build_dir,tile.lat,tile.lon)):
        UI.lvprint(0,"ERROR: A mesh file must first be constructed for the tile!")
        UI.exit_message_and_bottom_line('')
        return 0

    timer=time.time()
    
    tile.write_to_config()
    
    IMG.initialize_local_combined_providers_dict(tile)

    try:
        if not os.path.exists(os.path.join(tile.build_dir,'Earth nav data',FNAMES.round_latlon(tile.lat,tile.lon))):
            os.makedirs(os.path.join(tile.build_dir,'Earth nav data',FNAMES.round_latlon(tile.lat,tile.lon)))
        if not os.path.isdir(os.path.join(tile.build_dir,'textures')):
            os.makedirs(os.path.join(tile.build_dir,'textures'))
        if UI.cleaning_level>1 and not tile.grouped:
            for f in os.listdir(os.path.join(tile.build_dir,'textures')):
                if f[-4:]!='.png': continue
                try: os.remove(os.path.join(tile.build_dir,'textures',f))
                except: pass
        if not tile.grouped:    
            try: shutil.rmtree(os.path.join(tile.build_dir,'terrain'))
            except: pass
        if not os.path.isdir(os.path.join(tile.build_dir,'terrain')):
            os.makedirs(os.path.join(tile.build_dir,'terrain'))
    except Exception as e: 
        UI.lvprint(0,"ERROR: Cannot create tile subdirectories.")
        UI.vprint(3,e)
        UI.exit_message_and_bottom_line('')
        return 0
    
    download_queue=queue.Queue()
    convert_queue=queue.Queue()
    build_dsf_thread=threading.Thread(target=DSF.build_dsf,args=[tile,download_queue])
    download_thread=threading.Thread(target=download_textures,args=[tile,download_queue,convert_queue])
    build_dsf_thread.start()
    if not skip_downloads:
        download_thread.start()
        if not skip_converts:
            UI.vprint(1,"-> Opening convert queue and",max_convert_slots,"conversion workers.")
            dico_conv_progress={'done':0,'bar':3}
            convert_workers=parallel_launch(IMG.convert_texture,convert_queue,max_convert_slots,progress=dico_conv_progress)
    build_dsf_thread.join()
    if not skip_downloads:
        download_queue.put('quit')
        download_thread.join()
        if not skip_converts:
            for _ in range(max_convert_slots): convert_queue.put('quit')
            parallel_join(convert_workers) 
            if UI.red_flag: 
                UI.vprint(1,"DDS conversion process interrupted.")
            elif dico_conv_progress['done']>=1: 
                UI.vprint(1," *DDS conversion of textures completed.")
    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    if UI.cleaning_level>1:
        try: os.remove(FNAMES.alt_file(tile))
        except: pass
        try: os.remove(FNAMES.input_node_file(tile))
        except: pass
        try: os.remove(FNAMES.input_poly_file(tile))
        except: pass
    if UI.cleaning_level>2:
        try: os.remove(FNAMES.mesh_file(tile.build_dir,tile.lat,tile.lon))
        except: pass
        try: os.remove(FNAMES.apt_file(tile))
        except: pass
    if UI.cleaning_level>1 and not tile.grouped:
        remove_unwanted_textures(tile)
    UI.timings_and_bottom_line(timer)
    UI.logprint("Step 3 for tile lat=",tile.lat,", lon=",tile.lon,": normal exit.")
    return 1
##############################################################################

##############################################################################
def build_all(tile):
    VMAP.build_poly_file(tile)
    if UI.red_flag: UI.exit_message_and_bottom_line(''); return 0
    MESH.build_mesh(tile)
    if UI.red_flag: UI.exit_message_and_bottom_line(''); return 0
    MASK.build_masks(tile)
    if UI.red_flag: UI.exit_message_and_bottom_line(''); return 0
    build_tile(tile)
    if UI.red_flag: UI.exit_message_and_bottom_line(''); return 0
    UI.is_working=0
    return 1
##############################################################################

##############################################################################
def build_tile_list(tile,list_lat_lon,do_osm,do_mesh,do_mask,do_dsf,do_ovl,do_ptc):
    if UI.is_working: return 0
    timer=time.time()
    UI.lvprint(0,"Batch build launched for a number of",len(list_lat_lon),"tiles.")
    k=0
    for (lat,lon) in list_lat_lon:
        k+=1
        UI.vprint(1,"Dealing with tile ",k,"/",len(list_lat_lon),":",FNAMES.short_latlon(lat,lon)) 
        (tile.lat,tile.lon)=(lat,lon)
        tile.build_dir=FNAMES.build_dir(tile.lat,tile.lon,tile.custom_build_dir)
        tile.dem=None
        if do_ptc: tile.read_from_config()
        if (do_osm or do_mesh or do_dsf): tile.make_dirs()
        if do_osm: VMAP.build_poly_file(tile)
        if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
        if do_mesh: MESH.build_mesh(tile)
        if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
        if do_mask: MASK.build_masks(tile)
        if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
        if do_dsf: build_tile(tile)
        if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
        if do_ovl: OVL.build_overlay(lat,lon)
        if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
    UI.lvprint(0,"Batch process completed in",UI.nicer_timer(time.time()-timer))
    return 1
##############################################################################

##############################################################################
def remove_unwanted_textures(tile):
    texture_list=[]
    for f in os.listdir(os.path.join(tile.build_dir,'terrain')):
        if f[-4:]!='.ter': continue
        texture_list.append('_'.join(f[:-4].split('_')[:3])+'.dds')
    for f in os.listdir(os.path.join(tile.build_dir,'textures')):   
        if f[-4:]!='.dds': continue
        if f not in texture_list:
            print("Removing obsolete texture",f)
            try: os.remove(os.path.join(tile.build_dir,'textures',f))
            except:pass
##############################################################################
