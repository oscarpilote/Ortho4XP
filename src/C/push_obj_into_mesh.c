#include <stdio.h>
#include <string.h>

#include "mesh_defs.h"
#include "mesh_tile.h"
#include "mesh_io.h"
#include "mesh_split.h"

static int mtl_to_type(char* mtl)
{
	char *pos = strrchr(mtl,'_');
	if ( pos != NULL) {
		return atoi(++pos);
	} else {
		return 0;
	}
}

int main(int argc, char** argv) 
{
	TileParams tp;
	Mesh m;
	AffineT3 aff = {0,0,0,1,1,1};
	Mesh mbis;
	AffineT3 affbis;
	affbis.base_x = atof(argv[4]);
	affbis.base_y = atof(argv[5]);
	affbis.base_z = atof(argv[6]);
	affbis.scal_x = atof(argv[7]);
	affbis.scal_y = atof(argv[8]);
	affbis.scal_z = atof(argv[9]);
	int mesh_pos = atoi(argv[10]);
	if (read_tile_params_from_mesh_file(&tp, argv[1]) != 0) {
		printf("Could not deduce tile params from filename %s\n", argv[1]);
		printf("Aborting.\n");
		return -1;
	}
	if (read_mesh_from_mesh_file(&m, &aff, argv[1]) != 0) {
		printf("Error while reading mesh file %s\n", argv[1]);
		printf("Aborting.\n");
		return -1;
	}
	tp.zl = atoi(argv[2]);
	Grid g;
        webmercator_grid_from_tile_params(&tp, &g);
	MeshGrid mg;
	initialize_meshgrid_from_grid(&mg, &g);
	printf("Split\n");
	split_mesh_according_to_grid(&m, &g, &mg);
	printf("Dispose\n");
	dispose_mesh(&m);
	printf("Read from obj\n");
	read_mesh_from_obj_file(&mbis, &affbis, mtl_to_type, argv[3]); 
	printf("Dispose\n");
	dispose_mesh(&mg.meshes[mesh_pos]);
	mg.meshes[mesh_pos] = mbis;
	printf("Aggregate\n");
	aggregate_meshgrid_into_mesh(&mg, &m);
	printf("Dispose\n");
	dispose_meshgrid(&mg);
	//printf("Dispose\n");
	//dispose_mesh(&mbis);
	char filename[256];
	strcpy(filename, argv[1]);
	strcat(filename, ".new");
	printf("Write to file\n");
	write_mesh_to_mesh_file(&m, &aff, filename);
	dispose_mesh(&m);
	printf("Finished.\n");
	return 0;
}
