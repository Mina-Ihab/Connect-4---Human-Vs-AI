# here we define the game loops and how turned

import time
import numpy as np
from system.connectCatch import result, calculate_score
from system.constants import PIECE, FULL_BOARD_CELL, get_opponent_piece
from GUI.GameGUI import get_gui_setup, get_gui_input, gui_show_board, gui_game_over, gui_set_tree, gui_set_stats, gui_set_scores, gui_set_thinking, gui_set_time
from system.Alpha_Beta_Pruning import get_move as ai_choose

def is_full(empty_cols: np.ndarray):
    return np.all(empty_cols == FULL_BOARD_CELL)

def put_piece(board: np.ndarray, empty_cols: np.ndarray, column: int, player_piece: PIECE):
    if column < 0 or column >= len(empty_cols):
        return False
    row = empty_cols[column]
    if row != FULL_BOARD_CELL:
        board[row][column] = player_piece
        empty_cols[column] -= 1
        return True
    return False

def check_winner(board: np.ndarray, player_piece: PIECE):
    return result(board, player_piece, get_opponent_piece(player_piece))

def ai_choose_column(current_player, board, limit, heuristic): # find the row and col that changed from whole board
    board_copy, value, expanded_nodes, root = ai_choose(current_player, board, limit, heuristic)
    col = np.where(board != board_copy)[1][0]  # get only col index where changes
    return col, value, expanded_nodes, root

def get_move(current_player, player_color, board, limit, heuristic):
    if current_player == player_color:
        return get_gui_input()
    return ai_choose_column(current_player, board, limit, heuristic)  # limit can be adjusted for AI difficulty

def main_game_loop():
    length, width, limit, player_color, heuristic = get_gui_setup()
    board = np.full((length, width), PIECE.EMPTY_CELL, dtype=int)
    empty_cols = np.full(width, length-1, dtype=int)

    current_player = PIECE.RED_PLAYER

    while not is_full(empty_cols):

        if current_player != player_color:
            gui_set_thinking()  # disables the tree button
            start_time = time.perf_counter()

        move = get_move(current_player, player_color, board, limit, heuristic)

        if current_player == player_color:
            column = move
        else:
            column, value, expanded_nodes, root = move
            gui_set_time(time.perf_counter() - start_time)
            gui_set_tree(root)  # enables the tree button again
            gui_set_stats(value, expanded_nodes)

        while not put_piece(board, empty_cols, column, current_player):
            continue  # Wait for valid input
        current_player = get_opponent_piece(current_player)
        gui_show_board(board)
        gui_set_scores(calculate_score(board, player_color), calculate_score(board, get_opponent_piece(player_color)))
    gui_game_over(check_winner(board, player_color), board)
    return check_winner(board, player_color)