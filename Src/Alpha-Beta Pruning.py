import numpy as np
from Src.Heuristic import evaluate

EMPTY_CELL = 0
RED_PLAYER = 1
YELLOW_PLAYER = 2

def expand_board(player_turn : int, current_board : np.ndarray) -> list:
    length, width = current_board.shape

    expanded_boards = []

    for c in range(width):
        board_copy = current_board.copy()

        has_place = (current_board[0][c] == EMPTY_CELL)

        if has_place:
            for r in range(length - 1, -1, -1):
                if current_board[r][c] == EMPTY_CELL:
                    board_copy[r][c] = player_turn
                    expanded_boards.append(board_copy)
                    break

    return expanded_boards

def terminal_board(current_board : np.ndarray) -> int:
    return current_board.__contains__(EMPTY_CELL)


def get_move(player_turn : int, current_board : np.ndarray, k : int) -> tuple:
    return maximize(-float("inf"), float("inf"), 0, player_turn, current_board, k)

def maximize(alpha : float, beta : float, depth : int, player_turn : int, current_board : np.ndarray, k : int) -> tuple[np.ndarray, float]:
    if depth == k or terminal_board(current_board):
        return current_board, evaluate(current_board)

    max_value = -float("inf")
    max_move = None

    children_list = expand_board(player_turn, current_board)
    next_turn = RED_PLAYER if player_turn == YELLOW_PLAYER else YELLOW_PLAYER

    for move in children_list:
        (min_move, min_value) = minimize(alpha, beta, depth + 1, next_turn, move, k)

        if min_value > max_value:
            max_value = min_value
            alpha = max_value

            max_move = min_move

        if max_value >= beta: return max_move, max_value

    return max_move, max_value

def minimize(alpha : float, beta : float, depth : int, player_turn : int, current_board : np.ndarray, k: int) -> tuple[np.ndarray, float]:
    if depth == k or terminal_board(current_board):
        return current_board, evaluate(current_board)

    min_value = float("inf")
    min_move = None

    children_list = expand_board(player_turn, current_board)
    next_turn = RED_PLAYER if player_turn == YELLOW_PLAYER else YELLOW_PLAYER

    for move in children_list:
        (max_move, max_value) = maximize(alpha, beta, depth + 1, next_turn, move, k)

        if max_value < min_value:
            min_value = max_value
            beta = min_value

            min_move = max_move

        if min_value <= alpha: return min_move, min_value

    return min_move, min_value
