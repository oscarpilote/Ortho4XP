#include "rtree/rtree.h"
#include "mesh_defs.h"

struct Rect triangle_bounds(Mesh *m, uint32_t i)
{
	struct Rect rect;
	Vertex vert;
	vert = m->vertices[m->triangles[i].v1];
	rect.boundary[0] = rect.boundary[2] = vert.x;
	rect.boundary[1] = rect.boundary[3] = vert.y;
	vert = m->vertices[m->triangles[i].v2];
	rect.boundary[0] = vert.x < rect.boundary[0] ? vert.x : rect.boundary[0];
	rect.boundary[2] = vert.x > rect.boundary[2] ? vert.x : rect.boundary[2];
	rect.boundary[1] = vert.y < rect.boundary[1] ? vert.y : rect.boundary[1];
	rect.boundary[3] = vert.y > rect.boundary[3] ? vert.y : rect.boundary[3];
	vert = m->vertices[m->triangles[i].v3];
	rect.boundary[0] = vert.x < rect.boundary[0] ? vert.x : rect.boundary[0];
	rect.boundary[2] = vert.x > rect.boundary[2] ? vert.x : rect.boundary[2];
	rect.boundary[1] = vert.y < rect.boundary[1] ? vert.y : rect.boundary[1];
	rect.boundary[3] = vert.y > rect.boundary[3] ? vert.y : rect.boundary[3];
	return rect;
}



struct Node * create_mesh_index(Mesh *m)
{
	struct Rect rect; 
	struct Node *root = RTreeNewIndex();
	for (int i = 0; i < m->ntri; ++i) {
		rect = triangle_bounds(m, i);
		RTreeInsertRect(&rect, i+1, &root, 0);
	}
	return root;
}
	

