#pragma once
#include <stdlib.h>
#include <stdint.h>
#include "mesh_defs.h"
#include "mesh_connectivity.h"
#include "mesh_calcs.h"
#include "errors.h"


/******************************************************************************
 *
 *   I.   Forward declarations. 
 *
 * ***************************************************************************/

int stripify_mesh(Mesh *m);
int build_triangle_strips(Mesh *m, ConnectionMap *mc);
void update_next_available_tri(uint8_t * is_available, uint32_t * pnext_free);

/******************************************************************************
 *
 *   II.   Implementations. 
 *
 * ***************************************************************************/

int stripify_mesh(Mesh *m)
{
	ConnectionMap mc = {0,0,NULL,NULL};
	initialize_meshconnector(&mc, m->nvert, m->ntri);
	build_connectivity_map(m,&mc);
	build_triangle_strips(m,&mc);
	reindex_vertices_according_to_triangles_order(m);
	dispose_meshconnector(&mc);
	return 0;
}


int build_triangle_strips(Mesh *m, ConnectionMap *mc) 
{
	uint8_t *is_available = (uint8_t *) malloc((m->ntri + 1) * sizeof(uint8_t));
	Triangle *newtri = (Triangle *) malloc(m->ntri * sizeof(Triangle));
	if (is_available == NULL || newtri == NULL) {
		memoryerror();
		free(is_available); free(newtri);
		return -1;
	}
	for (int i = 0; i < m->ntri + 1; ++i) is_available[i] = 1;
	uint32_t cur = 0;
	uint8_t dir;
	uint32_t curtmp;
	uint8_t dirtmp;
	uint32_t next_available = 1;
	int total_strip = 0;
	int strip_len = 0;
	int in_strip = 0;
	while (cur < m->ntri) {
		*(newtri++) = m->triangles[cur];
		is_available[cur] = 0;
		strip_len++;
		if (cur == next_available) {
			update_next_available_tri(is_available, &next_available);
		}
		if (in_strip) {
			int odd = 1; //1-(strip_len&1);
			//assert(!is_available[mc->triconnect[3*cur+dir] & 0x3FFFFFFF]);
			curtmp =  mc->triconnect[3 * cur + ((dir + 2 - odd) % 3)];
			dirtmp =  curtmp >> 30;
			curtmp &= 0x3FFFFFFF;
			if (dirtmp != 3 && is_available[curtmp]) {
				cur = curtmp;
				dir = dirtmp;
				continue;
			}
			cur =  mc->triconnect[3 * cur + ((dir + 1 + odd) % 3)];
			dir =  cur >> 30;
			cur &= 0x3FFFFFFF;
			if (dir == 3 || !is_available[cur]) {
				cur = next_available;
				in_strip = 0;
				strip_len = 0;
				total_strip++;
			}
		} else { // new strip
			for (int j = 0; j < 3; ++j) {
				curtmp =  mc->triconnect[3 * cur + j];
				dirtmp =  curtmp >> 30;
				curtmp &= 0x3FFFFFFF;
				if (dirtmp != 3 && is_available[curtmp]) {
					in_strip = 1;
					cur = curtmp;
					dir = dirtmp;
					break;
				}
			}
			if (!in_strip) {
				cur = next_available;
				strip_len = 0;
				total_strip++;
			}
		}
	}
	free(is_available);
	newtri -= m->ntri;
	free(m->triangles);
	m->triangles = newtri;
	//printf("Average strip length : %lf\n",(double)m->ntri/total_strip);
	return total_strip;
}

void update_next_available_tri(uint8_t *is_available, uint32_t *pnext_free) 
{
	while (!is_available[*pnext_free]) ++(*pnext_free);
}


