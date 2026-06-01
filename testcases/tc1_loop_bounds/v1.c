/* TC1 v1: Fixed loop bounds — compiler can auto-vectorize and unroll */
#include <stdint.h>

void sum_array(const int *arr, int *result) {
    int s = 0;
    /* Fixed bound of 16: compiler can prove trip-count and vectorize */
    for (int i = 0; i < 16; i++) {
        s += arr[i];
    }
    *result = s;
}

void scale_array(float *arr, float factor) {
    /* Fixed stride-1 loop over 32 floats — ideal for SIMD */
    for (int i = 0; i < 32; i++) {
        arr[i] *= factor;
    }
}
