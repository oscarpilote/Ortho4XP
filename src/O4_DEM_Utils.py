import os
import io
import time
import requests
import zipfile
import itertools
from math import sqrt
import array
import numpy
try:
    import gdal
    has_gdal=True
except:
    has_gdal=False
from PIL import Image
import O4_UI_Utils as UI
import O4_File_Names as FNAMES

available_sources=(
                 'View','Viewfinderpanoramas (J. de Ferranti) - mostly worldwide',
                 'SRTM','SRTMv3 (from OpenTopography) - worldwide at latitudes < 60',
                 'NED1','NED 1" (from USGS) - USA, Canada, Mexico',
                 'NED1/3','NED 1/3" (from USGS) - USA',
                 'ALOS','ALOS 3W30 average (from OpenTopography) - mostly worldwide'
                 ) 
                 
global_sources = ('View','SRTM','ALOS')

##############################################################################
class DEM():
    def __init__(self,lat,lon,source='',fill_nodata=True,info_only=False):
        self.lat=lat
        self.lon=lon
        if ";" in source:
            self.alt=self.alt_composite
            self.alt_vec=self.alt_vec_composite
        else:
            self.alt=self.alt_nostrict
            self.alt_vec=self.alt_vec_nostrict
        self.load_data(source,info_only)
        if info_only: return 
        if fill_nodata=="to zero":
            self.nodata_to_zero()
        elif fill_nodata:
            fill_nodata_values_with_nearest_neighbor(self.alt_dem,self.nodata)
            
        UI.vprint(1,"    * Min altitude:",self.alt_dem.min(),", Max altitude:",self.alt_dem.max(),", Mean:",self.alt_dem.mean())

    def load_data(self,source,info_only=False):
        if not source:
            if os.path.exists(FNAMES.generic_tif(self.lat,self.lon)):
                source=FNAMES.generic_tif(self.lat, self.lon)
            else:
                source=available_sources[1]
        if ";" in source:
            source,local_sources=source.split(";")[0],source.split(";")[1:]
        else:
            local_sources=None
        if source in available_sources[1::2]:
            short_source=available_sources[available_sources.index(source)-1]
            if short_source in global_sources:
                (self.epsg,self.x0,self.y0,self.x1,self.y1,self.nodata,self.nxdem,self.nydem,self.alt_dem)=build_combined_raster(short_source,self.lat,self.lon,info_only)
            else:
                if ensure_elevation(short_source,self.lat,self.lon):
                    (self.epsg,self.x0,self.y0,self.x1,self.y1,self.nodata,self.nxdem,self.nydem,self.alt_dem)=\
                        read_elevation_from_file(FNAMES.elevation_data(short_source,self.lat,self.lon),self.lat,self.lon,info_only,3601)
                else:
                    (self.epsg,self.x0,self.y0,self.x1,self.y1,self.nodata,self.nxdem,self.nydem,self.alt_dem)=\
                        (4326,0,0,1,1,-32768,3601,3601,numpy.zeros((3601,3601),dtype=numpy.float32))    
        else:
            file_name=source
            (self.epsg,self.x0,self.y0,self.x1,self.y1,self.nodata,self.nxdem,self.nydem,self.alt_dem)=read_elevation_from_file(file_name,self.lat,self.lon,info_only)
        if not local_sources: return
        self.subdems=tuple()
        for local_source in local_sources:
            self.subdems+=(DEM(self.lat,self.lon,local_source,False,info_only),)
            self.subdems[-1].alt=self.subdems[-1].alt_strict
            self.subdems[-1].alt_vec=self.subdems[-1].alt_vec_strict

            
            
    def nodata_to_zero(self):
        if (self.alt_dem==self.nodata).any():
            UI.vprint(1,"   INFO: Replacing nodata nodes with zero altitude.")
            self.alt_dem[self.alt_dem==self.nodata]=0
        self.nodata=-32768
        return
        
    def write_to_file(self,filename):
        self.alt_dem.astype(numpy.float32).tofile(filename)
        return

    def create_normal_map(self,pixx,pixy):
        dx=numpy.zeros((self.nxdem,self.nydem))
        dy=numpy.zeros((self.nxdem,self.nydem))
        dx[:,1:-1]=(self.alt_dem[:,2:]-self.alt_dem[:,0:-2])/(2*pixx)
        dx[:,0]=(self.alt_dem[:,1]-self.alt_dem[:,0])/(pixx)
        dx[:,-1]=(self.alt_dem[:,-1]-self.alt_dem[:,-2])/(pixx)
        dy[1:-1,:]=(self.alt_dem[:-2,:]-self.alt_dem[2:,:])/(2*pixy)
        dy[0,:]=(self.alt_dem[0,:]-self.alt_dem[1,:])/(pixy)
        dy[-1,:]=(self.alt_dem[-2,:]-self.alt_dem[-1,:])/(pixy)
        del(self.alt_dem)
        norm=numpy.sqrt(1+dx**2+dy**2)
        dx=dx/norm
        dy=dy/norm
        del(norm)
        band_r=Image.fromarray(((1+dx)/2*255).astype(numpy.uint8)).resize((4096,4096))
        del(dx)
        band_g=Image.fromarray(((1-dy)/2*255).astype(numpy.uint8)).resize((4096,4096))
        del(dy)
        band_b=Image.fromarray((numpy.ones((4096,4096))*10).astype(numpy.uint8))
        band_a=Image.fromarray((numpy.ones((4096,4096))*128).astype(numpy.uint8))
        im=Image.merge('RGBA',(band_r,band_g,band_b,band_a))
        im.save('normal_map.png')

    def super_level_set(self,level,wgs84_bbox):
        (lonmin,lonmax,latmin,latmax)=wgs84_bbox
        xmin=lonmin-self.lon
        xmax=lonmax-self.lon
        ymin=latmin-self.lat
        ymax=latmax-self.lat
        if xmin<self.x0: xmin=self.x0
        if xmax>self.x1: xmax=self.x1
        if ymin<self.y0: ymin=self.y0
        if ymax>self.y1: ymax=self.y1
        pixx0=round((xmin-self.x0)/(self.x1-self.x0)*(self.nxdem-1))  
        pixx1=round((xmax-self.x0)/(self.x1-self.x0)*(self.nxdem-1))  
        pixy0=round((self.y1-ymax)/(self.y1-self.y0)*(self.nydem-1))  
        pixy1=round((self.y1-ymin)/(self.y1-self.y0)*(self.nydem-1))
        return ((xmin+self.lon,xmax+self.lon,ymin+self.lat,ymax+self.lat),self.alt_dem[pixy0:pixy1+1,pixx0:pixx1+1]>=level)

    def alt_nostrict(self,node):
        Nx=self.nxdem-1
        Ny=self.nydem-1
        x=node[0]
        y=node[1]
        x=max(x,self.x0)
        x=min(x,self.x1)
        y=max(y,self.y0)
        y=min(y,self.y1)
        px=(x-self.x0)/(self.x1-self.x0)*Nx
        py=(y-self.y0)/(self.y1-self.y0)*Ny
        nx=int(px)
        Nminusny=Ny-int(py)
        rx=px-nx
        ry=py+Nminusny-Ny
        t1=self.alt_dem[Nminusny,nx]
        t2=self.alt_dem[(Nminusny-1)*(Nminusny>=1),(nx+1)*(nx<Nx)+Nx*(nx==Nx)]
        t3=self.alt_dem[Nminusny,(nx+1)*(nx<Nx)+Nx*(nx==Nx)]
        t4=self.alt_dem[(Nminusny-1)*(Nminusny>=1),nx]
        return ((1-rx)*t1+ry*t2+(rx-ry)*t3)*(rx>=ry)+((1-ry)*t1+rx*t2+(ry-rx)*t4)*(rx<ry)

    def alt_strict(self,node):
        x=node[0]
        y=node[1]
        return self.nodata if ((x>self.x1) or (x<self.x0) or (y<self.y0) or (y>self.y1)) else self.alt_dem[int(round((self.y1-y)/(self.y1-self.y0)*(self.nydem-1))),int(round((x-self.x0)/(self.x1-self.x0)*(self.nxdem-1)))]
        
    def alt_composite(self,node):
        for subdem in self.subdems[::-1]:
            tmp=subdem.alt_strict(node)
            if tmp != subdem.nodata: return tmp
        return self.alt_nostrict(node)     
        
    def alt_vec_nostrict(self,way):
        Nx=self.nxdem-1
        Ny=self.nydem-1
        x,y=way[:,0],way[:,1]
        x=numpy.maximum.reduce([x,self.x0*numpy.ones(x.shape)])
        x=numpy.minimum.reduce([x,self.x1*numpy.ones(x.shape)])
        y=numpy.maximum.reduce([y,self.y0*numpy.ones(y.shape)])
        y=numpy.minimum.reduce([y,self.y1*numpy.ones(y.shape)])
        px=(x-self.x0)/(self.x1-self.x0)*Nx
        py=(y-self.y0)/(self.y1-self.y0)*Ny
        nx=px.astype(numpy.uint16)
        Nminusny=Ny-py.astype(numpy.uint16)
        rx=px-nx
        ry=py+Nminusny-Ny
        t1=[self.alt_dem[i][j] for i,j in zip(Nminusny,nx)]
        t2=[self.alt_dem[i][j] for i,j in zip((Nminusny-1)*(Nminusny>=1),(nx+1)*(nx<Nx)+Nx*(nx==Nx))]
        t3=[self.alt_dem[i][j] for i,j in zip(Nminusny,(nx+1)*(nx<Nx)+Nx*(nx==Nx))]
        t4=[self.alt_dem[i][j] for i,j in zip((Nminusny-1)*(Nminusny>=1),nx)]
        return ((1-rx)*t1+ry*t2+(rx-ry)*t3)*(rx>=ry)+((1-ry)*t1+rx*t2+(ry-rx)*t4)*(rx<ry)
        
    def alt_vec_strict(self,way):
        x,y=way[:,0],way[:,1]
        mask=(x>=self.x0)*(x<=self.x1)*(y>=self.y0)*(y<=self.y1)
        nx=numpy.round((x-self.x0)/(self.x1-self.x0)*(self.nxdem-1)).astype(numpy.uint16)
        Nminusny=numpy.round((self.y1-y)/(self.y1-self.y0)*(self.nydem-1)).astype(numpy.uint16)
        return numpy.array([self.alt_dem[i][j] if k else self.nodata for i,j,k in zip(Nminusny,nx,mask)])
    
    def alt_vec_composite(self,way):
        tmp=self.alt_vec_nostrict(way)
        for subdem in self.subdems:
            tmp2=subdem.alt_vec_strict(way)
            tmp[tmp2!=subdem.nodata]=tmp2[tmp2!=subdem.nodata]
        return tmp     
            
###############################################################################

###############################################################################
def build_combined_raster(source,lat,lon,info_only):
    world_tiles=numpy.array(Image.open(os.path.join(FNAMES.Utils_dir,'world_tiles.png')))
    if source in ('View','SRTM'):
        base=3601; overlap=1; beyond=36
        x0=y0=-0.01; x1=y1=1.01
        epsg=4326; nodata=-32768
        nxdem=nydem=base+2*beyond # = 3673
    elif source ==('ALOS'):
        base=3600; overlap=0; beyond = 36
        eps=1/7200
        x0=y0=-0.01+eps; x1=y1=1.01-eps
        epsg=4326; nodata=-32768
        nxdem=nydem=base+2*beyond # = 3672
    if info_only: return (epsg,x0,y0,x1,y1,nodata,nxdem,nydem,None)
    alt_dem=numpy.zeros((nydem,nxdem),dtype=numpy.float32)
    for (lat0,lon0) in itertools.product((lat,lat-1,lat+1),(lon,lon-1,lon+1)):
        verbose=True if (lat0==lat and lon0==lon) else False
        x=(180+lon0)%360
        y=89-lat0
        if not world_tiles[y,x]:
            tmparray=numpy.zeros((base,base),dtype=numpy.float32)
        elif ensure_elevation(source,lat0,(lon0+180)%360-180,verbose):
            tmparray=read_elevation_from_file(FNAMES.elevation_data(source,lat0,(lon0+180)%360-180),lat0,(lon0+180)%360-180,info_only,base)[-1]
        else:
            tmparray=numpy.zeros((base,base),dtype=numpy.float32)
        by=beyond
        ov=overlap    
        if lat0==lat and lon0==lon:
            alt_dem[by:-by,by:-by]=tmparray
        elif lat0==lat and lon0==lon-1:
            alt_dem[by:-by,:by]=tmparray[:,-by-ov:-ov] if ov else tmparray[:,-by:]
        elif lat0==lat and lon0==lon+1:
            alt_dem[by:-by,-by:]=tmparray[:,ov:ov+by] if ov else tmparray[:,:by]
        elif lat0==lat+1 and lon0==lon:
            alt_dem[:by,by:-by]=tmparray[-ov-by:-ov,:] if ov else tmparray[-by:,:]
        elif lat0==lat-1 and lon0==lon:
            alt_dem[-by:,by:-by]=tmparray[ov:ov+by,:] if ov else tmparray[:by,:]
        elif lat0==lat+1 and lon0==lon-1:
            alt_dem[:by,:by]=tmparray[-ov-by:-ov,-ov-by:-ov] if ov else tmparray[-by:,-by:]  
        elif lat0==lat+1 and lon0==lon+1:
            alt_dem[:by,-by:]=tmparray[-ov-by:-ov,ov:ov+by] if ov else tmparray[-by:,:by]
        elif lat0==lat-1 and lon0==lon-1:
            alt_dem[-by:,:by]=tmparray[ov:ov+by,-ov-by:-ov] if ov else tmparray[:by,-by:]
        elif lat0==lat-1 and lon0==lon+1:
            alt_dem[-by:,-by:]=tmparray[ov:ov+by,ov:ov+by] if ov else tmparray[:by,:by]
    return (epsg,x0,y0,x1,y1,nodata,nxdem,nydem,alt_dem)
##############################################################################

##############################################################################
def read_elevation_from_file(file_name,lat,lon,info_only=False,base_if_error=3601):
    alt_dem=None
    if file_name[-4:].lower()=='.hgt':
        x0=y0=0; x1=y1=1; epsg=4326; nodata=-32768
        try:
            nxdem=nydem=int(round(sqrt(os.path.getsize(file_name)/2)))
            if not info_only: alt_dem=numpy.fromfile(file_name,numpy.dtype('>i2')).astype(numpy.float32).reshape((nydem,nxdem))
            if nxdem==1201:
                nxdem=nydem=3601
                if not info_only:
                    fill_nodata_values_with_nearest_neighbor(alt_dem,nodata)
                    alt_dem=upsample(alt_dem)
        except:
            UI.lvprint(1,"    ERROR: in reading elevation from", file_name, "-> replaced with zero altitude.") 
            nxdem=nydem=base_if_error
            if not info_only: alt_dem=numpy.zeros((base_if_error,base_if_error),dtype=numpy.float32)
        
    elif file_name[-4:].lower() =='.raw':
        try:
            nxdem=nydem=int(round(sqrt(os.path.getsize(file_name)/2)))
            f = open(file_name, 'rb')
            alt = array.array('h')
            alt.fromfile(f,nxdem*nydem)
            f.close()
            if not info_only: alt_dem=numpy.asarray(alt,dtype=numpy.float32).reshape((nxdem,nydem))[::-1]
        except:
            UI.lvprint(1,"    ERROR: in reading elevation from", file_name, "-> replaced with zero altitude.") 
            nxdem=nydem=base_if_error
            if not info_only: alt_dem=numpy.zeros((base_if_error,base_if_error),dtype=numpy.float32)
        x0=y0=0; x1=y1=1; epsg=4326; nodata=-32768
    elif has_gdal:
        try:
            ds=gdal.Open(file_name)
            rs=ds.GetRasterBand(1)
            if not info_only: alt_dem=rs.ReadAsArray().astype(numpy.float32)
            (nxdem,nydem)=(ds.RasterXSize,ds.RasterYSize) 
            nodata=rs.GetNoDataValue()
            if nodata is None: 
                UI.vprint(1,"    WARNING: raster DEM does not advertise its no_data value, assuming -32768.")
                nodata=-32768
            else: # elevations being stored as float32, we push the nodata to that framework too, and then replace no_data values by -32768 anyway for uniformity
                nodata=numpy.float32(nodata)
                if not info_only: alt_dem[alt_dem==nodata]=-32768
                nodata=-32768
            try: 
                epsg=int(ds.GetProjection().split('"')[-2])
            except:
                UI.vprint(1,"    WARNING: raster DEM does not advertise its EPSG code, assuming 4326.") 
                epsg=4326
            if epsg not in (4326,4269): # let's be blind about 4269 which might be sufficiently close to 4326 for our purposes
                UI.lvprint(1,"    WARNING: unsupported EPSG code ",epsg,". Only EPSG:4326 is supported, result is likely to be non sense.") 
            geo=ds.GetGeoTransform()
            # We are assuming AREA_OR_POINT is area here 
            x0=geo[0]+.5*geo[1]-lon
            y1=geo[3]+.5*geo[5]-lat
            x1=x0+(nxdem-1)*geo[1] 
            y0=y1+(nydem-1)*geo[5]  
        except:
            UI.lvprint(1,"   ERROR: in reading ", file_name, "-> replaced with zero altitude.") 
            nxdem=nydem=base_if_error
            if not info_only: alt_dem=numpy.zeros((base_if_error,base_if_error),dtype=numpy.float32)
            x0=y0=0; x1=y1=1; epsg=4326; nodata=-32768
    elif not has_gdal:
        UI.lvprint(1,"   WARNING: unsupported raster (install Gdal):", file_name, "-> replaced with zero altitude.") 
        nxdem=nydem=base_if_error
        if not info_only: alt_dem=numpy.zeros((base_if_error,base_if_error),dtype=numpy.float32)
        x0=y0=0; x1=y1=1; epsg=4326; nodata=-32768
    return (epsg,x0,y0,x1,y1,nodata,nxdem,nydem,alt_dem)
##############################################################################    
           
##############################################################################
def ensure_elevation(source,lat,lon,verbose=True):
    if source=='View':
        # Viewfinderpanorama grouping of files and resolutions is a bit complicated...
        if (lat,lon) in ((44,5),(45,5),(46,5),(43,6),(44,6),(45,6),(46,6),(47,6),(43,7),(44,7),(45,7),
                         (46,7),(47,7),(45,8),(46,8),(47,8),(45,9),(46,9),(47,9),(45,10),(46,10),(47,10),
                         (45,11),(46,11),(47,11),(45,12),(46,12),(47,12),(46,13),(47,13),(46,14),(47,14),(46,15),(47,15)):
            resol = 1                 
            url="http://viewfinderpanoramas.org/dem1/"+os.path.basename(FNAMES.base_file_name(lat,lon)).lower()+".zip"
        else:
            deferranti_nbr=31+lon//6
            if deferranti_nbr<10:
                deferranti_nbr='0'+str(deferranti_nbr)
            else:
                deferranti_nbr=str(deferranti_nbr)
            alphabet=list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            deferranti_letter=alphabet[lat//4] if lat>=0 else alphabet[(-1-lat)//4]
            if lat<0:
                deferranti_letter='S'+deferranti_letter
            if deferranti_letter+deferranti_nbr in (
               "O31","P31","N32","O32","P32","Q32","N33","O33","P33","Q33","R33",
               "O34","P34","Q34","R34","O35","P35","Q35","R35","P36","Q36","R36"):
                resol=1
            else:
                resol=3
            url="http://viewfinderpanoramas.org/dem"+str(resol)+"/"+deferranti_letter+deferranti_nbr+".zip"
        if os.path.exists(FNAMES.viewfinderpanorama(lat,lon)) and (resol==3 or os.path.getsize(FNAMES.viewfinderpanorama(lat,lon))>=25934402):
            UI.vprint(2,"   Recycling ",FNAMES.viewfinderpanorama(lat,lon))
            return 1
        UI.vprint(1,"    Downloading ",FNAMES.viewfinderpanorama(lat,lon),"from Viewfinderpanoramas (J. de Ferranti).")    
        r=http_request(url,source,verbose)
        if not r: return 0
        with zipfile.ZipFile(io.BytesIO(r.content),"r") as zip_ref:
            for f in zip_ref.filelist:
                fname=os.path.basename(f.filename)
                if not fname: continue
                try:
                    lat0=int(fname[1:3])
                    lon0=int(fname[4:7])
                except:
                    UI.vprint(2,"      Archive contains the unknown file name",fname,"which is skipped.")    
                    continue
                if ('S' in fname) or ('s' in fname): lat0*=-1
                if ('W' in fname) or ('w' in fname): lon0*=-1
                out_filename=FNAMES.viewfinderpanorama(lat0, lon0)
                # we don't wish to overwrite a 1" version by downloading the whole archive of a nearby 3" one
                if not os.path.exists(out_filename) or os.path.getsize(out_filename)<=f.file_size: 
                    if not os.path.isdir(os.path.dirname(out_filename)):
                        os.makedirs(os.path.dirname(out_filename))
                    with open(out_filename,"wb") as out:
                        UI.vprint(2,"      Extracting",out_filename)
                        out.write(zip_ref.open(f,"r").read())
    elif source in ('SRTM','ALOS'):
        if os.path.exists(FNAMES.elevation_data(source,lat,lon)):
            UI.vprint(2,"   Recycling ",FNAMES.elevation_data(source,lat,lon))
            return 1 
        UI.vprint(1,"    Downloading ",FNAMES.elevation_data(source,lat,lon),"from OpenTopography (SDSC).")
        url="https://cloud.sdsc.edu/v1/AUTH_opentopography/Raster/"
        if source=='SRTM':
            url+="SRTM_GL1/SRTM_GL1_srtm/"
            if lat<-60 or lat>=60: return 0
            if lat<0: 
                url+="South/" 
            elif lat<=29:
                url+="North/North_0_29/"
            else:
                url+="North/North_30_60/" 
            url+=os.path.basename(FNAMES.viewfinderpanorama(lat,lon))    
        elif source=='ALOS':
            url+="AW3D30/AW3D30_alos/"
            if lat<0: 
                url+="South/" 
            elif lat<=45:
                url+="North/North_0_45/"
            else:
                url+="North/North_46_90/" 
            tmp=os.path.basename(FNAMES.base_file_name(lat,lon))
            tmp=tmp[0]+"0"+tmp[1:]+"_AVE_DSM.tif"    
            url+=tmp
        r=http_request(url,source,verbose)
        if not r: return 0
        if not os.path.isdir(os.path.dirname(FNAMES.elevation_data(source,lat,lon))):
            os.makedirs(os.path.dirname(FNAMES.elevation_data(source,lat,lon)))
        with open(FNAMES.elevation_data(source,lat,lon),"wb") as out:
            try:
                out.write(r.content)
            except:
                return 0
    elif source=='NED1/3':
        if os.path.exists(FNAMES.elevation_data(source,lat,lon)):
            UI.vprint(2,"   Recycling ",FNAMES.elevation_data(source,lat,lon))
            return 1 
        UI.vprint(1,"    Downloading ",FNAMES.elevation_data(source,lat,lon),"from USGS.")
        url_base='https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/IMG/'
        usgs_name='USGS_NED_13_n'+str(lat + 1)+'w'+str(-lon).zfill(3)+'_IMG'
        r=http_request(url_base+usgs_name+'.zip',source,verbose)
        if not r:
            UI.vprint(2,"    Trying alternative naming scheme.")
            usgs_name="imgn"+str(lat + 1)+"w"+str(-lon).zfill(3)+"_13"
            r=http_request(url_base+'n'+str(lat + 1).zfill(2)+'w'+str(-lon).zfill(3)+'.zip',source,verbose)
            if not r:
                return 0
        with zipfile.ZipFile(io.BytesIO(r.content),"r") as zip_ref:
            if not os.path.isdir(os.path.dirname(FNAMES.elevation_data(source,lat,lon))):
                os.makedirs(os.path.dirname(FNAMES.elevation_data(source,lat,lon)))
            with open(FNAMES.elevation_data(source,lat,lon),"wb") as out:
                try:
                    out.write((zip_ref.open(usgs_name+'.img',"r").read()))
                except:
                    return 0
    elif source=='NED1':
        if os.path.exists(FNAMES.elevation_data(source,lat,lon)):
            UI.vprint(2,"   Recycling ",FNAMES.elevation_data(source,lat,lon))
            return 1 
        UI.vprint(1,"    Downloading ",FNAMES.elevation_data(source,lat,lon),"from USGS.")
        url_base='https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/ArcGrid/'
        usgs_base='n'+str(lat + 1)+'w'+str(-lon).zfill(3)
        r=http_request(url_base+'USGS_NED_1_'+usgs_base+'_ArcGrid.zip',source,verbose)
        if not r:
            UI.vprint(2,"    Trying alternative naming scheme.")
            r=http_request(url_base+usgs_base+'.zip',source,verbose)
            if not r:
                return 0
        with zipfile.ZipFile(io.BytesIO(r.content),"r") as zip_ref:
            if not os.path.isdir(os.path.dirname(FNAMES.elevation_data(source,lat,lon))):
                os.makedirs(os.path.dirname(FNAMES.elevation_data(source,lat,lon)))
            for f in zip_ref.filelist:
                if not '.adf' in f.filename: continue
                fname=os.path.basename(f.filename)    
                with open(os.path.join(os.path.dirname(FNAMES.elevation_data(source,lat,lon)),fname),"wb") as out:
                    try:
                        out.write((zip_ref.open(f,"r").read()))
                    except:
                        return 0
    else:
        UI.vprint(1,"   ERROR: Unknown elevation source.")
        return 0
    return 1
##############################################################################
                
##############################################################################
def http_request(url,source,verbose=False):
    s=requests.Session()
    tentative=0
    while True: 
        try:
            r=s.get(url,timeout=10)
            status_code = str(r)   
            if ('[20' in status_code):
                return r
            elif ('[40' in status_code or '[30' in status_code):
                if verbose: UI.vprint(2,"    Server said 'Not Found'")
                return 0
            elif ('[5' in status_code):      
                if verbose: UI.vprint(2,"    Server said 'Internal Error'.",status_code)
            else:
                if verbose: UI.vprint(2,status_code)
        except Exception as e:
            if verbose: UI.vprint(2,e)
        tentative+=1
        if tentative==6: return 0
        UI.vprint(1,"    ",source,"server may be down or busy, new tentative in",2**tentative,"sec...")
        time.sleep(2**tentative)
##############################################################################

##############################################################################
def fill_nodata_values_with_nearest_neighbor(alt_dem,nodata):
        step=0
        while (alt_dem==nodata).any():
            if not step:
                UI.vprint(2,"    INFO: Elevation file contains voids, trying to fill them recursively by nearest neighbour.")       
            else:
                UI.vprint(2,"    ",step)
            alt10=numpy.roll(alt_dem,1,axis=0)
            alt10[0]=alt_dem[0]
            alt20=numpy.roll(alt_dem,-1,axis=0)
            alt20[-1]=alt_dem[-1]
            alt01=numpy.roll(alt_dem,1,axis=1)
            alt01[:,0]=alt_dem[:,0]
            alt02=numpy.roll(alt_dem,-1,axis=1)
            alt02[:,-1]=alt_dem[:,-1]
            atemp=numpy.maximum(alt10,alt20)
            atemp=numpy.maximum(atemp,alt01)
            atemp=numpy.maximum(atemp,alt02)
            alt_dem[alt_dem==nodata]=atemp[alt_dem==nodata]
            step+=1
            if step>20:
                UI.vprint(1,"    WARNING: The raster contain holes that seem to big to be filled... I'm filling the remainder with zero.")
                alt_dem[alt_dem==nodata]=0
                break
        if step: UI.vprint(2,"    Done.") 
##############################################################################

##############################################################################
def upsample(alt_dem):
        # only implemented from 1201 to 3601, might be worth upgrading it some day
        alt_dem_tmp=numpy.zeros((3601,3601),dtype=numpy.float32)
        for i in range(1201): 
            alt_dem_tmp[3*i,::3]=alt_dem[i]
            alt_dem_tmp[3*i,1::3]=2/3*alt_dem[i,:-1]+1/3*alt_dem[i,1:]
            alt_dem_tmp[3*i,2::3]=1/3*alt_dem[i,:-1]+2/3*alt_dem[i,1:]
            if i==1200: break
            alt_dem_tmp[3*i+1,::3]=2/3*alt_dem[i]+1/3*alt_dem[i+1]
            alt_dem_tmp[3*i+2,::3]=1/3*alt_dem[i]+2/3*alt_dem[i+1]
            alt_dem_tmp[3*i+1,1::3]=4/9*alt_dem[i][:-1]+2/9*alt_dem[i,1:]+2/9*alt_dem[i+1,:-1]+1/9*alt_dem[i+1,1:]
            alt_dem_tmp[3*i+2,1::3]=2/9*alt_dem[i][:-1]+1/9*alt_dem[i,1:]+4/9*alt_dem[i+1,:-1]+2/9*alt_dem[i+1,1:]
            alt_dem_tmp[3*i+1,2::3]=2/9*alt_dem[i][:-1]+4/9*alt_dem[i,1:]+1/9*alt_dem[i+1,:-1]+2/9*alt_dem[i+1,1:]
            alt_dem_tmp[3*i+2,2::3]=1/9*alt_dem[i][:-1]+2/9*alt_dem[i,1:]+2/9*alt_dem[i+1,:-1]+4/9*alt_dem[i+1,1:]
        return alt_dem_tmp
##############################################################################


##############################################################################
def smoothen(raster,pix_width,mask_im,preserve_boundary=True):
    if not pix_width: return raster
    if not mask_im: return raster
    tmp = numpy.array(raster)
    mask_array = numpy.array(mask_im,dtype=numpy.float)/255
    kernel=numpy.array(range(1,2*(pix_width+1)))
    kernel[pix_width+1:]=range(pix_width,0,-1)
    kernel=kernel/(pix_width+1)**2
    tmp=tmp*mask_array
    tmpw=numpy.array(mask_array)
    for i in range(0,len(tmp)):
        tmp[i]=numpy.convolve(tmp[i],kernel)[pix_width:-pix_width]
        tmpw[i]=numpy.convolve(tmpw[i],kernel)[pix_width:-pix_width]
    tmp=tmp.transpose() 
    tmpw=tmpw.transpose() 
    for i in range(0,len(tmp)):
        tmp[i]=numpy.convolve(tmp[i],kernel)[pix_width:-pix_width]
        tmpw[i]=numpy.convolve(tmpw[i],kernel)[pix_width:-pix_width]
    tmp=tmp.transpose()
    tmpw=tmpw.transpose()
    tmp[mask_array!=0]=mask_array[mask_array!=0]*tmp[mask_array!=0]/tmpw[mask_array!=0]+(1-mask_array[mask_array!=0])*raster[mask_array!=0]
    if preserve_boundary:
        for i in range(pix_width):
            tmp[i]=i/pix_width*tmp[i]+(pix_width-i)/pix_width*raster[i]
            tmp[-i-1]=i/pix_width*tmp[-i-1]+(pix_width-i)/pix_width*raster[-i-1]
        for i in range(pix_width):
            tmp[:,i]=i/pix_width*tmp[:,i]+(pix_width-i)/pix_width*raster[:,i]
            tmp[:,-i-1]=i/pix_width*tmp[:,-i-1]+(pix_width-i)/pix_width*raster[:,-i-1]
    return raster*(mask_array==0)+tmp*(mask_array!=0)
##############################################################################













    
    
    
    
    
       
