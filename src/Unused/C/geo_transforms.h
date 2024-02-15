#pragma once

#include <math.h>

#define earth_radius = 6378137.0
#define lat_to_m     = M_PI*earth_radius/180.0
#define m_to_lat     = 1.0/lat_to_m

typedef struct {
	double base_x, base_y;
	double scal_x, scal_y;
} AffineT2;

typedef struct {
	double base_x, base_y, base_z;
	double scal_x, scal_y, scal_z;
} AffineT3;

void  wgs84_to_orthogrid(double lon, double lat, double *x, double *y, int zl)
{
	double mult = 1 << (zl - 5);
	*x = (1.0 + lon / 180.0) * mult;
	*y = (1.0 - log(tan((lat + 90.0) * M_PI / 360)) / M_PI) * mult;
}

void  wgs84_to_orthogrid_with_snap(double lon, double lat, double *x, double *y, int zl)
{
	wgs84_to_orthogrid(lon, lat, x, y, zl);
	*x = (fabs(*x - round(*x)) > 0.0001) ? *x : round(*x);
	*y = (fabs(*y - round(*y)) > 0.0001) ? *y : round(*y);
}

void  orthogrid_to_wgs84(double x, double y, double *lon, double *lat, int zl)
{
	double mult = ldexp(1.0 , 5 - zl);
	*lon =	(x*mult-1)*180.0;
	*lat =	360 / M_PI * atan(exp(M_PI * (1 - y * mult))) - 90.0;  
}

void  orthogrid_to_wgs84_with_snap(double x, double y, double *lon, double *lat, int zl)
{
	orthogrid_to_wgs84(x, y, lon, lat, zl);
	*lon = (fabs(*lon - round(*lon)) > 0.000001) ? *lon : round(*lon);
	*lat = (fabs(*lat - round(*lat)) > 0.000001) ? *lat : round(*lat);
}


