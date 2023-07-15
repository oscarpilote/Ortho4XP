#include <stdio.h>
#include <time.h>
//#include <string.h>
#include "mesh_index.h"
//#include "mesh_defs.h"
#include "mesh_io.h"
#include "mesh_tile.h"
//#include "mesh_connectivity.h"
#include "mesh_strip.h"
//#include "mesh_simplify.h"

int point_in_tri(size_t id, void *arg)
{
    Mesh * m = * (Mesh **) arg;
    double *p = * (double **) ((size_t *) arg + 1); 
    double tol = ** (double **) ((size_t *) arg + 2);
    if (tol < -0.001) printf("Tol : %f\n",tol);
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
    return (v >= tol && w >= tol && u >= tol) ? (int) ++id : 0;
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
	//begin = clock();
	//if (stripify_mesh(&m)!= 0) {
	//	printf("Error while stripifying mesh.\n");
	//	printf("Aborting.\n");
	//	return -1;
	//} else {
	//	printf("Mesh stripified ok in %f sec.\n",(double) (clock()-begin) / CLOCKS_PER_SEC);
	//}
	
	begin = clock();
	struct Node *root = calloc(3*m.ntri, sizeof(struct Node));
	assert(root);
	next_allocated_node = root;
        root = create_mesh_index(&m); 
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
	size_t last_hit = 1;
	for (int k = 0; k < max_tests; ++k) {
	        double p,q;
		//test_point[0] = tp.lon + (double) rand() / RAND_MAX;
		//test_point[1] = tp.lat + (double) rand() / RAND_MAX;
		test_point[0] = tp.lon + (double) (k & Nmone) / N / 10;
		test_point[1] = tp.lat + (double) (k / N) / N / 10;
		test_rect.boundary[0] = test_point[0] - 0.00001;
		test_rect.boundary[2] = test_point[0] + 0.00001;
		test_rect.boundary[1] = test_point[1] - 0.00001;
		test_rect.boundary[3] = test_point[1] + 0.00001;
		cbargs[0] = (size_t) &m;
                cbargs[1] = (size_t) &test_point[0]; 
		cbargs[2] = (size_t) &tol;
		tol = 0;
		if (point_in_tri(last_hit, cbargs)) {
			continue;
		} 
		//printf("Test point : %f %f\n",test_point[0],test_point[1]);
		while (!(last_hit = RTreeSearch(root, &test_rect, point_in_tri, cbargs))) {
			tol = (tol < 0) ? tol * 10 : -0.001;
			if (tol < -1) {
				printf("Error : could not find containing triangle for %f %f !!!\n", test_point[0],test_point[1]);
				last_hit = 1;
				break;
			}
		}
		//printf("Succes with last_hit = %d\n",last_hit);
	}
	printf("Search tests finished in %f sec, average %.1f Mops/sec\n",(double) (clock()-begin) / CLOCKS_PER_SEC, (double) max_tests / ((double) (clock()-begin)) * CLOCKS_PER_SEC / 1000000);
	printf("Finished.\n");
	return 0;
}
