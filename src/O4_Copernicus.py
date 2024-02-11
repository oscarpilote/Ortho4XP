import gdal
import O4_Geo_Utils as GEO

FTY_filename = './Copernicus_data/FTY_2015_100m_eu_03035_d02_full.tif'
TCD_filename = './Copernicus_data/TCD_2015_100m_eu_03035_d04_full.tif'
CLC_filename = './Copernicus_data/CLC2018_CLC2018_V2018_20.tif'

xmin = 900000
ymax = 5500000 
resol = 100

dico_fty = {1: 'broad', 2: 'needle', 3: 'mixed', 0: 'non-tree', 254: 'unclassifiable', 255: 'outside area'}
dico_clc = {
    111:'Continuous urban fabric',
    112:'Discontinuous urban fabric',
    121:'Industrial or commercial units',
    122:'Road and rail networks and associated land',
    123:'Port areas',
    124:'Airports',
    131:'Mineral extraction sites',
    132:'Dump sites',
    133:'Construction sites',
    141:'Green urban areas',
    142:'Sport and leisure facilities',
    211:'Non-irrigated arable land',
    212:'Permanently irrigated land',
    213:'Rice fields',
    221:'Vineyards',
    222:'Fruit trees and berry plantations',
    223:'Olive groves',
    231:'Pastures',
    241:'Annual crops associated with permanent crops',
    242:'Complex cultivation patterns',
    243:'Land principally occupied by agriculture with significant areas of natural vegetation',
    244:'Agro-forestry areas',
    311:'Broad-leaved forest',
    312:'Coniferous forest',
    313:'Mixed forest',
    321:'Natural grasslands',
    322:'Moors and heathland',
    323:'Sclerophyllous vegetation',
    324:'Transitional woodland-shrub',
    331:'Beaches dunes sands',
    332:'Bare rocks',
    333:'Sparsely vegetated areas',
    334:'Burnt areas',
    335:'Glaciers and perpetual snow',
    411:'Inland marshes',
    412:'Peat bogs',
    421:'Salt marshes',
    422:'Salines',
    423:'Intertidal flats',
    511:'Water courses',
    512:'Water bodies',
    521:'Coastal lagoons',
    522:'Estuaries',
    523:'Sea and ocean',
    999:'NODATA'
}

def tcd(lat, lon):
    (x,y) = GEO.transform('4326','3035',lon,lat)
    ds = gdal.Open(TCD_filename)
    rb = ds.GetRasterBand(1)
    return rb.ReadAsArray(int((x-xmin)/resol),int((ymax -y)/resol),1,1)[0,0]

def fty(lat, lon):
    (x,y) = GEO.transform('4326','3035',lon,lat)
    ds = gdal.Open(FTY_filename)
    rb = ds.GetRasterBand(1)
    return dico_fty[rb.ReadAsArray(int((x-xmin)/resol),int((ymax -y)/resol),1,1)[0,0]]

def clc(lat, lon):
    (x,y) = GEO.transform('4326','3035',lon,lat)
    ds = gdal.Open(CLC_filename)
    rb = ds.GetRasterBand(1)
    return dico_clc[rb.ReadAsArray(int((x-xmin)/resol),int((ymax -y)/resol),1,1)[0,0]]

def copernicus(lat, lon):
    return [clc(lat,lon),fty(lat,lon),tcd(lat,lon)]

if  __name__ == '__main__':
    import sys
    try:
        lat = float(sys.argv[1])
        lon = float(sys.argv[2])
        print(copernicus(lat,lon))
    except:
        print("Syntax : python3 src/O4_Copernicus.py lat lon")
        
        
    
