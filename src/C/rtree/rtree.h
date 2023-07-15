#pragma once
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#define NDEBUG
#include "assert.h"
#include <math.h>


#ifndef TRUE
#define TRUE 1
#endif
#ifndef FALSE
#define FALSE 0
#endif

#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define MAX(a, b) ((a) > (b) ? (a) : (b))

/*-----------------------------------------------------------------------------
| Global definitions.
-----------------------------------------------------------------------------*/

#define NUMDIMS	2	/* number of dimensions */
#define NUMSIDES 2*NUMDIMS
#if NUMDIMS == 2
#define TEST
#endif

//#define SPLIT_L         /* will use linear versus quadratic search if defined */

typedef double RectReal;


struct Rect
{
	RectReal boundary[NUMSIDES]; /* xmin,ymin,...,xmax,ymax,... */
};

struct Node;

struct Branch
{
	struct Rect rect;
	struct Node *child;
};   

/* max branching factor of a node */
#ifndef MAXCARD
#define MAXCARD 6
#endif

struct Node * next_allocated_node = NULL;

#define METHODS 1
struct Branch BranchBuf[MAXCARD+1];
int BranchCount;
struct Rect CoverSplit;
RectReal CoverSplitArea;

/* variables for finding a partition */
struct PartitionVars
{
	int partition[MAXCARD+1];
	int total, minfill;
	int taken[MAXCARD+1];
	int count[2];
	struct Rect cover[2];
	RectReal area[2];
} Partitions[METHODS];

struct Node
{
	int count;
	int level; /* 0 is leaf, others positive */
	struct Branch branch[MAXCARD];
};

int NODECARD = MAXCARD;
int LEAFCARD = MAXCARD;

/* balance criteria for node splitting */
/* NOTE: can be changed if needed. */
#define MinNodeFill (NODECARD / 2)
#define MinLeafFill (LEAFCARD / 2)

#define MAXKIDS(n) ((n)->level > 0 ? NODECARD : LEAFCARD)
#define MINFILL(n) ((n)->level > 0 ? MinNodeFill : MinLeafFill)

struct ListNode
{
	struct ListNode *next;
	struct Node *node;
};



/*-----------------------------------------------------------------------------
|
| I. Rectangles
|
-----------------------------------------------------------------------------*/

#define Undefined(x) ((x)->boundary[0] > (x)->boundary[NUMDIMS])

extern void RTreeTabIn(int depth)
{
	int i;
	for(i=0; i<depth; i++)
		putchar('\t');
}

/*-----------------------------------------------------------------------------
| Initialize a rectangle to have all 0 coordinates.
-----------------------------------------------------------------------------*/
void RTreeInitRect(struct Rect *R)
{
	register struct Rect *r = R;
	register int i;
	for (i=0; i<NUMSIDES; i++)
		r->boundary[i] = (RectReal)0;
}


/*-----------------------------------------------------------------------------
| Return a rect whose first low side is higher than its opposite side -
| interpreted as an undefined rect.
-----------------------------------------------------------------------------*/
struct Rect RTreeNullRect()
{
	struct Rect r;
#ifdef TEST
	r.boundary[0] = (RectReal) 1;
	r.boundary[2] = (RectReal)-1;
	r.boundary[1] = r.boundary[3] = (RectReal)0;
	return r;
#else
	register int i;

	r.boundary[0] = (RectReal)1;
	r.boundary[NUMDIMS] = (RectReal)-1;
	for (i=1; i<NUMDIMS; i++)
		r.boundary[i] = r.boundary[i+NUMDIMS] = (RectReal)0;
	return r;
#endif
}


/*-----------------------------------------------------------------------------
| Print out the data for a rectangle.
-----------------------------------------------------------------------------*/
void RTreePrintRect(struct Rect *R, int depth)
{
	register struct Rect *r = R;
	register int i;
	assert(r);

	RTreeTabIn(depth);
	printf("rect:\n");
	for (i = 0; i < NUMDIMS; i++) {
		RTreeTabIn(depth+1);
		printf("%f\t%f\n", r->boundary[i], r->boundary[i + NUMDIMS]);
	}
}

/*-----------------------------------------------------------------------------
| Calculate the n-dimensional volume of a rectangle
-----------------------------------------------------------------------------*/
RectReal RTreeRectVolume(struct Rect *R)
{
#ifdef TEST
	if (Undefined(R))
		return (RectReal)0;
	return (R->boundary[2] - R->boundary[0])*(R->boundary[3] - R->boundary[1]);

#else
	register struct Rect *r = R;
	register int i;
	register RectReal volume = (RectReal)1;

	assert(r);
	if (Undefined(r))
		return (RectReal)0;

	for(i=0; i<NUMDIMS; i++)
		volume *= r->boundary[i+NUMDIMS] - r->boundary[i];
	assert(volume >= 0.0);
	return volume;
#endif
}

/* Precomputed volumes of the unit spheres for the first few dimensions */
const double UnitSphereVolumes[] = {
	0.000000,  /* dimension   0 */
	2.000000,  /* dimension   1 */
	3.141593,  /* dimension   2 */
	4.188790,  /* dimension   3 */
	4.934802,  /* dimension   4 */
	5.263789,  /* dimension   5 */
	5.167713,  /* dimension   6 */
	4.724766,  /* dimension   7 */
	4.058712,  /* dimension   8 */
	3.298509,  /* dimension   9 */
	2.550164,  /* dimension  10 */
	1.884104,  /* dimension  11 */
	1.335263,  /* dimension  12 */
	0.910629,  /* dimension  13 */
	0.599265,  /* dimension  14 */
	0.381443,  /* dimension  15 */
	0.235331,  /* dimension  16 */
	0.140981,  /* dimension  17 */
	0.082146,  /* dimension  18 */
	0.046622,  /* dimension  19 */
	0.025807,  /* dimension  20 */
};
#if NUMDIMS > 20
#	error "not enough precomputed sphere volumes"
#endif
#define UnitSphereVolume UnitSphereVolumes[NUMDIMS]


/*-----------------------------------------------------------------------------
| Calculate the n-dimensional volume of the bounding sphere of a rectangle
-----------------------------------------------------------------------------*/

/*
 * The exact volume of the bounding sphere for the given Rect.
 */
RectReal RTreeRectSphericalVolume(struct Rect *R)
{
#ifdef TEST
	if (Undefined(R))
		return (RectReal)0;
	return (RectReal) (((R->boundary[2]-R->boundary[0]) * (R->boundary[2]-R->boundary[0]) +  
	                    (R->boundary[3]-R->boundary[1]) * (R->boundary[3]-R->boundary[1])
	                   ) * UnitSphereVolume / 4
			  );   
#else
	register struct Rect *r = R;
	register int i;
	register double sum_of_squares=0;
	register double radius;
	assert(r);
	if (Undefined(r))
		return (RectReal)0;
	for (i = 0; i < NUMDIMS; i++) {
		double half_extent =
			(r->boundary[i+NUMDIMS] - r->boundary[i]) / 2;
		sum_of_squares += half_extent * half_extent;
	}
	radius = sqrt(sum_of_squares);
	return (RectReal)(pow(radius, NUMDIMS) * UnitSphereVolume);
#endif
}


/*-----------------------------------------------------------------------------
| Calculate the n-dimensional surface area of a rectangle
-----------------------------------------------------------------------------*/
//RectReal RTreeRectSurfaceArea(struct Rect *R)
//{
//	register struct Rect *r = R;
//	register int i, j;
//	register RectReal sum = (RectReal)0;
//
//	assert(r);
//	if (Undefined(r))
//		return (RectReal)0;
//
//	for (i=0; i<NUMDIMS; i++) {
//		RectReal face_area = (RectReal)1;
//		for (j=0; j<NUMDIMS; j++)
//			/* exclude i extent from product in this dimension */
//			if(i != j) {
//				RectReal j_extent =
//					r->boundary[j+NUMDIMS] - r->boundary[j];
//				face_area *= j_extent;
//			}
//		sum += face_area;
//	}
//	return 2 * sum;
//}
//


/*-----------------------------------------------------------------------------
| Combine two rectangles, make one that includes both.
-----------------------------------------------------------------------------*/
struct Rect RTreeCombineRect(struct Rect *R, struct Rect *Rr)
{
#ifdef TEST
	struct Rect new_rect;
	if (Undefined(R))
		return *Rr;

	if (Undefined(Rr))
		return *R;
	new_rect.boundary[0] = MIN(R->boundary[0], Rr->boundary[0]);
	new_rect.boundary[2] = MAX(R->boundary[2], Rr->boundary[2]);
	new_rect.boundary[1] = MIN(R->boundary[1], Rr->boundary[1]);
	new_rect.boundary[3] = MAX(R->boundary[3], Rr->boundary[3]);
        return new_rect; 	
#else
	register struct Rect *r = R, *rr = Rr;
	register int i, j;
	struct Rect new_rect;
	assert(r && rr);

	if (Undefined(r))
		return *rr;

	if (Undefined(rr))
		return *r;

	for (i = 0; i < NUMDIMS; i++)
	{
		new_rect.boundary[i] = MIN(r->boundary[i], rr->boundary[i]);
		j = i + NUMDIMS;
		new_rect.boundary[j] = MAX(r->boundary[j], rr->boundary[j]);
	}
	return new_rect;
#endif
}


/*-----------------------------------------------------------------------------
| Decide whether two rectangles overlap.
-----------------------------------------------------------------------------*/
int RTreeOverlap(struct Rect *R, struct Rect *S)
{
#ifdef TEST
	//printf("%f %f %f %f\n %f %f %f %f\n\n",R->boundary[0],R->boundary[2],R->boundary[1],R->boundary[3],S->boundary[0],S->boundary[2],S->boundary[1],S->boundary[3]);
	return  !( R->boundary[0] > S->boundary[2] || 
		  S->boundary[0] > R->boundary[2] ||
	          R->boundary[1] > S->boundary[3] || 
		  S->boundary[1] > R->boundary[3]
		); 
#else
	//printf("%f %f %f %f\n %f %f %f %f\n\n",R->boundary[0],R->boundary[2],R->boundary[1],R->boundary[3],S->boundary[0],S->boundary[2],S->boundary[1],S->boundary[3]);
	register struct Rect *r = R, *s = S;
	register int i, j;
	assert(r && s);

	for (i=0; i<NUMDIMS; i++)
	{
		j = i + NUMDIMS;  /* index for high sides */
		if (r->boundary[i] > s->boundary[j] ||
		    s->boundary[i] > r->boundary[j])
		{
			return FALSE;
		}
	}
	return TRUE;
#endif
}


/*-----------------------------------------------------------------------------
| Decide whether rectangle r is contained in rectangle s.
-----------------------------------------------------------------------------*/
int RTreeContained(struct Rect *R, struct Rect *S)
{
#ifdef TEST
 	// undefined rect is contained in any other
	//
	if (Undefined(R))
		return TRUE;

	// no rect (except an undefined one) is contained in an undef rect
	//
	if (Undefined(S))
		return FALSE;
	return (R->boundary[0] >= S->boundary[0] &&
	        R->boundary[2] <= S->boundary[2] &&
	        R->boundary[1] >= S->boundary[1] &&
	        R->boundary[3] <= S->boundary[3] 
	       );
#else
	register struct Rect *r = R, *s = S;
	register int i, j, result;
	//assert((int)r && (int)s);

 	// undefined rect is contained in any other
	//
	if (Undefined(r))
		return TRUE;

	// no rect (except an undefined one) is contained in an undef rect
	//
	if (Undefined(s))
		return FALSE;

	result = TRUE;
	for (i = 0; i < NUMDIMS; i++)
	{
		j = i + NUMDIMS;  /* index for high sides */
		result = result
			&& r->boundary[i] >= s->boundary[i]
			&& r->boundary[j] <= s->boundary[j];
	}
	return result;
#endif
}

/*-----------------------------------------------------------------------------
|
| II. Branches and Nodes 
|
-----------------------------------------------------------------------------*/

// Forward declaration
void RTreeSplitNode(struct Node *n, struct Branch *b, struct Node **nn);

// Initialize one branch cell in a node.
//
static void RTreeInitBranch(struct Branch *b)
{
	RTreeInitRect(&(b->rect));
	b->child = NULL;
}



// Initialize a Node structure.
//
void RTreeInitNode(struct Node *N)
{
	register struct Node *n = N;
	register int i;
	n->count = 0;
	n->level = -1;
	for (i = 0; i < MAXCARD; i++)
		RTreeInitBranch(&(n->branch[i]));
}



// Make a new node and initialize to have all branch cells empty.
//
struct Node * RTreeNewNode()
{
	register struct Node *n;

	//n = new Node;
	n = (struct Node*)malloc(sizeof(struct Node));
	assert(n);
	RTreeInitNode(n);
	return n;
	//return next_allocated_node++;
}


void RTreeFreeNode(struct Node *p)
{
	assert(p);
	//delete p;
	free(p);
}

// Forward declaration
void RTreePrintNode(struct Node *n, int depth);

static void RTreePrintBranch(struct Branch *b, int depth)
{
	RTreePrintRect(&(b->rect), depth);
	RTreePrintNode(b->child, depth);
}


// Print out the data in a node.
//
void RTreePrintNode(struct Node *n, int depth)
{
	int i;
	assert(n);

	RTreeTabIn(depth);
	printf("node");
	if (n->level == 0)
		printf(" LEAF");
	else if (n->level > 0)
		printf(" NONLEAF");
	else
		printf(" TYPE=?");
	printf("  level=%d  count=%d  address=%o\n", n->level, n->count, n);

	for (i=0; i<n->count; i++)
	{
		if(n->level == 0) {
			// RTreeTabIn(depth);
			// printf("\t%d: data = %d\n", i, n->branch[i].child);
		}
		else {
			RTreeTabIn(depth);
			printf("branch %d\n", i);
			RTreePrintBranch(&n->branch[i], depth+1);
		}
	}
}



// Find the smallest rectangle that includes all rectangles in
// branches of a node.
//
struct Rect RTreeNodeCover(struct Node *N)
{
	register struct Node *n = N;
	register int i, first_time=1;
	struct Rect r;
	assert(n);

	RTreeInitRect(&r);
	for (i = 0; i < MAXKIDS(n); i++)
		if (n->branch[i].child)
		{
			if (first_time)
			{
				r = n->branch[i].rect;
				first_time = 0;
			}
			else
				r = RTreeCombineRect(&r, &(n->branch[i].rect));
		}
	return r;
}



// Pick a branch.  Pick the one that will need the smallest increase
// in area to accomodate the new rectangle.  This will result in the
// least total area for the covering rectangles in the current node.
// In case of a tie, pick the one which was smaller before, to get
// the best resolution when searching.
//
int RTreePickBranch(struct Rect *R, struct Node *N)
{
#ifdef TEST
	register int i;
	RectReal increase, bestIncr = (RectReal) 1e99 , area, bestArea;
	int best;
	struct Rect tmp_rect;

	for (i=0; i < MAXCARD; i++)
	{
		if (N->branch[i].child)
		{
			area = RTreeRectSphericalVolume(&N->branch[i].rect);
			tmp_rect = RTreeCombineRect(R, &N->branch[i].rect);
			increase = RTreeRectSphericalVolume(&tmp_rect) - area;
			if (increase < bestIncr || (increase == bestIncr && area < bestArea))
			{
				best = i;
				bestArea = area;
				bestIncr = increase;
			}
		}
	}
	return best;
#else
	register struct Rect *r = R;
	register struct Node *n = N;
	register struct Rect *rr;
	register int i, first_time=1;
	RectReal increase, bestIncr=(RectReal)-1, area, bestArea;
	int best;
	struct Rect tmp_rect;
	assert(r && n);

	for (i=0; i<MAXKIDS(n); i++)
	{
		if (n->branch[i].child)
		{
			rr = &n->branch[i].rect;
			area = RTreeRectSphericalVolume(rr);
			tmp_rect = RTreeCombineRect(r, rr);
			increase = RTreeRectSphericalVolume(&tmp_rect) - area;
			if (increase < bestIncr || first_time)
			{
				best = i;
				bestArea = area;
				bestIncr = increase;
				first_time = 0;
			}
			else if (increase == bestIncr && area < bestArea)
			{
				best = i;
				bestArea = area;
				bestIncr = increase;
			}
		}
	}
	return best;
#endif
}




// Add a branch to a node.  Split the node if necessary.
// Returns 0 if node not split.  Old node updated.
// Returns 1 if node split, sets *new_node to address of new node.
// Old node updated, becomes one of two.
//
int RTreeAddBranch(struct Branch *B, struct Node *N, struct Node **New_node)
{
	register struct Branch *b = B;
	register struct Node *n = N;
	register struct Node **new_node = New_node;
	register int i;

	assert(b);
	assert(n);

	if (n->count < MAXKIDS(n))  /* split won't be necessary */
	{
		for (i = 0; i < MAXKIDS(n); i++)  /* find empty branch */
		{
			if (n->branch[i].child == NULL)
			{
				n->branch[i] = *b;
				n->count++;
				break;
			}
		}
		return 0;
	}
	else
	{
		assert(new_node);
		RTreeSplitNode(n, b, new_node);
		return 1;
	}
}



// Disconnect a dependent node.
//
void RTreeDisconnectBranch(struct Node *n, int i)
{
	assert(n && i>=0 && i<MAXKIDS(n));
	assert(n->branch[i].child);

	RTreeInitBranch(&(n->branch[i]));
	n->count--;
}

/*-----------------------------------------------------------------------------
|
| III. Spliting of Branches 
|
-----------------------------------------------------------------------------*/

#ifdef SPLIT_L
/*-----------------------------------------------------------------------------
| Load branch buffer with branches from full node plus the extra branch.
-----------------------------------------------------------------------------*/
static void RTreeGetBranches(struct Node *N, struct Branch *B)
{
	register struct Node *n = N;
	register struct Branch *b = B;
	register int i;

	assert(n);
	assert(b);

	/* load the branch buffer */
	for (i=0; i<MAXKIDS(n); i++)
	{
		assert(n->branch[i].child);  /* every entry should be full */
		BranchBuf[i] = n->branch[i];
	}
	BranchBuf[MAXKIDS(n)] = *b;
	BranchCount = MAXKIDS(n) + 1;

	/* calculate rect containing all in the set */
	CoverSplit = BranchBuf[0].rect;
	for (i=1; i<MAXKIDS(n)+1; i++)
	{
		CoverSplit = RTreeCombineRect(&CoverSplit, &BranchBuf[i].rect);
	}

	RTreeInitNode(n);
}



/*-----------------------------------------------------------------------------
| Initialize a PartitionVars structure.
-----------------------------------------------------------------------------*/
static void RTreeInitPVars(struct PartitionVars *P, int maxrects, int minfill)
{
	register struct PartitionVars *p = P;
	register int i;
	assert(p);

	p->count[0] = p->count[1] = 0;
	p->total = maxrects;
	p->minfill = minfill;
	for (i=0; i<maxrects; i++)
	{
		p->taken[i] = FALSE;
		p->partition[i] = -1;
	}
}



/*-----------------------------------------------------------------------------
| Put a branch in one of the groups.
-----------------------------------------------------------------------------*/
static void RTreeClassify(int i, int group, struct PartitionVars *p)
{
	assert(p);
	assert(!p->taken[i]);

	p->partition[i] = group;
	p->taken[i] = TRUE;

	if (p->count[group] == 0)
		p->cover[group] = BranchBuf[i].rect;
	else
		p->cover[group] = RTreeCombineRect(&BranchBuf[i].rect,
					&p->cover[group]);
	p->area[group] = RTreeRectSphericalVolume(&p->cover[group]);
	p->count[group]++;
}



/*-----------------------------------------------------------------------------
| Pick two rects from set to be the first elements of the two groups.
| Pick the two that are separated most along any dimension, or overlap least.
| Distance for separation or overlap is measured modulo the width of the
| space covered by the entire set along that dimension.
-----------------------------------------------------------------------------*/
static void RTreePickSeeds(struct PartitionVars *P)
{
	register struct PartitionVars *p = P;
	register int i, dim, high;
	register struct Rect *r, *rlow, *rhigh;
	register float w, separation, bestSep;
	RectReal width[NUMDIMS];
	int leastUpper[NUMDIMS], greatestLower[NUMDIMS];
	int seed0, seed1;
	assert(p);
	
	for (dim=0; dim<NUMDIMS; dim++)
	{
		high = dim + NUMDIMS;

		/* find the rectangles farthest out in each direction
		 * along this dimens */
		greatestLower[dim] = leastUpper[dim] = 0;
		for (i=1; i<NODECARD+1; i++)
		{
			r = &BranchBuf[i].rect;
			if (r->boundary[dim] >
			    BranchBuf[greatestLower[dim]].rect.boundary[dim])
			{
				greatestLower[dim] = i;
			}
			if (r->boundary[high] <
			    BranchBuf[leastUpper[dim]].rect.boundary[high])
			{
				leastUpper[dim] = i;
			}
		}

		/* find width of the whole collection along this dimension */
		width[dim] = CoverSplit.boundary[high] -
			     CoverSplit.boundary[dim];
	}

	/* pick the best separation dimension and the two seed rects */
	for (dim=0; dim<NUMDIMS; dim++)
	{
		high = dim + NUMDIMS;

		/* divisor for normalizing by width */
		assert(width[dim] >= 0);
		if (width[dim] == 0)
			w = (RectReal)1;
		else
			w = width[dim];

		rlow = &BranchBuf[leastUpper[dim]].rect;
		rhigh = &BranchBuf[greatestLower[dim]].rect;
		if (dim == 0)
		{
			seed0 = leastUpper[0];
			seed1 = greatestLower[0];
			separation = bestSep =
				(rhigh->boundary[0] -
				 rlow->boundary[NUMDIMS]) / w;
		}
		else
		{
			separation =
				(rhigh->boundary[dim] -
				rlow->boundary[dim+NUMDIMS]) / w;
			if (separation > bestSep)
			{
				seed0 = leastUpper[dim];
				seed1 = greatestLower[dim];
				bestSep = separation;
			}
		}
	}

	if (seed0 != seed1)
	{
		RTreeClassify(seed0, 0, p);
		RTreeClassify(seed1, 1, p);
	}
}



/*-----------------------------------------------------------------------------
| Put each rect that is not already in a group into a group.
| Process one rect at a time, using the following hierarchy of criteria.
| In case of a tie, go to the next test.
| 1) If one group already has the max number of elements that will allow
| the minimum fill for the other group, put r in the other.
| 2) Put r in the group whose cover will expand less.  This automatically
| takes care of the case where one group cover contains r.
| 3) Put r in the group whose cover will be smaller.  This takes care of the
| case where r is contained in both covers.
| 4) Put r in the group with fewer elements.
| 5) Put in group 1 (arbitrary).
|
| Also update the covers for both groups.
-----------------------------------------------------------------------------*/
static void RTreePigeonhole(struct PartitionVars *P)
{
	register struct PartitionVars *p = P;
	struct Rect newCover[2];
	register int i, group;
	RectReal newArea[2], increase[2];

	for (i=0; i<NODECARD+1; i++)
	{
		if (!p->taken[i])
		{
			/* if one group too full, put rect in the other */
			if (p->count[0] >= p->total - p->minfill)
			{
				RTreeClassify(i, 1, p);
				continue;
			}
			else if (p->count[1] >= p->total - p->minfill)
			{
				RTreeClassify(i, 0, p);
				continue;
			}

			/* find areas of the two groups' old and new covers */
			for (group=0; group<2; group++)
			{
				if (p->count[group]>0)
					newCover[group] = RTreeCombineRect(
						&BranchBuf[i].rect,
						&p->cover[group]);
				else
					newCover[group] = BranchBuf[i].rect;
				newArea[group] = RTreeRectSphericalVolume(
							&newCover[group]);
				increase[group] = newArea[group]-p->area[group];
			}

			/* put rect in group whose cover will expand less */
			if (increase[0] < increase[1])
				RTreeClassify(i, 0, p);
			else if (increase[1] < increase[0])
				RTreeClassify(i, 1, p);

			/* put rect in group that will have a smaller cover */
			else if (p->area[0] < p->area[1])
				RTreeClassify(i, 0, p);
			else if (p->area[1] < p->area[0])
				RTreeClassify(i, 1, p);

			/* put rect in group with fewer elements */
			else if (p->count[0] < p->count[1])
				RTreeClassify(i, 0, p);
			else
				RTreeClassify(i, 1, p);
		}
	}
	assert(p->count[0] + p->count[1] == NODECARD + 1);
}



/*-----------------------------------------------------------------------------
| Method 0 for finding a partition:
| First find two seeds, one for each group, well separated.
| Then put other rects in whichever group will be smallest after addition.
-----------------------------------------------------------------------------*/
static void RTreeMethodZero(struct PartitionVars *p, int minfill)
{
	RTreeInitPVars(p, BranchCount, minfill);
	RTreePickSeeds(p);
	RTreePigeonhole(p);
}




/*-----------------------------------------------------------------------------
| Copy branches from the buffer into two nodes according to the partition.
-----------------------------------------------------------------------------*/
static void RTreeLoadNodes(struct Node *N, struct Node *Q,
			struct PartitionVars *P)
{
	register struct Node *n = N, *q = Q;
	register struct PartitionVars *p = P;
	register int i;
	assert(n);
	assert(q);
	assert(p);

	for (i=0; i<NODECARD+1; i++)
	{
		if (p->partition[i] == 0)
			RTreeAddBranch(&BranchBuf[i], n, NULL);
		else if (p->partition[i] == 1)
			RTreeAddBranch(&BranchBuf[i], q, NULL);
		else
			assert(FALSE);
	}
}



/*-----------------------------------------------------------------------------
| Split a node.
| Divides the nodes branches and the extra one between two nodes.
| Old node is one of the new ones, and one really new one is created.
-----------------------------------------------------------------------------*/
void RTreeSplitNode(struct Node *n, struct Branch *b, struct Node **nn)
{
	register struct PartitionVars *p;
	register int level;
	RectReal area;

	assert(n);
	assert(b);

	/* load all the branches into a buffer, initialize old node */
	level = n->level;
	RTreeGetBranches(n, b);

	/* find partition */
	p = &Partitions[0];

	/* Note: can't use MINFILL(n) below since n was cleared by GetBranches() */
	RTreeMethodZero(p, level>0 ? MinNodeFill : MinLeafFill);

	/* record how good the split was for statistics */
	area = p->area[0] + p->area[1];

	/* put branches from buffer in 2 nodes according to chosen partition */
	*nn = RTreeNewNode();
	(*nn)->level = n->level = level;
	RTreeLoadNodes(n, *nn, p);
	assert(n->count + (*nn)->count == NODECARD+1);
}



/*-----------------------------------------------------------------------------
| Print out data for a partition from PartitionVars struct.
-----------------------------------------------------------------------------*/
static void RTreePrintPVars(struct PartitionVars *p)
{
	int i;
	assert(p);

	printf("\npartition:\n");
	for (i=0; i<NODECARD+1; i++)
	{
		printf("%3d\t", i);
	}
	printf("\n");
	for (i=0; i<NODECARD+1; i++)
	{
		if (p->taken[i])
			printf("  t\t");
		else
			printf("\t");
	}
	printf("\n");
	for (i=0; i<NODECARD+1; i++)
	{
		printf("%3d\t", p->partition[i]);
	}
	printf("\n");

	printf("count[0] = %d  area = %f\n", p->count[0], p->area[0]);
	printf("count[1] = %d  area = %f\n", p->count[1], p->area[1]);
	printf("total area = %f  effectiveness = %3.2f\n",
		p->area[0] + p->area[1],
		RTreeRectSphericalVolume(&CoverSplit)/(p->area[0]+p->area[1]));

	printf("cover[0]:\n");
	RTreePrintRect(&p->cover[0], 0);

	printf("cover[1]:\n");
	RTreePrintRect(&p->cover[1], 0);
}

#else

/*-----------------------------------------------------------------------------
| Load branch buffer with branches from full node plus the extra branch.
-----------------------------------------------------------------------------*/
static void RTreeGetBranches(struct Node *n, struct Branch *b)
{
	register int i;

	assert(n);
	assert(b);

	/* load the branch buffer */
	for (i=0; i<MAXKIDS(n); i++)
	{
		assert(n->branch[i].child); /* n should have every entry full */
		BranchBuf[i] = n->branch[i];
	}
	BranchBuf[MAXKIDS(n)] = *b;
	BranchCount = MAXKIDS(n) + 1;

	/* calculate rect containing all in the set */
	CoverSplit = BranchBuf[0].rect;
	for (i=1; i<MAXKIDS(n)+1; i++)
	{
		CoverSplit = RTreeCombineRect(&CoverSplit, &BranchBuf[i].rect);
	}
	CoverSplitArea = RTreeRectSphericalVolume(&CoverSplit);

	RTreeInitNode(n);
}




/*-----------------------------------------------------------------------------
| Put a branch in one of the groups.
-----------------------------------------------------------------------------*/
static void RTreeClassify(int i, int group, struct PartitionVars *p)
{
	assert(p);
	assert(!p->taken[i]);

	p->partition[i] = group;
	p->taken[i] = TRUE;

	if (p->count[group] == 0)
		p->cover[group] = BranchBuf[i].rect;
	else
		p->cover[group] =
			RTreeCombineRect(&BranchBuf[i].rect, &p->cover[group]);
	p->area[group] = RTreeRectSphericalVolume(&p->cover[group]);
	p->count[group]++;
}




/*-----------------------------------------------------------------------------
| Pick two rects from set to be the first elements of the two groups.
| Pick the two that waste the most area if covered by a single rectangle.
-----------------------------------------------------------------------------*/
static void RTreePickSeeds(struct PartitionVars *p)
{
	register int i, j, seed0, seed1;
	RectReal worst, waste, area[MAXCARD+1];

	for (i=0; i<p->total; i++)
		area[i] = RTreeRectSphericalVolume(&BranchBuf[i].rect);

	worst = -CoverSplitArea - 1;
	for (i=0; i<p->total-1; i++)
	{
		for (j=i+1; j<p->total; j++)
		{
			struct Rect one_rect = RTreeCombineRect(
						&BranchBuf[i].rect,
						&BranchBuf[j].rect);
			waste = RTreeRectSphericalVolume(&one_rect) -
					area[i] - area[j];
			if (waste > worst)
			{
				worst = waste;
				seed0 = i;
				seed1 = j;
			}
		}
	}
	RTreeClassify(seed0, 0, p);
	RTreeClassify(seed1, 1, p);
}




/*-----------------------------------------------------------------------------
| Copy branches from the buffer into two nodes according to the partition.
-----------------------------------------------------------------------------*/
static void RTreeLoadNodes(struct Node *n, struct Node *q,
			struct PartitionVars *p)
{
	register int i;
	assert(n);
	assert(q);
	assert(p);

	for (i=0; i<p->total; i++)
	{
		assert(p->partition[i] == 0 || p->partition[i] == 1);
		if (p->partition[i] == 0)
			RTreeAddBranch(&BranchBuf[i], n, NULL);
		else if (p->partition[i] == 1)
			RTreeAddBranch(&BranchBuf[i], q, NULL);
	}
}




/*-----------------------------------------------------------------------------
| Initialize a PartitionVars structure.
-----------------------------------------------------------------------------*/
static void RTreeInitPVars(struct PartitionVars *p, int maxrects, int minfill)
{
	register int i;
	assert(p);

	p->count[0] = p->count[1] = 0;
	p->cover[0] = p->cover[1] = RTreeNullRect();
	p->area[0] = p->area[1] = (RectReal)0;
	p->total = maxrects;
	p->minfill = minfill;
	for (i=0; i<maxrects; i++)
	{
		p->taken[i] = FALSE;
		p->partition[i] = -1;
	}
}




/*-----------------------------------------------------------------------------
| Print out data for a partition from PartitionVars struct.
-----------------------------------------------------------------------------*/
static void RTreePrintPVars(struct PartitionVars *p)
{
	register int i;
	assert(p);

	printf("\npartition:\n");
	for (i=0; i<p->total; i++)
	{
		printf("%3d\t", i);
	}
	printf("\n");
	for (i=0; i<p->total; i++)
	{
		if (p->taken[i])
			printf("  t\t");
		else
			printf("\t");
	}
	printf("\n");
	for (i=0; i<p->total; i++)
	{
		printf("%3d\t", p->partition[i]);
	}
	printf("\n");

	printf("count[0] = %d  area = %f\n", p->count[0], p->area[0]);
	printf("count[1] = %d  area = %f\n", p->count[1], p->area[1]);
	if (p->area[0] + p->area[1] > 0)
	{
		printf("total area = %f  effectiveness = %3.2f\n",
			p->area[0] + p->area[1],
			(float)CoverSplitArea / (p->area[0] + p->area[1]));
	}
	printf("cover[0]:\n");
	RTreePrintRect(&p->cover[0], 0);

	printf("cover[1]:\n");
	RTreePrintRect(&p->cover[1], 0);
}


/*-----------------------------------------------------------------------------
| Method #0 for choosing a partition:
| As the seeds for the two groups, pick the two rects that would waste the
| most area if covered by a single rectangle, i.e. evidently the worst pair
| to have in the same group.
| Of the remaining, one at a time is chosen to be put in one of the two groups.
| The one chosen is the one with the greatest difference in area expansion
| depending on which group - the rect most strongly attracted to one group
| and repelled from the other.
| If one group gets too full (more would force other group to violate min
| fill requirement) then other group gets the rest.
| These last are the ones that can go in either group most easily.
-----------------------------------------------------------------------------*/
static void RTreeMethodZero(struct PartitionVars *p, int minfill)
{
	register int i;
	RectReal biggestDiff;
	register int group, chosen, betterGroup;
	assert(p);

	RTreeInitPVars(p, BranchCount, minfill);
	RTreePickSeeds(p);

	while (p->count[0] + p->count[1] < p->total
		&& p->count[0] < p->total - p->minfill
		&& p->count[1] < p->total - p->minfill)
	{
		biggestDiff = (RectReal)-1.;
		for (i=0; i<p->total; i++)
		{
			if (!p->taken[i])
			{
				struct Rect *r, rect_0, rect_1;
				RectReal growth0, growth1, diff;

				r = &BranchBuf[i].rect;
				rect_0 = RTreeCombineRect(r, &p->cover[0]);
				rect_1 = RTreeCombineRect(r, &p->cover[1]);
				growth0 = RTreeRectSphericalVolume(
						&rect_0)-p->area[0];
				growth1 = RTreeRectSphericalVolume(
						&rect_1)-p->area[1];
				diff = growth1 - growth0;
				if (diff >= 0)
					group = 0;
				else
				{
					group = 1;
					diff = -diff;
				}

				if (diff > biggestDiff)
				{
					biggestDiff = diff;
					chosen = i;
					betterGroup = group;
				}
				else if (diff==biggestDiff &&
					 p->count[group]<p->count[betterGroup])
				{
					chosen = i;
					betterGroup = group;
				}
			}
		}
		RTreeClassify(chosen, betterGroup, p);
	}

	/* if one group too full, put remaining rects in the other */
	if (p->count[0] + p->count[1] < p->total)
	{
		if (p->count[0] >= p->total - p->minfill)
			group = 1;
		else
			group = 0;
		for (i=0; i<p->total; i++)
		{
			if (!p->taken[i])
				RTreeClassify(i, group, p);
		}
	}

	assert(p->count[0] + p->count[1] == p->total);
	assert(p->count[0] >= p->minfill && p->count[1] >= p->minfill);
}


/*-----------------------------------------------------------------------------
| Split a node.
| Divides the nodes branches and the extra one between two nodes.
| Old node is one of the new ones, and one really new one is created.
| Tries more than one method for choosing a partition, uses best result.
-----------------------------------------------------------------------------*/
extern void RTreeSplitNode(struct Node *n, struct Branch *b, struct Node **nn)
{
	register struct PartitionVars *p;
	register int level;

	assert(n);
	assert(b);

	/* load all the branches into a buffer, initialize old node */
	level = n->level;
	RTreeGetBranches(n, b);

	/* find partition */
	p = &Partitions[0];
	/* Note: can't use MINFILL(n) below since n was cleared by GetBranches() */
	RTreeMethodZero(p, level>0 ? MinNodeFill : MinLeafFill);

	/*
	 * put branches from buffer into 2 nodes
	 * according to chosen partition
	 */
	*nn = RTreeNewNode();
	(*nn)->level = n->level = level;
	RTreeLoadNodes(n, *nn, p);
	assert(n->count+(*nn)->count == p->total);
}
#endif




/*-----------------------------------------------------------------------------
|
| IV. Index 
|
-----------------------------------------------------------------------------*/

static int set_max(int *which, int new_max)
{
	if(2 > new_max || new_max > MAXCARD)
		return 0;
	*which = new_max;
	return 1;
}
int RTreeSetNodeMax(int new_max) { return set_max(&NODECARD, new_max); }
int RTreeSetLeafMax(int new_max) { return set_max(&LEAFCARD, new_max); }
int RTreeGetNodeMax() { return NODECARD; }
int RTreeGetLeafMax() { return LEAFCARD; }

// Make a new index, empty.  Consists of a single node.
//
struct Node * RTreeNewIndex()
{
	struct Node *x;
	x = RTreeNewNode();
	x->level = 0; /* leaf */
	return x;
}


/*
 * If passed to a tree search, this callback function will be called
 * with the ID of each data rect that overlaps the search rect
 * plus whatever user specific pointer was passed to the search.
 * It can terminate the search early by returning 0 in which case
 * the search will return the number of hits found up to that point.
 */
typedef int (*SearchHitCallback)(size_t id, void* arg);

// Search in an index tree or subtree for all data retangles that
// overlap the argument rectangle.
// Returns 0 if no overlap was found.
// Returns -1 if an overlap was found and the callback wants to terminate early.
// Returns 1 otherwise.
int RTreeSearch(struct Node *N, struct Rect *R, SearchHitCallback shcb, void* cbarg)
{
#ifdef TEST
	register int i;
	register int tmp;

	if (N->level > 0) /* this is an internal node in the tree */
	{
		for (i = 0; i < NODECARD; i++) {
		        if (N->branch[i].child && 
			    RTreeOverlap(R, &N->branch[i].rect) &&
			    (tmp = RTreeSearch(N->branch[i].child, R, shcb, cbarg)))
			{
				return tmp;
			} 
		}	    
	}
	else /* this is a leaf node */
	{
		for (i = 0; i < LEAFCARD; i++) {
			if (N->branch[i].child &&
			    RTreeOverlap(R, &N->branch[i].rect)) {
				if (shcb && (tmp = shcb((size_t) N->branch[i].child, cbarg))) {
					return tmp; // callback wants to terminate search early
				}
			}
		}
	}
	return 0;


#else
	register struct Node *n = N;
	register struct Rect *r = R; 
	register int i;
	register int tmp, found;

	assert(n);
	assert(n->level >= 0);
	assert(r);

	//printf("Level : %d\n",n->level);
	if (n->level > 0) /* this is an internal node in the tree */
	{
		for (i = 0; i < NODECARD; i++)
		        if (n->branch[i].child &&
			    RTreeOverlap(r,&n->branch[i].rect) &&
			    (tmp = RTreeSearch(n->branch[i].child, R, shcb, cbarg)))
			{
			     found = 1;
			     if (tmp < 0) return -1;
			} 
			    
	}
	else /* this is a leaf node */
	{
		for (i = 0; i < LEAFCARD; i++)
			if (n->branch[i].child &&
			    RTreeOverlap(r,&n->branch[i].rect))
			{
				found = 1;
				if (shcb && shcb((size_t) n->branch[i].child, cbarg))
					return -1; // callback wants to terminate search early
			}
	}
	return found;
#endif
}

// Inserts a new data rectangle into the index structure.
// Recursively descends tree, propagates splits back up.
// Returns 0 if node was not split.  Old node updated.
// If node was split, returns 1 and sets the pointer pointed to by
// new_node to point to the new node.  Old node updated to become one of two.
// The level argument specifies the number of steps up from the leaf
// level to insert; e.g. a data rectangle goes in at level = 0.
//
static int RTreeInsertRect2(struct Rect *r,
		size_t tid, struct Node *n, struct Node **new_node, int level)
{
	register int i;
	struct Branch b;
	struct Node *n2;

	assert(r && n && new_node);
	assert(level >= 0 && level <= n->level);

	// Still above level for insertion, go down tree recursively
	//
	if (n->level > level)
	{
		i = RTreePickBranch(r, n);
		if (!RTreeInsertRect2(r, tid, n->branch[i].child, &n2, level))
		{
			// child was not split
			//
			n->branch[i].rect =
				RTreeCombineRect(r, &(n->branch[i].rect));
			return 0;
		}
		else    // child was split
		{
			n->branch[i].rect = RTreeNodeCover(n->branch[i].child);
			b.child = n2;
			b.rect = RTreeNodeCover(n2);
			return RTreeAddBranch(&b, n, new_node);
		}
	}

	// Have reached level for insertion. Add rect, split if necessary
	//
	else if (n->level == level)
	{
		b.rect = *r;
		b.child = (struct Node *) tid;
		/* child field of leaves contains tid of data record */
		return RTreeAddBranch(&b, n, new_node);
	}
	else
	{
		/* Not supposed to happen */
		assert (FALSE);
		return 0;
	}
}



// Insert a data rectangle into an index structure.
// RTreeInsertRect provides for splitting the root;
// returns 1 if root was split, 0 if it was not.
// The level argument specifies the number of steps up from the leaf
// level to insert; e.g. a data rectangle goes in at level = 0.
// RTreeInsertRect2 does the recursion.
//
int RTreeInsertRect(struct Rect *R, size_t Tid, struct Node **Root, int Level)
{
#ifdef TEST
	register int i;
	register struct Node *newroot;
	struct Node *newnode;
	struct Branch b;
	if (RTreeInsertRect2(R, Tid, *Root, &newnode, Level))  /* root split */
	{
		newroot = RTreeNewNode();  /* grow a new root, & tree taller */
		newroot->level = (*Root)->level + 1;
		b.rect = RTreeNodeCover(*Root);
		b.child = *Root;
		RTreeAddBranch(&b, newroot, NULL);
		b.rect = RTreeNodeCover(newnode);
		b.child = newnode;
		RTreeAddBranch(&b, newroot, NULL);
		*Root = newroot;
		return 1;
	}
	else
		return 0;
#else
	register struct Rect *r = R;
	register size_t tid = Tid;
	register struct Node **root = Root;
	register int level = Level;
	register int i;
	register struct Node *newroot;
	struct Node *newnode;
	struct Branch b;
	int result;

	assert(r && root);
	assert(level >= 0 && level <= (*root)->level);
	for (i=0; i<NUMDIMS; i++)
		assert(r->boundary[i] <= r->boundary[NUMDIMS+i]);

	if (RTreeInsertRect2(r, tid, *root, &newnode, level))  /* root split */
	{
		newroot = RTreeNewNode();  /* grow a new root, & tree taller */
		newroot->level = (*root)->level + 1;
		b.rect = RTreeNodeCover(*root);
		b.child = *root;
		RTreeAddBranch(&b, newroot, NULL);
		b.rect = RTreeNodeCover(newnode);
		b.child = newnode;
		RTreeAddBranch(&b, newroot, NULL);
		*root = newroot;
		result = 1;
	}
	else
		result = 0;

	return result;
#endif
}

// Allocate space for a node in the list used in DeletRect to
// store Nodes that are too empty.
//
static struct ListNode * RTreeNewListNode()
{
	return (struct ListNode *) malloc(sizeof(struct ListNode));
}

static void RTreeFreeListNode(struct ListNode *p)
{
	free(p);
}



// Add a node to the reinsertion list.  All its branches will later
// be reinserted into the index structure.
//
static void RTreeReInsert(struct Node *n, struct ListNode **ee)
{
	register struct ListNode *l;

	l = RTreeNewListNode();
	l->node = n;
	l->next = *ee;
	*ee = l;
}


// Delete a rectangle from non-root part of an index structure.
// Called by RTreeDeleteRect.  Descends tree recursively,
// merges branches on the way back up.
// Returns 1 if record not found, 0 if success.
//
static int
RTreeDeleteRect2(struct Rect *R, size_t Tid, struct Node *N, struct ListNode **Ee)
{
	register struct Rect *r = R;
	register size_t tid = Tid;
	register struct Node *n = N;
	register struct ListNode **ee = Ee;
	register int i;

	assert(r && n && ee);
	assert(tid >= 0);
	assert(n->level >= 0);

	if (n->level > 0)  // not a leaf node
	{
	    for (i = 0; i < NODECARD; i++)
	    {
		if (n->branch[i].child && RTreeOverlap(r, &(n->branch[i].rect)))
		{
			if (!RTreeDeleteRect2(r, tid, n->branch[i].child, ee))
			{
				if (n->branch[i].child->count >= MinNodeFill)
					n->branch[i].rect = RTreeNodeCover(
						n->branch[i].child);
				else
				{
					// not enough entries in child,
					// eliminate child node
					//
					RTreeReInsert(n->branch[i].child, ee);
					RTreeDisconnectBranch(n, i);
				}
				return 0;
			}
		}
	    }
	    return 1;
	}
	else  // a leaf node
	{
		for (i = 0; i < LEAFCARD; i++)
		{
			if (n->branch[i].child &&
			    n->branch[i].child == (struct Node *) tid)
			{
				RTreeDisconnectBranch(n, i);
				return 0;
			}
		}
		return 1;
	}
}



// Delete a data rectangle from an index structure.
// Pass in a pointer to a Rect, the tid of the record, ptr to ptr to root node.
// Returns 1 if record not found, 0 if success.
// RTreeDeleteRect provides for eliminating the root.
//
int RTreeDeleteRect(struct Rect *R, size_t Tid, struct Node**Nn)
{
	register struct Rect *r = R;
	register size_t tid = Tid;
	register struct Node **nn = Nn;
	register int i;
	register struct Node *tmp_nptr;
	struct ListNode *reInsertList = NULL;
	register struct ListNode *e;

	assert(r && nn);
	assert(*nn);
	assert(tid >= 0);

	if (!RTreeDeleteRect2(r, tid, *nn, &reInsertList))
	{
		/* found and deleted a data item */

		/* reinsert any branches from eliminated nodes */
		while (reInsertList)
		{
			tmp_nptr = reInsertList->node;
			for (i = 0; i < MAXKIDS(tmp_nptr); i++)
			{
				if (tmp_nptr->branch[i].child)
				{
					RTreeInsertRect(
						&(tmp_nptr->branch[i].rect),
						(size_t)tmp_nptr->branch[i].child,
						nn,
						tmp_nptr->level);
				}
			}
			e = reInsertList;
			reInsertList = reInsertList->next;
			RTreeFreeNode(e->node);
			RTreeFreeListNode(e);
		}
		
		/* check for redundant root (not leaf, 1 child) and eliminate
		*/
		if ((*nn)->count == 1 && (*nn)->level > 0)
		{
			for (i = 0; i < NODECARD; i++)
			{
				tmp_nptr = (*nn)->branch[i].child;
				if(tmp_nptr)
					break;
			}
			assert(tmp_nptr);
			RTreeFreeNode(*nn);
			*nn = tmp_nptr;
		}
		return 0;
	}
	else
	{
		return 1;
	}
}


extern int RTreeSetNodeMax(int);
extern int RTreeSetLeafMax(int);
extern int RTreeGetNodeMax();
extern int RTreeGetLeafMax();


