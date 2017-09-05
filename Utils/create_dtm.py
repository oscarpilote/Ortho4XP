#!/usr/bin/env python3

import os,sys

s_srs=sys.argv[1] 
input_dem = sys.argv[2]
try:
    lat=int(sys.argv[3])
    lon=int(sys.argv[4])
    output_dem=sys.argv[5]
except:
    output_dem=sys.argv[3]
    
if not os.path.exists(output_dem):
    cmd="gdalwarp -s_srs epsg:"+s_srs+" -t_srs epsg:4326 -te "+str(lon-0.00002777)+" "+str(lat-0.00002777)+" "+str(lon+1+0.00002777)+" "+str(lat+1+0.00002777)+" -ts 18001 18001 -ot float32 -rb -dstnodata 0 "+input_dem+" "+output_dem
else:
    cmd="gdalwarp -s_srs epsg:"+s_srs+" -rb "+input_dem+" "+output_dem
os.system(cmd)
