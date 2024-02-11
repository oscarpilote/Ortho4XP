#include <stdlib.h>
#include <stdint.h>
#include <limits.h>
#include <math.h>
#include <assert.h>
#include "geo_transforms.h"
#include "mesh_defs.h"
#include "mesh_calcs.h"

typedef struct {
	int zl;
	int bounds[4];
	void (*xy_to_grid)(double,double,double*,double*,int);
	void (*grid_to_xy)(double,double,double*,double*,int);
} Grid;

typedef struct {
	int nbr_mesh;
	AffineT3 *scals;
	Mesh *meshes;
} MeshGrid;

// El cheapo (fast) hash table with open addressing.
typedef struct {  	
	double *  table;
	uint32_t  capacity;
	uint32_t  bits;
	uint32_t  numElems;	
} HashTable;


/******************************************************************************
 *
 *   I.   Forward declarations. 
 *
 * ***************************************************************************/
void dispose_meshgrid(MeshGrid *mg);
int initialize_meshgrid_from_grid(MeshGrid *mg, const Grid *g);
void optimize_z_scals_from_mesh_bounds(MeshGrid *mg);
int cut_mesh_according_to_grid(const Mesh *m, const Grid *g, Mesh *mcut);
int split_mesh_according_to_grid(const Mesh *m, const Grid *g, MeshGrid *mg);
int aggregate_meshgrid_into_mesh(const MeshGrid *mg, const Grid *g, Mesh *m);

static void check_cut_coord(int *poly, int nbr_points, double(*gc)[2], double *cut, int *idxc);
static void cut_convex_poly_along_grid(int recur, int *poly, int nbr_points, int type, const Mesh *m, const Grid *g, double (*gc)[2], Mesh *mcut, HashTable *new_vt);
static int find_cut_point(double cut, double ocut, int idxc, HashTable *vt, int next_idx);
static int find_or_set_new_index(int n, int k, int alt, int *idxinfo);

/******************************************************************************
 *
 *   II.   Implementations. 
 *
 * ***************************************************************************/

void dispose_meshgrid(MeshGrid *mg)
{
	mg->nbr_mesh=0;
	if (mg->meshes!=NULL) {
		for (int k=0;k<mg->nbr_mesh;++k) {
			dispose_mesh(&mg->meshes[k]);
		}
		free(mg->meshes);
	}
	free(mg->scals);
}

int initialize_meshgrid_from_grid(MeshGrid *mg, const Grid *g)
{
	int nbr_mesh = (g->bounds[2] - g->bounds[0]) * (g->bounds[3] - g->bounds[1]);
	mg->nbr_mesh = nbr_mesh;
	mg->meshes = (Mesh *) malloc(nbr_mesh * sizeof(Mesh));
	mg->scals  = (AffineT3 *) malloc(nbr_mesh * sizeof(AffineT3));
	if ((mg->meshes == NULL) || (mg->scals == NULL)) {
		dispose_meshgrid(mg);
		return 1;
	}
	int stride = g->bounds[2]-g->bounds[0];
	for (int k=0; k<nbr_mesh; ++k) {
		int p = g->bounds[0] + k % stride;
		int q = g->bounds[1] + k / stride;
		double xmin, xmax, ymin, ymax;
	        g->grid_to_xy(p, q, &xmin, &ymax, g->zl);
		g->grid_to_xy(p+1, q+1, &xmax, &ymin, g->zl);
                mg->scals[k].base_x = xmin;
		mg->scals[k].scal_x = xmax-xmin;
		mg->scals[k].base_y = ymin;
		mg->scals[k].scal_y = ymax - ymin;
		mg->scals[k].base_z = -32768;
		mg->scals[k].scal_z = 65535;
	}
	return 0;
}

void optimize_z_scals_from_mesh_bounds(MeshGrid *mg)
{
	for (int k=0; k<mg->nbr_mesh; ++k) {
		double r[2];
	        compute_mesh_bounds(&mg->meshes[k], 2, r);
		double span = r[1] - r[0];
		mg->scals[k].scal_z = (span < 770) ? 771 : (span < 1284) ? 1285 : (span < 4368) ? 4369 : 13107;
		mg->scals[k].base_z = floor(r[0]);
	}
}


#define CUTMARGIN 2
int cut_mesh_according_to_grid(const Mesh *m, const Grid *g, Mesh *mcut)
{
	// Set up memory for containers
	uint32_t nntri = m->ntri * CUTMARGIN;
	uint32_t nnvert = m->nvert * CUTMARGIN;
	if ((mcut->triangles = (Triangle *) calloc(nntri, sizeof(Triangle))) == NULL) goto memory_missing;
	if ((mcut->vertices = (Vertex *) calloc(nnvert, sizeof(Vertex))) == NULL) goto memory_missing; 
	if ((mcut->normals = (Normal *) calloc(nnvert, sizeof(Normal))) == NULL) goto memory_missing; 
	double (*gc)[2];  // vertices grid coordinates
	if ((gc = (double (*)[2]) calloc(nnvert, sizeof(double[2]))) == NULL) goto memory_missing;
        HashTable new_vt;
	new_vt.bits = (int) ceil(log2(m->nvert+1))+4;
	new_vt.capacity = 1 << new_vt.bits;
	printf("Nombre de bits : %d, soit %d slots\n",new_vt.bits,new_vt.capacity);
	new_vt.numElems = 0;
	new_vt.table = (double *) calloc(3 * new_vt.capacity, sizeof(double));
	if (new_vt.table == NULL) goto memory_missing;
	for (int i = 0; i < new_vt.capacity; ++i) new_vt.table[3*i+2] = -1;
	// Initialize containers
	mcut->ntri = 0;
	mcut->nvert = m->nvert;
	memcpy(mcut->vertices, m->vertices, m->nvert * sizeof(Vertex));
	memcpy(mcut->normals, m->normals, m->nvert * sizeof(Normal));
	// Compute grid coordinates and round them off if sufficiently close to integer
	printf("Computing grid coordinates.\n");
	for (int i = 0; i < m->nvert; ++i) {
		g->xy_to_grid(m->vertices[i].x, m->vertices[i].y, &gc[i][0], &gc[i][1], g->zl);
	}
	// Cut triangles
	printf("Cutting triangles.\n");
	for (int i=0 ; i < m->ntri; ++i) {
		//printf("--------------> %d %d\n",i,mcut->ntri);
		cut_convex_poly_along_grid(0,(int *) &m->triangles[i], 3, m->triangles[i].type, m, g, gc, mcut, &new_vt);
	}
	return 0;
memory_missing:
	dispose_mesh(mcut);
	free(gc);
	free(new_vt.table);
	return 1;
}
#undef CUTMARGIN


static void check_cut_coord(int *poly, int nbr_points, double(*gc)[2], double *cut, int *idxc)
{
	int min_x, max_x, min_y, max_y;
	min_x = INT_MAX;
	min_y = INT_MAX;
	max_x = INT_MIN;
	max_y = INT_MIN;
	double eps = 1e-5;
	double x_eff, y_eff;
	for (int i = 0; i < nbr_points; i++) {
		x_eff = (fabs(gc[poly[i]][0]-round(gc[poly[i]][0])) < eps) ? round(gc[poly[i]][0]) : gc[poly[i]][0];
		y_eff = (fabs(gc[poly[i]][1]-round(gc[poly[i]][1])) < eps) ? round(gc[poly[i]][1]) : gc[poly[i]][1];
		min_x = ((int) x_eff < min_x) ? ((int) x_eff) : min_x;
		min_y = ((int) y_eff < min_y) ? ((int) y_eff) : min_y;
		max_x = ((int)(ceil(x_eff)) > max_x) ? ((int) (ceil(x_eff))) : max_x;
		max_y = ((int)(ceil(y_eff)) > max_y) ? ((int) (ceil(y_eff))) : max_y;
		//printf("%d %lf %lf %d %d %d %d\n",poly[i], gc[poly[i]][0],gc[poly[i]][1],min_x,max_x,min_y,max_y);
	}
	if ((max_x-min_x) < 2 && (max_y-min_y) < 2) {
		*idxc = -1;
	} else if ((max_x-min_x) >= (max_y-min_y)) { // cut along x = cst
		*cut = round((max_x + min_x) / 2.0); 
		*idxc = 0;
	} else {
		*cut = round((max_y + min_y) / 2.0); 
		*idxc = 1;
	}
}

static int find_cut_point(double cut, double ocut, int idxc, HashTable *new_vt, int next_idx)
{
	double oocut = (int)ocut + ((int)((ocut-(int)ocut)*(1<<16))/(double)(1<<16));
	//double oocut = ocut;
	//printf("%lf %lf\n", ocut,oocut);
	//uint32_t pos = 32654435769.0*(oocut+cut+cut*oocut);
	uint32_t pos = (((uint32_t)cut + 31) * ((uint32_t)(oocut * 19)+7)); 
	int count=0;
	static int trouve = 0;
	while (1) {
                pos = pos & ((1 << new_vt->bits) - 1);
		double *p = &new_vt->table[3*pos];
		if ((int) p[2] == -1) {        
			p[idxc] = cut;
			p[1-idxc] = oocut;
			p[2] = next_idx;
			new_vt->numElems++;
			//printf("New cut point at index %d\n",next_idx);
			//printf("Count0 : %d %lf \n",count,(double)new_vt->numElems/new_vt->capacity);
			return next_idx;
		} else if (p[idxc] == cut && p[1-idxc] == oocut) {
			//printf("Trouvé !!!!!!!!!!! %d\n",(int) p[2]);
			//printf("Count1 : %d %lf\n",count,(double)new_vt->numElems/new_vt->capacity);
			trouve++;
			//printf("%d %d %lf\n",new_vt->numElems,trouve,(double)new_vt->numElems/trouve);
			//printf("%d\n",(int)p[2]);
			return (int) p[2];
		} else {
			pos++;
			count++;
		}
	}
}
	
#define MAX_POINTS 12
#define NEXT(k) (((k) < (nbr_points-1)) ? ((k)+1) : 0)
#define PREV(k) (((k) > 0) ? ((k)-1) : (nbr_points-1))
static void cut_convex_poly_along_grid(int recur, int *poly, int nbr_points, int type, const Mesh *m, const Grid *g, double (*gc)[2], Mesh *mcut, HashTable *new_vt)
{
	//if (recur>0) printf("%d\n",recur);
	//if (recur>4) {
	//	printf("Nbr points : %d\n", nbr_points);
	//	for (int k=0; k < nbr_points; ++k) {
	//		printf("%lf %lf\n",gc[poly[k]][0],gc[poly[k]][1]);
	//	}
	//}
	assert(recur<10);
	//printf("Nbr points %d\n",nbr_points);
	double cut;
	int idxc;
	check_cut_coord(poly, nbr_points, gc, &cut, &idxc);
	if (idxc == -1) {
		//printf("Ok.\n");
		for (int i=nbr_points-2; i>0; --i) {
			mcut->triangles[mcut->ntri].v3 = poly[i + 1];
			mcut->triangles[mcut->ntri].v2 = poly[i];
			mcut->triangles[mcut->ntri].v1 = poly[0];
			mcut->triangles[mcut->ntri].type = type;
			mcut->ntri++;
		}
		return;
	}
	//printf("Not Ok !!!!!!!!!!!!! %d\n",idxc);
	double ocut;
	uint32_t halfpoly[MAX_POINTS];
	int kin=0;
	int kout=0;
	uint32_t idxin, idxout;
	uint32_t idx1, idx2;
	double lambda;
	if (gc[poly[kin]][idxc] < cut) {
		kin++;
		while (gc[poly[kin]][idxc] < cut) kin++;
	} else {
		kin = nbr_points - 1;
		while (gc[poly[kin]][idxc] >= cut) kin--;
		kin = NEXT(kin);
	}
	// A ce niveau kin contient l'indice d'entrée dans la zone >= cut.
	if (gc[poly[kin]][idxc] > cut) {
		// Construction du point de coupe
		//printf("Coupe0\n");
		idx2 = poly[kin];
		idx1 = poly[PREV(kin)];
		//printf("%d %d %d %d\n",kin,idx2,PREV(kin),idx1);
		lambda = (gc[idx2][idxc]-cut) / (gc[idx2][idxc]-gc[idx1][idxc]);
		//assert(lambda <=1);
		//assert(lambda>=0);
		ocut = lambda * gc[idx1][1 - idxc] + (1 - lambda) *  gc[idx2][1 - idxc];
		if ((idxin = find_cut_point(cut, ocut, idxc, new_vt, mcut->nvert)) == mcut->nvert) {
			gc[idxin][idxc] = cut;
			gc[idxin][1 - idxc] = ocut;
			g->grid_to_xy(gc[idxin][0],gc[idxin][1],&mcut->vertices[idxin].x, &mcut->vertices[idxin].y, g->zl);
			mcut->vertices[idxin].z = lambda * mcut->vertices[idx1].z + (1 - lambda) * mcut->vertices[idx2].z;
			mcut->normals[idxin].nx = lambda * mcut->normals[idx1].nx + (1 - lambda) * mcut->normals[idx2].nx;
			mcut->normals[idxin].ny = lambda * mcut->normals[idx1].ny + (1 - lambda) * mcut->normals[idx2].ny;
			mcut->nvert++;
		}
		// Ajout du point de coupe et du point courant
		//printf("Ajout1 %d\n",idxin);
		halfpoly[kout++] = idxin;
		//printf("Ajout2 %d\n",idx2);
		halfpoly[kout++] = idx2;
		kin = NEXT(kin);
	} else {
		//printf("Pas coupe0\n");
		// Ajout du point courant et du suivant.
		idxin = poly[kin];
		//printf("Ajout1bis %d\n",idxin);
		halfpoly[kout++] = idxin;
		kin = NEXT(kin);
		//printf("Ajout2bis %d\n",poly[kin]);
		halfpoly[kout++] = poly[kin];
		kin = NEXT(kin);
	}
	while (gc[poly[kin]][idxc] > cut) {
		//printf("Ajout3 %d\n",poly[kin]);
		halfpoly[kout++] = poly[kin];
		kin = NEXT(kin);
	}
	// première réentrée dans la zone <= cut
	if (gc[poly[kin]][idxc] < cut) {
		// Ajouter le point de coupe
		//printf("Coupe1\n");
		idx2 = poly[kin];
		idx1 = poly[PREV(kin)];
		//printf("%d %d %d %d\n",kin,idx2,PREV(kin),idx1);
		if (gc[idx2][idxc]-gc[idx1][idxc] >= 0) printf("%lf %lf\n",gc[idx2][idxc],gc[idx1][idxc]);
		//assert(gc[idx2][idxc]-gc[idx1][idxc] < 0);
		//assert(gc[idx2][idxc]<=cut);
		lambda = (gc[idx2][idxc]-cut) / (gc[idx2][idxc]-gc[idx1][idxc]);
		//assert(lambda <=1);
		//assert(lambda>=0);
		ocut = lambda * gc[idx1][1 - idxc] + (1 - lambda) *  gc[idx2][1 - idxc];
		if ((idxout = find_cut_point(cut, ocut, idxc, new_vt, mcut->nvert )) == mcut->nvert) {
			gc[idxout][idxc] = cut;
			gc[idxout][1 - idxc] = ocut;
			g->grid_to_xy(gc[idxout][0],gc[idxout][1],&mcut->vertices[idxout].x, &mcut->vertices[idxout].y, g->zl);
			mcut->vertices[idxout].z = lambda * mcut->vertices[idx1].z + (1 - lambda) * mcut->vertices[idx2].z;
			mcut->normals[idxout].nx = lambda * mcut->normals[idx1].nx + (1 - lambda) * mcut->normals[idx2].nx;
			mcut->normals[idxout].ny = lambda * mcut->normals[idx1].ny + (1 - lambda) * mcut->normals[idx2].ny;
			mcut->nvert++;
		}
		// Ajout du point de coupe et du point courant
		halfpoly[kout++] = idxout;
		//halfpoly[kout++] = idx2;
		//kin = NEXT(kin);
	} else {
		//printf("Pas Coupe1\n");
		halfpoly[kout++] = poly[kin];
		idxout = poly[kin]; 
		kin = NEXT(kin);
	}
	cut_convex_poly_along_grid(recur+1, halfpoly, kout, type, m, g, gc, mcut, new_vt);
	kout = 0;
	halfpoly[kout++] = idxout;
	halfpoly[kout++] = poly[kin];
	kin = NEXT(kin);
	while (gc[poly[kin]][idxc] < cut) {
		halfpoly[kout++] = poly[kin];
		kin = NEXT(kin);
	}
	halfpoly[kout++] = idxin;
	cut_convex_poly_along_grid(recur +1, halfpoly, kout, type, m, g, gc, mcut, new_vt);
}
#undef MAX_POINTS
#undef PREV
#undef NEXT

int split_mesh_according_to_grid(const Mesh *m, const Grid *g, MeshGrid *mg) 
{
	// shortcuts
	Vertex   *mv = m->vertices;
	Normal   *mn = m->normals;
	Triangle *mt = m->triangles;
	// variables
	int *mntri;   // nbr of triangles in each mesh
	int *mnvert;  // nbr of vertices in each mesh
	int *t2mesh;  // triangle to mesh map
	int *idxinfo; // hash table 
	// clean-up in case it wouldn't be cleared yet.
	dispose_meshgrid(mg);
	// initialization
	if (initialize_meshgrid_from_grid(mg,g) != 0) return 0;
	int nbr_mesh = mg->nbr_mesh;
	// memory allocation
	if ((mntri= (int *) calloc(nbr_mesh, sizeof(int))) == NULL) goto memory_missing;
	if ((mnvert=(int *) calloc(nbr_mesh, sizeof(int))) == NULL) goto memory_missing;
	if ((t2mesh=(int *) calloc(m->ntri, sizeof(int))) == NULL) goto memory_missing;
	for (int i=0; i<m->ntri; ++i) {
		double bary_x = (mv[mt[i].v1].x + mv[mt[i].v2].x + mv[mt[i].v3].x) / 3.0;
		double bary_y = (mv[mt[i].v1].y + mv[mt[i].v2].y + mv[mt[i].v3].y) / 3.0;
		double p,q;
		g->xy_to_grid(bary_x,bary_y,&p,&q,g->zl);
		int k = ((int)p - g->bounds[0])+((int)q-g->bounds[1])*(g->bounds[2]-g->bounds[0]);  // row major 
		//printf("%d %d\n",(int)p - g->bounds[0],(int)q-g->bounds[1]);
		//printf("%d %d\n",k,nbr_mesh);
		t2mesh[i] = k;
		mntri[k] += 1;
	}
	for (int k=0; k<nbr_mesh; ++k) {
		if (!mntri[k]) continue;
		mg->meshes[k].ntri = mntri[k];
		if ((mg->meshes[k].triangles = (Triangle *) calloc(mntri[k], sizeof(Triangle))) == NULL) goto memory_missing;
                if ((mg->meshes[k].vertices = (Vertex *) calloc(3*mntri[k], sizeof(Vertex))) == NULL) goto memory_missing; // certainly more than necessary
                if ((mg->meshes[k].normals = (Normal *) calloc(3*mntri[k], sizeof(Normal))) == NULL) goto memory_missing; // certainly more than necessary
	}
	free(mntri);
	if ((idxinfo = (int *) malloc(8*m->nvert * sizeof(int))) == NULL) goto memory_missing;
	for (int i=0; i<8*m->nvert; ++i) idxinfo[i]=INT_MAX;
	Triangle **newtri = (Triangle **) malloc(nbr_mesh * sizeof(Triangle *));
	Vertex **newvert = (Vertex **) malloc(nbr_mesh * sizeof(Vertex *));
	Normal **newnorm = (Normal **) malloc(nbr_mesh * sizeof(Normal *));
	if ((newtri == NULL) || (newvert == NULL) || (newnorm == NULL)) goto memory_missing;
	for (int k=0; k<nbr_mesh; ++k) newtri[k] = mg->meshes[k].triangles;
	for (int k=0; k<nbr_mesh; ++k) newvert[k] = mg->meshes[k].vertices;
	for (int k=0; k<nbr_mesh; ++k) newnorm[k] = mg->meshes[k].normals;
	for (int i=0; i<m->ntri;++i) {
		int k = t2mesh[i];
		int newidx;
		newidx = find_or_set_new_index(mt[i].v1, k, mnvert[k], idxinfo);
		(*newtri[k]).v1 = newidx;
		if (newidx == mnvert[k]) {
			*newvert[k] = mv[mt[i].v1];
			*newnorm[k] = mn[mt[i].v1];
                        newvert[k]++; 
			newnorm[k]++;
			mnvert[k]++;
		}
		newidx = find_or_set_new_index(mt[i].v2, k, mnvert[k], idxinfo);
		(*newtri[k]).v2 = newidx;
		if (newidx == mnvert[k]) {
			*newvert[k] = mv[mt[i].v2];
			*newnorm[k] = mn[mt[i].v2];
                        newvert[k]++; 
			newnorm[k]++;
			mnvert[k]++;
		}
		newidx = find_or_set_new_index(mt[i].v3, k, mnvert[k], idxinfo);
		(*newtri[k]).v3 = newidx;
		if (newidx == mnvert[k]) {
			*newvert[k] = mv[mt[i].v3];
			*newnorm[k] = mn[mt[i].v3];
                        newvert[k]++; 
			newnorm[k]++;
			mnvert[k]++;
		}
		(*newtri[k]).type = mt[i].type;
		newtri[k]++;
	}
	free(newtri); free(newvert); free(newnorm);
	free(idxinfo);
	free(t2mesh);
	for (int k=0; k<nbr_mesh; ++k) mg->meshes[k].nvert = mnvert[k];
	free(mnvert);
	optimize_z_scals_from_mesh_bounds(mg);
	return 0;
memory_missing:
	free(mntri); free(mnvert); free(t2mesh); free(idxinfo); free(newtri);
       	free(newnorm); free(newvert);
	dispose_meshgrid(mg);
	return 1;
}




static int find_or_set_new_index(int n, int k, int alt, int *idxinfo) 
{
	int *p = idxinfo + 8 * n;
	while (1) {
		if (p[0] == k) return p[1]; // the vertex was already treated
		if (p[0] == INT_MAX) {      // the vertex is new
			p[0] = k;
			p[1] = alt; 
			return alt;
		}
		p+=2;                       // the vertex was already put in a coincident mesh
	}
}

int aggregate_meshgrid_into_mesh(const MeshGrid *mg, Mesh *m)
{
	uint32_t idx_shift = 0;
        uint32_t total_vert = 0;
        uint32_t total_tri = 0;
	for (int i = 0; i < mg->nbr_mesh; ++i) {
		total_vert += mg->meshes[i].nvert;
		total_tri += mg->meshes[i].ntri;
	}
	if (initialize_mesh(m, total_vert, total_tri) != 0) return -1;
        total_vert = 0;
        total_tri = 0;
	for (int i = 0; i < mg->nbr_mesh; ++i) {
		memcpy(&m->vertices[total_vert], mg.meshes[i].vertices, mg->meshes[i].nvert * sizeof(Vertex));
		memcpy(&m->triangles[total_tri], mg.meshes[i].triangles, mg->meshes[i].ntri * sizeof(Triangle));
		for (int j = 0; j < mg->meshes[i].ntri; ++j) {
			m->triangles[total_tri + j].n1 += total_vert;
			m->triangles[total_tri + j].n2 += total_vert;
			m->triangles[total_tri + j].n3 += total_vert;
		}
		total_vert += mg->meshes[i].nvert;
		total_tri += mg->meshes[i].ntri;
	}
	m->nvert = total_vert;
	m->ntri = total_tri;
}

