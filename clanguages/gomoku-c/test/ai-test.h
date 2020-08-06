//
// Created by qixiaofeng on 2020/8/3.
//

#ifndef GOMOKU_C_AI_TEST_H
#define GOMOKU_C_AI_TEST_H

#include "ai-player.h"

wchar_t p_ai_board_get(Board const *board, Point const *point);

unsigned p_evaluate_point(Board const *board, Point const *sourcePoint, cb_evaluator_t cbEvaluator);

unsigned p_default_evaluator(Board const *board, Point const *sourcePoint, Point const *targetPoint);

void test_ai();

#endif //GOMOKU_C_AI_TEST_H