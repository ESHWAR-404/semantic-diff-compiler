/* TC1 v2: Variable loop bounds — compiler cannot prove trip-count */
#include <stdint.h>

void sum_array(const int *arr, int *result, int n) {
    int s = 0;
    /* Variable bound: trip count unknown, vectorization requires runtime check */
    for (int i = 0; i < n; i++) {
        s += arr[i];
    }
    *result = s;
}

void scale_array(float *arr, float factor, int n) {
    /* Variable n: prevents full unrolling, may inhibit auto-vectorization */
    for (int i = 0; i < n; i++) {
        arr[i] *= factor;
    }
}
