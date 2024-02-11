#pragma once
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <string.h>
#include <assert.h>

#include "mesh_defs.h"
#include "geo_transforms.h"
#include "txt_io_fast.h"
#include "errors.h"
#include "hash_tables.h"


/******************************************************************************
 *
 *   I.   Forward declarations. 
 *
 *****************************************************************************/

int read_mesh_from_mesh_file (Mesh *m, const AffineT3 *aff, const char* filename);
int write_mesh_to_mesh_file  (const Mesh *m, const AffineT3 *aff, const char* filename);
int read_mesh_from_meshg_file(Mesh *m, const AffineT3 *aff, FILE *f); 
int write_mesh_to_meshg_file (const  Mesh *m, const AffineT3 *aff, FILE *f);


int read_mesh_from_obj_file(Mesh *m, const AffineT3 *aff, int (*mtl_to_type)(char*), const char* filename); 
int write_mesh_to_obj_file(const Mesh *m, const AffineT3 *aff, void (*type_to_mtl)(int, char*), const char* filename); 

/******************************************************************************
 *
 *   II.   Implementations. 
 *
 *****************************************************************************/

#define LINE 64
int read_mesh_from_mesh_file(Mesh *m, const AffineT3 *aff, const char* filename) 
{
	FILE *f = fopen(filename,"r");
	if (f == NULL) return 1;
	char	line[LINE];
	for (int i = 0; i < 5; ++i) {
		fgets(line, LINE, f);
	}
	sscanf(line, "%d \n", &m->nvert);
	printf("Number of nodes: %d\n", m->nvert);
	m->vertices = (Vertex*) malloc(m->nvert * sizeof(Vertex));
	if (m->vertices == NULL) goto memory_fail;
	m->avert = m->nvert;
	char *subline;
	for (int i = 0; i < m->nvert; ++i) {
		fgets(line, LINE, f);
		subline=line;
		m->vertices[i].x = aff->base_x + aff->scal_x * quick_strtod(&subline, ' ');
		m->vertices[i].y = aff->base_y + aff->scal_y * quick_strtod(&subline, ' ');
		m->vertices[i].z = aff->base_z + aff->scal_z * quick_strtod(&subline, ' ');
	}
	for (int i = 3; i--; ) {
		fgets(line, LINE, f);
	}
	m->normals = (Normal*) malloc(m->nvert * sizeof(Normal));
	if (m->normals == NULL) goto memory_fail;
	for (int i = 0; i < m->nvert; ++i) {
		fgets(line, LINE, f);
		subline = line;
		m->normals[i].nx = quick_strtod(&subline, ' ');
		m->normals[i].ny = quick_strtod(&subline, '\n');
	}
	for (int i = 2; i--; ) {
		fgets(line, LINE, f);
	}
	fgets(line, LINE, f);
	sscanf(line, "%d", &m->ntri);
	printf("Number of triangles: %d\n", m->ntri);
	m->triangles = (Triangle*) malloc(m->ntri * sizeof(Triangle));
	if (m->triangles == NULL) goto memory_fail;
	m->atri = m->ntri;
	for (int i = 0; i < m->ntri; ++i) {
		fgets(line, LINE, f);
		subline=line;
		m->triangles[i].v1 = quick_strtou(&subline, ' ')-1;
		m->triangles[i].v2 = quick_strtou(&subline, ' ')-1;
		m->triangles[i].v3 = quick_strtou(&subline, ' ')-1;
		m->triangles[i].type = quick_strtou(&subline, '\n');
	}
	fclose(f);
	return 0;
memory_fail:
	fclose(f);
	memoryerror();
	dispose_mesh(m); 
	return -1;
}
#undef LINE

int write_mesh_to_mesh_file  (const Mesh *m, const AffineT3 *aff, const char* filename)
{
	FILE *f = fopen(filename,"w");
	if (f == NULL) return 1;
	fprintf(f,"MeshVersionFormatted 1.30\n");
	fprintf(f,"Dimension 3\n\n");
	fprintf(f,"Vertices\n");
	fprintf(f,"%d\n",m->nvert);
	for (int i = 0; i < m->nvert; ++i) {
		fprintf(f,"%lf %lf %lf 0\n",m->vertices[i].x,m->vertices[i].y,m->vertices[i].z);
	}
	fprintf(f,"\n");
	fprintf(f,"Normals\n");
	fprintf(f,"%d\n",m->nvert);
	for (int i = 0; i < m->nvert; ++i) {
		fprintf(f, "%lf %lf\n", m->normals[i].nx, m->normals[i].ny);
	}
	fprintf(f,"\n");
	fprintf(f,"Triangles\n");
	fprintf(f,"%d\n",m->ntri);
	for (int i = 0; i < m->ntri; ++i) {
		fprintf(f,"%d %d %d %d\n", m->triangles[i].v1+1, m->triangles[i].v2+1, m->triangles[i].v3+1, m->triangles[i].type);
	}
	fclose(f);
	return 0;
}

// To optimize disk space in serialization, vertices (resp. normals)
// are encoded with uint16 (resp. int8) integer coordinates.
// The latter are relative to the mesh_bucket AffineT3,
// with the formula:
//
//      abs_coord = base + (int_coord*scal)/(2^k-1),
//
// where k=16 (resp. 8).
// Note that this may induce some snapping. Note also that vertex integer 
// coordinates are unsigned while normals integer coordinates are signed.
// Regarding vertex indices in triangles, they are encoded with
// 16bits if the total number of vertices in the bucket allows, else with 
// 32bits. The order in the file is always tri0.v1 tri0.v2 tri0.v3
// ... triN.v1 triN.v2 triN.v3 tri0.type ... triN.type
// since this is likely to be lower entropy and therefore
// better 7z compressible. 
int read_mesh_from_meshg_file( Mesh *m, const  AffineT3 *aff, FILE *f) 
{
	// Nbr of vertices
	if (fread(&m->nvert, sizeof(uint32_t), 1, f) != 1) return 1;
	// Vertices
	size_t memsize=m->nvert * sizeof(uint32_t);
	void *mem = malloc(memsize);
	if (mem == NULL) return 1;
	uint16_t *u16= (uint16_t*) mem;
	if (fread(u16, sizeof(uint16_t), m->nvert, f) != m->nvert) return 1;
	for (int i = 0; i < m->nvert; ++i) m->vertices[i].x = (u16[i] * aff->scal_x) / 65535 + aff->base_x;
	if (fread(u16, sizeof(uint16_t), m->nvert, f) != m->nvert) return 1;
	for (int i = 0; i < m->nvert; ++i) m->vertices[i].y = (u16[i] * aff->scal_y) / 65535 + aff->base_y;
	if (fread(u16, sizeof(uint16_t), m->nvert, f) != m->nvert) return 1;
	for (int i = 0; i < m->nvert; ++i) m->vertices[i].z = (u16[i] * aff->scal_z) / 65535 + aff->base_z;
	// Normals
	int8_t *u8 = (int8_t *) mem;
	if (fread(u8,sizeof(int8_t),m->nvert,f)!=m->nvert) return 1;
	for (int i = 0; i < m->nvert; ++i) m->normals[i].nx = (double)(u8[i]) / 127;
	if (fread(u8, sizeof(int8_t), m->nvert, f) != m->nvert) return 1;
	for (int i = 0; i < m->nvert; ++i) m->normals[i].ny = (double)(u8[i]) / 127;
	// Nbr of triangles
	if (fread(&m->ntri, sizeof(uint32_t), 1, f) != 1) return 1;
	size_t new_memsize = 3 * m->ntri * (m->nvert < (1 << 16) ? sizeof(uint16_t) : sizeof(uint32_t));
	if (new_memsize>memsize) {
		memsize = new_memsize;
		mem = realloc(mem, memsize);
		if (mem == NULL) return 1;
		u16 = (uint16_t *) mem;
		u8 = (int8_t *) mem;
	}
	// Triangles
	if (m->nvert < (1 << 16)) {
		if (fread(u16, sizeof(uint16_t), 3 * m->ntri, f) != 3 * m->ntri) return 1;
		for (int i = 0; i < m->ntri; ++i) {
			m->triangles[i].v1 = u16[3 * i + 0];
			m->triangles[i].v2 = u16[3 * i + 1];
			m->triangles[i].v3 = u16[3 * i + 2];
		}
	} else {
		uint32_t *u32 = (uint32_t *) mem;
		if (fread(u32, sizeof(uint32_t), 3 * m->ntri, f) != 3 * m->ntri) return 1;
		for (int i = 0; i < m->ntri; ++i) {
			m->triangles[i].v1 = u32[3 * i + 0];
			m->triangles[i].v2 = u32[3 * i + 1];
			m->triangles[i].v3 = u32[3 * i + 2];
		}
	}
	if (fread(u8, sizeof(int8_t), m->ntri, f) != m->ntri) return 1;
	for (int i = 0; i < m->ntri; ++i) {
		m->triangles[i].type = u8[i];
	}
	free(mem);
	return 0;
}

// Same for writing.
int write_mesh_to_meshg_file(const  Mesh *m, const  AffineT3 *aff, FILE *f) 
{
	if (fwrite(&aff->base_x, sizeof(double), 1, f) != 1) return 1;
	if (fwrite(&aff->base_y, sizeof(double), 1, f) != 1) return 1;
	if (fwrite(&aff->base_z, sizeof(double), 1, f) != 1) return 1;
	if (fwrite(&aff->scal_x, sizeof(double), 1, f) != 1) return 1;
	if (fwrite(&aff->scal_y, sizeof(double), 1, f) != 1) return 1;
	if (fwrite(&aff->scal_z, sizeof(double), 1, f) != 1) return 1;
	// Nbr of vertices
	if (fwrite(&m->nvert, sizeof(uint32_t), 1, f) != 1) return 1;
	// Vertices
	size_t memsize = m->nvert * sizeof(uint16_t);
	void* mem = malloc(memsize);
	if (mem == NULL) return 1;
	uint16_t* u16=(uint16_t *)mem;
	for (int i=0;i<m->nvert;++i) u16[i] = round((m->vertices[i].x-aff->base_x)/aff->scal_x*65535);
	if (fwrite(u16,sizeof(uint16_t),m->nvert,f)!=m->nvert) return 1;
	for (int i=0;i<m->nvert;++i) u16[i] = round((m->vertices[i].y-aff->base_y)/aff->scal_y*65535);
	if (fwrite(u16,sizeof(uint16_t),m->nvert,f)!=m->nvert) return 1;
	for (int i=0;i<m->nvert;++i) u16[i] = round((m->vertices[i].z-aff->base_z)/aff->scal_z*65535);
	if (fwrite(u16,sizeof(uint16_t),m->nvert,f)!=m->nvert) return 1;
	// Normals
	int8_t* u8 = (int8_t *)mem;
	for (int i=0;i<m->nvert;++i) u8[i] = round((m->normals[i].nx)*127);
	if (fwrite(u8,sizeof(int8_t),m->nvert,f)!=m->nvert) return 1;
	for (int i=0;i<m->nvert;++i) u8[i] = round((m->normals[i].ny)*127);
	if (fwrite(u8,sizeof(int8_t),m->nvert,f)!=m->nvert) return 1;
	// Nbr of triangles
	if (fwrite(&m->ntri,sizeof(uint32_t),1,f)!=1) return 1;
	// Triangles
	size_t new_memsize = 3 * m->ntri * (m->nvert<(1<<16) ? sizeof(uint16_t) : sizeof(uint32_t));
	if (new_memsize>memsize) {
		memsize = new_memsize;
		mem = realloc(mem,memsize);
		if (mem==NULL) return 1;
		u16=(uint16_t *)mem;
		u8=(int8_t *)mem;
	}
	if (m->nvert<(1<<16)) {
		for (int i=0;i<m->ntri;++i) {
			u16[3*i+0] = m->triangles[i].v1;
			u16[3*i+1] = m->triangles[i].v2;
			u16[3*i+2] = m->triangles[i].v3;
		}
		if (fwrite(u16,sizeof(uint16_t),3*m->ntri,f)!=3*m->ntri) return 1;
		for (int i=0;i<m->ntri;++i) {
			u8[i]=m->triangles[i].type;
		}
		if (fwrite(u8,sizeof(uint8_t),m->ntri,f)!=m->ntri) return 1;
	} else {
		uint32_t *u32 = (uint32_t *)mem;
		for (int i=0;i<m->ntri;++i) {
			u32[3*i+0] = m->triangles[i].v1;
			u32[3*i+1] = m->triangles[i].v2;
			u32[3*i+2] = m->triangles[i].v3;
		}
		if (fwrite(u32,sizeof(uint32_t),3*m->ntri,f)!=3*m->ntri) return 1;
		for (int i=0;i<m->ntri;++i) {
			u8[i]=m->triangles[i].type;
		}
		if (fwrite(u8,sizeof(uint8_t),m->ntri,f)!=m->ntri) return 1;
	}
	free(mem);
	return 0;
}

#define LINE 128
int read_mesh_from_obj_file(Mesh *m, const AffineT3 *aff, int (*mtl_to_type)(char*), const char* filename) 
{
	FILE *f = fopen(filename,"r");
	if (f == NULL) return 1;
	char	line[LINE];
	uint32_t nv = 0;
	uint32_t nn = 0;
	uint32_t nt = 0;
	uint32_t nf = 0;
	uint32_t ntri = 0;
	uint32_t v1, v2, v3;
	int type;
	while (fgets(line, LINE, f) != NULL) {
		if (line[0] == 'v' && line[1] == ' ') nv += 1;
		else if (line[0] == 'v' && line[1] == 'n') nn += 1;
		else if (line[0] == 'v' && line[1] == 't') nt += 1;
		else if (line[0] == 'f' && line[1] == ' ') ntri += 1;
	}
	printf("Number of node coords: %d\n", nv);
	printf("Number of normal coords: %d\n", nn);
	printf("Number of texture coords: %d\n", nt);
	printf("Number of triangles: %d\n", ntri);
	Vertex *vertices = (Vertex*) malloc(nv * sizeof(Vertex));
	Normal *normals  = (Normal*) malloc(nn * sizeof(Normal));
	m->nvert = m->ntri = 0;
	m->vertices  = (Vertex*) malloc(3 * ntri * sizeof(Vertex));
	m->normals   = (Normal*) malloc(3 * ntri * sizeof(Normal));
	m->triangles = (Triangle*) malloc(ntri * sizeof(Triangle));
	if (vertices == NULL || normals == NULL || 
		m->vertices == NULL || m->normals == NULL || 
		m->triangles == NULL) goto memory_fail;
	char *subline;
	nv = nn = 0;
	struct HashTable ht;
	initialize_hashtable(&ht, 24, 2);
	rewind(f);
	while (fgets(line, LINE, f) != NULL) {
		if (line[0] == 'v' && line[1] == ' ') {
			subline = &line[2];
			vertices[nv].x = aff->base_x + aff->scal_x * quick_strtod(&subline, ' ');
			vertices[nv].y = aff->base_y + aff->scal_y * quick_strtod(&subline, ' ');
			vertices[nv].z = aff->base_z + aff->scal_z * quick_strtod(&subline, '\n');
			nv++;
		} else if (line[0] == 'v' && line[1] == 'n') {
			subline = &line[3];
			normals[nn].nx = quick_strtod(&subline, ' ');
			normals[nn].ny = quick_strtod(&subline, '\n');
			nn++;
		} else if (line[0] == 'v' && line[1] == 't') {
			// not dealing with texture coordinates yet
		} else if (line[0] == 'f' && line[1] == ' ') {
			uint32_t keys[2];
			uint32_t hash;
			subline = &line[2];
			keys[0] = quick_strtou(&subline, '/');
			quick_strtou(&subline, '/');
			keys[1] = quick_strtou(&subline, ' ');
			hash = 31 * keys[0] + 17 * keys[1] + keys[0] * keys[1];
			v1 = find_or_insert_in_hashtable(hash, keys, m->nvert, &ht);
			if (v1 == m->nvert) {
				assert(keys[0] > 0);
				assert(keys[1] > 0);
				m->vertices[v1] = vertices[keys[0] - 1];
				m->normals[v1] = normals[keys[1] - 1];
				m->nvert++;
			}
			keys[0] = quick_strtou(&subline, '/');
			quick_strtou(&subline, '/');
			keys[1] = quick_strtou(&subline, ' ');
			hash = 31 * keys[0] + 17 * keys[1] + keys[0] * keys[1];
			v2 = find_or_insert_in_hashtable(hash, keys, m->nvert, &ht);
			if (v2 == m->nvert) {
				assert(keys[0] > 0);
				assert(keys[1] > 0);
				m->vertices[v2] = vertices[keys[0] - 1];
				m->normals[v2] = normals[keys[1] - 1];
				m->nvert++;
			}
			keys[0] = quick_strtou(&subline, '/');
			quick_strtou(&subline, '/');
			keys[1] = quick_strtou(&subline, '\n');
			hash = 31 * keys[0] + 17 * keys[1] + keys[0] * keys[1];
			v3 = find_or_insert_in_hashtable(hash, keys, m->nvert, &ht);
			if (v3 == m->nvert) {
				assert(keys[0] > 0);
				assert(keys[1] > 0);
				m->vertices[v3] = vertices[keys[0] - 1];
				m->normals[v3] = normals[keys[1] - 1];
				m->nvert++;
			}
			m->triangles[m->ntri].v1 = v1;
			m->triangles[m->ntri].v2 = v2;
			m->triangles[m->ntri].v3 = v3;
			m->triangles[m->ntri].type = type;
			m->ntri++;
		} else if (strncmp(line, "usemtl ", 7) == 0) {
				type = mtl_to_type(&line[7]);
		}
	}
	fclose(f);
	m->vertices = (Vertex *) realloc(m->vertices, m->nvert * sizeof(Vertex));
	m->normals = (Normal *) realloc(m->normals, m->nvert * sizeof(Normal));
	printf("Final number of vertices and triangles : %d %d\n",m->nvert, m->ntri);
	free(vertices);
	free(normals);
	return 0;
memory_fail:
	fclose(f);
	free(vertices);
	free(normals);
	dispose_mesh(m); 
	return -1;
}
#undef LINE

/*#define MAXFILENAME 128
//int  write_mesh_to_obj_file(const Mesh *m, const AffineT3 *aff, const char* filename)
//{
//	char mtl_filename[MAXFILENAME];
/     	strncp(mtl_filename, filename, MAXFILENAME);
	strncp(mtl_filename + strlen(mtl_filename)-3, "mtl", 3);
	FILE *f = fopen(filename, "w");
	FILE *g = fopen(mtl_filename, "w");
	if (f == NULL) return 1;
	frpintf(f,"mtllib %s\n",mtl_filename);
	fprintf(f,"usemtl land\n")
	for (int i = 0; i < m->nvert; ++i) {
		fprintf(f, "v %.5lf %.5lf %.5lf\n", (m->vertices[i].x - aff->base_x) / aff->scal_x,
				(m->vertices[i].y - aff->base_y) / aff->scal_y,
				(m->vertices[i].z - aff->base_z) / aff->scal_z
				);
		fprintf(f, "vn %.2lf %.2lf\n", (m->normals[i].x - aff->base_x) / aff->scal_x,
				(m->normals[i].y - aff->base_y) / aff->scal_y,
				(m->normals[i].z - aff->base_z) / aff->scal_z
				);
	}
	fprintf(f,"usemtl land\n");
	// TODO
}
*/
