/* TC4 v1: Scalar ops — aliasing prevents auto-vectorization */
#include <stddef.h>

void multiply_arrays(float *out, float *a, float *b, int n) {
    /* Pointers may alias — compiler emits scalar loop */
    for (int i = 0; i < n; i++) {
        out[i] = a[i] * b[i];
    }
}

void saxpy(float *y, float alpha, const float *x, int n) {
    /* Without restrict: aliasing between y and x inhibits vectorization */
    for (int i = 0; i < n; i++) {
        y[i] = alpha * x[i] + y[i];
    }
}
