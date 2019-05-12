import os
import sys
import time
import queue
from math import  atan, ceil, floor 
import numpy
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import O4_DEM_Utils as DEM
import O4_File_Names as FNAMES
import O4_UI_Utils as UI
import O4_Geo_Utils as GEO
import O4_Imagery_Utils as IMG
import O4_OSM_Utils as OSM
import O4_Vector_Utils as VECT
import O4_Mesh_Utils as MESH
from O4_Parallel_Utils import parallel_execute

mask_altitude_above=0.5
masks_build_slots=4
##############################################################################
def needs_mask(tile, til_x_left,til_y_top,zoomlevel,*args):
    if int(zoomlevel)<tile.mask_zl:
        return False
    factor=2**(zoomlevel-tile.mask_zl)
    m_til_x=(int(til_x_left/factor)//16)*16
    m_til_y=(int(til_y_top/factor)//16)*16
    rx=int((til_x_left-factor*m_til_x)/16)
    ry=int((til_y_top-factor*m_til_y)/16)
    mask_file=os.path.join(FNAMES.mask_dir(tile.lat,tile.lon),FNAMES.legacy_mask(m_til_x,m_til_y))
    if not os.path.isfile(mask_file): 
        return False
    big_img=Image.open(mask_file)
    x0=int(rx*4096/factor)
    y0=int(ry*4096/factor)
    small_img=big_img.crop((x0,y0,x0+4096//factor,y0+4096//factor))
    small_array=numpy.array(small_img,dtype=numpy.uint8)
    if small_array.max()<=30: 
        return False
    else:
        return small_img
##############################################################################

##############################################################################
def build_masks(tile,for_imagery=False):
    if UI.is_working: return 0
    UI.is_working=1
    # Which grey level for inland water equivalent ?
    im=Image.open(os.path.join(FNAMES.Utils_dir,'water_transition.png'))
    sea_level=im.getpixel((0,127*(1-min(1,0.1+tile.ratio_water))))
    del(im)
    ##########################################
    def transition_profile(ratio,ttype):
        if ttype=='spline':
            return 3*ratio**2-2*ratio**3
        elif ttype=='linear':
            return ratio
        elif ttype=='parabolic':
            return 2*ratio-ratio**2
    ##########################################
    UI.red_flag=False
    UI.logprint("Step 2.5 for tile lat=",tile.lat,", lon=",tile.lon,": starting.")
    UI.vprint(0,"\nStep 2.5 : Building masks for tile "+FNAMES.short_latlon(tile.lat,tile.lon)+" : \n--------\n")
    timer=time.time()
    if not os.path.exists(FNAMES.mesh_file(tile.build_dir,tile.lat,tile.lon)):
        UI.lvprint(0,"ERROR: Mesh file ",FNAMES.mesh_file(tile.build_dir,tile.lat,tile.lon),"absent.")
        UI.exit_message_and_bottom_line(''); return 0
    dest_dir=FNAMES.mask_dir(tile.lat, tile.lon) if not for_imagery else os.path.join(FNAMES.mask_dir(tile.lat, tile.lon),"Combined_imagery")    
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    mesh_file_name_list=[]
    for close_lat in range(tile.lat-1,tile.lat+2):
        for close_lon in range(tile.lon-1,tile.lon+2):
            close_build_dir = tile.build_dir if tile.grouped else tile.build_dir.replace(FNAMES.tile_dir(tile.lat,tile.lon),FNAMES.tile_dir(close_lat,close_lon))
            close_mesh_file_name=FNAMES.mesh_file(close_build_dir,close_lat,close_lon)
            if os.path.isfile(close_mesh_file_name):
                mesh_file_name_list.append(close_mesh_file_name)
    ####################
    dico_masks={}
    dico_masks_inland={}
    ####################
    [til_x_min,til_y_min]=GEO.wgs84_to_orthogrid(tile.lat+1,tile.lon,tile.mask_zl)
    [til_x_max,til_y_max]=GEO.wgs84_to_orthogrid(tile.lat,tile.lon+1,tile.mask_zl)
    UI.vprint(1,"-> Deleting existing masks")
    for til_x in range(til_x_min,til_x_max+1,16):
        for til_y in range(til_y_min,til_y_max+1,16):
            try:
                os.remove(os.path.join(dest_dir, FNAMES.legacy_mask(til_x, til_y)))
            except:
                pass
    UI.vprint(1,"-> Reading mesh data")
    for mesh_file_name in mesh_file_name_list:
        try:
            f_mesh=open(mesh_file_name,"r")
            UI.vprint(1,"   * ",mesh_file_name)
        except:
            UI.lvprint(1,"Mesh file ",mesh_file_name," could not be read. Skipped.")
            continue
        mesh_version=float(f_mesh.readline().strip().split()[-1])
        has_water = 7 if mesh_version>=1.3 else 3
        for i in range(3):
            f_mesh.readline()
        nbr_pt_in=int(f_mesh.readline())
        pt_in=numpy.zeros(5*nbr_pt_in,'float')
        for i in range(0,nbr_pt_in):
            pt_in[5*i:5*i+3]=[float(x) for x in f_mesh.readline().split()[:3]]
        for i in range(0,3):
            f_mesh.readline()
        for i in range(0,nbr_pt_in):
            pt_in[5*i+3:5*i+5]=[float(x) for x in f_mesh.readline().split()[:2]]
        for i in range(0,2): # skip 2 lines
            f_mesh.readline()
        nbr_tri_in=int(f_mesh.readline()) # read nbr of tris
        step_stones=nbr_tri_in//100
        percent=-1
        UI.vprint(2," Attribution process of masks buffers to water triangles for "+str(mesh_file_name)+".")
        for i in range(0,nbr_tri_in):
            if i%step_stones==0:
                percent+=1
                UI.progress_bar(1, int(percent*5/10))
                if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
            (n1,n2,n3,tri_type)=[int(x)-1 for x in f_mesh.readline().split()[:4]]
            tri_type+=1
            if (not tri_type) or (not (tri_type & has_water)) or ((tri_type & has_water)<2 and not tile.use_masks_for_inland):
                continue
            (lon1,lat1)=pt_in[5*n1:5*n1+2]
            (lon2,lat2)=pt_in[5*n2:5*n2+2]
            (lon3,lat3)=pt_in[5*n3:5*n3+2]
            bary_lat=(lat1+lat2+lat3)/3
            bary_lon=(lon1+lon2+lon3)/3
            (til_x,til_y)=GEO.wgs84_to_orthogrid(bary_lat,bary_lon,tile.mask_zl)
            if til_x < til_x_min-16 or til_x > til_x_max+16 or til_y < til_y_min-16 or til_y>til_y_max+16:
                continue
            (til_x2,til_y2)=GEO.wgs84_to_orthogrid(bary_lat,bary_lon,tile.mask_zl+2)
            a=(til_x2//16)%4
            b=(til_y2//16)%4
            if (til_x,til_y) in dico_masks:
                dico_masks[(til_x,til_y)].append((lat1,lon1,lat2,lon2,lat3,lon3))
            else:
                dico_masks[(til_x,til_y)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
            if a==0: 
                if (til_x-16,til_y) in dico_masks:
                    dico_masks[(til_x-16,til_y)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                else:
                    dico_masks[(til_x-16,til_y)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
                if b==0: 
                    if (til_x-16,til_y-16) in dico_masks:
                        dico_masks[(til_x-16,til_y-16)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                    else:
                        dico_masks[(til_x-16,til_y-16)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
                elif b==3:
                    if (til_x-16,til_y+16) in dico_masks:
                        dico_masks[(til_x-16,til_y+16)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                    else:
                        dico_masks[(til_x-16,til_y+16)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
            elif a==3:
                if (til_x+16,til_y) in dico_masks:
                    dico_masks[(til_x+16,til_y)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                else:
                    dico_masks[(til_x+16,til_y)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
                if b==0: 
                    if (til_x+16,til_y-16) in dico_masks:
                        dico_masks[(til_x+16,til_y-16)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                    else:
                        dico_masks[(til_x+16,til_y-16)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
                elif b==3:
                    if (til_x+16,til_y+16) in dico_masks:
                        dico_masks[(til_x+16,til_y+16)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                    else:
                        dico_masks[(til_x+16,til_y+16)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
            if b==0: 
                if (til_x,til_y-16) in dico_masks:
                    dico_masks[(til_x,til_y-16)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                else:
                    dico_masks[(til_x,til_y-16)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
            elif b==3:
                if (til_x,til_y+16) in dico_masks:
                    dico_masks[(til_x,til_y+16)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                else:
                    dico_masks[(til_x,til_y+16)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
        f_mesh.close()
        if not tile.use_masks_for_inland:
            UI.vprint(2,"   Taking care of inland water near shoreline")
            f_mesh=open(mesh_file_name,"r")
            for i in range(0,4):
                f_mesh.readline()
            nbr_pt_in=int(f_mesh.readline())
            for i in range(0,2*nbr_pt_in+5):
                f_mesh.readline()
            nbr_tri_in=int(f_mesh.readline()) # read nbr of tris
            step_stones=nbr_tri_in//100
            percent=-1
            for i in range(0,nbr_tri_in):
                if i%step_stones==0:
                    percent+=1
                    UI.progress_bar(1, int(percent*5/10))
                    if UI.red_flag: UI.exit_message_and_bottom_line(); return 0
                (n1,n2,n3,tri_type)=[int(x)-1 for x in f_mesh.readline().split()[:4]]
                tri_type+=1
                if not (tri_type & has_water)==1:
                    continue
                (lon1,lat1)=pt_in[5*n1:5*n1+2]
                (lon2,lat2)=pt_in[5*n2:5*n2+2]
                (lon3,lat3)=pt_in[5*n3:5*n3+2]
                bary_lat=(lat1+lat2+lat3)/3
                bary_lon=(lon1+lon2+lon3)/3
                (til_x,til_y)=GEO.wgs84_to_orthogrid(bary_lat,bary_lon,tile.mask_zl)
                if til_x < til_x_min-16 or til_x > til_x_max+16 or til_y < til_y_min-16 or til_y>til_y_max+16:
                    continue
                (til_x2,til_y2)=GEO.wgs84_to_orthogrid(bary_lat,bary_lon,tile.mask_zl+2)
                a=(til_x2//16)%4
                b=(til_y2//16)%4
                # Here an inland water tri is added ONLY if sea water tri were already added for this mask extent
                if (til_x,til_y) in dico_masks:
                    if (til_x,til_y) in dico_masks_inland:
                        dico_masks_inland[(til_x,til_y)].append((lat1,lon1,lat2,lon2,lat3,lon3))
                    else:
                        dico_masks_inland[(til_x,til_y)]=[(lat1,lon1,lat2,lon2,lat3,lon3)]
            f_mesh.close()
    UI.vprint(1,"-> Construction of the masks")
    if tile.masks_use_DEM_too:
        try:
            fill_nodata = tile.fill_nodata or "to zero"
            source= ((";" in tile.custom_dem) and tile.custom_dem.split(";")[0]) or tile.custom_dem
            tile.dem=DEM.DEM(tile.lat,tile.lon,source,fill_nodata,info_only=False)
        except:
            UI.exit_message_and_bottom_line("\nERROR: Could not determine the appropriate eleva(tion source. Please check your custom_dem entry.")
            return 0
                
    masks_queue=queue.Queue()
    for key in dico_masks: masks_queue.put(key)
    dico_progress={'done':0,'bar':1}
    def build_mask(til_x,til_y):
        if til_x<til_x_min or til_x>til_x_max or til_y<til_y_min or til_y>til_y_max:
            return 1
        (latm0,lonm0)=GEO.gtile_to_wgs84(til_x,til_y,tile.mask_zl)
        (px0,py0)=GEO.wgs84_to_pix(latm0,lonm0,tile.mask_zl)
        px0-=1024
        py0-=1024
        # 1) We start with a black mask 
        mask_im=Image.new("L",(4096+2*1024,4096+2*1024),'black')
        mask_draw=ImageDraw.Draw(mask_im)
        # 2) We fill it with white over the extent of each tile around for which we had a mesh available
        for mesh_file_name in mesh_file_name_list:
            latlonstr=mesh_file_name.split('.mes')[-2][-7:]
            lathere=int(latlonstr[0:3])
            lonhere=int(latlonstr[3:7]) 
            (px1,py1)=GEO.wgs84_to_pix(lathere,lonhere,tile.mask_zl)
            (px2,py2)=GEO.wgs84_to_pix(lathere,lonhere+1,tile.mask_zl)
            (px3,py3)=GEO.wgs84_to_pix(lathere+1,lonhere+1,tile.mask_zl)
            (px4,py4)=GEO.wgs84_to_pix(lathere+1,lonhere,tile.mask_zl)
            px1-=px0; px2-=px0; px3-=px0; px4-=px0; py1-=py0; py2-=py0; py3-=py0; py4-=py0
            mask_draw.polygon([(px1,py1),(px2,py2),(px3,py3),(px4,py4)],fill='white')
        # 3a)  We overwrite the white part of the mask with grey (ratio_water dependent) where inland water was detected in the first part above   
        if (til_x,til_y) in dico_masks_inland:    
            for (lat1,lon1,lat2,lon2,lat3,lon3) in dico_masks_inland[(til_x,til_y)]:
                (px1,py1)=GEO.wgs84_to_pix(lat1,lon1,tile.mask_zl)
                (px2,py2)=GEO.wgs84_to_pix(lat2,lon2,tile.mask_zl)
                (px3,py3)=GEO.wgs84_to_pix(lat3,lon3,tile.mask_zl)
                px1-=px0; px2-=px0; px3-=px0; py1-=py0; py2-=py0; py3-=py0
                mask_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill=sea_level) #int(255*(1-tile.ratio_water)))   
        # 3b) We overwrite the white + grey part of the mask with black where sea water was detected in the first part above
        for (lat1,lon1,lat2,lon2,lat3,lon3) in dico_masks[(til_x,til_y)]:
            (px1,py1)=GEO.wgs84_to_pix(lat1,lon1,tile.mask_zl)
            (px2,py2)=GEO.wgs84_to_pix(lat2,lon2,tile.mask_zl)
            (px3,py3)=GEO.wgs84_to_pix(lat3,lon3,tile.mask_zl)
            px1-=px0; px2-=px0; px3-=px0; py1-=py0; py2-=py0; py3-=py0
            mask_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill='black')
        del(mask_draw)
        #mask_im=mask_im.convert("L") 
        img_array=numpy.array(mask_im,dtype=numpy.uint8)
        
        if tile.masks_use_DEM_too:
            #computing the part of the mask coming from the DEM: 
            (latmax,lonmin)= GEO.pix_to_wgs84(px0,py0,tile.mask_zl)
            (latmin,lonmax)= GEO.pix_to_wgs84(px0+6144,py0+6144,tile.mask_zl)
            (x03857,y03857)=GEO.transform('4326','3857',lonmin,latmax)
            (x13857,y13857)=GEO.transform('4326','3857',lonmax,latmin)
            ((lonmin,lonmax,latmin,latmax),demarr4326)=tile.dem.super_level_set(mask_altitude_above,(lonmin,lonmax,latmin,latmax))  
            if demarr4326.any():
                demim4326=Image.fromarray(demarr4326.astype(numpy.uint8)*255)
                del(demarr4326)
                s_bbox=(lonmin,latmax,lonmax,latmin)
                t_bbox=(x03857,y03857,x13857,y13857)
                demim3857=IMG.gdalwarp_alternative(s_bbox,'4326',demim4326,t_bbox,'3857',(6144,6144))
                demim3857=demim3857.filter(ImageFilter.GaussianBlur(0.3*2**(tile.mask_zl-14))) # slight increase of area
                dem_array=(numpy.array(demim3857,dtype=numpy.uint8)>0).astype(numpy.uint8)*255
                del(demim3857)
                del(demim4326)
                img_array=numpy.maximum(img_array,dem_array)
        
        custom_mask_array=numpy.zeros((4096,4096),dtype=numpy.uint8)
        if tile.masks_custom_extent:
            (latm1,lonm1)=GEO.gtile_to_wgs84(til_x+16,til_y+16,tile.mask_zl)
            bbox_4326=(lonm0,latm0,lonm1,latm1)
            masks_im=IMG.has_data(bbox_4326,tile.masks_custom_extent,True,mask_size=(4096,4096),is_sharp_resize=False,is_mask_layer=False)
            if masks_im:
                custom_mask_array=(numpy.array(masks_im,dtype=numpy.uint8)*(sea_level/255)).astype(numpy.uint8)
        
        if (img_array.max()==0) and (custom_mask_array.max()==0): # no need to test if the mask is all white since it would otherwise not be present in dico_mask
            UI.vprint(1,"   Skipping", FNAMES.legacy_mask(til_x, til_y))
            return 1
        else:
            UI.vprint(1,"   Creating", FNAMES.legacy_mask(til_x, til_y))
        # Blur of the mask
        pxscal=GEO.webmercator_pixel_size(tile.lat+0.5,tile.mask_zl)
        if tile.masking_mode=="sand":
            blur_width=int(tile.masks_width/pxscal)
        elif tile.masking_mode=="rocks":
            blur_width=tile.masks_width/(2*pxscal)
        elif tile.masking_mode=="3steps":
            blur_width=[L/pxscal for L in tile.masks_width]
        if tile.masking_mode=="sand" and blur_width: 
        # convolution with a hat function
            b_img_array=numpy.array(img_array)
            kernel=numpy.array(range(1,2*blur_width))
            kernel[blur_width:]=range(blur_width-1,0,-1)
            kernel=kernel/blur_width**2
            for i in range(0,len(b_img_array)):
                b_img_array[i]=numpy.convolve(b_img_array[i],kernel,'same')
            b_img_array=b_img_array.transpose() 
            for i in range(0,len(b_img_array)):
                b_img_array[i]=numpy.convolve(b_img_array[i],kernel,'same')
            b_img_array=b_img_array.transpose()
            b_img_array=2*numpy.minimum(b_img_array,127)   
            b_img_array=numpy.array(b_img_array,dtype=numpy.uint8)
        elif tile.masking_mode=="rocks" and blur_width: 
        # slight increase of the mask, then gaussian blur, nonlinear map and a tiny bit of smoothing again on a short scale along the shore
            b_img_array=(numpy.array(Image.fromarray(img_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(blur_width/1.7)),dtype=numpy.uint8)>0).astype(numpy.uint8)*255
            #blur it
            b_img_array=numpy.array(Image.fromarray(b_img_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(blur_width)),dtype=numpy.uint8)
            #nonlinear transform to make the transition quicker at the shore (gaussian is too flat) 
            gamma=2.5
            b_img_array=(((numpy.tan((b_img_array.astype(numpy.float32)-127.5)/128*atan(3))-numpy.tan(-127.5/128*atan(3)))\
                    *254/(2*numpy.tan(127.5/128*atan(3))))**gamma/(255**(gamma-1))).astype(numpy.uint8)
            #b_img_array=(1.4*(255-((256-b_img_array.astype(numpy.float32))/256.0)**0.2*255)).astype(numpy.uint8)
            #b_img_array=numpy.minimum(b_img_array,200)
            #still some slight smoothing at the shore
            b_img_array=numpy.maximum(b_img_array,numpy.array(Image.fromarray(img_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(2**(tile.mask_zl-14))),dtype=numpy.uint8))
        elif tile.masking_mode=="3steps": 
        # why trying something so complicated...
            transin=blur_width[0]
            midzone=blur_width[1]
            transout=blur_width[2]
            #print(transin,midzone,transout)
            shore_level=255
            b_img_array=b_mask_array=numpy.array(img_array)
            # First the transition at the shore
            # We go from shore_level to sea_level in transin meters
            stepsin=int(transin/3)
            for i in range(stepsin):
                value=shore_level+transition_profile((i+1)/stepsin,'parabolic')*(sea_level-shore_level)
                b_mask_array=(numpy.array(Image.fromarray(b_mask_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(1)),dtype=numpy.uint8)>0).astype(numpy.uint8)*255
                b_img_array[(b_img_array==0)*(b_mask_array!=0)]=value
                UI.vprint(2,value)
            # Next the intermediate zone at constant transparency
            sea_b_radius=midzone/3
            sea_b_radius_buffered=(midzone+transout)/3
            b_mask_array=(numpy.array(Image.fromarray(b_mask_array).convert("L").\
                filter(ImageFilter.GaussianBlur(sea_b_radius_buffered)),dtype=numpy.uint8)>0).astype(numpy.uint8)*255
            b_mask_array=(numpy.array(Image.fromarray(b_mask_array).convert("L").\
                filter(ImageFilter.GaussianBlur(sea_b_radius_buffered-sea_b_radius)),dtype=numpy.uint8)==255).astype(numpy.uint8)*255
            b_img_array[(b_img_array==0)*(b_mask_array!=0)]=sea_level
            # Finally the transition to the X-Plane sea
            # We go from sea_level to 0 in transout meters
            stepsout=int(transout/3)  
            for i in range(stepsout):
                value=sea_level*(1-transition_profile((i+1)/stepsout,'linear'))
                b_mask_array=(numpy.array(Image.fromarray(b_mask_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(1)),dtype=numpy.uint8)>0).astype(numpy.uint8)*255
                b_img_array[(b_img_array==0)*(b_mask_array!=0)]=value
                UI.vprint(2,value)
            # To smoothen the thresolding introduced above we do a global short extent gaussian blur
            b_img_array=numpy.array(Image.fromarray(b_img_array).convert("L").\
                    filter(ImageFilter.GaussianBlur(2)),dtype=numpy.uint8)
        else:
            # Just a (futile) copy
            b_img_array=numpy.array(img_array)
        
        # Ensure land is kept to 255 on the mask to avoid unecessary ones, crop to final size, and take the
        # max with the possible custom extent mask
        img_array=numpy.maximum((img_array>0).astype(numpy.uint8)*255,b_img_array)[1024:4096+1024,1024:4096+1024]
        img_array=numpy.maximum(img_array,custom_mask_array)

        if not (img_array.max()==0 or img_array.min()==255):
            masks_im=Image.fromarray(img_array)  #.filter(ImageFilter.GaussianBlur(3))
            masks_im.save(os.path.join(dest_dir,FNAMES.legacy_mask(til_x, til_y)))
            UI.vprint(2,"     Done.") 
        else:
            UI.vprint(1,"     Ends-up being discarded.")
        return 1
    parallel_execute(build_mask,masks_queue,masks_build_slots,progress=dico_progress)
    UI.progress_bar(1, 100)
    UI.timings_and_bottom_line(timer)
    UI.logprint("Step 2.5 for tile lat=",tile.lat,", lon=",tile.lon,": normal exit.")
    return
##############################################################################

##############################################################################
def triangulation_to_image(name,pixel_size,grid_size_or_bbox):
    f_node = open(name+'.1.node','r')
    nbr_pt=int(f_node.readline().split()[0])
    vertices=numpy.zeros(2*nbr_pt)
    for i in range(0,nbr_pt):
        # Triangle .node files have the node number in front
        vertices[2*i:2*i+2]=[float(x) for x in f_node.readline().split()[1:3]]
    f_node.close()
    xmin=vertices[::2].min()
    xmax=vertices[::2].max()
    ymin=vertices[1::2].min()
    ymax=vertices[1::2].max()
    if isinstance(grid_size_or_bbox,tuple): # bbox
        bbox = grid_size_or_bbox
        (xmin,ymin,xmax,ymax)=bbox
    else: # float
        grid_size = grid_size_or_bbox
        xmin=floor((xmin-grid_size)/grid_size)*grid_size
        xmax=ceil((xmax+grid_size)/grid_size)*grid_size
        ymin=floor((ymin-grid_size)/grid_size)*grid_size
        ymax=ceil((ymax+grid_size)/grid_size)*grid_size
    mask_im=Image.new("1",(int((xmax-xmin)/pixel_size),int((ymax-ymin)/pixel_size)))
    mask_draw=ImageDraw.Draw(mask_im)
    f_ele  = open(name+'.1.ele','r')
    nbr_tri=int(f_ele.readline().split()[0])
    for i in range(nbr_tri):
        (n1,n2,n3)=[int(x)-1 for x in f_ele.readline().split()[1:4]]
        (x1,y1)=vertices[2*n1:2*n1+2]
        (x2,y2)=vertices[2*n2:2*n2+2]
        (x3,y3)=vertices[2*n3:2*n3+2]
        (px1,py1)=[round((x1-xmin)/pixel_size),round((y1-ymin)/pixel_size)]
        (px2,py2)=[round((x2-xmin)/pixel_size),round((y2-ymin)/pixel_size)]
        (px3,py3)=[round((x3-xmin)/pixel_size),round((y3-ymin)/pixel_size)]
        try:
            mask_draw.polygon([(px1,py1),(px2,py2),(px3,py3)],fill='white')
        except:
            pass
    f_ele.close()
    return ((xmin,ymin,xmax,ymax),ImageOps.flip(mask_im).convert("L"))
##############################################################################

if __name__ == '__main__':
    UI.log=False
    UI.verbosity=2
    Syntax='Syntax :\n--------\n(PYTHON) extent_code  pixel_size buffer_size blur_size [OSM query] [EPSG code] [bbox_or_grid_size]\nAll three sizes in meters, \
            buffer_size can be negative too.\nIf OSM query is not used, data must be cached in an extent_code.osm.bz2 file. EPSG code defaults \
            to 4326, if it is used the OSM query needs to be used too.\n\nExample :(from a subdirectory of Extents)\
            \n---------\npython3 ../../src/O4_Mask_Utils.py Suisse  20 0 400 rel[\"admin_level\"=\"2\"][\"name:fr\"=\"Suisse\"]'
    nargs=len(sys.argv)
    if not nargs in (5,6,7,8):
        print(Syntax)
        sys.exit(1)
    name=sys.argv[1]
    cached_file_name=name+'.osm.bz2'
    if nargs==5 and not os.path.exists(cached_file_name):
        print(Syntax)
        sys.exit(1)
    if nargs in (6,7,8):
        query_tmp=sys.argv[5]
        query=''
        for char in query_tmp:
            if char=='[':
                query+='["'
            elif char==']':
                query+='"]'
            elif char in['=','~']:
                query+='"'+char+'"'
            else:
                query+=char
    else:
        query=None
    if nargs in (7,8):
        epsg_code=sys.argv[6]
    else:
        epsg_code='4326'
    if nargs==8:
        grid_size_or_bbox = eval(sys.argv[7])
    else:
        grid_size_or_bbox= 0.02 if epsg_code=='4326' else 2000 
    pixel_size=float(sys.argv[2])
    buffer_width=float(sys.argv[3])/pixel_size
    mask_width=int(int(sys.argv[4])/pixel_size)
    pixel_size = pixel_size/111120 if epsg_code=='4326' else pixel_size # assuming meters if not degrees
    vector_map=VECT.Vector_Map()
    osm_layer=OSM.OSM_layer()
    if not os.path.exists(cached_file_name):
        print("OSM query...")
        if not OSM.OSM_query_to_OSM_layer(query,'',osm_layer,'all',cached_file_name=cached_file_name):
            print("OSM query failed. Exiting.")
            del(vector_map)
            time.sleep(1)
            sys.exit(0)
    else:
        print("Recycling OSM file...")
        osm_layer.update_dicosm(cached_file_name,None)
    print("Transform to multipolygon...") 
    multipolygon_area=OSM.OSM_to_MultiPolygon(osm_layer,0,0)
    del(osm_layer)
    if not multipolygon_area.area:
        #try: os.remove(cached_file_name)
        #except: pass    
        print("Humm... an empty response. Are you sure about the exact OSM tag for your region ?")
        print("Exiting with no extent created.")
        del(vector_map)
        time.sleep(1)
        sys.exit(0)
    if epsg_code!='4326':
        name+='_'+epsg_code
        print("Changing coordinates to match EPSG code")
        import pyproj
        import shapely.ops
        s_proj=pyproj.Proj(init='epsg:4326')
        t_proj=pyproj.Proj(init='epsg:'+epsg_code)
        reprojection = lambda x, y: pyproj.transform(s_proj, t_proj, x, y)
        multipolygon_area=shapely.ops.transform(reprojection,multipolygon_area)

    vector_map.encode_MultiPolygon(multipolygon_area,VECT.dummy_alt,'DUMMY',check=True,cut=False)
    vector_map.write_node_file(name+'.node')
    vector_map.write_poly_file(name+'.poly')
    print("Triangulate...")
    MESH.triangulate(name,os.path.join(os.path.dirname(sys.argv[0]),'..'))
    ((xmin,ymin,xmax,ymax),mask_im)=triangulation_to_image(name,pixel_size,grid_size_or_bbox)
    print("Mask size : ",mask_im.size,"pixels.")
    buffer=''
    try:
        f=open(name+'.ext','r')
        for line in f.readlines():
            if ("#" not in line) or query: continue
            if "Initially" not in line:
                buffer+="# Initially c"+line[3:] 
            else:
                buffer+=line
        f.close()
    except:
        pass
    buffer+="# Created with : "+' '.join(sys.argv)+'\n'
    buffer+="mask_bounds="+str(xmin)+","+str(ymin)+","+str(xmax)+","+str(ymax)+"\n"
    f=open(name+'.ext','w')
    f.write(buffer)
    f.close()
    if buffer_width:
        UI.vprint(1,"Buffer of the mask...")
        mask_im=mask_im.filter(ImageFilter.GaussianBlur(buffer_width/4))
        if buffer_width>0:
            mask_im=Image.fromarray((numpy.array(mask_im,dtype=numpy.uint8)>0).astype(numpy.uint8)*255)
        else: # buffer width can be negative
            mask_im=Image.fromarray((numpy.array(mask_im,dtype=numpy.uint8)==255).astype(numpy.uint8)*255)
    if mask_width:
        mask_width+=1
        UI.vprint(1,"Blur of the mask...")
        img_array=numpy.array(mask_im,dtype=numpy.uint8)
        kernel=numpy.ones(int(mask_width))/int(mask_width)
        kernel=numpy.array(range(1,2*mask_width))
        kernel[mask_width:]=range(mask_width-1,0,-1)
        kernel=kernel/mask_width**2
        for i in range(0,len(img_array)):
            img_array[i]=numpy.convolve(img_array[i],kernel,'same')
        img_array=img_array.transpose() 
        for i in range(0,len(img_array)):
            img_array[i]=numpy.convolve(img_array[i],kernel,'same')
        img_array=img_array.transpose()
        img_array[img_array>=128]=255
        img_array[img_array<128]*=2  
        img_array=numpy.array(img_array,dtype=numpy.uint8)
        mask_im=Image.fromarray(img_array)
    mask_im.save(name+".png")
    for f in [name+'.poly',name+'.node',name+'.1.node',name+'.1.ele']:
        try: 
            os.remove(f)
        except:
            pass
    print("Done!")

