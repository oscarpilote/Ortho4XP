
#include "rtree_new.h"
#include <stdio.h>

struct Rect rects[] = {
	{0, 0, 2, 2}, // xmin, ymin, xmax, ymax (for 2 dimensional RTree)
	{5, 5, 7, 7},
	{8, 5, 9, 6},
	{7, 1, 9, 2},
};
int nrects = sizeof(rects) / sizeof(rects[0]);
struct Rect search_rect = {
	{6, 4, 10, 6}, // search will find above rects that this one overlaps
};

int MySearchCallback(size_t id, void* arg) 
{
	// Note: -1 to make up for the +1 when data was inserted
	printf("Hit data rect %d\n", id-1);
	return 1; // keep going
}

void main()
{
	struct Node* root = RTreeNewIndex();
	int i, nhits;
	printf("nrects = %d\n", nrects);
	/*
	 * Insert all the data rects.
	 * Notes about the arguments:
	 * parameter 1 is the rect being inserted,
	 * parameter 2 is its ID. NOTE: *** ID MUST NEVER BE ZERO ***, hence the +1,
	 * parameter 3 is the root of the tree. Note: its address is passed
	 * because it can change as a result of this call, therefore no other parts
	 * of this code should stash its address since it could change undernieth.
	 * parameter 4 is always zero which means to add from the root.
	 */
	for(i=0; i<nrects; i++)
		RTreeInsertRect(&rects[i], i+1, &root, 0); // i+1 is rect ID. Note: root can change
	nhits = RTreeSearch(root, &search_rect, MySearchCallback, 0);
	printf("Search resulted in %d hits\n", nhits);
}
