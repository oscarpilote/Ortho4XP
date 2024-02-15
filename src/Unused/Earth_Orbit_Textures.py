import sys, os, shutil, subprocess, time
import O4_Imagery_Utils as IMG
IMG.initialize_color_filters_dict()
IMG.initialize_providers_dict()

if __name__ == '__main__':
    tdir = sys.argv[1]
    if sys.argv[2] not in IMG.providers_dict:
        print("Unknown provider.")
        sys.exit()
    if ("Earth Orbit Textures" not in tdir) or (not os.path.isdir(tdir)):
        print("Error, target directory does not exist or is not an Earth Orbit Textures directory.")
        sys.exit()
    if not os.path.isdir(os.path.join(tdir,'XP_Orig')):
        os.makedir(os.path.join(tdir,'XP_Orig'))
    for f in os.listdir(tdir):
        if '.dds' not in f:
            continue
        if os.path.getsize(os.path.join(tdir,f))>=10*1e6:
            continue
        lat = int(f[:3])
        lon = int(f[3:7])
        if lon==-180: lon=-179.9999
        try:
            (success,im) = IMG.build_texture_from_bbox_and_size((lon,lat+10,lon+10,lat),'4326',(4096,4096),IMG.providers_dict[sys.argv[2]])
        except Exception as e:
            print(e)
            continue
        if success:
            im.save(os.path.join(tdir,f.replace('.dds','.png')))
            if not os.path.exists(os.path.join(tdir,'XP_Orig',f)):
                shutil.copyfile(os.path.join(tdir,f),os.path.join(tdir,'XP_Orig',f))
            cnv_cmd = conv_cmd=[IMG.dds_convert_cmd,'-bc1','-fast',os.path.join(tdir,f.replace('.dds','.png')), os.path.join(tdir,f), IMG.devnull_rdir]
            tentative = 0
            while True:
                if not subprocess.call(conv_cmd,stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT):
                    break
                tentative+=1
                if tentative==10:
                    IMG.UI.lvprint(1,"ERROR: Could not convert texture", f, "(10 tries)")
                    break
                time.sleep(1)
            os.remove(os.path.join(tdir,f.replace('.dds','.png')))
            print("Image ",f,"successfully processed.")
        else:
            print("ERROR for texture", f)
