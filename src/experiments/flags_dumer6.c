/* FILE GENERATED BY gen_dumer.py */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "sub_isd.h"
#ifdef MANAGE_COL
	#if	MANAGE_COL == 2
		#include "counterht_col2.h"
	#else
		#include "counterht_col.h"
	#endif
#else
	#include "counterht.h"
#endif
#include "m4ri/m4ri.h"
#include "libisd.h"
#include "final_test.h"
#include "sparse_words_list.h"
#include "measure.h"
#include "syscall_macros.h"
#define P 6
static word* L;
static unsigned int N;
static word* syndsprime;
static unsigned int n, k, r, l, w, L_len, threshold;
static unsigned int lprime;
static int shift;

static unsigned int L0_size;
static counterht L0;
static word* xors_table;

static sw_list** h;

static short** unpack;

static unsigned int L0_flags_size;
static uint64_t* L0_flags;

void unpack_counter(unsigned int* c1, unsigned int* c2, unsigned int* c3, counter c) {
	*c1 = unpack[c][0];
	*c2 = unpack[c][1];
	*c3 = unpack[c][2];
}

void print_parameters(isd_params* params) {
	printf("n : %d\n", params->n);
	printf("r : %d\n", params->r);
	printf("w : %d\n", params->w);
	printf("l : %d\n", params->l);
	printf("p : %d\n", params->p);
	printf("eff_word_len : %ld\n", min(params->r, word_len));
	printf("threshold : %d\n", params->weight_threshold);
}

void sub_isd_init(isd_params* params, word* local_L, word* local_synds, unsigned int local_N, sw_list** local_h, ranctx* state) {
	params->p = P;
	(void) state;
	print_parameters(params);
	L = local_L;
	N = local_N;
	syndsprime = local_synds;
	h = local_h;

	n = params->n;
	r = params->r;
	k = params->k;
	l = params->l;
	w = params->w;

	L_len = k+l;

	threshold = params->weight_threshold;

	unsigned long long nb_of_sums = nCr(L_len/2, P/2);

	// lprime can be used to tune hash table size. It should be less than or equal to l. Best case is when the table fits in the cache. 
	// Lowering lprime will rise hash table occupation ratio but also intern collision probability. That means it will reduce number of generated collisions if table collisions are discarded.
	lprime = (l+ log(nb_of_sums)/log(2))/2;
	lprime = l;
	printf("lprime : %d\n", lprime);

	shift = min(r, word_len) - lprime;

	L0_size = 1ULL << lprime;
	L0 = counterht_init(L0_size, nb_of_sums);

	L0_flags_size = L0_size/(8*sizeof(uint64_t));
	L0_flags = (uint64_t*) malloc(L0_flags_size*sizeof(uint64_t));

	xors_table = (word*) MALLOC(nb_of_sums * sizeof(word));

	unsigned int i;
	unsigned int c1, c2, c3;

	counter c = 0;
	unpack = (short**) MALLOC(nb_of_sums * sizeof(short*));
	for (i = 0; i < nb_of_sums; ++i) {
		unpack[i] = (short*) MALLOC(P/2 * sizeof(short));
	}
	for (c1 = 2; c1 < L_len/2; ++c1) {
	for (c2 = 1; c2 < c1; ++c2) {
	for (c3 = 0; c3 < c2; ++c3) {
		unpack[c][0] = c1;
		unpack[c][1] = c2;
		unpack[c][2] = c3;
		++c;
	}}}
}


void sub_isd() {
	word synd = syndsprime[0]; //DOOM not implemented
	unsigned int c1, c2, c3, c4, c5, c6;

	counter c;
	counter_container* ccont;
	word index;
	word value;
/* Intermediate sums */
	word sum1;
	word sum12;
	word sum123;
	word sumS4;
	word sumS45;
	word sumS456;

	unsigned int weight;
	int final_weight;
	const word max_word_zero_l_bits = 1UL << (word_len - l); /* A word with its l MSB zeroed is lower than this value */

	//counterht_reset(L0, L0_size);
	unsigned int i;
	for (i = 0; i < L0_flags_size; ++i) {
		L0_flags[i] = 0;
	}
	
	c = 0;
	for (c1 = 2; c1 < L_len/2; ++c1) {
		sum1 = L[c1];
	for (c2 = 1; c2 < c1; ++c2) {
		sum12 = sum1 ^ L[c2];
	for (c3 = 0; c3 < c2; ++c3) {
		sum123 = sum12 ^ L[c3];
		value = sum123;
		index = value >> shift;
		counterht_store(L0, index, c);
		L0_flags[index / (8*sizeof(uint64_t))] |= 1UL << (index % (8*sizeof(uint64_t)));
		xors_table[c] = value;
		++c;
	}}}

	for (c4 = L_len/2 + 2; c4 < L_len; ++c4) {
		sumS4 = synd ^ L[c4];
	for (c5 = L_len/2 + 1; c5 < c4; ++c5) {
		sumS45 = sumS4 ^ L[c5];
		for (c6 = L_len/2 + 0; c6 < c5; ++c6) {
			sumS456 = sumS45 ^ L[c6];
			value = sumS456;
			index = value >> shift;
			if (L0_flags[index/(8*sizeof(uint64_t))] >> (index % (8*sizeof(uint64_t))) & 1UL) {
				for(ccont = counterht_get(L0, index); ccont != NULL; ccont = counterht_next(L0, index, ccont)) {
					c = counter_container_open(ccont);
					value ^= xors_table[c];
					if (value < max_word_zero_l_bits) {
						incr_collision_counter();
						weight = isd_weight(value);
						if (weight < threshold) {
							bday_cycle_stopwatch_stop();
							incr_final_test_counter();
							final_test_cycle_stopwatch_start();
							unpack_counter(&c1, &c2, &c3, c);
							final_weight = final_test(0, weight, P, c1, c2, c3, c4, c5, c6);
							if (final_weight != -1) {
								sw_list_append(h, sw_filled_new(0, final_weight, P, c1, c2, c3, c4, c5, c6));
							}
							final_test_cycle_stopwatch_stop();
							bday_cycle_stopwatch_start();
						}	
					}
				}
			}
		}}}}

void sub_isd_free() {
	unsigned long long nb_of_sums = nCr(L_len/2, P/2);
	unsigned long long i;
	for (i = 0; i < nb_of_sums; ++i) {
		free(unpack[i]);
	}
	free(unpack);
	counterht_free(L0);
	free(xors_table);
}

