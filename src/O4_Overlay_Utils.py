import time
import os
import shutil
import sys
import subprocess
import O4_File_Names as FNAMES
import O4_UI_Utils as UI

# the following is meant to be modified directly by users who need it
ovl_exclude_pol=(0,)
ovl_exclude_net=()

# the following is meant to be modified by the CFG module at run time
custom_overlay_src=''

if 'dar' in sys.platform:
    unzip_cmd    = "7z "
    dsftool_cmd  = os.path.join(FNAMES.Utils_dir,"DSFTool.app ")
elif 'win' in sys.platform: 
    unzip_cmd    = os.path.join(FNAMES.Utils_dir,"7z.exe ")
    dsftool_cmd  = os.path.join(FNAMES.Utils_dir,"DSFTool.exe ")
else:
    unzip_cmd    = "7z "
    dsftool_cmd  = os.path.join(FNAMES.Utils_dir,"DSFTool ")

##############################################################################
def build_overlay(lat,lon):
    if UI.is_working: return 0
    UI.is_working=1
    timer=time.time()
    UI.logprint("Step 4 for tile lat=",lat,", lon=",lon,": starting.")
    UI.vprint(0,"\nStep 4 : Extracting overlay for tile "+FNAMES.short_latlon(lat,lon)+" : \n--------\n")
    file_to_sniff=os.path.join(custom_overlay_src,"Earth nav data",FNAMES.long_latlon(lat,lon)+'.dsf')
    if not os.path.exists(file_to_sniff):
        UI.exit_message_and_bottom_line("   ERROR: file ",file_to_sniff,"absent. Recall that the overlay source directory needs to be set in the config window first.")
        return 0
    file_to_sniff_loc=os.path.join(FNAMES.Tmp_dir,FNAMES.short_latlon(lat,lon)+'.dsf')
    UI.vprint(1,"-> Making a copy of the original overlay DSF in tmp dir")
    try:
        shutil.copy(file_to_sniff,file_to_sniff_loc)
    except:
        UI.exit_message_and_bottom_line("   ERROR: could not copy it. Disk full, write permissions, erased tmp dir ?")
        return 0
    f = open(file_to_sniff_loc,'rb')
    dsfid = f.read(2).decode('ascii')
    f.close()
    if dsfid == '7z':
        UI.vprint(1,"-> The original DSF is a 7z archive, uncompressing...")
        os.rename(file_to_sniff_loc,file_to_sniff_loc+'.7z')
        os.system(unzip_cmd+' e -o'+FNAMES.Tmp_dir+' "'+file_to_sniff_loc+'.7z"')
    UI.vprint(1,"-> Converting the copy to text format")
    dsfconvertcmd=[dsftool_cmd.strip(),' -dsf2text '.strip(),file_to_sniff_loc,os.path.join(FNAMES.Tmp_dir,'tmp_dsf.txt')]
    fingers_crossed=subprocess.Popen(dsfconvertcmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            UI.vprint(1,'     '+line.decode("utf-8")[:-1])
    if fingers_crossed.returncode:
        UI.exit_message_and_bottom_line("   ERROR: DSFTool crashed.")
        return 0
    UI.vprint(1,"-> Selecting overlays for copy/paste")
    f=open(os.path.join(FNAMES.Tmp_dir,'tmp_dsf.txt'),'r')
    g=open(os.path.join(FNAMES.Tmp_dir,'tmp_dsf_without_mesh.txt'),'w')
    line=f.readline()
    g.write('PROPERTY sim/overlay 1\n')
    pol_type=0
    while line:
        if 'PROPERTY' in line:
            g.write(line)
        elif 'POLYGON_DEF' in line:
            level=2 if 'facade' not in line else 3
            UI.vprint(level,pol_type,":",line.split()[1])
            pol_type+=1
            g.write(line)
        elif 'NETWORK_DEF' in line:
            g.write(line)
        elif 'BEGIN_POLYGON' in line:
            pol_type = int(line.split()[1])
            if pol_type not in ovl_exclude_pol and ovl_exclude_pol!=['*']:
                while line and ('END_POLYGON' not in line):
                    g.write(line)
                    line=f.readline()
                g.write(line)
            else:
                while line and ('END_POLYGON' not in line):
                    line=f.readline()
        elif 'BEGIN_SEGMENT' in line:
            road_type = int(line.split()[2])
            if road_type not in ovl_exclude_net and ovl_exclude_net!=['*']:
                while line and ('END_SEGMENT' not in line):
                    g.write(line)
                    line=f.readline()
                g.write(line)
            else:
                while line and ('END_SEGMENT' not in line):
                    line=f.readline()
        line=f.readline()
    f.close()
    g.close()
    UI.vprint(1,"-> Converting back the text DSF to binary format")
    dsfconvertcmd=[dsftool_cmd.strip(),' -text2dsf '.strip(),os.path.join(FNAMES.Tmp_dir,'tmp_dsf_without_mesh.txt'),os.path.join(FNAMES.Tmp_dir,'tmp_dsf_without_mesh.dsf')] 
    fingers_crossed=subprocess.Popen(dsfconvertcmd,stdout=subprocess.PIPE,bufsize=0)
    while True:
        line = fingers_crossed.stdout.readline()
        if not line: 
            break
        else:
            print('     '+line.decode("utf-8")[:-1])
    dest_dir=os.path.join(FNAMES.Overlay_dir,"Earth nav data",FNAMES.round_latlon(lat,lon))
    UI.vprint(1,"-> Coping the final overlay DSF in "+dest_dir) 
    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
        except:
            UI.exit_message_and_bottom_line("   ERROR: could not create destination directory "+str(dest_dir))
            return 0
    shutil.copy(os.path.join(FNAMES.Tmp_dir,'tmp_dsf_without_mesh.dsf'),os.path.join(dest_dir,FNAMES.short_latlon(lat,lon)+'.dsf'))
    os.remove(os.path.join(FNAMES.Tmp_dir,'tmp_dsf_without_mesh.dsf'))
    os.remove(os.path.join(FNAMES.Tmp_dir,'tmp_dsf_without_mesh.txt'))
    os.remove(os.path.join(FNAMES.Tmp_dir,'tmp_dsf.txt'))
    os.remove(file_to_sniff_loc)
    try:
        os.remove(os.path.join(FNAMES.Tmp_dir,'tmp_dsf.txt.elevation.raw')) 
        os.remove(os.path.join(FNAMES.Tmp_dir,'tmp_dsf.txt.sea_level.raw')) 
    except: 
        pass
    if dsfid == '7z':
        os.remove(file_to_sniff_loc+'.7z')
    UI.timings_and_bottom_line(timer)
    return 1
##############################################################################
