#pragma once
#include <stdlib.h>
#include "mesh_defs.h"

void compute_mesh_bounds(Mesh *m, int j, double bounds[2]) 
{
       double min = 1e99;
       double max = -1e99;
       j = j % 3;  
       for (int i = 0; i < m->nvert; i++) {
	       min = (min > m->vertices[i].coord[j]) ? m->vertices[i].coord[j] : min;
	       max = (max < m->vertices[i].coord[j]) ? m->vertices[i].coord[j] : max;
       }
       bounds[0] = min;
       bounds[1] = max;
}

// Reindex vertices according to triangles order, letting unused ones out.
int reindex_vertices_according_to_triangles_order(Mesh *m) 
{
	Vertex   *newvert = (Vertex   *) malloc(m->nvert * sizeof(Vertex));
	Normal   *newnorm = (Normal   *) malloc(m->nvert * sizeof(Vertex));
	uint32_t *newidx  = (uint32_t *) malloc(m->nvert * sizeof(uint32_t));
	if (newvert == NULL || newnorm == NULL || newidx == NULL) {
		free(newvert); free(newnorm); free(newidx);
		return -1;
	}
        for (int j = 0; j<m->nvert; ++j) newidx[j]=-1;
	uint32_t idxcur = 0;
	for (int j = 0; j<m->ntri; ++j) {
		if (newidx[m->triangles[j].v1] == -1) {
			newidx[m->triangles[j].v1] = idxcur;
			newvert[idxcur] = m->vertices[m->triangles[j].v1];
			newnorm[idxcur] = m->normals[m->triangles[j].v1];
			idxcur++;
		}
		m->triangles[j].v1 = newidx[m->triangles[j].v1];
		if (newidx[m->triangles[j].v2] == -1) {
			newidx[m->triangles[j].v2] = idxcur;
			newvert[idxcur] = m->vertices[m->triangles[j].v2];
			newnorm[idxcur] = m->normals[m->triangles[j].v2];
			idxcur++;
		}
		m->triangles[j].v2 = newidx[m->triangles[j].v2];
		if (newidx[m->triangles[j].v3] == -1) {
			newidx[m->triangles[j].v3] = idxcur;
			newvert[idxcur] = m->vertices[m->triangles[j].v3];
			newnorm[idxcur] = m->normals[m->triangles[j].v3];
			idxcur++;
		}
		m->triangles[j].v3 = newidx[m->triangles[j].v3];
	}
	free(m->vertices);
	free(m->normals);
	m->vertices = newvert;
	m->normals = newnorm;
	free(newidx);
	return 0;
};

