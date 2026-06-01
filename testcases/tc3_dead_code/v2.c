/* TC3 v2: Dead code removed; control flow simplified */
#include <stdlib.h>

int classify_value(int x) {
    /* Simplified: no dead return, same semantics */
    if (x > 100) return 3;
    if (x > 50)  return 2;
    if (x > 0)   return 1;
    if (x == 0)  return 0;
    return -1;
}

int safe_divide(int a, int b) {
    if (b == 0) return 0;
    return a / b;   /* dead branch removed */
}

typedef enum { OP_ADD = 0, OP_SUB, OP_MUL, OP_DIV, OP_UNKNOWN } Op;

int dispatch(Op op, int a, int b) {
    /* Switch replaces chain of ifs — may produce lookup table in IR */
    switch (op) {
        case OP_ADD: return a + b;
        case OP_SUB: return a - b;
        case OP_MUL: return a * b;
        case OP_DIV: return (b != 0) ? a / b : 0;
        default:     return 0;
    }
}
