# pragma once

struct HashTable {  	
	uint8_t   bits;
	uint8_t   nkeys;
	uint32_t  capacity; // = (2^bits)
	uint32_t  size;
	uint32_t  *data;
};


int initialize_hashtable(struct HashTable *ht, uint8_t bits, uint8_t nkeys)
{
	ht->bits = bits;
	ht->capacity = 1 << bits;
	ht->nkeys = nkeys;
	ht->data = (uint32_t *) calloc(ht->capacity * (nkeys + 1), sizeof(uint32_t)); 
	if (ht->data == NULL) return -1;
	ht->size = 0;
	for (int i = 0; i < ht->capacity; ++i) {
		ht->data[(nkeys + 1) * i] = -1;
	}
	return 0;
}
	
void dispose_hashtable(struct HashTable *ht)
{
	if (ht->data != NULL) {
		free(ht->data);
		ht->data = NULL;
	}
	ht->size=0;
}

#define CMAX 6
uint32_t find_or_insert_in_hashtable(uint32_t hash, uint32_t *keys, uint32_t alt_value, struct HashTable *ht) 
{
	//static int trouve = 0;
	//static int nouveau = 0;
	uint32_t pos = hash;
	//int count = 0;
	while (1) {
		//++count;
		pos = pos & ((1 << ht->bits) - 1);
		uint32_t *p = ht->data + pos * (ht->nkeys + 1);
		if (p[0] == -1) {
			p[0] = alt_value;
			for (int i = 0; i < ht->nkeys; ++i) {
				p[i+1] = keys[i];
			}
			ht->size++;
			//nouveau++;
			//printf("%lf\n",(double) nouveau / (nouveau + trouve));
			//if (count > CMAX) printf("%d\n",count);
			return alt_value;
		} else {
			int same = 1;
			for (int i = 0; i < ht->nkeys; ++i) {
				same &= (p[i+1] == keys[i]);
			}
			if (same) {
				//trouve++;
				//printf("%lf\n",(double) nouveau / (nouveau + trouve));
				//if (count > CMAX) printf("%d\n",count);
				return p[0];
			} else {
				pos++;
			}
		}
	}
}
#undef CMAX






