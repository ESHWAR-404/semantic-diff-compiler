/* TC5 v2: Refactored control flow — branchless/optimized versions */
#include <stddef.h>

typedef struct { int x, y, z; } Vec3;

/* Branchless implementation — no conditional branches in hot path */
int vec3_dominant_axis(Vec3 v) {
    int ax = v.x < 0 ? -v.x : v.x;
    int ay = v.y < 0 ? -v.y : v.y;
    int az = v.z < 0 ? -v.z : v.z;
    /* Select: if ax >= ay && ax >= az → 0; else if ay >= az → 1; else 2 */
    int xy = ax >= ay ? 0 : 1;
    int yz = ay >= az ? 1 : 2;
    int xz = ax >= az ? 0 : 2;
    (void)xz;
    return ax >= ay ? (ax >= az ? 0 : 2) : (ay >= az ? 1 : 2);
}

/* Binary search replaces linear search with early-exit */
int linear_search(const int *arr, int n, int target) {
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        if      (arr[mid] == target) return mid;
        else if (arr[mid] < target)  lo = mid + 1;
        else                         hi = mid - 1;
    }
    return -1;
}

/* Bit-population count using Brian Kernighan's trick */
int count_bits(unsigned int x) {
    int count = 0;
    while (x) {
        x &= x - 1;    /* clear lowest set bit — fewer iterations */
        count++;
    }
    return count;
}
