#include "mesh_defs.h"
#include "mesh_calcs.h"
#include "hash_tables.h"

int simplify_mesh(Mesh *m)
{
	struct HashTable ht;
	double bounds[6];
	if (initialize_hashtable(&ht, (uint8_t) ceil(log2(m->nvert+1))+4, 2) != 0) {
		printf("Memory error\n");
		return -1;
	}
	compute_mesh_bounds(m, 0, bounds);
	compute_mesh_bounds(m, 1, bounds + 2);
	uint32_t *old_to_new = (uint32_t *) malloc(m->nvert * sizeof(uint32_t));
	uint32_t new_nvert;
	uint32_t new_ntri;
	Vertex *new_vert = (Vertex *) malloc(m->nvert * sizeof(Vertex));
	Normal *new_norm = (Normal *) malloc(m->nvert * sizeof(Normal));
	Triangle *new_tri = (Triangle *) malloc(m->ntri * sizeof(Triangle));
	for (int i = 0; i < m->nvert; ++i) {
		uint32_t keys[2];
		keys[0] = (uint32_t) ((m->vertices[i].x - bounds[0])/(bounds[1] - bounds[0]) * (1 << 24));
		keys[1] = (uint32_t) ((m->vertices[i].y - bounds[2])/(bounds[3] - bounds[2]) * (1 << 24));
		uint32_t hash = 31 * keys[0] + 17 * keys[1] + keys[0] * keys[1];
		old_to_new[i] = find_or_insert_in_hashtable(hash, keys, ht.size, &ht);
		if (old_to_new[i] == ht.size) {
			new_vert[old_to_new[i]] = m->vertices[i];
			new_norm[old_to_new[i]] = m->normals[i];
		}
	}
	new_nvert = ht.size;
	new_ntri = 0;
	for (int i = 0; i < m->ntri; ++i) {
		uint32_t v1 = old_to_new[m->triangles[i].v1];
		uint32_t v2 = old_to_new[m->triangles[i].v2];
		uint32_t v3 = old_to_new[m->triangles[i].v3];
		if ( v1 != v2 && v2 != v3 && v1 != v3 ) {
			new_tri[new_ntri].v1 = v1;
			new_tri[new_ntri].v2 = v2;
			new_tri[new_ntri].v3 = v3;
			new_tri[new_ntri].type = m->triangles[i].type;
			new_ntri++;
		}
	}
	printf("Final number of vertices : %d\n",new_nvert);	
	printf("Final number of triangles : %d\n",new_ntri);	
	return 0;
}
