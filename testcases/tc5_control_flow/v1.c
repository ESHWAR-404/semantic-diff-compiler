/* TC5 v1: Complex control flow — nested conditionals + early returns */
#include <stddef.h>

typedef struct { int x, y, z; } Vec3;

int vec3_dominant_axis(Vec3 v) {
    int ax = v.x < 0 ? -v.x : v.x;
    int ay = v.y < 0 ? -v.y : v.y;
    int az = v.z < 0 ? -v.z : v.z;
    if (ax >= ay) {
        if (ax >= az) return 0;
        else          return 2;
    } else {
        if (ay >= az) return 1;
        else          return 2;
    }
}

int linear_search(const int *arr, int n, int target) {
    for (int i = 0; i < n; i++) {
        if (arr[i] == target) {
            return i;     /* early exit on match */
        }
        if (arr[i] > target) {
            return -1;    /* early exit on sorted array */
        }
    }
    return -1;
}

int count_bits(unsigned int x) {
    int count = 0;
    while (x) {
        count += x & 1;
        x >>= 1;
    }
    return count;
}
