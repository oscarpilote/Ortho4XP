#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>

#include "dsf_def.h"
#include "dem_def.h"
#include "hash_tables.h"

#define  HEAD_ID  ('H' << 24) + ('E' << 16) + ('A' << 8)+ 'D'
#define  PROP_ID  ('P' << 24) + ('R' << 16) + ('O' << 8)+ 'P'
#define  DEFN_ID  ('D' << 24) + ('E' << 16) + ('F' << 8)+ 'N'
#define  TERT_ID  ('T' << 24) + ('E' << 16) + ('R' << 8)+ 'T'
#define  OBJT_ID  ('O' << 24) + ('B' << 16) + ('J' << 8)+ 'T'
#define  POLY_ID  ('P' << 24) + ('O' << 16) + ('L' << 8)+ 'Y'
#define  NETW_ID  ('N' << 24) + ('E' << 16) + ('T' << 8)+ 'W'
#define  DEMN_ID  ('D' << 24) + ('E' << 16) + ('M' << 8)+ 'N'
#define  GEOD_ID  ('G' << 24) + ('E' << 16) + ('O' << 8)+ 'D'
#define  POOL_ID  ('P' << 24) + ('O' << 16) + ('O' << 8)+ 'L'
#define  SCAL_ID  ('S' << 24) + ('C' << 16) + ('A' << 8)+ 'L'
#define  PO32_ID  ('P' << 24) + ('O' << 16) + ('3' << 8)+ '2'
#define  SC32_ID  ('S' << 24) + ('C' << 16) + ('3' << 8)+ '2'
#define  DEMS_ID  ('D' << 24) + ('E' << 16) + ('M' << 8)+ 'S'
#define  DEMI_ID  ('D' << 24) + ('E' << 16) + ('M' << 8)+ 'I'
#define  DEMD_ID  ('D' << 24) + ('E' << 16) + ('M' << 8)+ 'D'
#define  CMDS_ID  ('C' << 24) + ('M' << 16) + ('D' << 8)+ 'S'



int read_atom_head(uint32_t *atom_id, uint32_t *atom_size, FILE * f);
int process_atom(uint32_t atom_id , uint32_t atom_size, DSF * dsf, FILE *f);
int process_super_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_prop_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_tert_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_objt_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_poly_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_netw_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_demn_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int preprocess_geod_atom(uint32_t atom_size, DSF * dsf, FILE *f);
int process_pool_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_scal_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_po32_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_sc32_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_demi_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_demd_atom(uint32_t atom_size, DSF *dsf, FILE *f);
int process_cmds_atom(uint32_t atom_size, DSF *dsf, FILE *f, Mesh *m);
int read_16bit_data_plane(uint16_t *data, int nbr_pts, int encoding, FILE *f);
int read_32bit_data_plane(uint32_t *data, int nbr_pts, int encoding, FILE *f);

#define BUFSIZE 256
int read_dsf(DSF * dsf, char * filename)
{
	FILE *f;
	char buffer[BUFSIZE];
	uint16_t buf16[255];
	char *pos;
	uint32_t atom_id, atom_size;
	int32_t i32, format;
	f=fopen(filename,"rb");
	if (f == NULL) return -1;

	fread(buffer,8,1,f);
	if (strncmp(buffer, "7z", 2) == 0) {
		fclose(f);
		printf("The file %s is a 7z archive, uncompressing it with external 7z...\n",filename);
		if (snprintf(buffer, BUFSIZE, "7z e -y -bb3 \"%s\"", filename) > BUFSIZE) {
			printf("Too long file name... exiting.\n");
			return -1;
		}
		if (system(buffer) != 0) {
			printf("Could not uncompress the file properly (perhaps a missing 7z ?)\n");
			return -1;
		}
		pos = filename + strlen(filename) - 11;
		f=fopen(pos, "rb");
		if (f == NULL) return -1;
		fread(buffer, 8, 1, f);
	}
	if (strncmp(buffer, "XPLNEDSF", 8) != 0) {
		printf("The file %s is not a valid DSF.\n",filename);
		printf("Exiting.\n");
		return -1;
	} else {
		printf("This seems to be a valid DSF.\n");
	}
	// Skip format
	fseek(f, 4, SEEK_CUR);
	long int curpos = ftell(f);
	fseek(f, 0, SEEK_END);
	long int endpos = ftell(f) - 16;
	fseek(f, curpos, SEEK_SET); 
	while (ftell(f) < endpos) {
		if (read_atom_head(&atom_id, &atom_size, f)) return -1;
		if (process_atom(atom_id, atom_size, dsf, f)) return -1;
	}
	return 0;
}
#undef BUFSIZE




int read_atom_head(uint32_t *atom_id, uint32_t *atom_size, FILE * f)
{
	fread(atom_id, 4, 1, f);
	fread(atom_size, 4, 1, f);
	if (
			*atom_id != HEAD_ID &&
			*atom_id != PROP_ID &&
		       	*atom_id != DEFN_ID &&
			*atom_id != TERT_ID &&
			*atom_id != OBJT_ID &&
			*atom_id != POLY_ID &&
			*atom_id != NETW_ID &&
			*atom_id != DEMN_ID &&
			*atom_id != GEOD_ID &&
			*atom_id != POOL_ID &&
			*atom_id != SCAL_ID &&
			*atom_id != PO32_ID &&
			*atom_id != SC32_ID &&
			*atom_id != DEMS_ID &&
			*atom_id != DEMI_ID &&
			*atom_id != DEMD_ID &&
			*atom_id != CMDS_ID
	   ) {
		printf("Unknown atom head !\n");
		return -1;	
	}
	return 0;
}

int process_atom(uint32_t atom_id, uint32_t atom_size, DSF * dsf, FILE *f)
{
	switch(atom_id) {
		case  HEAD_ID :
			return process_super_atom(atom_size, dsf, f);
		case  PROP_ID :
			return process_prop_atom(atom_size, dsf, f);
		case  DEFN_ID :
			return process_super_atom(atom_size, dsf, f);
		case  TERT_ID :
			return process_tert_atom(atom_size, dsf, f);
		case  OBJT_ID :
			return process_objt_atom(atom_size, dsf, f);
		case  POLY_ID :
			return process_poly_atom(atom_size, dsf, f);
		case  NETW_ID :
			return process_netw_atom(atom_size, dsf, f);
		case  DEMN_ID :
			return process_demn_atom(atom_size, dsf, f);
		case  GEOD_ID :
			return preprocess_geod_atom(atom_size, dsf, f) 
			|| process_super_atom(atom_size, dsf, f);
		case  POOL_ID :
			return process_pool_atom(atom_size, dsf, f);
		case  SCAL_ID :
			return process_scal_atom(atom_size, dsf, f);
		case  PO32_ID :
			return process_po32_atom(atom_size, dsf, f);
		case  SC32_ID :
			return process_sc32_atom(atom_size, dsf, f);
		case  DEMS_ID :
			return process_super_atom(atom_size, dsf, f);
		case  DEMI_ID :
			return process_demi_atom(atom_size, dsf, f);
		case  DEMD_ID :
			return process_demd_atom(atom_size, dsf, f);
		case  CMDS_ID :
			return process_cmds_atom(atom_size, dsf, f);
	}
	return -1;
}

int process_super_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	uint32_t sub_atom_id, sub_atom_size;
        int consume = 8;
	while (consume < atom_size) {
		if (read_atom_head(&sub_atom_id, &sub_atom_size, f)) return -1;
		process_atom(sub_atom_id, sub_atom_size, dsf, f);
		consume += sub_atom_size;
	}
	return 0;
}

int process_prop_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	char *buffer;
	char *pos;
	buffer = (char *) malloc(atom_size);
	if (buffer == NULL) return -1;
        fread(buffer, atom_size-8, 1, f);
	pos = buffer;
	while (pos < buffer + atom_size - 8) {
		if (strncmp(pos, "sim/west", 8) == 0) {
			pos += strlen(pos) + 1;
			dsf->lon = atoi(pos);
		} else if (strncmp(pos, "sim/south", 9) == 0) {
			pos += strlen(pos) + 1;
			dsf->lat = atoi(pos);
		} else {
			pos += strlen(pos) + 1;
		}
		pos += strlen(pos) + 1;
	}
	free(buffer);
	return 0;
}


int process_tert_atom(uint32_t atom_size, DSF *dsf, FILE *f)
{
	char *pos;
	char *end;
	int nter = 0;
	dsf->ter_def_ = (char *) malloc(atom_size - 8);
	if (dsf->ter_def_ == NULL) return -1;
        fread(dsf->ter_def_, atom_size-8, 1, f);
	pos = dsf->ter_def_;
	end = dsf->ter_def_ + atom_size - 8;
	while (pos < end) {
		nter++;
		pos += strlen(pos) + 1;
	}
	dsf->ter_def = (char **) malloc(nter * sizeof(char *));
	if (dsf->ter_def == NULL) return -1;
	pos = dsf->ter_def_;
	nter = 0;
	while (pos < end) {
		dsf->ter_def[nter] = pos;
		nter++;
		pos += strlen(pos) + 1;
	}
	dsf->nter = nter;
	return 0;
}

int process_objt_atom(uint32_t atom_size, DSF *dsf, FILE *f)
{
	char *pos;
	char *end;
	int nobj = 0;
	dsf->obj_def_ = (char *) malloc(atom_size-8);
	if (dsf->obj_def_ == NULL) return -1;
        fread(dsf->obj_def_, atom_size-8, 1, f);
	pos = dsf->obj_def_;
	end = dsf->obj_def_ + atom_size - 8;
	while (pos < end) {
		nobj++;
		pos += strlen(pos) + 1;
	}
	dsf->obj_def = (char **) malloc(nobj * sizeof(char *));
	if (dsf->obj_def == NULL) return -1;
	pos = dsf->obj_def_;
	nobj = 0;
	while (pos < end) {
		dsf->obj_def[nobj] = pos;
		nobj++;
		pos += strlen(pos) + 1;
	}
	dsf->nobj = nobj;
	return 0;
}

int process_poly_atom(uint32_t atom_size, DSF *dsf, FILE *f)
{
	char *pos;
	char *end;
	int npol = 0;
	dsf->pol_def_ = (char *) malloc(atom_size-8);
	if (dsf->pol_def_ == NULL) return -1;
        fread(dsf->pol_def_, atom_size-8, 1, f);
	pos = dsf->pol_def_;
	end = dsf->pol_def_ + atom_size - 8;
	while (pos < end) {
		npol++;
		pos += strlen(pos) + 1;
	}
	dsf->pol_def = (char **) malloc(npol * sizeof(char *));
	if (dsf->pol_def == NULL) return -1;
	pos = dsf->pol_def_;
	npol = 0;
	while (pos < end) {
		dsf->pol_def[npol] = pos;
		npol++;
		pos += strlen(pos) + 1;
	}
	dsf->npol = npol;
	return 0;
}

int process_netw_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	char *pos;
	char *end;
	int nnet = 0;
	dsf->net_def_ = (char *) malloc(atom_size-8);
	if (dsf->net_def_ == NULL) return -1;
        fread(dsf->net_def_, atom_size-8, 1, f);
	pos = dsf->net_def_;
	end = dsf->net_def_ + atom_size - 8;
	while (pos < end) {
		nnet++;
		pos += strlen(pos) + 1;
	}
	dsf->net_def = (char **) malloc(nnet * sizeof(char *));
	if (dsf->net_def == NULL) return -1;
	pos = dsf->net_def_;
	nnet = 0;
	while (pos < end) {
		dsf->net_def[nnet] = pos;
		nnet++;
		pos += strlen(pos) + 1;
	}
	dsf->nnet = nnet;
	return 0;
}

int process_demn_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	char *pos;
	char *end;
	int ndem = 0;
	dsf->dem_def_ = (char *) malloc(atom_size-8);
	if (dsf->dem_def_ == NULL) return -1;
        fread(dsf->dem_def_, atom_size-8, 1, f);
	pos = dsf->dem_def_;
	end = dsf->dem_def_ + atom_size - 8;
	while (pos < end) {
		ndem++;
		pos += strlen(pos) + 1;
	}
	dsf->dem_def = (char **) malloc(ndem * sizeof(char *));
	if (dsf->dem_def == NULL) return -1;
	pos = dsf->dem_def_;
	ndem = 0;
	while (pos < end) {
		dsf->dem_def[ndem] = pos;
		ndem++;
		pos += strlen(pos) + 1;
	}
	dsf->dem = (struct DEM*) malloc(ndem * sizeof(struct DEM));
	if (dsf->dem == NULL) return -1;
	dsf->ndem = 0; // will be increased one step at a time when reading DEMD atoms
	return 0;
}

int preprocess_geod_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	int npool,nscal,npo32,nsc32;
	npool = 0; nscal = 0; npo32 = 0; nsc32 = 0;
	int consume = 8;
	long int init_pos = ftell(f);
	uint32_t sub_atom_id, sub_atom_size;
	while (consume < atom_size) {
		if (read_atom_head(&sub_atom_id, &sub_atom_size, f)) return -1;
		if (sub_atom_id == POOL_ID) {
			npool+=1;
		} else if (sub_atom_id == SCAL_ID) {
			nscal+=1;
		} else if (sub_atom_id == PO32_ID) {
			npo32+=1;
		} else if (sub_atom_id == SC32_ID) {
			nsc32+=1;
		} else {
			return -1;
		}
		fseek(f, sub_atom_size - 8, SEEK_CUR);
		consume += sub_atom_size;
	}
	if (npool != nscal || npo32 != nsc32) return -1;
	dsf->npool = 0; dsf->nscal = 0; // will be increased step by step when reading pool/scal atoms
	dsf->pool_size = (uint32_t *) malloc(npool * sizeof(uint32_t));
	dsf->pool_plane = (uint8_t *) malloc(npool * sizeof(uint8_t));
	dsf->pool = (uint16_t **) malloc(npool * sizeof(uint16_t *));
	dsf->scal = (float **) malloc(npool * sizeof(float *));
	dsf->offset = (float **) malloc(npool * sizeof(float *));
	dsf->npo32 = 0; dsf->nsc32 = 0; // will be increased step by step when reading po32/sc32 atoms
	dsf->po32_size = (uint32_t *) malloc(npo32 * sizeof(uint32_t));
	dsf->po32_plane = (uint8_t *) malloc(npo32 * sizeof(uint8_t));
	dsf->po32 = (uint32_t **) malloc(npo32 * sizeof(uint32_t *));
	dsf->sc32 = (float **) malloc(npo32 * sizeof(float *));
	dsf->off32 = (float **) malloc(npo32 * sizeof(float *));
	fseek(f,init_pos,SEEK_SET);
	return 0;
}



#define MAXPLANES 11
int process_pool_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
        uint32_t nbr_pts;
	uint8_t nbr_planes;
	uint8_t encoding[MAXPLANES];
	fread(&nbr_pts, 4, 1, f);
	fread(&nbr_planes, 1, 1, f);
	dsf->pool_size[dsf->npool] = nbr_pts;
	dsf->pool_plane[dsf->npool] = nbr_planes;
	dsf->pool[dsf->npool] = (uint16_t *) malloc(nbr_planes * nbr_pts * sizeof(uint16_t)); 
	if (dsf->pool[dsf->npool] == NULL) return -1;
	uint16_t *pos = dsf->pool[dsf->npool];
	for (int i = 0; i < nbr_planes; ++i) {
		fread(&encoding[i],1,1,f);
		read_16bit_data_plane(pos, nbr_pts, encoding[i], f);
		pos += nbr_pts;
	}
	dsf->npool++;
	return 0;
}
#undef MAXPLANES

int process_scal_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	int nbr = (atom_size - 8)/(2 * sizeof(float));
	dsf->scal[dsf->nscal] = (float *) malloc(nbr * sizeof(float));
	dsf->offset[dsf->nscal] = (float *) malloc(nbr * sizeof(float));
	if (dsf->scal[dsf->nscal] == NULL || dsf->offset[dsf->nscal] == NULL) return -1;
	for (int i=0; i < nbr; ++i) {
		fread(&dsf->scal[dsf->nscal][i], 4, 1, f);
		fread(&dsf->offset[dsf->nscal][i], 4, 1, f);
	}
	dsf->nscal++;
	return 0;
}

#define MAXPLANES 11
int process_po32_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
        uint32_t nbr_pts;
	uint8_t nbr_planes;
	uint8_t encoding[MAXPLANES];
	fread(&nbr_pts, 4, 1, f);
	fread(&nbr_planes, 1, 1, f);
	dsf->po32_size[dsf->npo32] = nbr_pts;
	dsf->po32_plane[dsf->npo32] = nbr_planes;
	dsf->po32[dsf->npo32] = (uint32_t *) malloc(nbr_planes * nbr_pts * sizeof(uint32_t)); 
	if (dsf->po32[dsf->npo32] == NULL) return -1;
	uint32_t *pos = dsf->po32[dsf->npo32];
	for (int i = 0; i < nbr_planes; ++i) {
		fread(&encoding[i],1,1,f);
		read_32bit_data_plane(pos, nbr_pts, encoding[i], f);
		pos += nbr_pts;
	}
	dsf->npo32++;
	return 0;
}
#undef MAXPLANES

int process_sc32_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	int nbr = (atom_size - 8)/(2 * sizeof(float));
	dsf->sc32[dsf->nsc32] = (float *) malloc(nbr * sizeof(float));
	dsf->off32[dsf->nsc32] = (float *) malloc(nbr * sizeof(float));
	if (dsf->sc32[dsf->nsc32] == NULL || dsf->off32[dsf->nsc32] == NULL) return -1;
	for (int i=0; i < nbr; ++i) {
		fread(&dsf->sc32[dsf->nsc32][i], 4, 1, f);
		fread(&dsf->off32[dsf->nsc32][i], 4, 1, f);
	}
	dsf->nsc32++;
	return 0;
}

int process_demi_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	struct DEM * dem = &dsf->dem[dsf->ndem];
	// skip version number
	fseek(f, 1, SEEK_CUR);
	fread(&dem->bpp, 1, 1, f);
	fread(&dem->flags, 2, 1, f);
	fread(&dem->pixx, 4, 1, f);
	fread(&dem->pixy, 4, 1, f);
	fread(&dem->scale, 4, 1, f);
	fread(&dem->offset, 4, 1, f);
	return 0;
}
int process_demd_atom(uint32_t atom_size, DSF * dsf, FILE *f)
{
	struct DEM * dem = &dsf->dem[dsf->ndem];
	dem->encoded_data = malloc(atom_size - 8);
	dem->data = (float *) malloc(dem->pixx * dem->pixy * sizeof(float));
	if (dem->encoded_data == NULL || dem->data == NULL) return -1;
	fread(dem->encoded_data, atom_size - 8, 1, f);
	if (dem->flags == 0) {
		float * data = dem->encoded_data;
		for (int i = 0; i < dem->pixx * dem->pixy; ++i) {
			dem->data[i] = (double) *data++ * dem->scale + dem->offset;
		}
	} else if (dem->flags == 1 && dem->bpp == 1) {
		int8_t * data = dem->encoded_data;
		for (int i = 0; i < dem->pixx * dem->pixy; ++i) {
			dem->data[i] = (double) *data++ * dem->scale + dem->offset;
		}
	} else if (dem->flags == 1 && dem->bpp == 2) {
		int16_t * data = dem->encoded_data;
		for (int i = 0; i < dem->pixx * dem->pixy; ++i) {
			dem->data[i] = (double) *data++ * dem->scale + dem->offset;
		}
	} else if (dem->flags == 1 && dem->bpp == 4) {
		int32_t * data = dem->encoded_data;
		for (int i = 0; i < dem->pixx * dem->pixy; ++i) {
			dem->data[i] = (double) *data++ * dem->scale + dem->offset;
		}
	} else if (dem->flags == 2 && dem->bpp == 1) {
		uint8_t * data = dem->encoded_data;
		for (int i = 0; i < dem->pixx * dem->pixy; ++i) {
			dem->data[i] = (double) *data++ * dem->scale + dem->offset;
		}
	} else if (dem->flags == 2 && dem->bpp == 2) {
		uint16_t * data = dem->encoded_data;
		for (int i = 0; i < dem->pixx * dem->pixy; ++i) {
			dem->data[i] = (double) *data++ * dem->scale + dem->offset;
		}
	} else if (dem->flags == 2 && dem->bpp == 4) {
		uint32_t * data = dem->encoded_data;
		for (int i = 0; i < dem->pixx * dem->pixy; ++i) {
			dem->data[i] = (double) *data++ * dem->scale + dem->offset;
		}
	} else {
		return -1;
	}
	// discard encoded_data
	free(dem->encoded_data);
	dsf->ndem++;
	return 0;
}

int process_cmds_atom(uint32_t atom_size, DSF * dsf, FILE *f, Mesh *m)
{
	// temporaries
	char buffer[4];
	uint8_t m, n;
	uint16_t param;
	uint16_t index;
	uint16_t idx_begin, idx_end;
	uint32_t idx3[3];
	uint16_t idx255[255];
	double   double[11];
	HashTable ht;
	// dsf related
	uint8_t cmd;
	uint16_t curpool = 0;
	uint32_t junction_offset = 0;
	int curdef;
	uint8_t road_sub_type;
	uint8_t overlay_flag;
	float near_lod, far_lod;
        int occur[34];
	for (int i = 0; i < 34; ++i) occur[i] = 0;
	// how much work is already done
	int consume = 8;
	while (consume < atom_size) {
		fread(&cmd, 1, 1, f);
		++consume;
		occur[cmd]++;
		switch (cmd) {
			case 1:
				fread(&curpool, 2, 1, f);
				consume += 2;
				break;
			case 2:
				fread(&junction_offset, 4, 1, f);
				consume += 4;
				break;
			case 3:
				fread(buffer, 1, 1, f);
				curdef = * (uint8_t *) buffer;
				consume += 1;
				break;
			case 4:
				fread(buffer, 2, 1, f);
				curdef = * (uint16_t *) buffer;
				consume += 2;
				break;
			case 5:
				fread(buffer, 4, 1, f);
				curdef = * (uint32_t *) buffer;

				consume += 4;
				break;
			case 6:
				fread(&road_sub_type, 1, 1, f);
				consume += 1;
				break;
			case 7:
				fread(&index, 2, 1, f);
				// TODO add object
				consume += 2;
				break;
			case 8:
				fread(&idx_begin, 2, 1, f);
				fread(&idx_end, 2, 1, f);
				// TODO add object range
				consume += 4;
				break;
			case 9:
				fread(&n, 1, 1, f);
				// TODO add network vertices (using junction_offset)
				fseek(f, 2 * n, SEEK_CUR);
				consume += 1 + 2 * n;
				break;
			case 10:
				fread(&idx_begin, 2, 1, f);
				fread(&idx_end, 2, 1, f);
				// TODO add network vertices range
				consume += 4;
				break;
			case 11:
				fread(&n, 1, 1, f);
				// TODO add network vertices (without junction_offset)
				fseek(f, 4 * n, SEEK_CUR);
				consume += 1 + 4 * n;
				break;
			case 12:
				fread(&param, 2, 1,f);
				fread(&n, 1, 1, f);
				// TODO add simple polygon
				fseek(f, 2 * n, SEEK_CUR);
				consume += 3 + 2 * n; 
				break;
			case 13:
				fread(&param, 2, 1,f);
				fread(&idx_begin, 2, 1, f);
				fread(&idx_end, 2, 1, f);
				// TODO add simple polygon (range)
				consume += 6;
				break;
			case 14:
				fread(&param, 2, 1,f);
				fread(&n, 1, 1, f);
				consume +=3;
				// TODO add polygon with holes
				for (int i = 0; i < n; ++i) {
					fread(&m, 1, 1, f);
					fseek(f, 2 * m, SEEK_CUR);
					consume += 1 + 2 * m;
				}
				break;
			case 15:
				fread(&param, 2, 1,f);
				fread(&n, 1, 1, f);
				// TODO add polygon with holes (range)
				fseek(f, 2 * (n +1), SEEK_CUR);
				consume += 3 + 2 * (n + 1); 
				break;
			case 16:
				// begin terrain patch
				break;
			case 17:
				fread(&overlay_flag, 1, 1, f);
				consume += 1;
				break;
			case 18:
				fread(&overlay_flag, 1, 1, f);
				fread(&near_lod, 4, 1, f);
				fread(&far_lod, 4, 1, f);
				consume += 9;
				break;
// Strangely there are no commands from 19 to 22...			 
			case 23:
				fread(&n, 1, 1, f);
				Vertex vert;
			    	Normal norm;
				fread(idx255, sizeof(uint16_t), n, f);	
				for (int i = 0; i < n; ) {
					for (int j = 0; j < 3; ++j, ++i) {
						decode(&dsf, curpool, idx255[i], dbl11);
						keys[0] = (uint32_t) ((dbl[0] - dsf.lon) * (1 << 24));
						keys[1] = (uint32_t) ((dbl[1] - dsf.lat) * (1 << 24));
						uint32_t hash = 31 * keys[0] + 17 * keys[1] + keys[0] * keys[1];
						idx3[j] = find_or_insert_in_hashtable(hash, keys, ht.size, &ht);
						if (idx3[j] == ht.size) {
							m->vertices[m->nvert].x = dbl[0];
							m->vertices[m->nvert].y = dbl[1];
							m->vertices[m->nvert].z = dbl[2];
							if (dsf.pool_plane[curpool] > 3) {
								m->normals[m->nvert].nx = dbl[3];
								m->normals[m->nvert].ny = dbl[4];
							} else {
								m->normals[m->nvert].nx = 0;
								m->normals[m->nvert].ny = 0;
							}
							m->nvert++;
						}
					}
					m->triangles[m->ntri].n1 = idx3[0];
					m->triangles[m->ntri].n2 = idx3[1];
					m->triangles[m->ntri].n3 = idx3[2];
					m->triangles[m->ntri].type = curdef;
					m->ntri++;
				}
				// TODO add triangle patch
				//fseek(f, 2 * n, SEEK_CUR);
				consume += 1 + 2 * n;
				break;
			case 24:
				fread(&n, 1, 1, f);
				// TODO add triangle patch cross-pool
				fseek(f, 2 * 2 * n, SEEK_CUR);
				consume += 1 + 2 * 2* n;
				break;
			case 25:
				fread(&idx_begin, 2, 1, f);
				fread(&idx_end, 2, 1, f);
				// TODO add triangle patch (range)
				consume += 4;
				break;
			case 26:
				fread(&n, 1, 1, f);
				// TODO add triangle strip
				fseek(f, 2 * n, SEEK_CUR);
				consume += 1 + 2 * n;
				break;
			case 27:
				fread(&n, 1, 1, f);
				// TODO add triangle strip cross-pool
				fseek(f, 2 * 2 * n, SEEK_CUR);
				consume += 1 + 2 * 2* n;
				break;
			case 28:
				fread(&idx_begin, 2, 1, f);
				fread(&idx_end, 2, 1, f);
				// TODO add triangle strip (range)
				consume += 4;
				break;
			case 29:
				fread(&n, 1, 1, f);
				// TODO add triangle fan
				fseek(f, 2 * n, SEEK_CUR);
				consume += 1 + 2 * n;
				break;
			case 30:
				fread(&n, 1, 1, f);
				// TODO add triangle fan cross-pool
				fseek(f, 2 * 2 * n, SEEK_CUR);
				consume += 1 + 2 * 2* n;
				break;
			case 31:
				fread(&idx_begin, 2, 1, f);
				fread(&idx_end, 2, 1, f);
				// TODO add triangle fan (range)
				consume += 4;
				break;
			case 32:
				fread(&n, 1, 1, f);
				fseek(f, n, SEEK_CUR);
				consume += 1 + n;
				break;
			// Skip longer comment commands (unused)
			default:
				printf("Unknown command %d, exiting.\n",cmd);
				return -1;
		}
	}
	for (int i = 1; i < 34; ++i) printf("%2d : %6d\n",i,occur[i]);
	return 0;
}

int read_16bit_data_plane(uint16_t *data, int nbr_pts, int encoding, FILE *f)
{
	int cur = 0;
	uint8_t rlb;
	if (!(encoding & 2)) {
		cur = fread(data, sizeof(uint16_t), nbr_pts, f);
	} else { // RL
		while (cur < nbr_pts) {
			fread(&rlb, sizeof(uint8_t), 1, f);
			int rep = rlb & 127;
			if (rlb & 128) {
				uint16_t repdata ;
				fread(&repdata, sizeof(uint16_t), 1, f);
				for (int i = 0; i < rep; ++i) {
					data[cur++] = repdata;
				}
			} else {
				for (int i = 0; i < rep; ++i) {
					fread(&data[cur++], sizeof(uint16_t), 1, f);
				}
			}
		}
	}
	if (cur != nbr_pts) {
		printf("Corrupted data plane ! %d %d\n",cur,nbr_pts);
		return -1;
	}
	if (encoding & 1) {
		for (int i = 1; i < nbr_pts; ++i) {
		       data[i] = data[i-1] - data[i];
		}
	}
	return 0;	
}

int read_32bit_data_plane(uint32_t *data, int nbr_pts, int encoding, FILE *f)
{
	int cur = 0;
	uint8_t rlb;
	if (!(encoding & 2)) {
		cur = fread(data, sizeof(uint32_t), nbr_pts, f);
	} else { // RL
		while (cur < nbr_pts) {
			fread(&rlb, sizeof(uint8_t), 1, f);
			int rep = rlb & 127;
			if (rlb & 128) {
				uint32_t repdata ;
				fread(&repdata, sizeof(uint32_t), 1, f);
				for (int i = 0; i < rep; ++i) {
					data[cur++] = repdata;
				}
			} else {
				for (int i = 0; i < rep; ++i) {
					fread(&data[cur++], sizeof(uint32_t), 1, f);
				}
			}
		}
	}
	if (cur != nbr_pts) {
		printf("Corrupted data plane ! %d %d\n",cur,nbr_pts);
		return -1;
	}
	if (encoding & 1) {
		for (int i = 1; i < nbr_pts; ++i) {
		       data[i] = data[i-1] - data[i];
		}
	}		
	return 0;	
}

static decode(DSF *dsf, uint16_t pool, uint16_t idx, double *decoded);
{
	for (int i = 0; i < dsf->pool_plane[pool]; ++i) {
		decoded[i] = (double) dsf->offset[pool][i] + (double) dsf->scal[pool][i] * dsf->pool[pool][idx + i * dsf->pool_length[pool]] / 65535.0;  
	}
}


int main(int argc, char **argv)
{
	DSF dsf;
	read_dsf(&dsf, argv[1]);
	return 0;
}
