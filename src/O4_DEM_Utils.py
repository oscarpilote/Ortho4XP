import os
import io
import time
import requests
import zipfile
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

#default_dem_source='SRTM_1sec'
default_dem_source='viewfinderpanorama'

##############################################################################
class DEM():

    def __init__(self,lat,lon,file_name='',fill_nodata=True,info_only=False):
        self.lat=lat
        self.lon=lon
        self.load_data(file_name,info_only)
        if info_only: return 
        if fill_nodata:
            self.fill_nodata()
        else:
            self.nodata_to_zero()
        UI.vprint(1,"   Min altitude:",self.alt_dem.min(),", Max altitude:",self.alt_dem.max(),", Mean:",self.alt_dem.mean())

    def load_data(self,file_name='',info_only=False):
        if not file_name:
            if default_dem_source=='viewfinderpanorama':
                file_name=FNAMES.viewfinderpanorama(self.lat, self.lon)
                ensure_viewfinderpanorama(self.lat,self.lon)
            elif default_dem_source=='SRTM_1sec':
                file_name=FNAMES.SRTM_1sec(self.lat, self.lon)
                ensure_SRTM_1sec(self.lat,self.lon)
        if ('.hgt') in file_name or ('.HGT' in file_name):
            try:
                self.nxdem=self.nydem=int(round(sqrt(os.path.getsize(file_name)/2)))
                if not info_only: self.alt_dem=numpy.fromfile(file_name,numpy.dtype('>i2')).astype(numpy.float32).reshape((self.nxdem,self.nydem))
            except:
                UI.lvprint(1,"   ERROR: in reading elevation from", file_name, "-> replaced with zero altitude.") 
                self.nxdem=self.nydem=3601
                if not info_only: self.alt_dem=numpy.zeros([3601,3601],dtype=numpy.float32)
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
                if not info_only: self.alt_dem=numpy.asarray(alt,dtype=numpy.float32).reshape((self.nxdem,self.nydem))[::-1]
            except:
                UI.lvprint(1,"   ERROR: in reading elevation from", file_name, "-> replaced with zero altitude.") 
                self.nxdem=self.nydem=3601
                if not info_only: self.alt_dem=numpy.zeros([3601,3601],dtype=numpy.float32)
            self.x0=self.y0=0
            self.x1=self.y1=1
            self.epsg=4326
            self.nodata=-32768
        elif has_gdal:
            self.ds=gdal.Open(file_name)
            self.rs=self.ds.GetRasterBand(1)
            if not info_only: self.alt_dem=self.rs.ReadAsArray().astype(numpy.float32)
            (self.nxdem,self.nydem)=(self.ds.RasterXSize,self.ds.RasterYSize) 
            self.nodata=self.rs.GetNoDataValue()
            if self.nodata is None: 
                UI.vprint(1,"   WARNING: raster DEM does not advertise its no_data value, assuming -32768.")
                self.nodata=-32768
            else: # elevations being stored as float32, we push the nodata to that framework too
                self.nodata=numpy.float32(self.nodata)
            try: 
                self.epsg=int(self.ds.GetProjection().split('"')[-2])
            except:
                UI.vprint(1,"   WARNING: raster DEL does not advertise its EPSG code, assuming 4326.") 
                self.epsg=4326
            if self.epsg!=4326:
                UI.lvprint(1,"   WARNING: unsupported EPSG code ",self.epsg,". Only EPSG:4326 is supported, result is likely to be non sense.") 
            self.geo=self.ds.GetGeoTransform()
            self.x0=self.geo[0]+.5*self.geo[1]-self.lon
            self.y1=self.geo[3]+.5*self.geo[5]-self.lat
            self.x1=self.x0+(self.nxdem-1)*self.geo[1] 
            self.y0=self.y1+(self.nydem-1)*self.geo[5]  
        elif not has_gdal:
            UI.lvprint(1,"   WARNING: unsupported raster (install Gdal):", file_name, "-> replaced with zero altitude.") 
            self.nxdem=self.nydem=3601
            if not info_only: self.alt_dem=numpy.zeros([3601,3601],dtype=numpy.float32)
            self.x0=self.y0=0
            self.x1=self.y1=1
            self.epsg=4326
            self.nodata=-32768


    def fill_nodata(self):
        step=0
        while (self.alt_dem==self.nodata).any():
            if not step:
                UI.vprint(1,"   INFO: Elevation file contains voids, trying to fill them recursively by nearest neighbour.")       
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
                UI.vprint(1,"   WARNING: The hole seems to big to be filled as is... I'm filling the remainder with zero.")
                self.alt_dem[self.alt_dem==self.nodata]=0
                break
        if step: UI.vprint(1,"   Done.") 
        
    def nodata_to_zero(self):
        if self.nodata!=0 and (self.alt_dem==self.nodata).any():
            UI.vprint(1,"   INFO: Replacing nodata nodes with zero altitude.")
            self.alt_dem[self.alt_dem==self.nodata]=0
            self.nodata=0
        return
        
    def upsample_if_low_res(self):
        if not(self.nxdem==1201 and self.nydem==1201):
            return
        UI.vprint(2,'   INFO: Up-sampling raster DEM to 1" resolution')
        alt_dem_tmp=numpy.zeros((3601,3601),dtype=numpy.float32)
        for i in range(1201): 
            alt_dem_tmp[3*i,::3]=self.alt_dem[i]
            alt_dem_tmp[3*i,1::3]=2/3*self.alt_dem[i,:-1]+1/3*self.alt_dem[i,1:]
            alt_dem_tmp[3*i,2::3]=1/3*self.alt_dem[i,:-1]+2/3*self.alt_dem[i,1:]
            if i==1200: break
            alt_dem_tmp[3*i+1,::3]=2/3*self.alt_dem[i]+1/3*self.alt_dem[i+1]
            alt_dem_tmp[3*i+2,::3]=1/3*self.alt_dem[i]+2/3*self.alt_dem[i+1]
            alt_dem_tmp[3*i+1,1::3]=4/9*self.alt_dem[i][:-1]+2/9*self.alt_dem[i,1:]+2/9*self.alt_dem[i+1,:-1]+1/9*self.alt_dem[i+1,1:]
            alt_dem_tmp[3*i+2,1::3]=2/9*self.alt_dem[i][:-1]+1/9*self.alt_dem[i,1:]+4/9*self.alt_dem[i+1,:-1]+2/9*self.alt_dem[i+1,1:]
            alt_dem_tmp[3*i+1,2::3]=2/9*self.alt_dem[i][:-1]+4/9*self.alt_dem[i,1:]+1/9*self.alt_dem[i+1,:-1]+2/9*self.alt_dem[i+1,1:]
            alt_dem_tmp[3*i+2,2::3]=1/9*self.alt_dem[i][:-1]+2/9*self.alt_dem[i,1:]+2/9*self.alt_dem[i+1,:-1]+4/9*self.alt_dem[i+1,1:]
        self.alt_dem=alt_dem_tmp
        self.nxdem=self.nydem=3601

    def write_to_file(self,filename):
        self.alt_dem.astype(numpy.float32).tofile(filename)
        return
    
    def smoothen(self,smoothing_width,mask_im):
        #return
        if not smoothing_width: return
        if not mask_im: return
        UI.vprint(1,"   Smoothing elevation over airports.") 
        kernel=numpy.array(range(1,2*smoothing_width))
        kernel[smoothing_width:]=range(smoothing_width-1,0,-1)
        kernel=kernel/smoothing_width**2
        alt_dem_orig=self.alt_dem[:]
        for _ in range(2):
            top_add=numpy.ones((smoothing_width,1)).dot(self.alt_dem[[0]]) 
            bottom_add=numpy.ones((smoothing_width,1)).dot(self.alt_dem[[-1]]) 
            self.alt_dem=numpy.vstack((top_add,self.alt_dem,bottom_add))
            self.alt_dem=self.alt_dem.transpose()
        del(top_add); del(bottom_add)
        for i in range(0,len(self.alt_dem)):
            self.alt_dem[i]=numpy.convolve(self.alt_dem[i],kernel,'same')
        self.alt_dem=self.alt_dem.transpose() 
        for i in range(0,len(self.alt_dem)):
            self.alt_dem[i]=numpy.convolve(self.alt_dem[i],kernel,'same')
        self.alt_dem=self.alt_dem.transpose()
        self.alt_dem=self.alt_dem[smoothing_width:-smoothing_width,smoothing_width:-smoothing_width]
        for i in range(smoothing_width):
            self.alt_dem[i]=i/smoothing_width*self.alt_dem[i]+(smoothing_width-i)/smoothing_width*alt_dem_orig[i]
            self.alt_dem[-i-1]=i/smoothing_width*self.alt_dem[-i-1]+(smoothing_width-i)/smoothing_width*alt_dem_orig[-i-1]
        for i in range(smoothing_width):
            self.alt_dem[:,i]=i/smoothing_width*self.alt_dem[:,i]+(smoothing_width-i)/smoothing_width*alt_dem_orig[:,i]
            self.alt_dem[:,-i-1]=i/smoothing_width*self.alt_dem[:,-i-1]+(smoothing_width-i)/smoothing_width*alt_dem_orig[:,-i-1]
        if not mask_im.size==(self.nxdem,self.nydem):
            UI.vprint(2,"    Resizing airport mask.")
            mask_im=mask_im.resize((self.nxdem,self.nydem),Image.BICUBIC)
        mask=numpy.array(mask_im).astype(numpy.float32)/255
        mask=(mask>0).astype(numpy.float32)
        self.alt_dem=mask*self.alt_dem+(1-mask)*alt_dem_orig
        return
        
    def smoothen_2(self,smoothing_width,mask_im):
        if not smoothing_width: return
        if not mask_im: return
        UI.vprint(1,"   Smoothing elevation over airports.") 
        tmp = self.alt_dem[:]
        mask_array = numpy.array(mask_im)
        kernel=numpy.array(range(1,2*smoothing_width))
        kernel[smoothing_width:]=range(smoothing_width-1,0,-1)
        #kernel=kernel/smoothing_width**2
        tmp=tmp*mask_array
        tmpw=mask_array[:].astype(numpy.uint16)
        print(tmpw.max(),tmpw.min())
        for _ in range(2):
            top_add=numpy.ones((smoothing_width,1)).dot(tmp[[0]]) 
            bottom_add=numpy.ones((smoothing_width,1)).dot(tmp[[-1]]) 
            tmp=numpy.vstack((top_add,tmp,bottom_add))
            tmp=tmp.transpose()
            top_addw=numpy.ones((smoothing_width,1)).dot(tmpw[[0]]) 
            bottom_addw=numpy.ones((smoothing_width,1)).dot(tmpw[[-1]]) 
            tmpw=numpy.vstack((top_addw,tmpw,bottom_addw))
            tmpw=tmpw.transpose()
        del(top_add); del(bottom_add);del(top_addw); del(bottom_addw)
        for i in range(0,len(tmp)):
            tmp[i]=numpy.convolve(tmp[i],kernel,'same')
            tmpw[i]=numpy.convolve(tmpw[i],kernel,'same')
        tmp=tmp.transpose() 
        tmpw=tmpw.transpose() 
        for i in range(0,len(tmp)):
            tmp[i]=numpy.convolve(tmp[i],kernel,'same')
            tmpw[i]=numpy.convolve(tmpw[i],kernel,'same')
        tmp=tmp.transpose()
        tmpw=tmpw.transpose()
        tmp=tmp[smoothing_width:-smoothing_width,smoothing_width:-smoothing_width]
        tmpw=tmpw[smoothing_width:-smoothing_width,smoothing_width:-smoothing_width]
        print(tmpw[mask_array!=0].min(),tmpw[(mask_array)!=0].max())
        tmp[mask_array]=tmp[mask_array]/tmpw[mask_array]
        del(tmpw)
        for i in range(smoothing_width):
            tmp[i]=i/smoothing_width*tmp[i]+(smoothing_width-i)/smoothing_width*self.alt_dem[i]
            tmp[-i-1]=i/smoothing_width*tmp[-i-1]+(smoothing_width-i)/smoothing_width*self.alt_dem[-i-1]
        for i in range(smoothing_width):
            tmp[:,i]=i/smoothing_width*tmp[:,i]+(smoothing_width-i)/smoothing_width*self.alt_dem[:,i]
            tmp[:,-i-1]=i/smoothing_width*tmp[:,-i-1]+(smoothing_width-i)/smoothing_width*self.alt_dem[:,-i-1]
        self.alt_dem[mask_array]=tmp[mask_array]
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
    
    #def alt_vec_mean(self,way):
    #    return self.alt_vec(way).mean()*numpy.ones(len(way))
    
    #def alt_vec_shift(self,way,shift):
    #    return self.alt_vec(way+shift*GEO.m_to_lat*weighted_normals(way)) 
        
    
    #def way_is_too_much_banked(self,way,shift,limit):
    #    return (numpy.abs(self.alt_vec(way)-self.alt_vec_shift(way,shift))>=limit).any()
    
  
          
###############################################################################
#def weighted_normals(way,side='left'):
#    N=len(way)
#    if N<2: return numpy.zeros(N)
#    sign=numpy.array([[-1,1]]) if side=='left' else numpy.array([[1,-1]])
#    tg=way[1:]-way[:-1]
#    tg=tg/(1e-6+numpy.linalg.norm(tg,axis=1)).reshape(N-1,1)
#    tg=numpy.vstack([tg,tg[-1]])   
#    if N>2:
#        scale=1e-6+numpy.linalg.norm(tg[1:-1]+tg[:-2],axis=1).reshape(N-2,1)
#        #tg[1:-1]=2*(tg[1:-1]+tg[:-2])/(scale*numpy.maximum(scale,0.5))
#        tg[1:-1]=(tg[1:-1]+tg[:-2])/(scale)
#    if (way[0]==way[-1]).all():
#        scale=1e-6+numpy.linalg.norm(tg[0]+tg[-1])
#        #tg[0]=tg[-1]=2*(tg[0]+tg[-1])/(scale*numpy.maximum(scale,0.5))
#        tg[0]=tg[-1]=(tg[0]+tg[-1])/(scale) 
#    return  numpy.roll(tg,1,axis=1)*sign
###############################################################################

###############################################################################
#def convolve_periodic(way,kernel):
#    # way is expected to be closed, and way[0]==way[-1], the convolution is
#    # meant with respect to periodic variables
#    k=len(kernel)//2
#    return numpy.convolve(numpy.concatenate(way[-k-1:-1],way,way[1:k+1]),kernel,'valid')
    
    

##############################################################################
def ensure_SRTM_1sec(lat,lon): 
    # don't got further as long as cookie is not set!
    return
    out_filename= FNAMES.SRTM_1sec(lat,lon)  
    if os.path.exists(out_filename):
        UI.vprint(1,'   Recycling NASA SRTM 1" elevation data.')
        return 1
    UI.vprint(1,"   Downloading elevation data from USGS.")    
    s=requests.Session()
    tentative=0
    url="https://e4ftl01.cr.usgs.gov//MODV6_Dal_D/SRTM/SRTMGL1.003/2000.02.11/"+os.path.basename(FNAMES.viewfinderpanorama(lat,lon))[:-4]+".SRTMGL1.hgt.zip"
    while True: 
        try:
            print(url)
            r=s.get(url,timeout=10,headers={'Referer':'e4ftl01.cr.usgs.gov','Cookie':'DATA=[TODO:implement automatic cookie set up after user registration on USGS]'})
            if ('Response [20' in str(r)):
                break
            else:
                print(r,r.headers,str(r.content))
        except Exception as e:
            UI.vprint(2,e)
        tentative+=1
        if tentative==6: return 0
        UI.vprint(1,"      USGS server may be down or busy, new tentative in",2**tentative,"sec...")
        time.sleep(2**tentative)
    with zipfile.ZipFile(io.BytesIO(r.content),"r") as zip_ref:
        for f in zip_ref.filelist:
            fname=os.path.basename(f.filename)
            if not fname: continue
            if not os.path.isdir(os.path.dirname(out_filename)):
                os.makedirs(os.path.dirname(out_filename))
            with open(out_filename,"wb") as out:
                UI.vprint(2,"      Extracting",out_filename)
                out.write(zip_ref.open(f,"r").read())
    return    
##############################################################################    

##############################################################################
def ensure_viewfinderpanorama(lat,lon):
    if (lat,lon) in ((44,5),(45,5),(46,5),(43,6),(44,6),(45,6),(46,6),(47,6),(43,7),(44,7),(45,7),
                     (46,7),(47,7),(45,8),(46,8),(47,8),(45,9),(46,9),(47,9),(45,10),(46,10),(47,10),
                     (45,11),(46,11),(47,11),(45,12),(46,12),(47,12),(46,13),(47,13),(46,14),(47,14),(46,15),(47,15)):
        resol = 1                 
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
    if os.path.exists(FNAMES.viewfinderpanorama(lat,lon)) and (resol==3 or os.path.getsize(FNAMES.viewfinderpanorama(lat,lon))>=25934402):
        UI.vprint(1,"   Recycling Viewfinderpanoramas (J. de Ferranti) elevation data.")
        return 1
    UI.vprint(1,"   Downloading elevation data from Viewfinderpanoramas (J. de Ferranti).")    
    s=requests.Session()
    tentative=0
    while True: 
        try:
            r=s.get(url,timeout=10)
            if ('Response [20' in str(r)):
                break
        except Exception as e:
            UI.vprint(2,e)
        tentative+=1
        if tentative==6: return 0
        UI.vprint(1,"      Viewfinderpanoramas server may be down or busy, new tentative in",2**tentative,"sec...")
        time.sleep(2**tentative)
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
    return 
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














    
    
    
    
    
       
