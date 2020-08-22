#include "testool.h"
#include "test-physics.h"

/*TODO
 * # Two ball bounce.
 *   - Both moving.
 *   - One moving.
 * # Matrix math.
 * # Engine: File based objects loader.
 * # Engine: Objects manager.
 * # Engine: Physics manager.
 * # Double-buffer.
 */

#define M_print_aabb(aabb) p_print_aabb(aabb, #aabb, __FUNCTION__)

void p_print_aabb(AABB const *aabb, char const *name, char const *function) {
    printf("%s: AABB [%s], left: %6.2f, right: %6.2f; "
           "top: %6.2f, bottom: %6.2f\n",
           function, name,
           aabb->left, aabb->right,
           aabb->top, aabb->bottom);
}

void p_test_is_overlap() {
    AABB aabbOne = {0, 0, 10, 10,};
    AABB aabbTwo = {10.01, 10.01, 20, 20};
    M_print_aabb(&aabbOne);
    M_test_int(p_is_aabb_overlap(&aabbOne, &aabbTwo), false);
    aabbTwo.left = 10;
    M_test_int(p_is_aabb_overlap(&aabbOne, &aabbTwo), false);
    aabbTwo.top = 10;
    M_test_int(p_is_aabb_overlap(&aabbOne, &aabbTwo), true);
    aabbTwo.top = 9.99;
    M_test_int(p_is_aabb_overlap(&aabbOne, &aabbTwo), true);
    aabbTwo.left = -0.01;
    aabbTwo.right = 10.01;
    M_test_int(p_is_aabb_overlap(&aabbOne, &aabbTwo), true);
}

int main() {
    M_run_test_suite(p_test_is_overlap);
    return 0;
}
