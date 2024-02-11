
#include "index.h"
#include "card.h"

int NODECARD = MAXCARD;
int LEAFCARD = MAXCARD;

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
