/* TC2 v1: No inlining hint — helper stays as a call site */
#include <stddef.h>

static int clamp(int val, int lo, int hi) {
    if (val < lo) return lo;
    if (val > hi) return hi;
    return val;
}

void clamp_array(int *arr, int n, int lo, int hi) {
    for (int i = 0; i < n; i++) {
        arr[i] = clamp(arr[i], lo, hi);
    }
}

static int dot_product_elem(const int *a, const int *b, int i) {
    return a[i] * b[i];
}

int dot_product(const int *a, const int *b, int n) {
    int result = 0;
    for (int i = 0; i < n; i++) {
        result += dot_product_elem(a, b, i);
    }
    return result;
}
