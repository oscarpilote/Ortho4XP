import os
import sys
import time
import requests
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

if 'dar' in sys.platform:
    unzip_cmd       = "7z "
elif 'win' in sys.platform: 
    unzip_cmd       = os.path.join(UI.Ortho4XP_dir, "Utils", "7z.exe ")
else:
    unzip_cmd       = "7z "

##############################################################################
class DEM():

    def __init__(self,lat,lon,file_name='',fill_nodata=True):
        self.lat=lat
        self.lon=lon
        self.load_data(file_name) 
        if fill_nodata:
            self.fill_nodata()
        else:
            self.nodata_to_zero()


    def load_data(self,file_name=''):
        if not file_name:
            file_name=FNAMES.viewfinderpanorama(self.lat, self.lon)
            if not os.path.exists(file_name):
                download_viewfinderpanorama(self.lat,self.lon)
        if ('.hgt') in file_name or ('.HGT' in file_name):
            try:
                self.nxdem=self.nydem=int(round(sqrt(os.path.getsize(file_name)/2)))
                self.alt_dem=numpy.fromfile(file_name,numpy.dtype('>i2')).astype(numpy.float32).reshape((self.nxdem,self.nydem))
            except:
                UI.lvprint(1,"   Error in reading", file_name, "-> replaced with zero altitude.") 
                self.nxdem=self.nydem=1201
                self.alt_dem=numpy.zeros([1201,1201],dtype=numpy.float32)
            self.x0=self.y0=0
            self.x1=self.y1=1
            self.epsg=4326
            self.nodata=-32768
        elif ('.raw') in file_name or ('.RAW' in file_name):
            try:
                self.nxdem=self.nydem=int(round(sqrt(os.path.getsize(file_name)/2)))
                f = open(file_name, 'rb')
                alt = array.array('h')
                alt.fromfile(f,self.nxdem*self.nydem)
                f.close()
            except:
                UI.lvprint(1,"   Error in reading", file_name, "-> replaced with zero altitude.") 
                self.nxdem=self.nydem=1201
                self.alt_dem=numpy.zeros([1201,1201],dtype=numpy.float32)
            self.alt_dem=numpy.asarray(alt,dtype=numpy.float32).reshape((self.nxdem,self.nydem))[::-1]
            self.x0=self.y0=0
            self.x1=self.y1=1
            self.epsg=4326
            self.nodata=-32768
        elif has_gdal:
            self.ds=gdal.Open(file_name)
            self.rs=self.ds.GetRasterBand(1)
            self.alt_dem=self.rs.ReadAsArray().astype(numpy.float32)
            (self.nxdem,self.nydem)=(self.ds.RasterXSize,self.ds.RasterYSize) 
            self.nodata=self.rs.GetNoDataValue()
            if self.nodata is None: self.nodata=-32768
            try: 
                self.epsg=int(self.ds.GetProjection().split('"')[-2])
            except:
                UI.vprint(1,"  Raster did not contain EPSG code information, assuming 4326.") 
                self.epsg=4326
            if self.epsg!=4326:
                UI.lvprint(1,"  Error, unsupported EPSG code :",self.epsg,". Only EPSG 4326 is supported, data replaced with zero altitude.") 
                self.nxdem=self.nydem=1201
                self.alt_dem=numpy.zeros([1201,1201],dtype=numpy.float32)
                self.x0=self.y0=0
                self.x1=self.y1=1
                self.epsg=4326
                self.nodata=-32768
            else:    
                self.geo=self.ds.GetGeoTransform()
                self.x0=self.geo[0]+.5*self.geo[1]-self.lon
                self.y1=self.geo[3]+.5*self.geo[5]-self.lat
                self.x1=self.x0+(self.nxdem-1)*self.geo[1] 
                self.y0=self.y1+(self.nydem-1)*self.geo[5]  
        elif not has_gdal:
            UI.lvprint(1,"  Error, unsupported raster (install Gdal):", file_name, "-> replaced with zero altitude.") 
            self.nxdem=self.nydem=1201
            self.alt_dem=numpy.zeros([1201,1201],dtype=numpy.float32)
            self.x0=self.y0=0
            self.x1=self.y1=1
            self.epsg=4326
            self.nodata=-32768


    def fill_nodata(self):
        step=0
        while (self.alt_dem==self.nodata).any():
            if not step:
                UI.vprint(1,"    Caution: Elevation file contains voids, filling them recursively by nearest neighbour.")       
            else:
                UI.vprint(2,step)
            alt10=numpy.roll(self.alt_dem,1,axis=0)
            alt10[0]=self.alt_dem[0]
            alt20=numpy.roll(self.alt_dem,-1,axis=0)
            alt20[-1]=self.alt_dem[-1]
            alt01=numpy.roll(self.alt_dem,1,axis=1)
            alt01[:,0]=self.alt_dem[:,0]
            alt02=numpy.roll(self.alt_dem,-1,axis=1)
            alt02[:,-1]=self.alt_dem[:,-1]
            atemp=numpy.maximum(alt10,alt20)
            atemp=numpy.maximum(atemp,alt01)
            atemp=numpy.maximum(atemp,alt02)
            self.alt_dem[self.alt_dem==self.nodata]=atemp[self.alt_dem==self.nodata]
            step+=1
            if step>10:
                print("The hole seems to big to be filled as is... I fill the remainder with zero.")
                self.alt_dem[self.alt_dem==self.nodata]=0
                break
        if step: UI.vprint(1,"          Done.\n") 
        
    def nodata_to_zero(self):
        if self.nodata!=0 and (self.alt_dem==self.nodata).any():
            UI.vprint(1,"    Caution: Replacing nodata nodes with zero altitude.")
            self.alt_dem[self.alt_dem==self.nodata]=0
        return

    def write_to_file(self,filename):
        self.alt_dem.tofile(filename)
        return
    
    def smoothen(self,smoothing_width):
        kernel=numpy.array(range(1,2*smoothing_width))
        kernel[smoothing_width:]=range(smoothing_width-1,0,-1)
        kernel=kernel/smoothing_width**2
        self.alt_dem=numpy.array(self.alt_dem)
        for _ in range(2):
            top_add=numpy.ones((smoothing_width,1)).dot(self.alt_dem[[0]]) 
            bottom_add=numpy.ones((smoothing_width,1)).dot(self.alt_dem[[-1]]) 
            self.alt_dem=numpy.vstack((top_add,self.alt_dem,bottom_add))
            self.alt_dem=self.alt_dem.transpose()
        for i in range(0,len(self.alt_dem)):
            self.alt_dem[i]=numpy.convolve(self.alt_dem[i],kernel,'same')
        self.alt_dem=self.alt_dem.transpose() 
        for i in range(0,len(self.alt_dem)):
            self.alt_dem[i]=numpy.convolve(self.alt_dem[i],kernel,'same')
        self.alt_dem=self.alt_dem.transpose()
        self.alt_dem=self.alt_dem[smoothing_width:-smoothing_width,smoothing_width:-smoothing_width]
        for i in range(smoothing_width):
            self.alt_dem[i]=i/smoothing_width*self.alt_dem[i]+(smoothing_width-i)/smoothing_width*self.alt_dem[i]
            self.alt_dem[-i-1]=i/smoothing_width*self.alt_dem[-i-1]+(smoothing_width-i)/smoothing_width*self.alt_dem[-i-1]
        for i in range(smoothing_width):
            self.alt_dem[:,i]=i/smoothing_width*self.alt_dem[:,i]+(smoothing_width-i)/smoothing_width*self.alt_dem[:,i]
            self.alt_dem[:,-i-1]=i/smoothing_width*self.alt_dem[:,-i-1]+(smoothing_width-i)/smoothing_width*self.alt_dem[:,-i-1]
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

    def alt_vec(self,way):
        Nx=self.nxdem-1
        Ny=self.nydem-1
        x=way[:,0]
        y=way[:,1]
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

    def alt_vec_road(self,way):
        return self.alt_vec(way+0.00005*weighted_normals(way))

    def alt_vec_mean(self,way):
        return self.alt_vec(way).mean()*numpy.ones(len(way))

    def alt_vec_nodata(self,way):
        return self.nodata*numpy.ones(len(way))

    def way_is_too_much_banked(self,way,limit):
        return (numpy.abs(self.alt_vec(way)-self.alt_vec_road(way))>=limit).any()
    
  
          
##############################################################################
def weighted_normals(way,side='left'):
    # traiter les cas de petits N !!!
    N=len(way)
    if N<2: return numpy.zeros(N)
    sign=numpy.array([[-1,1]]) if side=='left' else numpy.array([[1,-1]])
    tg=way[1:]-way[:-1]
    tg=tg/(1e-6+numpy.linalg.norm(tg,axis=1)).reshape(N-1,1)
    tg=numpy.vstack([tg,tg[-1]])   
    if N>2:
        scale=1e-6+numpy.linalg.norm(tg[1:-1]+tg[:-2],axis=1).reshape(N-2,1)
        #tg[1:-1]=2*(tg[1:-1]+tg[:-2])/(scale*numpy.maximum(scale,0.5))
        tg[1:-1]=(tg[1:-1]+tg[:-2])/(scale)
    if (way[0]==way[-1]).all():
        scale=1e-6+numpy.linalg.norm(tg[0]+tg[-1])
        #tg[0]=tg[-1]=2*(tg[0]+tg[-1])/(scale*numpy.maximum(scale,0.5))
        tg[0]=tg[-1]=(tg[0]+tg[-1])/(scale) 
    return  numpy.roll(tg,1,axis=1)*sign
##############################################################################

##############################################################################
def download_viewfinderpanorama(lat,lon):
    UI.vprint(1,"   No elevation file found, I download it from viewfinderpanorama (J. de Ferranti)")
    if (lat,lon) in ((44,5),(45,5),(46,5),(43,6),(44,6),(45,6),(46,6),(47,6),(43,7),(44,7),(45,7),
                     (46,7),(47,7),(45,8),(46,8),(47,8),(45,9),(46,9),(47,9),(45,10),(46,10),(47,10),
                     (45,11),(46,11),(47,11),(45,12),(46,12),(47,12),(46,13),(47,13),(46,14),(47,14),(46,15),(47,15)):
        url="http://viewfinderpanoramas.org/dem1/"+os.path.basename(FNAMES.viewfinderpanorama(lat,lon)).lower().replace('hgt','zip')
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
    s=requests.Session()
    dem_download_ok = False
    tentative=0
    while dem_download_ok != True and tentative<10:
        r=s.get(url)
        if ('Response [20' in str(r)):
            print("   Done. The zip archive will now be extracted in the Elevation_data dir.") 
            dem_download_ok=True
        else:
            tentative+=1 
            print("      Viewfinderpanorama server was busy, new tentative...")
            time.sleep(1)
    if tentative==10:
        return [numpy.zeros([1201,1201],dtype=numpy.float32),1201]
    zipfile=open(os.path.join(FNAMES.Tmp_dir,"viewfinderpanoramas.zip"),'wb')
    zipfile.write(r.content)
    zipfile.close()
    os.system(unzip_cmd+' e -y -o'+FNAMES.Elevation_dir+' "'+os.path.join(FNAMES.Tmp_dir,'viewfinderpanoramas.zip')+'"')
    os.remove(os.path.join(FNAMES.Tmp_dir,'viewfinderpanoramas.zip'))
    return 
    ##############################################################################
