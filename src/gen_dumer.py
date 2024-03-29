#!/usr/bin/env python

## \file gen_dumer.py
#Generate code of the sub_isd module using Dumer algorithm
#
#Parameters p is set as first parameter of the command line. It must be even.

import os
import sys

def repeat(format, start, end, sep):
	return sep.join([format % (i) for i in range(start, end + 1)])

try:
	ncols=int(sys.argv[1])
except:
	sys.stderr.write('usage : ' +sys.argv[0]+' ncols\n')
	sys.exit(1)

if(ncols%2 != 0):
	sys.stderr.write('p must be even')
	sys.exit(2)

o = ""

o += """/* FILE GENERATED BY %s */\n\n""" % os.path.basename(sys.argv[0])

o += """#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <m4ri/m4ri.h>
#include "sub_isd.h"
#include "libisd.h"
#include "ciht.h"
#include "support.h"
#include "final_test.h"
#include "sparse_words_list.h"
#include "measure.h"
#include "syscall_macros.h"
"""

o += "#define P %d" % (ncols)

o += """
static word* L;
static unsigned int N;
static word* syndsprime;
static unsigned int n, k, r, l, w, L_len, threshold;
static unsigned int lprime;
static int shift;

unsigned int L0_support_len;
word* L0_support;
unsigned int L1_support_len;
word* L1_support;

static unsigned int L0_size;
static ciht_t L0;

static sw_list** h;

"""

o += """
void print_parameters(isd_params* params) {
	printf("n : %d\\n", params->n);
	printf("r : %d\\n", params->r);
	printf("w : %d\\n", params->w);
	printf("l : %d\\n", params->l);
	printf("p : %d\\n", params->p);
	printf("eff_word_len : %ld\\n", min(params->r, word_len));
	printf("threshold : %d\\n", params->weight_threshold);
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
	printf("lprime : %d\\n", lprime);

	shift = min(r, word_len) - lprime;

	prepare_half0(&L0_support, &L0_support_len, L_len);
	prepare_half1(&L1_support, &L1_support_len, L_len);

	L0_size = 1ULL << lprime;
	L0 = ciht_init(L0_size, P/2, 0);
}


"""





o += """
void sub_isd() {
	word synd = syndsprime[0]; //DOOM not implemented
"""

o += "	ci_t " + repeat("L0_c%d", 0, ncols//2-1, ", ") +";\n"
o += "	ci_t " + repeat("L1_c%d", 0, ncols//2-1, ", ") +";\n"
o += """
	word index;
	word value;

	unsigned int weight;
	int final_weight;

	#ifdef SORT_L
		qsort(L, L_len/2, sizeof(word), word_cmp);
		qsort(L+L_len/2, L_len - L_len/2, sizeof(word), word_cmp);
	#endif

	build_half0(L0_support, L, L_len);
	build_half1(L1_support, L, L_len);

	ciht_reset(L0, L0_size, P/2);
"""

o += "	for (L0_c0 = %d; L0_c0 < L0_support_len; ++L0_c0) {\n" % (ncols//2-1)

for i in range(1,ncols//2):
	o += "	for (L0_c%d = %d; L0_c%d < L0_c%d; ++L0_c%d) {\n" % (i, ncols//2-i-1, i, i-1, i)

o += """		value = 0\n"""
for i in range(ncols//2):
	o += "			^ L0_support[L0_c%d]\n" % (i)
o += "		;"

o +="""
		index = value >> shift;
"""
o += "		ci_t t[P/2] = {%s};" % (repeat("L0_c%d", 0, ncols//2-1, ", "))
o += """
		ciht_store(L0, index, t, P/2);
	"""
for i in range(1, ncols//2):
	o += "	}\n"
o += "	}\n"

o += "	for (L1_c0 = %d; L1_c0 < L1_support_len; ++L1_c0) {\n" % (ncols//2-1)

for i in range(1,ncols//2):
	o += "	for (L1_c%d = %d; L1_c%d < L1_c%d; ++L1_c%d) {\n" % (i, ncols//2-i-1, i, i-1, i)

o += """		value = synd\n"""
for i in range(ncols//2):
	o += "			^ L1_support[L1_c%d]\n" % (i)
o += "		;"

o += """
		index = value >> shift;
		ci_t* t0 = ciht_get(L0, index, P/2);
		if (t0) {
"""
for i in range(ncols//2):
	o += "			L0_c%d = t0[%d];\n" % (i, i)

o += """			value = value\n"""
for i in range(ncols//2):
	o += "				^ L0_support[L0_c%d]\n" % (i)
o += "			;"

o += """
			incr_collision_counter();
			weight = isd_weight(value);
			if (weight < threshold) {
				bday_cycle_stopwatch_stop();
				incr_final_test_counter();
				final_test_cycle_stopwatch_start();
"""
o += """				ci_t candidate[P] = {
"""
for i in range(ncols//2):
	o += "						inv_half0(L0_c%d, L_len),\n" % (i)
for i in range(ncols//2):
	o += "						inv_half1(L1_c%d, L_len),\n" % (i)
o += "				};\n"

o += "				final_weight = final_test_array(0, weight, P, candidate);"
o += """
				if (final_weight != -1) {
"""
o += "					sw_list_append(h, sw_filled_new_array(0, final_weight, P, candidate));"
o += """
				}
				final_test_cycle_stopwatch_stop();
				bday_cycle_stopwatch_start();
			}	
		}
	"""
for i in range(ncols//2):
	  o += "}"
o += "	}\n"

o += """
void sub_isd_free() {
	free(L0_support);
	free(L1_support);
	ciht_free(L0);
}
"""

print(o)
