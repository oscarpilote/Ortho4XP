#!/usr/bin/env python3
# Licence: GPL v3 
from rectpack import *
from PIL import Image, ImageFilter, ImageStat
import os, sys
import numpy
from math import *
import time
import fileinput

################
debug_level=2              # Mettre à zéro pour lui couper le sifflet
resol_target = 20          # Niveau de résolution cherché, en pix par unité de longueru du .obj (à mettre à 1mètre pour X-Plane)
min_stddev_thresh=4        # Niveau de déviation standard du rgb de la texture en dessous duquel elle sera considérée comme unie 
                           # (ce qui permet de beaucoup diminuer les besoins de tuilage dans certains cas mais rend)
cut_to_tile_priority = 5   # Niveau de priorité entre le tuilage interne ou le découpage des faces, à 1 on ne fait que tuiler, 
                           # plus on monte plus on donne priorité à la découpe
accepted_tiling_increase=1 # On accepte que le tuilage puisse faire grossir au plus les textures d'un tel facteur (entier)
                           # Si à 1 alors le tuilage n'est possible que si la résolution initale des textures est suffisamment
                           # supérieure à la résolution cible 
max_downscale=4            # On ne réduira jamais plus les textures que par un facteur max_downscale, même si leur résolution 
                           # initiale était gigantiesque par rapport au reste 
max_acceptable_resol=4000  # Une face qui ferait porter à sa texture une résolution supérieure à cette valeur sera
                           # transformée en texture unie (cela permet de contourner certaines erreurs de conception des modèles)

smallest_area_tol=0.0001

xyz_snap_init=0.01         # cela attache les points sur une grille 
xyz_snap_final=0.01        # in fine le seul qui a sans doute de l'intérêt, en mètre, permet de de fabriquer un low poly 
                           # simplement par accroche sur une grille de pas donné (toutes les faces écrasées par l'opération
                           # sont évacuées
st_snap_init=0.0001        # idem mais pour les coordonées textures
st_snap_final=0.0001       # idem mais pour les coordonées textures
norm_snap_init=0           #.01

safe_pix=4                 # bord ajouté à chaque texture, il n'est pas utilisé en tant que tel mais évite que les compressions 
                           # dds ou internes ne viennent faire baver les couleurs adjacentes.
double_faces = False
################

if 'dar' in sys.platform:
    dir_sep         = '/'
    unzip_cmd       = "7z "
    convert_cmd_bis = "nvcompress-osx -bc1 -fast " 
    devnull_rdir    = " >/dev/null 2>&1"
elif 'win' in sys.platform: 
    dir_sep         = '\\'
    unzip_cmd       = "7z.exe "
    convert_cmd_bis = "nvcompress.exe -bc1 -fast " 
    devnull_rdir    = " > nul  2>&1"
else:
    dir_sep         = '/'
    unzip_cmd       = "7z "
    convert_cmd_bis     = "nvcompress -fast -bc1a " 
    devnull_rdir    = " >/dev/null 2>&1 "


def syntax():
    return


msg_list=[]
def print_error_once(msg):
   if not msg in msg_list:
       msg_list.append(msg)
       print(msg) 
  
def cut_poly(poly):
    s_range = int(ceil(numpy.max(poly[0]))-floor(numpy.min(poly[0])))
    t_range = int(ceil(numpy.max(poly[1]))-floor(numpy.min(poly[1])))
    assert s_range + t_range >=1
    if s_range<=1 and t_range<=1:
        return [poly[:,[0,j,j+1]] for j in range(1,poly.shape[1]-1)]
    elif s_range>=t_range:
        s_cut=floor(numpy.min(poly[0]))+s_range//2
        poly=numpy.roll(poly,-1*numpy.argmax(numpy.logical_xor(poly[0,0]>=s_cut,poly[0,:]>=s_cut)),axis=1)
        poly1=poly[:,poly[0]>=s_cut]
        poly2=poly[:,poly[0]<s_cut]
        t12=(s_cut-poly2[0,0])*(poly1[1,-1]-poly2[1,0])/(poly1[0,-1]-poly2[0,0])+poly2[1,0] if poly2[0,0]!=poly1[0,-1] else poly2[1,0]
        d12=(s_cut-poly2[0,0])*(poly1[2,-1]-poly2[2,0])/(poly1[0,-1]-poly2[0,0])+poly2[2,0] if poly2[0,0]!=poly1[0,-1] else poly2[2,0]
        t21=(s_cut-poly1[0,0])*(poly2[1,-1]-poly1[1,0])/(poly2[0,-1]-poly1[0,0])+poly1[1,0] if poly1[0,0]!=poly2[0,-1] else poly1[1,0]
        d21=(s_cut-poly1[0,0])*(poly2[2,-1]-poly1[2,0])/(poly2[0,-1]-poly1[0,0])+poly1[2,0] if poly1[0,0]!=poly2[0,-1] else poly1[2,0]
        if s_cut!=poly1[0,-1]: poly1=numpy.column_stack((poly1,[s_cut,t12,d12]))
        if s_cut!=poly1[0,0]: poly1=numpy.column_stack((poly1,[s_cut,t21,d21]))
        if s_cut!=poly2[0,-1]: poly2=numpy.column_stack((poly2,[s_cut,t21,d21]))
        if s_cut!=poly2[0,0]: poly2=numpy.column_stack((poly2,[s_cut,t12,d12]))
        return cut_poly(numpy.array(poly1))+cut_poly(numpy.array(poly2))
    else:
        t_cut=floor(numpy.min(poly[1]))+t_range//2
        poly=numpy.roll(poly,-1*numpy.argmax(numpy.logical_xor(poly[1,0]>=t_cut,poly[1,:]>=t_cut)),axis=1)
        poly1=poly[:,poly[1]>=t_cut]
        poly2=poly[:,poly[1]<t_cut]
        s12=(t_cut-poly2[1,0])*(poly1[0,-1]-poly2[0,0])/(poly1[1,-1]-poly2[1,0])+poly2[0,0] if poly2[1,0]!=poly1[1,-1] else poly2[0,0]
        d12=(t_cut-poly2[1,0])*(poly1[2,-1]-poly2[2,0])/(poly1[1,-1]-poly2[1,0])+poly2[2,0] if poly2[1,0]!=poly1[1,-1] else poly2[2,0]
        s21=(t_cut-poly1[1,0])*(poly2[0,-1]-poly1[0,0])/(poly2[1,-1]-poly1[1,0])+poly1[0,0] if poly1[1,0]!=poly2[1,-1] else poly1[0,0]
        d21=(t_cut-poly1[1,0])*(poly2[2,-1]-poly1[2,0])/(poly2[1,-1]-poly1[1,0])+poly1[2,0] if poly1[1,0]!=poly2[1,-1] else poly1[2,0]
        if t_cut!=poly1[1,-1]: poly1=numpy.column_stack((poly1,[s12,t_cut,d12]))
        if t_cut!=poly1[1,0]: poly1=numpy.column_stack((poly1,[s21,t_cut,d21]))
        if t_cut!=poly2[1,-1]: poly2=numpy.column_stack((poly2,[s21,t_cut,d21]))
        if t_cut!=poly2[1,0]: poly2=numpy.column_stack((poly2,[s12,t_cut,d12]))
        return cut_poly(numpy.array(poly1))+cut_poly(numpy.array(poly2))

if __name__ == '__main__':

    try:
        fin=sys.argv[1]
    except:
        syntax()
    try:
        output=sys.argv[2]
        if output not in ['wavefront','x-plane']:
            output='x-plane'
            print('Unknown output format, will use x-plane obj.')
    except:
        output='x-plane'     
    findir=fin.split('/')[:-1]
    finfilename = fin.split('/')[-1]
    finbasename = '.'.join(finfilename.split('.')[:-1])
    finext      = finfilename.split('.')[-1]
    
    #print(findir,finfilename,finbasename,finext)
    if finext=='kmz':
        os.system(unzip_cmd+" e '"+fin+"' -o'"+finbasename+"' -y models "+devnull_rdir)
        with fileinput.FileInput(finbasename+'/untitled.dae', inplace=True, backup='.bak') as file:
            for line in file:
                print(line.replace("untitled", finbasename), end='') 
        os.rename(finbasename+'/untitled.dae',finbasename+'.dae')
    if finext in ['kmz','dae']:
        # look for units and orientation
        ftest=open(finbasename+'.dae','r')
        meter_conv=None
        up_axis=None
        for line in ftest.readlines():
            if '<unit ' in line:
                meter_conv=float(line.split()[1].split('=')[1][1:-1])
            elif '<up_axis>' in line:
                up_axis=line.split('<up_axis>')[1].split('</up_axis>')[0]
            if meter_conv and up_axis: 
                break
        ftest.close()
        if not meter_conv: meter_conv=1
        if not up_axis: up_axis='Y'
        print(meter_conv,up_axis)
        if os.path.isfile(finbasename+'.obj'):  os.remove(finbasename+'.obj')
        if os.path.isfile(finbasename+'.mtl'):  os.remove(finbasename+'.mtl')
        os.system("meshtool --load_collada '"+finbasename+".dae' --combine_effects --combine_materials "+\
              "--combine_primitives --save_obj '"+finbasename+".obj'")
        if (meter_conv!=1) or ('z' in up_axis) or ('Z' in up_axis):
            fold=open(finbasename+'.obj','r')
            fnew=open(finbasename+'.obj.tmp','w')
            if 'z' in up_axis or 'Z' in up_axis:
                for line in fold.readlines():
                    if line[0:2]=='v ':
                        x,y,z=[float(t) for t in line.split()[1:]]
                        x*=meter_conv
                        y*=meter_conv
                        z*=meter_conv
                        fnew.write("v "+str(x)+" "+str(z)+" "+str(-1*y)+"\n")
                    elif line[0:2]=='vn ':
                        nx,ny,nz=[float(t) for t in line.split()[1:]]
                        fnew.write("vn "+str(nx)+" "+str(nz)+" "+str(-1*ny)+"\n")
                    else:
                        fnew.write(line)
            else: # assuming z is up
                for line in fold.readlines():
                    if line[0:2]=='v ':
                        x,y,z=[float(t) for t in line.split()[1:]]
                        x*=meter_conv
                        y*=meter_conv
                        z*=meter_conv
                        fnew.write("v "+str(x)+" "+str(y)+" "+str(z)+"\n")
                    else:
                        fnew.write(line)
        fold.close()
        fnew.close()
        os.rename(finbasename+'.obj.tmp',finbasename+'.obj')   
   
    if not os.path.isfile(finbasename+'.mtl'):
        print("No mtl file found.")
        sys.exit()


    #####
    #
    # 1 : Readind the mtl and getting info on the textures
    #
    #####

    if debug_level>=1:
        print("\nI. Reading the mtl file and analyzing textures")
        print(  "###############################################################################\n")
    dico_mtl={}
    dico_texture={}
    mtl_texture_list=[]
    mtl_exclude_list=[]
    texture_list=[]
    f=open(finbasename+'.mtl','r')
    for line in f.readlines():
       items=line.split()
       if not items: continue
       if items[0]=='newmtl':
           mtlname=items[1]
           dico_mtl[mtlname]=[[0,0,0,1],''] 
       elif items[0]=='Kd':
           dico_mtl[mtlname][0][0:3]=[float(x) for x in items[1:4]]
       elif items[0]=='d':
           dico_mtl[mtlname][0][3]*=float(items[1]) 
       elif items[0]=='map_Kd':
           texture_name=' '.join(items[1:])
           if os.path.isfile(texture_name):
               im=Image.open(texture_name)
               mean=ImageStat.Stat(im).mean
               #print("mean : ",mean)
               stddev= [round(x*10)/10 for x in ImageStat.Stat(im).stddev]
               if numpy.max(numpy.array(stddev)) < min_stddev_thresh:
                   if debug_level>=2:
                       print("    Texture ",texture_name.split('/')[-1]," will be transformed into plain color")
                       print("    due to its low standard deviation for each of its bands : ",stddev)
                       print()  
                   dico_mtl[mtlname][0][0:3]=[x/255 for x in mean[0:3]]
                   try:
                       dico_mtl[mtlname][0][3]*=mean[3]/255
                   except:
                       pass
                   continue
               dico_mtl[mtlname][1]=texture_name
               mtl_texture_list.append(mtlname)
               if texture_name not in texture_list: 
                   texture_list.append(texture_name)
               dico_texture[texture_name]={}
               dico_texture[texture_name]['size']   = im.size
               dico_texture[texture_name]['mean']   = mean
               if len(mean)==4 and mean[3]<=230:
                   dico_texture[texture_name]['transparent_layer']=True
               else: 
                   dico_texture[texture_name]['transparent_layer']=False
               dico_texture[texture_name]['stddev'] = stddev
               dico_texture[texture_name]['resol'] = []
               dico_texture[texture_name]['st_span'] = [1,1]
               dico_texture[texture_name]['hard_tiling'] = [1,1]
               dico_texture[texture_name]['end_size'] = []
               dico_texture[texture_name]['f_count_in'] = 0
               dico_texture[texture_name]['f_count_out'] = 0
               dico_texture[texture_name]['f_count_in_bad_resol'] = 0
               dico_texture[texture_name]['f_count_out_bad_resol'] = 0
               im.close()
           else:
               print("The texture file ",texture_name," referenced by the material ",mtlname," is missing.")
               print("The corresponding faces will be ignored.")
               mtl_exclude_list.append(mtlname)
    f.close()

    #####
    #
    # 2 : Recording x,y,z and analyzing tiling needs and resols from s,t 
    #
    #####

    if debug_level>=1:
        print("\nII. Analyzing mesh and deciding about subtiling")
        print(  "###############################################################################\n")

    dico_v={}
    dico_vt={}
    dico_vn={}
    vtot=1
    vttot=1
    vntot=1
    finit=0
    bad_resol_list=[]
    f=open(finbasename+'.obj','r')
    for line in f.readlines():
        if line[0:7]=='usemtl ':
            mtlname=line[7:-1]
            if mtlname in mtl_texture_list:
                texture_name=dico_mtl[mtlname][1]
                [width,height]=dico_texture[texture_name]['size']
        elif line[0:2]=='v ':
            [x,y,z]=[float(t) for t in line[2:-1].split()]
            if xyz_snap_init:
                x=round(x/xyz_snap_init)*xyz_snap_init  
                y=round(y/xyz_snap_init)*xyz_snap_init  
                z=round(z/xyz_snap_init)*xyz_snap_init  
            dico_v[vtot]=[x,y,z]
            vtot+=1
        elif line[0:3]=='vt ':
            [s,t]=[float(x) for x in line[3:-1].split()]
            if st_snap_init:
                s=round(s/st_snap_init)*st_snap_init  
                t=round(t/st_snap_init)*st_snap_init  
            dico_vt[vttot]=[s,t]
            vttot+=1
        elif line[0:3]=='vn ':
            [nx,ny,nz]=[float(t) for t in line[2:-1].split()]
            if norm_snap_init:
                nx=round(x/norm_snap_init)*norm_snap_init  
                ny=round(y/norm_snap_init)*norm_snap_init  
                nz=round(z/norm_snap_init)*norm_snap_init  
            dico_vn[vntot]=[nx,ny,nz]
            vntot+=1
        elif line[0:2]=='f ':
            finit+=1 
            #print(finit)
            if mtlname not in mtl_texture_list:
               continue 
            idx_joined = line[2:].split()
            idx_vt=[int(p.split('/')[1]) for p in idx_joined]
            polyvt=numpy.transpose(numpy.array([dico_vt[ivt] for ivt in idx_vt]))
            idx_v=[int(p.split('/')[0]) for p in idx_joined]
            polyv=numpy.transpose(numpy.array([dico_v[iv] for iv in idx_v]))
            space_length=numpy.sum(numpy.abs(polyv-numpy.roll(polyv,1,axis=1)))
            pix_length=numpy.sum(numpy.dot(numpy.array([[width,height]]),numpy.abs(polyvt-numpy.roll(polyvt,1,axis=1))))
            s_span = int(ceil(numpy.max(polyvt[0]))-floor(numpy.min(polyvt[0])))
            t_span = int(ceil(numpy.max(polyvt[1]))-floor(numpy.min(polyvt[1])))
            if space_length<1e-6 or pix_length/space_length>= max_acceptable_resol:
                dico_texture[texture_name]['f_count_in_bad_resol']+=1 
                dico_texture[texture_name]['f_count_out_bad_resol']+=s_span*t_span 
                bad_resol_list.append(finit)
                continue
            dico_texture[texture_name]['resol'].append(pix_length/space_length)
            dico_texture[texture_name]['f_count_in']+=1 
            dico_texture[texture_name]['f_count_out']+=s_span*t_span 
            [s_span_tmp,t_span_tmp]=dico_texture[texture_name]['st_span']
            s_span=max(s_span_tmp,s_span)
            t_span=max(t_span_tmp,t_span)
            dico_texture[texture_name]['st_span']=[s_span,t_span]
    f.close()

    #####
    #
    # 3 : Deciding about tiling and sizes of the textures 
    #
    #####


    for texture_name in dico_texture:
        [s_span,t_span]=dico_texture[texture_name]['st_span']
        [width,height]=dico_texture[texture_name]['size']
        if dico_texture[texture_name]['resol']:
            resol=ceil(numpy.array(dico_texture[texture_name]['resol']).mean())
        else:
            resol=1000
        stddev=dico_texture[texture_name]['stddev']
        f_count_in=dico_texture[texture_name]['f_count_in']
        f_count_out=dico_texture[texture_name]['f_count_out']
        f_count_in_bad_resol=dico_texture[texture_name]['f_count_in_bad_resol']
        f_count_out_bad_resol=dico_texture[texture_name]['f_count_out_bad_resol']
        if debug_level>=2 and (s_span!=1 or t_span != 1) :
            print()
            print("--> Texture ",texture_name.split('/')[-1]," was used with tiling in the .obj file :")
            print("   ",s_span," tiles in width  for a texture of initial width  ",width,",")      
            print("   ",t_span," tile in height for a texture of initial height ",height,".")
            print("    Texture initial resolution was roughly ",resol," pix/m.")
            #print(dico_texture[texture_name]['resol'])
            print("    Texture initial face count was : ",f_count_in)
            print("    Texture approx face count in order to avoid tiling would be : ",f_count_out,",")
            print("    a ratio of : ",round(f_count_out/f_count_in*10)/10,".")
            if f_count_in_bad_resol>=1:
                print("!!!!Texture initial face count with absurdly high resol was : ",f_count_in_bad_resol)
                print("!!!!These faces will be turned to plain color to avoid something like ",f_count_out_bad_resol," new faces.")
            print("    Texture standard deviation is ",stddev,".")
        elif debug_level>=2:
            print()
            print("--> Texture ",texture_name.split('/')[-1]," did not necessitate tiling.")

        # It would be useless to increase the size of low resol textures to cope with the resol_arget
        if resol<resol_target: 
            resol_init=int(resol)
            resol=resol_target
            upscale_blocked=True
        else:
            upscale_blocked=False 
        tiling_pot=floor(resol/resol_target)*accepted_tiling_increase 
        hard_tile_s=1
        hard_tile_t=1
        if f_count_out > cut_to_tile_priority * f_count_in:
            hard_tile_s=int(ceil(s_span/ceil(s_span/tiling_pot)))
            hard_tile_t=int(ceil(t_span/ceil(t_span/tiling_pot)))
        if debug_level>=2 and (s_span!=1 or t_span != 1) :
            print("    -> Texture tiling will end-up being : ",hard_tile_s,"x",hard_tile_t) 
        assert hard_tile_s>=1
        assert hard_tile_t>=1
        dico_texture[texture_name]['hard_tiling']=[hard_tile_s,hard_tile_t]
        end_width=ceil(width*hard_tile_s*resol_target/resol)
        end_height=ceil(height*hard_tile_s*resol_target/resol)
        downscale_limited=False
        if end_width<width/max_downscale: 
            end_width=ceil(width/max_downscale)
            downscale_limited=True
        if end_height<height/max_downscale: 
            end_height=ceil(height/max_downscale)
            downscale_limited=True
        if debug_level>=2:
            if downscale_limited:
                print("    -> Texture final size would be : ",end_width,"x",end_height," (downscale limited).")
            elif upscale_blocked: 
                print("    -> Texture final size would be : ",end_width,"x",end_height," (initially too low res at ",resol_init,").")
            else: 
                print("    -> Texture final size would be : ",end_width,"x",end_height,".")
        dico_texture[texture_name]['end_size']=[end_width,end_height]
         
    #####
    #
    # 4 : Adding small 3x3 textures for the plain colors and assimilated textures  
    #
    #####

    for mtlname in dico_mtl:
        if mtlname not in mtl_texture_list+mtl_exclude_list:
            texture_name=mtlname+'_fake'
            texture_list.append(texture_name)
            dico_texture[texture_name]={} 
            dico_texture[texture_name]['end_size']=[3,3]
            dico_texture[texture_name]['hard_tiling']=[1,1]
            dico_texture[texture_name]['plain']=True
            dico_texture[texture_name]['mean']=dico_mtl[mtlname][0]
            if dico_mtl[mtlname][0][3]<0.9:
               dico_texture[texture_name]['transparent_layer']=True
            else: 
               dico_texture[texture_name]['transparent_layer']=False

    #####
    #
    # 5 : Packing of the textures, including the shape of the bin  
    #
    #####

    if debug_level>=1:
        print("\nIII. Packing of textures")
        print(  "###############################################################################\n")

    total_pix=0
    for texture_name in texture_list:
        total_pix+=numpy.prod(numpy.array(dico_texture[texture_name]['end_size']))

    if debug_level>=2:
        print("Trying square bin size")
    packing_successful=False
    margin_s=1
    while not packing_successful:
        packer_s=newPacker()
        i=0
        for texture_name in texture_list:
            packer_s.add_rect(dico_texture[texture_name]['end_size'][0],dico_texture[texture_name]['end_size'][1],i)
            i+=1
        bin_size_s=int(sqrt(total_pix)*(1+margin_s/100))  
        packer_s.add_bin(bin_size_s,bin_size_s)
        packer_s.pack()
        for bin in packer_s:
            if len(bin.rect_list())==i:
                packing_successful=True
                if debug_level>=2:
                    print("  -> Packing successful with ",2*margin_s," percent of void at most in the final texture.")
            else:
                margin_s+=1 

    if debug_level>=2:
        print("Trying rectangular bin size")
    packing_successful=False
    margin_r=1
    while not packing_successful:
        packer_r=newPacker()
        i=0
        for texture_name in texture_list:
            packer_r.add_rect(dico_texture[texture_name]['end_size'][0],dico_texture[texture_name]['end_size'][1],i)
            i+=1
        bin_size_r=int(sqrt(total_pix/2)*(1+margin_r/100))  
        packer_r.add_bin(2*bin_size_r,bin_size_r)
        packer_r.pack()
        for bin in packer_r:
            if len(bin.rect_list())==i:
                packing_successful=True
                if debug_level>=2:
                    print("  -> Packing successful with ",2*margin_r," percent of void at most in the final texture.")
            else:
                margin_r+=1

    if margin_s <= margin_r:
        bin_size_w=bin_size_s
        bin_size_h=bin_size_s
        packer=packer_s
        del(packer_r)
        shape_type="square"
    else:
        bin_size_w=2*bin_size_r
        bin_size_h=bin_size_r
        packer=packer_r
        del(packer_s)
        shape_type="rectangle" 
    if debug_level>=2:
        print("Will keep the ",shape_type ," one.")
    if debug_level>=3:
        print("Now that we have our packing strategy, we need to rework it taking into account")
        print("the power of 2 rule for textures. Rather than growing the big texture and leaving")
        print("void into it we will now rescale the small textures a priori (and it is really")
        print("important do it a priori and not after packing because we wish boundaries of the")
        print("subtextures to fall exactly on integer pixels, something that would be lost be")
        print("a final rescaling after packing.")  
    pow2_size_w=2**(ceil(log(bin_size_w)/log(2)))
    if pow2_size_w>4096: 
        if debug_level>=1:
            print("Texture final size would have been too high for X-Plane, ",pow2_size_w,"in width, we ")
            print("will limit it to 4096.")
        pow2_size_w=4096
    
    if shape_type=="square":
        pow2_size_h=pow2_size_w
    else:
        pow2_size_h=pow2_size_w//2
    if debug_level>=1:
        print("Final X-Plane texture size will be ",pow2_size_w,"x",pow2_size_h)

    scaling_factor=(pow2_size_w/bin_size_w)

    for texture_name in texture_list:
        dico_texture[texture_name]['final_size']=dico_texture[texture_name]['end_size'][:]

    if debug_level>=2:
        print("Final packing")
    packing_successful=False
    margin=0
    while not packing_successful:
        packer=newPacker()
        i=0
        for texture_name in texture_list:
            final_width=max(int(dico_texture[texture_name]['end_size'][0]*scaling_factor*(100-margin)/100),3)
            final_height=max(int(dico_texture[texture_name]['end_size'][1]*scaling_factor*(100-margin)/100),3)
            dico_texture[texture_name]['final_size']=[final_width,final_height]
            packer.add_rect(final_width+2*safe_pix,final_height+2*safe_pix,i)
            i+=1
        packer.add_bin(pow2_size_w,pow2_size_h)
        packer.pack()
        for bin in packer:
            if len(bin.rect_list())==i:
                packing_successful=True
                if debug_level>=3:
                    print("Packing successful after ",margin," testing steps.")
            else:
                margin+=1 
 

    big_image=Image.new('RGBA',(pow2_size_w,pow2_size_h),(0,0,0,0))

    for bin in packer:
        for rect in bin.rect_list():
            texture_name=texture_list[rect[4]]
            texture=dico_texture[texture_name]
            texture['offset']=[x+safe_pix for x in rect[0:2]]
            [w,h]=[x-2*safe_pix for x in rect[2:4]]
            [width,height]=texture['final_size']
            if 'plain' not in texture:
                [orig_width,orig_height]=texture['size']
                [hard_tile_s,hard_tile_t]=texture['hard_tiling']
                small_image_unique=Image.open(texture_name)
                if hard_tile_s!=1 or hard_tile_t!=1:
                    big_width=orig_width*hard_tile_s
                    big_height=orig_height*hard_tile_t
                    small_image=Image.new('RGBA',(big_width,big_height),(0,0,0,0))
                    for i in range(0,hard_tile_s):
                        for j in range(0,hard_tile_t):
                            small_image.paste(small_image_unique,(i*orig_width,j*orig_height)) 
                else:
                    small_image=small_image_unique
                if small_image.size!=[width,height]:
                    small_image,small_image_plus_border=small_image.resize((width,height)),small_image.resize((width+2*safe_pix,height+2*safe_pix))
            else: # plain in texture
                (R,G,B,A)=[round(float(x)*255) for x in dico_texture[texture_name]['mean']]
                small_image=Image.new('RGBA',(3,3),(R,G,B,A))
                small_image_plus_border=Image.new('RGBA',(3+2*safe_pix,3+2*safe_pix),(R,G,B,A))
              
            if w!=width or h!=height:
                texture['rotation_flag']=True
                small_image=small_image.transpose(Image.ROTATE_90)
                small_image_plus_border=small_image_plus_border.transpose(Image.ROTATE_90)
            else:
                texture['rotation_flag']=False
            big_image.paste(small_image_plus_border,(rect[0],rect[1]))
            big_image.paste(small_image,(texture['offset'][0],texture['offset'][1]))
    if debug_level>=1:
        print("Saving final texture ",finbasename+'-grouped.png')          
    big_image.save(finbasename+'-grouped.png')

    #####
    #
    # 6 : Reading faces and performing face cut given the decided hard tiling factors
    #
    #####

    if debug_level>=1:
        print("\nIV. Proceeding to face cuts to get around original tiling")
        print(  "###############################################################################\n")


    dico_f={}
    ftot=0
    fskiped=0
    fsing=0
    finit=0
    f=open(finbasename+'.obj','r')
    for line in f.readlines():
        if line[0:7]=='usemtl ':
            mtlname=line[7:-1] 
            if mtlname in mtl_texture_list:
                texture_name=dico_mtl[mtlname][1]
                texture=dico_texture[texture_name]
                record=True 
            elif mtlname in mtl_exclude_list:
                record=False
            else:
                texture_name=mtlname+"_fake"
                texture=dico_texture[texture_name]
                record=True
        elif line[0:2]=='f ': 
            finit+=1
            if not record:
                fskiped+=1
                continue
            idx_joined = line[2:].split()
            idx_v=[int(p.split('/')[0]) for p in idx_joined]
            idx_vn=[int(p.split('/')[-1]) for p in idx_joined]
            normal=numpy.array([dico_vn[ivn] for ivn in idx_vn])
            normal=numpy.sum(normal,axis=0)
            normal=normal/numpy.linalg.norm(normal)
            # Hack!
            #normal=numpy.array([0,1,0])
            polyv=numpy.transpose(numpy.array([dico_v[iv] for iv in idx_v]))
            if mtlname in mtl_texture_list and finit not in bad_resol_list: 
                idx_vt=[int(p.split('/')[1]) for p in idx_joined]
                polyvt=numpy.transpose(numpy.array([dico_vt[ivt] for ivt in idx_vt]))
                polyvt[0]/=texture['hard_tiling'][0]
                polyvt[1]/=texture['hard_tiling'][0]
                s_range = int(ceil(numpy.max(polyvt[0]))-floor(numpy.min(polyvt[0])))
                t_range = int(ceil(numpy.max(polyvt[1]))-floor(numpy.min(polyvt[1])))
                if s_range<=1 and t_range<=1:
                    for j in range(1,polyv.shape[1]-1):
                        dico_f[ftot]=[texture_name,polyv[:,[0,j,j+1]],polyvt[:,[0,j,j+1]],normal] 
                        ftot+=1
                    continue
                #continue  
                # Being here means that cuts need to be done
                # We first reoder points so that the first segment is non trivial in texture,
                longuestsize=numpy.abs(polyvt-numpy.roll(polyvt,1,axis=1)).max()
                if longuestsize<=1e-3:
                    if debug_level>=3: print("petit cote!!!!!!!!!!!!!!!!!!") 
                    for j in range(1,polyv.shape[1]-1):
                        dico_f[ftot]=[texture_name,polyv[:,[0,j,j+1]],numpy.dot(polyvt[:,[0]],numpy.array([[1,1,1]])),normal] 
                        ftot+=1
                    continue 
                while numpy.abs(polyvt[:,1]-polyvt[:,0]).max()<=longuestsize/2:
                    polyvt=numpy.roll(polyvt,1,axis=1)
                    polyv=numpy.roll(polyv,1,axis=1) 
                # Now since the face as seen in texture could degenerate into a segment, we will add 
                # a supplementary coordinates that will desingularize the mapping in that case. 
                if polyv.shape[1]==3:
                    #continue
                    pseudopoly=numpy.concatenate((polyvt[:],[[0,0,1]]),axis=0)
                    #triangle=True 
                else:
                    facetransf=numpy.linalg.pinv(polyv[:,1:3]-polyv[:,[0]])
                    pseudocoords=facetransf.dot(polyv-polyv[:,[0]])[1] 
                    pseudocoords[0:3]=[0,0,1] # should be so anyway but just in case pinv would do poorly his job (?) 
                    pseudopoly=numpy.concatenate((polyvt[:],[pseudocoords]),axis=0) 
                    print("Pas un triangle !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    #print(polyv)
                    #print(pseudopoly)
                    #time.sleep(1)
                    #triangle=False
                st_tris=cut_poly(numpy.array(pseudopoly))
                pseudoinv=numpy.dot(polyv[:,1:3]-polyv[:,[0]],numpy.linalg.pinv(pseudopoly[:,1:3]-pseudopoly[:,[0]]))
                for st_tri in st_tris:
                    dico_f[ftot]=[texture_name,polyv[:,[0]]+numpy.dot(pseudoinv,st_tri-pseudopoly[:,[0]]),st_tri[0:2],normal] 
                    #if not triangle and debug_level>=4:
                    #    print(dico_f[ftot][1])
                    #    time.sleep(1)
                    #print(dico_f[ftot]) 
                    ftot+=1 
            else: # fake texture or bad resol
                #continue
                for j in range(1,polyv.shape[1]-1):
                    dico_f[ftot]=[texture_name,polyv[:,[0,j,j+1]],numpy.ones((2,3))*0.5,normal] 
                    ftot+=1
    f.close()

    print()
    print("* Total number of initial faces : ",finit)
    print("* Total number of faces after triangulation and UV cut : ",ftot," (doubled to "+str(2*ftot)+")" if double_faces else "")
    print("* Total number of faces skiped due to non existing texture : ",fskiped)
    print("* Total number of faces skiped due to a singular UV map : ",fsing)


    #####
    #
    # 7 : Computing new texture coordinates and vertex dictionnary
    #
    #####

    if debug_level>=1:
        print("\nV. Computing new texture coordinates and writing the output obj file")
        print(  "###############################################################################\n")

    if output=='wavefront':
        dico_new_v={}
        dico_new_vt={}
        dico_new_vn={}
        new_v_total=1
        new_vt_total=1
        new_vn_total=1
        new_v_buffer=''
        new_vt_buffer=''
        new_vn_buffer=''
    elif output=='x-plane':
        dico_VT={}
        VT_total=0
        VT_buffer=''

    TRI_total=0
    IDX_list_no_transp=[]
    IDX_list_transp=[]

    fsimp=0

    for idf in range(0,ftot):
        [texture_name,polyv,polyvt,normal]=dico_f[idf] 
        IDX_list = IDX_list_transp if dico_texture[texture_name]['transparent_layer'] else IDX_list_no_transp 
        texture=dico_texture[texture_name]
        if not "plain" in texture:
            s_offset=(texture['offset'][0])/pow2_size_w
            t_offset=(texture['offset'][1])/pow2_size_h
            if not texture['rotation_flag']:
                s_scale=(texture['final_size'][0])/pow2_size_w
                t_scale=(texture['final_size'][1])/pow2_size_h
            else:    
                s_scale=(texture['final_size'][1])/pow2_size_w
                t_scale=(texture['final_size'][0])/pow2_size_h
        else: # for uniform color we point everything to the center of the 3x3 small uniform square
            s_offset=(1+texture['offset'][0])/pow2_size_w
            t_offset=(1+texture['offset'][1])/pow2_size_h
            s_scale=0
            t_scale=0
        shift=[[floor(numpy.mean(line))] for line in polyvt]
        polyvt=polyvt-shift
        polyvt[1,:]*=-1
        polyvt[1,:]+=1
        if numpy.max(polyvt)>1 or numpy.min(polyvt)<0:
            if debug_level>=3:
                print("C'est quoi ce bordel !!!!!!!!")
                print(numpy.max(polyvt),numpy.min(polyvt))
              
        if not texture['rotation_flag']:
            polyvt*=[[s_scale],[-1*t_scale]]
            polyvt+=[[s_offset],[1-t_offset]]
        else:
            polyvt*=[[t_scale],[s_scale]]
            polyvt+=[[1-t_offset-t_scale],[s_offset]]
            polyvt=polyvt[::-1]  
        if xyz_snap_final:
            polyv=numpy.round(polyv/xyz_snap_final)*xyz_snap_final
            if numpy.linalg.norm(numpy.cross(polyv[:,1]-polyv[:,0],polyv[:,2]-polyv[:,0])) < smallest_area_tol:
                fsimp+=1
                continue
        if st_snap_final: 
            polyvt=numpy.round(polyvt/st_snap_final)*st_snap_final
        if output=='wavefront':
            for i in [0,2,1]:
                strtmpv=' '.join([str(x) for x in [polyv[0,i],polyv[1,i],polyv[2,i]]])
                strtmpvt=' '.join([str(x) for x in [polyvt[0,i],polyvt[1,i]]])
                strtmpvn=' '.join([str(x) for x in normal])
                if strtmpv not in dico_new_v:
                    new_v_buffer+="v "+strtmpv+'\n'
                    dico_new_v[strtmpv]=new_v_total
                    new_v_total+=1
                if strtmpvt not in dico_new_vt:
                    new_vt_buffer+="vt "+strtmpvt+'\n'
                    dico_new_vt[strtmpvt]=new_vt_total
                    new_vt_total+=1
                if strtmpvn not in dico_new_vn:
                    new_vn_buffer+="vn "+strtmpvn+'\n'
                    dico_new_vn[strtmpvn]=new_vn_total
                    new_vn_total+=1
                IDX_list.append([dico_new_v[strtmpv],dico_new_vt[strtmpvt],dico_new_vn[strtmpvn]])
        elif output=='x-plane':
            for i in [0,2,1]:
                strtmp=' '.join([str(x) for x in [polyv[0,i],polyv[1,i],polyv[2,i],normal[0],normal[1],normal[2],polyvt[0,i],polyvt[1,i]]]) 
                if strtmp in dico_VT:
                    IDX_list.append(dico_VT[strtmp])
                else:
                    dico_VT[strtmp]=VT_total
                    VT_buffer+="VT "+strtmp+"\n" 
                    IDX_list.append(VT_total)
                    VT_total+=1
        TRI_total+=1
        if double_faces:
            IDX_list.append(IDX_list[-3])   
            IDX_list.append(IDX_list[-2])   
            IDX_list.append(IDX_list[-4])   
            TRI_total+=1

    # we group and set the transparent faces at last to let them show through    
    IDX_list=IDX_list_no_transp+IDX_list_transp

    if fsimp >0 and debug_level>=1:
        print("A total of ",fsimp," faces were crunched and skipped due to the simplification of xyz_snap_final.") 

    #####
    #
    # 8 : Writing the output obj file
    #
    #####
 
    if output=='wavefront':
        g=open(finbasename+'-Wavefront.mtl','w')
        g.write('newmtl unique_texture\n')
        g.write('map_Kd '+ finbasename+'-grouped.png\n')	
        g.close()  
 
        g=open(finbasename+'-Wavefront.obj','w')
        g.write('mtllib '+finbasename+'-Wavefront.mtl\n')
        g.write('usemtl unique_texture\n')
        g.write(new_v_buffer)
        g.write(new_vt_buffer)
        g.write(new_vn_buffer)
        for tri_idx in range(0,TRI_total):
            g.write('f')
            for j in [0,1,2]:
                g.write(' '+str(IDX_list[3*tri_idx+j][0])+'/'+str(IDX_list[3*tri_idx+j][1])+'/'+str(IDX_list[3*tri_idx+j][2]))
            g.write('\n')
        g.close()
        print("Done. Output filename is ",finbasename+'-Wavefront.obj')
    elif output=='x-plane':
        g=open(finbasename+'-XPlane.obj','w')
        g.write('I\n800\nOBJ\n\nTEXTURE ')
        g.write(finbasename+'-grouped.png\n')
        g.write('POINT_COUNTS    ')
        g.write(str(VT_total))
        g.write(' 0 0 ')
        g.write(str(3*TRI_total))
        g.write('\n\n') 
        g.write(VT_buffer)
        del VT_buffer
        g.write('\n')
        idx=0
        idx10=(TRI_total*3)//10
        for i in range(0,idx10):
            g.write('IDX10 ')
            for j in range(0,10):
                g.write(str(IDX_list[10*i+j])+" ")
            g.write("\n")
        for j in range(0,(TRI_total*3)%10):
            g.write('IDX ')
            g.write(str(IDX_list[idx10*10+j]))
            g.write("\n")
        g.write("\n")
        g.write("TRIS 0 "+str(3*TRI_total))
        g.close()
        print("Done. Output filename is ",finbasename+'-XPlane.obj')








   
