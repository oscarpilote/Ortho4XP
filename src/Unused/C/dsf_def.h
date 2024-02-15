#pragma once
#include "dem_def.h"
#include "mesh_defs.h"

typdedef struct {
	int terrain_type;
	uint8_t overlay_flag;
	float near_lod, far_lod;
	int coords_per_vertex;
	int ntri;
	uint16_t *pool_idx;
	uint16_t *idx_in_pool;
} Patch_t;

typedef struct {
	int demn;
	int pooln;
	int scaln;
	int po32n;
	int sc32n;
} DSF_reader_t;

typedef struct {
	int lon, lat;
	// TERT
	char **ter_def;
	int nter;
	// OBJT
	char **obj_def;
	int nobj;
	// POLY
	char **pol_def;
	int npol;
	// NETW
	char **net_def;
	int nnet;
        // DEMN / DEMI / DEMD
	char **dem_def;
	int ndem;
	struct DEM *dem;
	// POOL / SCAL
	uint16_t **pool;
	uint32_t *pool_size;
	uint8_t  *pool_plane;
	float **scal;
	float **offset;
	int npool;
	int nscal; // should equal npool but comes handy when reading atoms
	// PO32 / SC32
	uint32_t **po32;
	uint32_t *po32_size;
	uint8_t  *po32_plane;
	float **sc32;
	float **off32;
	int npo32;
	int nsc32; // should equal npool but comes handy when reading atoms
	// Patches
	Patch_t *patch;
	int npatch;
	// Polygons
	int npoly;
} DSF;	
