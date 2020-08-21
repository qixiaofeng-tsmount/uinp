//
// Created by qixiaofeng on 2020/8/20.
//

#include <stdio.h>
#include <stdbool.h>
#include "physics.h"

#define m_g 9.8
#define m_pixels_per_meter 50

void p_get_circle_aabb(Circle const *circle, AABB *aabb) {
    aabb->leftTop.x = circle->origin.x - circle->radius;
    aabb->leftTop.y = circle->origin.y - circle->radius;
    aabb->rightBottom.x = circle->origin.x + circle->radius;
    aabb->rightBottom.y = circle->origin.y + circle->radius;
}

bool p_is_overlap(AABB *a, AABB *b) {
    if (a->leftTop.x > b->rightBottom.x) {
        return false;
    }
    if (b->leftTop.x > a->rightBottom.x) {
        return false;
    }
    if (a->leftTop.y < b->rightBottom.y) {
        return false;
    }
    if (b->leftTop.y < a->rightBottom.y) {
        return false;
    }
    return true;
}

void update_motion(RigidCircle *rigidCircle, double deltaSeconds) {
    #define M_update(t) \
    double const\
        t##VelocityIncrement = deltaSeconds * rigidCircle->motion.acceleration.t,\
        t##VelocityIncrementHalf = t##VelocityIncrement * 0.5,\
        t##VelocityMiddle = rigidCircle->motion.velocity.t + t##VelocityIncrementHalf,\
        t##Movement = deltaSeconds * t##VelocityMiddle;\
    printf(#t": %+5.4f, d"#t": %+5.4f, ds: %+5.4f, mv: %+5.4f; ",\
        rigidCircle->motion.velocity.t, rigidCircle->motion.acceleration.t,\
        deltaSeconds, t##Movement);\
    rigidCircle->motion.velocity.t += t##VelocityIncrement;\
    rigidCircle->circle.origin.t += t##Movement;

    M_update(y)
    M_update(x)
    printf("\n");

    #undef M_update
}

void add_gravity_to(RigidCircle *rigidCircle) {
    static double const G_actual_g = m_g * m_pixels_per_meter;
    rigidCircle->motion.acceleration.y += G_actual_g;
}

void collide_circle_with_aabb(RigidCircle *rigidCircle, RigidAABB *rigidAABB) {
    static AABB circleAABB;
    p_get_circle_aabb(&rigidCircle->circle, &circleAABB);
    if (false == p_is_overlap(&circleAABB, &rigidAABB->aabb)) {
        return;
    }
    printf("=======");
    rigidCircle->motion.velocity.y = rigidCircle->motion.velocity.y;
    rigidCircle->circle.origin.y = rigidCircle->circle.origin.y - (
            0.1 + circleAABB.rightBottom.y - rigidAABB->aabb.leftTop.y
    );
}

#undef m_g
#undef m_pixels_per_meter
