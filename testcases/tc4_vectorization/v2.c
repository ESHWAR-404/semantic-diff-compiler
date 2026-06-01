/* TC4 v2: __restrict__ qualifier enables full auto-vectorization */
#include <stddef.h>

void multiply_arrays(float * __restrict__ out,
                     float * __restrict__ a,
                     float * __restrict__ b, int n) {
    /* restrict: no aliasing — compiler emits vectorized loop */
    for (int i = 0; i < n; i++) {
        out[i] = a[i] * b[i];
    }
}

void saxpy(float * __restrict__ y, float alpha,
           const float * __restrict__ x, int n) {
    /* restrict: auto-vectorizer uses <8 x float> SIMD operations */
    for (int i = 0; i < n; i++) {
        y[i] = alpha * x[i] + y[i];
    }
}
