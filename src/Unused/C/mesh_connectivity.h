#pragma once

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include "mesh_defs.h"

typedef struct {
	uint32_t nvert;
	uint32_t ntri;
	uint32_t * triconnect;
	uint32_t * vconnect;
} ConnectionMap;

// El cheapo (fast) hash table with open addressing. Will be initialized with 6
// times the total triangle count. That number could be lowered towards 1.5 
// (the theoretical minimum), but it would slow down the process, especially below 2.0. 
typedef struct {  	
	Edge * table;
	uint32_t  capacity;
	uint32_t  bits;
	uint32_t  numElems;	
} EdgeTable;



/******************************************************************************
 *
 *   I.   Forward declarations. 
 *
 * ***************************************************************************/


int initialize_meshconnector(ConnectionMap * mc, size_t nvert, size_t ntri); 
void print_meshconnector(Mesh *m, ConnectionMap *mc);
void reset_meshconnector(ConnectionMap * mc);
void dispose_meshconnector(ConnectionMap * mc); 
int build_connectivity_map(Mesh *m, ConnectionMap *mc);
void check_or_set_companion_edge(EdgeTable * edge_t, Edge edge, uint32_t pos, uint32_t * triconnect);
uint32_t hash_edge(uint32_t v1, uint32_t v2);


/******************************************************************************
 *
 *   II.   Implementations. 
 *
 * ***************************************************************************/

int initialize_meshconnector(ConnectionMap * mc, size_t nvert, size_t ntri) 
{
	if (mc->vconnect==NULL) {
		mc->vconnect = (uint32_t *) malloc(nvert*sizeof(uint32_t));
	} else if (mc->nvert < nvert) {
		mc->vconnect = (uint32_t *) realloc(mc->vconnect,nvert*sizeof(uint32_t));
	}
	if (mc->vconnect==NULL) {
		memoryerror();
		return -1;
	}
	for (int i=0;i<nvert;++i) mc->vconnect[i]=0;
	if (mc->triconnect==NULL) {
		mc->triconnect = (uint32_t *) malloc(3*ntri*sizeof(uint32_t));
	} else if (mc->ntri < ntri) {
		mc->triconnect = (uint32_t *) realloc(mc->triconnect,3*ntri*sizeof(uint32_t));
	}
	if (mc->triconnect==NULL) {
		memoryerror();
		free(mc->vconnect);
		return -1;
	}
	for (int i=0;i<3*ntri;++i) {
		mc->triconnect[i]=0xFFFFFFFF;
	}
	mc->nvert=nvert;
	mc->ntri=ntri;
	return 0;
}

void print_meshconnector(Mesh *m, ConnectionMap *mc) 
{
	for (int i=0;i<m->ntri;++i) {
		printf("%d: %d %d, %d %d, %d %d\n",i,
				mc->triconnect[3*i] & 0x3FFFFFFF, mc->triconnect[3*i] >> 30,
				mc->triconnect[3*i+1] & 0x3FFFFFFF, mc->triconnect[3*i+1] >> 30,
				mc->triconnect[3*i+2] & 0x3FFFFFFF, mc->triconnect[3*i+2] >> 30
		      );
	}
}


void reset_meshconnector(ConnectionMap * mc) 
{
	for (int i=0;i<mc->nvert;++i) mc->vconnect[i]=0;
	for (int i=0;i<3*mc->ntri;++i) mc->triconnect[i]=0xFFFFFFFF;
}

void dispose_meshconnector(ConnectionMap * mc) 
{
	free(mc->vconnect);
	free(mc->triconnect);
}

int build_connectivity_map(Mesh *m, ConnectionMap *mc) 
{
	EdgeTable edge_t;
	edge_t.bits = (int) ceil(log2(4*m->ntri+1));
	edge_t.capacity = 1 << edge_t.bits;
	edge_t.table = (Edge *) malloc(edge_t.capacity*sizeof(Edge));
	if (edge_t.table==NULL) {
		memoryerror();
		return -1;
	}
	for (int i=0;i<edge_t.capacity;++i) edge_t.table[i].v1=0xFFFFFFFF;
	for (uint32_t i=0; i < m->ntri; ++i) {
		uint32_t v1,v2,v3;
		v1=m->triangles[i].v1;
		v2=m->triangles[i].v2;
		v3=m->triangles[i].v3;
		check_or_set_companion_edge(&edge_t, (Edge) {v1,v2,i,0}, hash_edge(v1,v2), mc->triconnect);
		check_or_set_companion_edge(&edge_t, (Edge) {v2,v3,i,1}, hash_edge(v2,v3), mc->triconnect);
		check_or_set_companion_edge(&edge_t, (Edge) {v3,v1,i,2}, hash_edge(v3,v1), mc->triconnect); 
		mc->vconnect[m->triangles[i].v1]+=1;
		mc->vconnect[m->triangles[i].v2]+=1;
		mc->vconnect[m->triangles[i].v3]+=1;
	}
	free(edge_t.table);
	return 0;
}

void check_or_set_companion_edge(EdgeTable * edge_t, Edge edge, uint32_t pos, uint32_t * triconnect) 
{
	while (1) {
		pos = pos & ((1<<edge_t->bits)-1); 
		Edge edge2= edge_t->table[pos];
		if ((edge2.v2 == edge.v1) && (edge2.v1 == edge.v2)) {
			triconnect[3*edge.tri+edge.triPos]=edge2.tri+(edge2.triPos<<30);  // most 2 significants
			triconnect[3*edge2.tri+edge2.triPos]=edge.tri+(edge.triPos<<30);  // bits used for triPos info  (-> effectively limits the maximum number of tris to 2^30)
			break;
		}
		if (edge2.v1==0xFFFFFFFF) {  // empty spot
			edge_t->table[pos]=edge;
			edge_t->numElems +=1;
			break;
		}
		pos++;
	}
}

// It is important to use unsigned types here because the hash will typically overflow for ints.
uint32_t hash_edge(uint32_t v1, uint32_t v2) 
{
	//return 32654435769*(v1+v2); Knuth's golden hash is no better here than product.
	return ((++v1)*(++v2));
}




