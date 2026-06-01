/* TC3 v1: Contains dead code and unreachable branches */
#include <stdlib.h>

int classify_value(int x) {
    if (x > 100) {
        return 3;
    } else if (x > 50) {
        return 2;
    } else if (x > 0) {
        return 1;
    } else if (x == 0) {
        return 0;
    } else {
        return -1;
    }
    /* Dead code — unreachable after return chain */
    return 999;
}

int safe_divide(int a, int b) {
    if (b == 0) {
        return 0;
    }
    int result = a / b;
    if (b == 0) {      /* Always false — dead branch */
        result = -1;
    }
    return result;
}

/* Version with enum-based dispatch — more branches */
typedef enum { OP_ADD = 0, OP_SUB, OP_MUL, OP_DIV, OP_UNKNOWN } Op;

int dispatch(Op op, int a, int b) {
    if (op == OP_ADD) return a + b;
    if (op == OP_SUB) return a - b;
    if (op == OP_MUL) return a * b;
    if (op == OP_DIV) return (b != 0) ? a / b : 0;
    if (op == OP_UNKNOWN) return 0;  /* explicit default */
    return 0;                         /* unreachable */
}
