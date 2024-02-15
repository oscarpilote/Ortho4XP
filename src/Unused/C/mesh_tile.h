#pragma once
#include "mesh_split.h"
#include "geo_transforms.h"
#include "mesh_io.h"

typedef struct {
	int lon, lat;
	int zl;
	double mesh_version;
} TileParams;


int set_lon_lat_from_file_name(int *lon, int *lat, char *filename) {
	char *pos;
        if (((pos = strrchr(filename,'/')) != NULL) || ((pos=strrchr(filename,'\\')) != NULL)) {
		pos += 1;
	} else {
		pos = filename;
	}	
	if (sscanf(pos,"Data%d%d.mesh",lat,lon)!=2) {
		printf("Could not read lat or lon from file name.\n");
		return 1;
	}
	return 0;
}

#define LINE 64
int read_tile_params_from_mesh_file(TileParams *tp, char* filename)
{
	if (set_lon_lat_from_file_name(&tp->lon, &tp->lat,filename)!=0) return 1;
	FILE *f=fopen(filename,"r");
	if (f==NULL) return 1;
	char	line[LINE];
	fgets(line,LINE,f);
	int info = sscanf(line,"%*s %lf %d\n",&tp->mesh_version,&tp->zl);
	if (info==0) {
		tp->mesh_version=1.2;
		tp->zl=19;
	} else if (info==1) {
		tp->zl=18;
	}
	fclose(f);
	return 0;
}
#undef LINE 



void webmercator_grid_from_tile_params(TileParams *tp, Grid *g)
{
        g->zl = tp->zl;
	double eps = 1e-6;
	double pmin, pmax, qmin, qmax;
	wgs84_to_orthogrid(tp->lon+eps, tp->lat+1-eps, &pmin, &qmin, tp->zl);
	wgs84_to_orthogrid(tp->lon+1-eps, tp->lat+eps, &pmax, &qmax, tp->zl);
	g->bounds[0] = (int)pmin;
	g->bounds[1] = (int)qmin;
	g->bounds[2] = (int)pmax + 1;
	g->bounds[3] = (int)qmax + 1;
	g->xy_to_grid = &wgs84_to_orthogrid_with_snap;
	g->grid_to_xy = &orthogrid_to_wgs84_with_snap;
}


int write_tile_meshgrid_to_meshg_file(const MeshGrid *mg, const TileParams *tp, const char* filename)
{
	FILE *f;
        if ((f = fopen(filename,"wb")) == NULL) goto write_fail;
	if (fwrite(&tp->lon,sizeof(int),1,f)!=1) goto write_fail;
	if (fwrite(&tp->lat,sizeof(int),1,f)!=1) goto write_fail;
	if (fwrite(&tp->zl,sizeof(int),1,f)!=1) goto write_fail;
	if (fwrite(&tp->mesh_version,sizeof(double),1,f)!=1) goto write_fail;
	for (int k=0;k<mg->nbr_mesh;++k) {
		if (write_mesh_to_meshg_file(&mg->meshes[k],&mg->scals[k],f)!=0) goto write_fail;
	}
	fclose(f);
	return 0;
write_fail:
	printf("Error while tempting to write to %s\n",filename);
	if (f!=NULL) fclose(f);
	return 1;
}




