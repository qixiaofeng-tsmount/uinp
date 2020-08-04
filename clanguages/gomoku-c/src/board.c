#include <string.h>
#include <stdbool.h>

#include "macro-constants.h"

typedef bool (*cb_checker_t)(int);

int const win_count = 4;

int board[m_table_logic_size][m_table_logic_size];

void
clear_board() {
    memset(board, m_empty_slot, sizeof(int) * m_table_logic_size * m_table_logic_size);
}

bool
is_empty_slot(int x, int y) {
    return m_empty_slot == board[x][y];
}

bool
is_same_flag(int pieceFlag, int x, int y) {
    return pieceFlag == board[x][y];
}

bool
p_check_up_border(int coordinate) {
    return coordinate > -1;
}

bool
p_check_bottom_border(int coordinate) {
    return coordinate < m_table_logic_size;
}

cb_checker_t
get_checker(bool isIncreasing) {
    return isIncreasing ? p_check_bottom_border : p_check_up_border;
}

int
p_count_continuous_same_flag(int pieceFlag, int x, int y, int incrementX, int incrementY) {
    #define M_count_piece(target) \
    if (pieceFlag == target) { \
        ++count; \
    } else { \
        return count; \
    }

    int count = 0;
    if (0 == incrementX) {
        cb_checker_t checker = get_checker(incrementY > 0);
        for (int i = y + incrementY; checker(i); i += incrementY) {
            M_count_piece(board[x][i])
        }
        return count;
    } else if (0 == incrementY) {
        cb_checker_t checker = get_checker(incrementX > 0);
        for (int i = x + incrementX; checker(i); i += incrementX) {
            M_count_piece(board[i][y])
        }
        return count;
    }
    cb_checker_t xChecker = get_checker(incrementX > 0);
    cb_checker_t yChecker = get_checker(incrementY > 0);
    for (int i = x + incrementX, j = y + incrementY; xChecker(i) && yChecker(j); i += incrementX, j += incrementY) {
        M_count_piece(board[i][j])
    }
    return count;

    #undef M_count_piece
}

bool
is_game_end(int x, int y, int pieceFlag) {
    #define M_check_game_end(iX1, iY1, iX2, iY2) if (win_count <= ( \
        p_count_continuous_same_flag(pieceFlag, x, y, iX1, iY1) \
        + p_count_continuous_same_flag(pieceFlag, x, y, iX2, iY2)) \
    ) {\
        return true; \
    }

    // Check horizontal.
    M_check_game_end(1, 0, -1, 0)
    // Check vertical.
    M_check_game_end(0, 1, 0, -1)
    // Check top-left to bottom-right.
    M_check_game_end(1, 1, -1, -1)
    // Check top-right to bottom-left.
    M_check_game_end(-1, 1, 1, -1)

    return false;

    #undef M_check_game_end
}

void
put_piece_at(int x, int y, int pieceFlag) {
    board[x][y] = pieceFlag;
}
