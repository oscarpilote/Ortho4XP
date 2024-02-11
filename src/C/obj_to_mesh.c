#include <stdio.h>
#include <string.h>

#include "geo_transforms.h"
#include "mesh_io.h"

int main(int aqrgc, char **argv) {
	Mesh m;
	AffineT3 aff = {0,0,0,1,1,1};
	if (read_mesh_from_obj_file(&m, &aff, argv[1]) !=0 ) {
		printf("Error while reading obj file %s\n",argv[1]);
		printf("Aborting.\n");
		return -1;
	} else {
		printf("Obj file read ok.\n");
	}
	char filename[256];
	strcpy(filename, argv[1]);
	strcpy(filename + strlen(filename) - 3, "mesh\0");
	if (write_mesh_to_mesh_file(&m, &aff, filename) != 0) {
		printf("Error while writing mesh file %s\n", filename);
		printf("Aborting.\n");
		return -1;
	}
	return 0;
}
