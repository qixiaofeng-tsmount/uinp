#ifndef BOARD_H
#define BOARD_H

void clear_board();
bool is_empty_slot();
bool is_game_end(int x, int y, int pieceFlag);
void put_piece_at(int x, int y, int pieceFlag);

#endif // guard end for BOARD_H
