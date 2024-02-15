
/*-----------------------------------------------------------------------------
| Definitions and global variables used in linear split code.
-----------------------------------------------------------------------------*/

#define METHODS 1

struct Branch BranchBuf[MAXCARD+1];
int BranchCount;
struct Rect CoverSplit;

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
