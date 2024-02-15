// File : mesh.h
#pragma once 
#include <stdlib.h>
#include <stdint.h>


// A vertex is here simple a triple of doubles.
typedef union {
	struct {
		double x,y,z;
	};
		double coord[3];
} Vertex;

// A vertex normal is a couple of doubles (the third one can be recovered from 
// the requirement of unit length).
typedef struct {
	double nx,ny;
} Normal;

// We rely on the notion of indexed mesh: triangle vertices are refered to 
// by their index number (starting at 0). A triangle has an additional 
// (integer) type. 
typedef struct {
	uint32_t v1, v2, v3;
	int type;
} Triangle;


// The mesh structure is reduced to a minimum: a sequence of vertices 
// referenced by a sequence of (typed) triangles. 
typedef struct {
	uint32_t avert;  // allocated vertices
	uint32_t nvert;  // actual number of vertices
	uint32_t atri;   // allocated triangles
	uint32_t ntri;   // actual number of triangles
	Vertex* vertices;
	Normal* normals;
	Triangle* triangles;
} Mesh;

// An oriented edge. It refers to the indices of its extremities (v1 and v2), to
// the index of the mesh triangle on its left (tri) and the listing position of itself
// inside the afore mentioned triangle (i.e. either 0, 1 or 2).
typedef struct {
	uint32_t v1, v2;
	uint32_t tri;
	uint32_t triPos;
} Edge; 

void initialize_mesh(Mesh *m)
{
	m->avert = 0;
	m->nvert = 0;
	m->atri = 0;
	m->ntri = 0;
	m->vertices = NULL;
	m->normals = NULL;
	m->triangles = NULL;
}

void dispose_mesh(Mesh *m)
{
	if (m->avert > 0) {
		free(m->vertices);
		free(m->normals);
	}
	if (m->atri > 0) {
		free(m->triangles);
	}
	m->vertices = NULL;
	m->normals = NULL;
	m->triangles = NULL;
	m->avert = 0;
	m->nvert = 0;
	m->atri = 0;
	m->ntri = 0;
}

int reserve_mesh(Mesh *m, uint32_t avert, uint32_t atri)
{
	m->nvert = 0;
	m->ntri = 0;
	m->vertices = (Vertex *) malloc(avert * sizeof(Vertex));
	m->normals = (Normal *) malloc(avert * sizeof(Normal));
	m->avert = avert;
	m->triangles = (Triangle *) malloc(atri * sizeof(Triangle));
	m->atri = atri;
	if (m->vertices == NULL || m->normals == NULL || m->triangles == NULL) {
		dispose_mesh(m);
		return -1;
	}
	return 0;
}

int increase_mesh_capacity(Mesh *m, uint32_t plusvert, uint32_t plustri)
{
	Vertex *v = (Vertex *) realloc(m->vertices, (m->avert + plusvert) * sizeof(Vertex));
	if (v != NULL) {
		m->vertices = v;
	} else {
		return -1;
	}
	Normal *n = (Normal *) realloc(m->normals, (m->avert + plusvert) * sizeof(Normal));
	if (n != NULL) {
		m->normals = n;
	} else {
		// revert to initial state
		m->vertices = (Vertex *) realloc(m->vertices, m->avert * sizeof(Vertex));
		return -1;
	}
	Triangle *t = (Triangle *) realloc(m->triangles, (m->atri + plustri) * sizeof(Triangle));
	if (t != NULL) {
		m->triangles = t;
	} else {
		// revert to initial state
		m->vertices = (Vertex *) realloc(m->vertices, m->avert * sizeof(Vertex));
		m->normals = (Normal *) realloc(m->normals, m->avert * sizeof(Normal));
		return -1;
	}
	// update capacities
	m->avert += plusvert;
	m->atri += plustri;
	return 0;
}







