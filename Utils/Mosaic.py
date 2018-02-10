#!/usr/bin/env python3                                                       
from math import *
import sys, os

Ortho4XP_dir='..'

if 'dar' in sys.platform:
    dir_sep         = '/'
    delete_cmd      = "rm "
    jpegtopnm       = "/usr/local/netpbm/bin/jpegtopnm " 
    pnmtojpeg       = "/usr/local/netpbm/bin/pnmtojpeg " 
    pamundice       = "/usr/local/netpbm/bin/pamundice " 
    pamdice         = "/usr/local/netpbm/bin/pamdice " 


elif 'win' in sys.platform: 
    dir_sep         = '\\'
    delete_cmd      = "del "	
    jpegtopnm       = "C:\\netpbm\\bin\\jpegtopnm " 
    pnmtojpeg       = "C:\\netpbm\\bin\\pnmtojpeg " 
    pamundice       = "C:\\netpbm\\bin\\pamundice " 
    pamdice         = "C:\\netpbm\\bin\\pamdice " 
else:
    dir_sep         = '/'
    delete_cmd      = "rm "
    jpegtopnm       = "/usr/local/netpbm/bin/jpegtopnm " 
    pnmtojpeg       = "/usr/local/netpbm/bin/pnmtojpeg " 
    pamundice       = "/usr/local/netpbm/bin/pamundice " 
    pamdice         = "/usr/local/netpbm/bin/pamdice " 

##############################################################################
def filename(lat,lon,til_x_left,til_y_top,zoomlevel,website,complete=True):
    strlat='{:+.0f}'.format(lat).zfill(3)
    strlon='{:+.0f}'.format(lon).zfill(4)
    file_dir=Ortho4XP_dir+dir_sep+"Orthophotos"+dir_sep+strlat+strlon+\
             dir_sep+website+'_'+str(zoomlevel)+dir_sep
    file_name=str(til_y_top)+"_"+str(til_x_left)+"_"+website+str(zoomlevel)   
    file_ext=".jpg"
    if complete==True:
        return file_dir+file_name+file_ext
    else:
        return file_name+file_ext
##############################################################################


##############################################################################
def wgs84_to_texture(lat,lon,zoomlevel,website):
    half_meridian=pi*6378137
    ratio_x=lon/180           
    ratio_y=log(tan((90+lat)*pi/360))/pi
    pix_x=(ratio_x+1)*(2**(zoomlevel+7))
    pix_y=(1-ratio_y)*(2**(zoomlevel+7))
    til_x=pix_x//256
    til_y=pix_y//256
    tex_x=(til_x//16)*16
    tex_y=(til_y//16)*16
    return [int(tex_x),int(tex_y)]
##############################################################################

if __name__ == '__main__':
    try:
        action    = sys.argv[1] 
        latmin    = float(sys.argv[2])
        latmax    = float(sys.argv[3])
        lonmin    = float(sys.argv[4])
        lonmax    = float(sys.argv[5])
        zoomlevel = int(sys.argv[6]) 
        website   = sys.argv[7]
    except:
        print("La ligne de commande ne respecte pas la syntaxe")
        sys.exit()

    lat=floor((latmin+latmax)/2.0)
    lon=floor((lonmin+lonmax)/2.0)
    filename_assembled = "assemblage_"+str(latmin)+'_'+str(latmax)+'_'+\
                          str(lonmin)+'_'+str(lonmax)+'_'+website+'_'+str(zoomlevel)+'.pnm'
    #print(filename_assembled)
    if action=='assemble':
        [tex_x_left,tex_y_top] = wgs84_to_texture(latmax,lonmin,zoomlevel,website)
        [tex_x_right,tex_y_bot] = wgs84_to_texture(latmin,lonmax,zoomlevel,website)
        nbr_tex_x=int((tex_x_right-tex_x_left)/16+1)
        nbr_tex_y=int((tex_y_bot-tex_y_top)/16+1)
        answer=input('''
L'opération que vous souhaitez réaliser nécessitera environ ''' +'{:.1f}'.format(nbr_tex_x*nbr_tex_y*0.05)+''' Gb d'espace
disque disponible (et la moitié en fin d'opération). Je continue ? (O = oui, sinon non) : ''')
        if answer != 'O' :
            print("C'est sans doute plus raisonnable.")
            sys.exit()
        for tex_y in range(tex_y_top,tex_y_bot+1,16):
            for tex_x in range(tex_x_left,tex_x_right+1,16):
                strx=str(int((tex_y-tex_y_top)/16)).zfill(3)
                stry=str(int((tex_x-tex_x_left)/16)).zfill(3)
                new_file_name='tmp_'+stry+'_'+strx+'.pnm'
                if os.path.isfile(filename(lat,lon,tex_x,tex_y,zoomlevel,website))==True:
                    if os.path.getsize(filename(lat,lon,tex_x,tex_y,zoomlevel,website)) > 80000:
                        os.system(jpegtopnm+" "+filename(lat,lon,tex_x,tex_y,zoomlevel,website)+' > '+\
                            new_file_name)
                    else:
                        os.system(jpegtopnm+" white4096x4096.jpg  > "+\
                              new_file_name)
                else:
                    os.system(jpegtopnm+" white4096x4096.jpg  > "+\
                              new_file_name)
        os.system(pamundice+" -across="+str(nbr_tex_x)+\
                " -down="+str(nbr_tex_y)+" tmp_%3a_%3d.pnm  > "\
                +str(filename_assembled))
        os.system(delete_cmd+" tmp*.pnm")
        print("Opération terminée, sauf message d'erreur le fichier créé se nomme "+filename_assembled)
    elif action=='split':
        [tex_x_left,tex_y_top] = wgs84_to_texture(latmax,lonmin,zoomlevel,website)
        [tex_x_right,tex_y_bot] = wgs84_to_texture(latmin,lonmax,zoomlevel,website)
        nbr_tex_x=int((tex_x_right-tex_x_left)/16+1)
        nbr_tex_y=int((tex_y_bot-tex_y_top)/16+1)
        print
        formatx=1
        if nbr_tex_x>10:
            formatx=2
        if nbr_tex_x>100:
            formatx=3
        formaty=1
        if nbr_tex_y>10:
            formaty=2
        if nbr_tex_y>100:
            formaty=3
        if not os.path.isfile(filename_assembled):
            print("Le fichier "+filename_assembled+" ne semble pas être présent dans le répertoire courant")
            sys.exit()
        os.system(pamdice+" "+filename_assembled+" -outstem=out_tmp -width=4096 -height=4096")
        answer=input('''
Voulez-vous écraser les anciennes orthophotos ? (O = Oui, sinon j'écrirai les nouvelles dans le répertoire courant) : ''')
        if answer=='O':
            complete=True
        else:
            complete=False
        for tex_y in range(tex_y_top,tex_y_bot+1,16):
            for tex_x in range(tex_x_left,tex_x_right+1,16):
                strx=str(int((tex_y-tex_y_top)/16)).zfill(formaty)
                stry=str(int((tex_x-tex_x_left)/16)).zfill(formatx)
                out_tmp_fname="out_tmp_"+strx+'_'+stry+'.ppm'
                if os.path.isfile(filename(lat,lon,tex_x,tex_y,zoomlevel,website))==True:
                    os.system(pnmtojpeg+" "+out_tmp_fname+' > '+\
                            filename(lat,lon,tex_x,tex_y,zoomlevel,website,complete=False))
                os.system(delete_cmd+' '+out_tmp_fname) 
    else:
        print("La ligne de commande ne respecte pas la syntaxe")
        sys.exit()

