#!/usr/bin/env python

# Ce script peut etre utilie pour vider des dsf d'overlays de certains polygones,
# par exemple les haies autour des parties herbeuses ou bien une orthophoto d'une
# scene locale.
# Copier ce fichier ainsi que DSTool(/.exe/.app/) dans le repertoire  
# contenant le(s) DSF a nettoyer, et sous Mac/Linux s'assurer qu'ils 
# sont executables.
# Exemple d'utilisation :
# ./DSFremovepol.py read +45+006.dsf               -> fournit la liste des polygones (autres que facades) avec leur indice
# ./DSFremovepol.py remove [543,2234] +45+006.dsf  -> enleve tous les polygones dont les indices sont dans la liste 
# Apres utilisation il vous restera des fichier dsftext.txt et dsftxtnew.txt, vous pouvez les virer.

import os, sys

if 'dar' in sys.platform:
    dsftool_cmd="./DSFTool.app "
elif 'win' in sys.platform:
    dsftool_cmd="DSFTool.exe "
else:
    dsftool_cmd="./DSFTool "
if sys.argv[1]=='read':
    os.system(dsftool_cmd+" -dsf2text  "+sys.argv[2]+" dsftext.txt")
    f=open("dsftext.txt",'r')
    counter=-1
    for line in f.readlines():
        if 'BEGIN' in line:
            sys.exit()
        if 'POLYGON_DEF' in line:
            counter+=1
            if 'facade' not in line:
                linesplit=line.split()
                print(str(counter)+' : '+linesplit[1])
    f.close()
    sys.exit()
if sys.argv[1]=='remove':
    removelist=sys.argv[2]
    os.system(dsftool_cmd+" -dsf2text  "+sys.argv[3]+" dsftext.txt")
    fin=open("dsftext.txt",'r')
    fout=open("dsftextnew.txt",'w')
    line=fin.readline()
    while line!='':
        if 'BEGIN_POLYGON' in line:
            index=line.split()[1]
            if index in removelist:
                while 'END_POLYGON' not in line:
                    line=fin.readline()
            else:
                fout.write(line)
        else:
            fout.write(line)
        line=fin.readline()
    fin.close()
    fout.close()
    os.system(dsftool_cmd+" -text2dsf  dsftextnew.txt "+sys.argv[3])
      


