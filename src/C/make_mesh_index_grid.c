#include <stdio.h>
#include <time.h>
//#include <string.h>
//#include "mesh_defs.h"
#include "mesh_io.h"
#include "mesh_tile.h"
//#include "mesh_connectivity.h"
#include "mesh_strip.h"
#include "mesh_simplify.h"
#include "mesh_index.h"

int point_in_tri(size_t id, void *arg)
{
    Mesh * m = * (Mesh **) arg;
    double *p = * (double **) ((size_t *) arg + 1); 
    double tol = ** (double **) ((size_t *) arg + 2);
    id--;
    Vertex v0 = m->vertices[m->triangles[id].v1];
    Vertex v1 = m->vertices[m->triangles[id].v2];
    Vertex v2 = m->vertices[m->triangles[id].v3];
    //printf("%f %f %f %f %f %f %f %f\n",v0.x,v0.y,v1.x,v1.y,v2.x,v2.y,p[0],p[1]);
    v1.x -= v0.x; 
    v2.x -= v0.x;
    double px = p[0] - v0.x;
    v1.y -= v0.y; 
    v2.y -= v0.y;
    double py = p[1] - v0.y;
    double d11 = v1.x * v1.x + v1.y * v1.y;
    double d12 = v1.x * v2.x + v1.y * v2.y;
    double d22 = v2.x * v2.x + v2.y * v2.y;
    double dp1 = v1.x * px + v1.y * py;
    double dp2 = v2.x * px + v2.y * py;
    double invDenom = 1.0 / (d11 * d22 - d12 * d12); 
    double v = (d22 * dp1 - d12 * dp2) * invDenom;
    double w = (d11 * dp2 - d12 * dp1) * invDenom;
    double u = 1.0 - v - w;
    //printf("%f %f %f\n",u,v,w);
    return -1 * (v >= tol && w >= tol && u >= tol);
}

int main(int argc, char** argv)
{
	clock_t begin;
	TileParams tp;
	begin = clock();
	if (read_tile_params_from_mesh_file(&tp, argv[1]) != 0) {
		printf("Could not deduce tiles params from filename %s\n", argv[1]);
		printf("Aborting.\n");
		return -1;
	} else {
		printf("Tile params read ok in %f sec.\n",(double) (clock()-begin) / CLOCKS_PER_SEC);
	}
	begin = clock();
	Mesh m;
	AffineT3 aff = {0,0,0,1,1,1};
	if (read_mesh_from_mesh_file(&m, &aff, argv[1]) != 0) {
		printf("Error while reading mesh file %s\n", argv[1]);
		printf("Aborting.\n");
		return -1;
	} else {
		printf("Tile meshread ok in %f sec.\n",(double) (clock()-begin) / CLOCKS_PER_SEC);
	}
	tp.zl = atoi(argv[3]);
	printf("Zoomlevel : %d\n", tp.zl); 
	begin = clock();
	Grid g;
        webmercator_grid_from_tile_params(&tp, &g);
  	MeshGrid mg;
	initialize_meshgrid_from_grid(&mg, &g);
	printf("Grid initialized ok.\n");
	split_mesh_according_to_grid(&m, &g, &mg);
	printf("Mesh split ok in %f sec, %d meshes.\n",(double) (clock()-begin) / CLOCKS_PER_SEC, mg.nbr_mesh);
	begin = clock();
	for (int k = 0; k < mg.nbr_mesh; ++k) {
		stripify_mesh(&mg.meshes[k]);
	}
	printf("Meshes strified ok in %f sec.\n",(double) (clock()-begin) / CLOCKS_PER_SEC);
	begin = clock();
	struct Node **allocated_nodes = (struct Node **) malloc(mg.nbr_mesh * sizeof(struct Node *));
	struct Node **roots = (struct Node **) malloc(mg.nbr_mesh * sizeof(struct Node *));
	for (int k = 0; k < mg.nbr_mesh; ++k) {
                next_allocated_node = (struct Node *) calloc(3 * mg.meshes[k].ntri, sizeof(struct Node));
		allocated_nodes[k] = next_allocated_node;
                roots[k] = create_mesh_index(&mg.meshes[k]); 
		//printf("Root level : %d\n", roots[k]->level);
	}
	printf("Mesh indexed ok in %f sec.\n",(double) (clock()-begin) / CLOCKS_PER_SEC);
	begin = clock();
	int max_tests = atoi(argv[2]);
	int bits = ceil(log2(max_tests) / 2);
	int N = (1 << bits);
	int Nmone = (1 << bits) - 1;
	struct Rect test_rect;
	size_t cbargs[3];
	double test_point[2];
	double tol;
	for (int l = 0; l < max_tests; ++l) {
	        double p,q;
		//test_point[0] = tp.lon + (double) rand() / RAND_MAX;
		//test_point[1] = tp.lat + (double) rand() / RAND_MAX;
		test_point[0] = tp.lon + (double) (l & Nmone) / N;
		test_point[1] = tp.lat + (double) (l / N) / N;
 		g.xy_to_grid(test_point[0], test_point[1], &p, &q, g.zl);
		int k = ((int)p - g.bounds[0]) + ((int)q - g.bounds[1]) * (g.bounds[2] - g.bounds[0]);  // row major 
		//printf("k : %d\n",k);
		//test_rect.boundary[0] = test_rect.boundary[2] = test_point[0];
		//test_rect.boundary[1] = test_rect.boundary[3] = test_point[1];
		test_rect.boundary[0] = test_point[0] - 0.00001;
		test_rect.boundary[2] = test_point[0] + 0.00001;
		test_rect.boundary[1] = test_point[1] - 0.00001;
		test_rect.boundary[3] = test_point[1] + 0.00001;
		cbargs[0] = (size_t) &(mg.meshes[k]);
                cbargs[1] = (size_t) &test_point[0]; 
		cbargs[2] = (size_t) &tol;
		//printf("Test point : %f %f\n",test_point[0],test_point[1]);
		//printf("Tri : %d  Tests : %d\n", mg.meshes[k].ntri, RTreeSearch(roots[k], &test_rect, point_in_tri, cbargs));
		tol = 0;
		while (RTreeSearch(roots[k], &test_rect, point_in_tri, cbargs) > 0) {
			tol = (tol < 0) ? tol * 10 : -0.001;
			if (tol < -1) {
				printf("Error : could not find containing triangle for %f %f !!!\n", test_point[0],test_point[1]);
				break;
			}
		}
	}
	printf("Search tests finished in %f sec, average %.1f Mops/sec\n",(double) (clock()-begin) / CLOCKS_PER_SEC, (double) max_tests / ((double) (clock()-begin)) * CLOCKS_PER_SEC / 1000000);
	printf("Finished.\n");
	return 0;
}
