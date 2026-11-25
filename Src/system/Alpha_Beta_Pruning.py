import numpy as np

from system.connectCatch import result
from system.Heuristic import evaluate_board
from system.constants import PIECE
from GUI.TreeNode import TreeNode

# Expanding the board by trying to put the player pieces in each available position and then add the new board to a list
def expand_board(player_turn : int, current_board : np.ndarray) -> list:
    length, width = current_board.shape

    expanded_boards = []

    for c in range(width):
        board_copy = current_board.copy()

        has_place = (current_board[0][c] == PIECE.EMPTY_CELL)

        if has_place:
            for r in range(length - 1, -1, -1):
                if current_board[r][c] == PIECE.EMPTY_CELL:
                    board_copy[r][c] = player_turn
                    expanded_boards.append((board_copy, c))
                    break

    return expanded_boards

# Check whether the current board contain empty position (not full board)
def terminal_board(current_board : np.ndarray) -> bool:
    return not (current_board[0] == PIECE.EMPTY_CELL).any()

# Return the best move from the point of view of minimax alpha beta tree
def get_move(current_turn : int, current_board : np.ndarray, k : int, heuristic) -> tuple:
    expanded_nodes = [0]

    player_color = PIECE.RED_PLAYER if current_turn == PIECE.YELLOW_PLAYER else PIECE.YELLOW_PLAYER

    root = TreeNode(current_board, 0, current_turn)
    board, value = maximize(-float("inf"), float("inf"), 0, current_turn, player_color, current_board, k, root, expanded_nodes, heuristic)
    return board, value, expanded_nodes[0], root

# Try the get the best move to maximize the minimax value of the current board
def maximize(alpha : float, beta : float, depth : int, current_color : int, player_color : int, current_board : np.ndarray, k : int, node : TreeNode, expanded_nodes : list, heuristic) -> tuple[np.ndarray, float]:
    if terminal_board(current_board):
        ai_color = PIECE.RED_PLAYER if player_color == PIECE.YELLOW_PLAYER else PIECE.YELLOW_PLAYER

        node.value = result(current_board, ai_color, player_color)
        return current_board, node.value

    if depth == k:
        node.value = evaluate_board(current_board, player_color, heuristic)
        return current_board, node.value

    max_value = -float("inf")
    max_move = None

    children_list = expand_board(current_color, current_board)
    expanded_nodes[0] += len(children_list)

    next_turn = PIECE.RED_PLAYER if current_color == PIECE.YELLOW_PLAYER else PIECE.YELLOW_PLAYER

    for i, (child_board, column) in enumerate(children_list):
        child_node = TreeNode(
            child_board,
            depth + 1,
            next_turn,
            move=column
        )
        node.children.append(child_node)

        (min_move, min_value) = minimize(alpha, beta, depth + 1, next_turn, player_color, child_board, k, child_node, expanded_nodes, heuristic)
        child_node.value = min_value

        if min_value > max_value:
            max_value = min_value
            alpha = max(alpha, max_value)

            max_move = child_board

        # If max value is greater than or equal to the beta then prune,
        # because the upper level is min turn so it try to get the smallest minimax value
        if max_value >= beta:
            node.pruned = True
            node.pruned_count = len(children_list) - (i + 1)
            node.value = max_value
            node.pruned_moves = [(b, col, depth + 1) for b, col in children_list[i + 1:]]

            return max_move, max_value

    node.value = max_value
    return max_move, max_value

# Try the get the best move to minimize the minimax value of the current board
def minimize(alpha : float, beta : float, depth : int, current_color : int, player_color : int, current_board : np.ndarray, k: int, node : TreeNode, expanded_nodes: list, heuristic) -> tuple[np.ndarray, float]:
    if terminal_board(current_board):
        ai_color = PIECE.RED_PLAYER if player_color == PIECE.YELLOW_PLAYER else PIECE.YELLOW_PLAYER

        node.value = result(current_board, ai_color, player_color)
        return current_board, node.value

    if depth == k:
        node.value = evaluate_board(current_board, player_color, heuristic)
        return current_board, node.value

    min_value = float("inf")
    min_move = None

    children_list = expand_board(current_color, current_board)
    expanded_nodes[0] += len(children_list)

    next_turn = PIECE.RED_PLAYER if current_color == PIECE.YELLOW_PLAYER else PIECE.YELLOW_PLAYER

    for i, (child_board, column) in enumerate(children_list):
        child_node = TreeNode(
            child_board,
            depth + 1,
            next_turn,
            move=column
        )
        node.children.append(child_node)

        (max_move, max_value) = maximize(alpha, beta, depth + 1, next_turn, player_color, child_board, k, child_node, expanded_nodes, heuristic)
        child_node.value = max_value

        if max_value < min_value:
            min_value = max_value
            beta = min(beta, min_value)

            min_move = child_board

        # If min value is smaller than or equal to the alpha then prune,
        # because the upper level is max turn so it try to get the biggest minimax value
        if min_value <= alpha:
            node.pruned = True
            node.pruned_count = len(children_list) - (i + 1)
            node.value = min_value
            node.pruned_moves = [(b, col, depth + 1) for b, col in children_list[i + 1:]]
            
            return min_move, min_value

    node.value = min_value
    return min_move, min_value
