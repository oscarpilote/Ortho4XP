import gdal, numpy, sys, os
from PIL import Image,ImageFilter

def build_dtm_mask(t_bbox,t_size,region_mask_name,blur_radius=0):
    (region_name,epsg_code,xmin,ymax,xmax,ymin)=os.path.basename(region_mask_name).split('_')[0:6]
    xmin=float(xmin); xmax=float(xmax); ymin=float(ymin); ymax=float(ymax)
    (x0,y0,x1,y1)=t_bbox
    if x0>xmax or x1<xmin or y0<ymin or y1>ymax:
        return False
    mask_im=Image.open(region_mask_name).convert("L")
    (sizex,sizey)=mask_im.size
    pxx0=int((x0-xmin)/(xmax-xmin)*sizex)
    pxx1=int((x1-xmin)/(xmax-xmin)*sizex)
    pxy0=int((ymax-y0)/(ymax-ymin)*sizey)
    pxy1=int((ymax-y1)/(ymax-ymin)*sizey)
    small_im=mask_im.crop((pxx0,pxy0,pxx1,pxy1))
    if small_im.getbbox():
        if blur_radius: 
            return small_im.resize(t_size).filter(ImageFilter.GaussianBlur(blur_radius))
        else:
            print(t_size)
            return small_im.resize(t_size)
    else:
        return False

def build_composite_dtm(lat,lon,outfilename,dtm_list,fill_steps):
    # all dems are assumed to be of the same size and extent
    dtm_arrays=[]
    dtm_masks=[]
    for (dtm,no_data,region_mask) in dtm_list:    
        print(dtm,no_data,region_mask)
        dtm_ds=gdal.Open(dtm)
        dtm_rs=dtm_ds.GetRasterBand(1)
        dtm_array = dtm_rs.ReadAsArray()
        dtm_mask = numpy.array(build_dtm_mask((lon,lat+1,lon+1,lat),dtm_array.shape,region_mask),dtype=numpy.uint8)
        print(dtm_mask.max(),dtm_mask.min())
        if dtm_mask is False: print("No data mask value for ",dtm,", skipping it."); continue
        no_data=dtm_rs.GetNoDataValue()
        print(numpy.sum(dtm_array==no_data))
        for i in range(fill_steps):
            print(i)
            alt10=numpy.roll(dtm_array,1,axis=0)
            alt10[0]=dtm_array[0]
            alt20=numpy.roll(dtm_array,-1,axis=0)
            alt20[-1]=dtm_array[-1]
            atemp=numpy.maximum(alt10,alt20)
            del(alt10)
            del(alt20)
            alt01=numpy.roll(dtm_array,1,axis=1)
            alt01[:,0]=dtm_array[:,0]
            atemp=numpy.maximum(atemp,alt01)
            del(alt01)
            alt02=numpy.roll(dtm_array,-1,axis=1)
            alt02[:,-1]=dtm_array[:,-1]
            atemp=numpy.maximum(atemp,alt02)
            del(alt02)
            atemp[atemp<=400]=no_data
            dtm_array[dtm_array==no_data]=atemp[dtm_array==no_data]
            del(atemp)
        print(numpy.sum(dtm_array==no_data))
        dtm_mask[dtm_array==no_data]=0
        dtm_arrays.append(dtm_array)
        dtm_masks.append(dtm_mask)
    masks_sum=numpy.zeros(dtm_array.shape,dtype=numpy.uint16)
    for dtm_mask in dtm_masks:
        masks_sum+=dtm_mask
    #if masks_sum==0:
    #    print("Warning, some pixel is not covered by any data value !!!")
    #    sys.exit()
    print(masks_sum.max())
    dtm_composite=numpy.zeros(dtm_array.shape,dtype=numpy.float32)
    for (dtm_array,dtm_mask) in zip(dtm_arrays,dtm_masks):
        dtm_composite+=dtm_array*dtm_mask
    dtm_composite[masks_sum!=0]/=masks_sum[masks_sum!=0]
    # we assume that after our slight hole-filling, the only remaining totally no_data zones is the sea, and put it to zero
    dtm_composite[masks_sum==0]=0
    del(masks_sum)
    del(dtm_array)
    del(dtm_arrays)
    del(dtm_masks)
    driver = gdal.GetDriverByName("GTiff")
    rows,cols=dtm_composite.shape
    outdata = driver.Create(outfilename, rows, cols, 1, gdal.GDT_Float32)
    outdata.GetRasterBand(1).WriteArray(dtm_composite)
    outdata.FlushCache()
       

if __name__ == '__main__':
     lat=int(sys.argv[1])
     lon=int(sys.argv[2])
     outfilename=sys.argv[3]
     fill_steps=int(sys.argv[4])
     dtm_list=[]
     for i in range((len(sys.argv)-5)//3):
         dtm_list.append(sys.argv[5+3*i:5+3*i+3])
     build_composite_dtm(lat,lon,outfilename,dtm_list,fill_steps)
     
     
