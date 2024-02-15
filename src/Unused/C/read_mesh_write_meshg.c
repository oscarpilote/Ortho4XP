#include <stdio.h>
#include <string.h>
#include "mesh_defs.h"
#include "mesh_io.h"
#include "mesh_tile.h"
#include "mesh_connectivity.h"
#include "mesh_strip.h"
#include "mesh_simplify.h"

int main(int argc,char** argv)
{
	TileParams tp;
	Mesh m;
	AffineT3 aff = {0,0,0,1,1,1};
	if (read_tile_params_from_mesh_file(&tp,argv[1]) != 0) {
		printf("Could not deduce tiles params from filename %s\n",argv[1]);
		printf("Aborting.\n");
		return -1;
	} else {
		printf("Tile params read ok.\n");
	}
	if (read_mesh_from_mesh_file(&m,&aff,argv[1])!=0) {
		printf("Error while reading mesh file %s\n",argv[1]);
		printf("Aborting.\n");
		return -1;
	} else {
		printf("Tile meshread ok.\n");
	}
	tp.zl=atoi(argv[2]);
	Grid g;
        webmercator_grid_from_tile_params(&tp,&g);
	Mesh mcut;
	cut_mesh_according_to_grid(&m,&g,&mcut);
	printf("Number of new triangles and vertices : %d %d\n",mcut.ntri,mcut.nvert);
	simplify_mesh(&mcut);
	char filename[256];
	strcpy(filename,argv[1]);
	strcat(filename,"c");
	if (write_mesh_to_mesh_file(&mcut, &aff, filename) != 0) {
		printf("Error while writing mesh file %s\n", filename);
		printf("Aborting.\n");
		return -1;
	}
	//MeshGrid mg;
	//initialize_meshgrid_from_grid(&mg,&g);
	//printf("Grid initialized ok.\n");
	//split_mesh_according_to_grid(&m,&g,&mg);
	//printf("Mesh split ok.\n");
	//for (int k=0;k<mg.nbr_mesh;++k) {
	//	stripify_mesh(&mg.meshes[k]);
	//}
	//strcpy(filename,argv[1]);
	//strcat(filename,"g");
	//write_tile_meshgrid_to_meshg_file(&mg, &tp, filename);
	printf("Finished.\n");
	return 0;
}
