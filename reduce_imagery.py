#!/usr/bin/env python3

import os,sys
from PIL import Image,ImageFilter
import itertools

source_dir =sys.argv[1]
source_zl=int(source_dir[-2:])
dest_zl=int(sys.argv[2])
dest_dir=source_dir[:-2]+str(dest_zl)
delta_zl=source_zl-dest_zl
small_image_size= 4096//(2**delta_zl)

if len(sys.argv)==4 and sys.argv[3]=='safe': 
    safe=True
else:
    safe=False
skipped_list=[]

if not os.path.exists(dest_dir):
    os.makedirs(dest_dir)

for f in os.listdir(source_dir):
    try:
        s_tily,s_tilx,name_end=f.split('_')[:3]
        s_tily,s_tilx = (int(x) for x in (s_tily,s_tilx))
        name_end_new=name_end[:-6]+str(dest_zl)+'.jpg'
    except:
        print("File",f,"non valid, skipping it.")
        continue
    t_tily,t_tilx= (x//(2**delta_zl*16)*16 for x in (s_tily,s_tilx))
    dest_file=os.path.join(dest_dir,str(t_tily)+'_'+str(t_tilx)+'_'+name_end_new)
    if os.path.isfile(dest_file) or dest_file in skipped_list:
        print("Skipping ",f, "already present in",dest_file)
        continue
    big_image=Image.new('RGB',(4096,4096))
    keep_that_one=True
    for (i,j) in itertools.product(range(0,2**delta_zl),range(0,2**delta_zl)):
            print(i,j)
            part_tily = 2**delta_zl*t_tily+16*j  
            part_tilx = 2**delta_zl*t_tilx+16*i 
            small_image_file=os.path.join(source_dir,str(part_tily)+'_'+str(part_tilx)+'_'+name_end)
            try:
                small_image=Image.open(small_image_file).resize((small_image_size,small_image_size),Image.BICUBIC)
            except:
                if safe:
                    print("One missing small file, skipping",dest_file)  
                    keep_that_one=False
                    print("keep :",keep_that_one)
                    skipped_list.append(dest_file)
                    break
                print("One missing small file, using white instead !!!!!!!!!!!!!!!!!!!")  
                small_image=Image.new('RGB',(small_image_size,small_image_size),'white')
            big_image.paste(small_image,(i*small_image_size,j*small_image_size))
    if keep_that_one: big_image.save(dest_file)
    
