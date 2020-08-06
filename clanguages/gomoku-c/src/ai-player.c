//
// Created by qixiaofeng on 2020/7/30.
//

#include <string.h>
#include <stdio.h>
#include <stdbool.h>

#include "board.h"
#include "ai-player.h"
#include "macro-functions.h"

#define M_debug_ppp(point) p_print_point(point, __FUNCTION__, __LINE__);

bool p_enable_print = true;
wchar_t p_g_appearance = m_empty_appeance;
unsigned values[m_table_logic_size][m_table_logic_size];

wchar_t
p_ai_board_get(Board const *board, Point const *const point) {
    return board->grids[point->x][point->y];
}

void
p_print_point(Point const *point, char const *functionName, int lineNumber) {
    if (false == p_enable_print) {
        return;
    }
    printf(
            "Print Point(%d, %d) at %s [%d]. Address: %p.\n",
            point->x, point->y, functionName, lineNumber, point
    );
}

unsigned
p_default_evaluator(Board const *board, Point const *sourcePoint, Point const *targetPoint) {
    if (board->grids[sourcePoint->x][sourcePoint->y] == board->grids[targetPoint->x][targetPoint->y]) {
        return 1;
    }
    return 0;
}

unsigned
p_evaluate_point(Board const *board, Point const *const sourcePoint, cb_evaluator_t cbEvaluator) {
    /*!
     * Empty grid is with initial value 1.
     * Ocuppied grid is with value 0.
     * Accumulate value with counting neighbors.
     *
     * Stop while meet enemy piece or border.
     */
    bool notEmpty = (false == (m_empty_appeance == board->grids[sourcePoint->x][sourcePoint->y]));
    if (notEmpty) {
        return 0;
    }
    return cbEvaluator(board, sourcePoint, sourcePoint);
}

wchar_t
ai_get_appearance() {
    return p_g_appearance;
}

void
ai_set_appearance(wchar_t const targetAppearance) {
    p_g_appearance = targetAppearance;
    M_clear_board(values, 0u)

    Point point = {
            .x = 0,
            .y = 0
    };
    M_debug_ppp(&point)
}

void
ai_play_hand(Board *board, HandDescription const *prevHand, HandDescription *currHand) {
    currHand->x = prevHand->x; //XXX Eliminate unused warning.

    /*TODO Check if there is any piece occupying the hand position. */
    currHand->x = 0;
    currHand->y = 0;
    currHand->appearance = p_g_appearance;
    put_piece_at(board, currHand);
}

#undef M_debug_ppp