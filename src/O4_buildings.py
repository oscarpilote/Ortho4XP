from math import atan2, pi
import numpy
from shapely import geometry, affinity


##############################################################################
def min_bounding_rectangle(pol):
    pol=pol.convex_hull
    way=numpy.array(pol.exterior.coords) 
    edges=way[1:]-way[:-1]
    min_area=9999999
    for i in range(len(edges)):
        angle=atan2(edges[i,1],edges[i,0])
        (xmin,ymin,xmax,ymax)=affinity.rotate(pol,-1*angle,origin=tuple(way[i]),use_radians=True).bounds
        test_area=(ymax-ymin)*(xmax-xmin)
        if test_area<min_area:
            min_area=test_area
            ret_val=(i,angle,xmin,ymin,xmax,ymax)
    (i,angle,xmin,ymin,xmax,ymax)=ret_val
    if (xmax-xmin) >= (ymax-ymin):
        L = xmax - xmin
        l = ymax - ymin
        azimuth = (180 / pi * angle) + 360 * (angle < 0)
    else: 
        L = ymax - ymin
        l = xmax - xmin
        azimuth = (180 / pi * angle) + 90
        if azimuth < 0: azimuth += 360
    return (affinity.rotate(geometry.box(xmin, ymin, xmax, ymax), angle,origin=tuple(way[i]), use_radians=True), L, l, azimuth)
##############################################################################  


