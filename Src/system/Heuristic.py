from system.connectCatch import calculate_score
from system.constants import WIN_RADIUS, PIECE
from scipy.signal import convolve2d
import numpy as np

def ai_color(player_piece):
    if player_piece == PIECE.RED_PLAYER:
        return PIECE.YELLOW_PLAYER
    return PIECE.RED_PLAYER

def player_heuristic(board, player_piece):
    score = 0
    weight = 1
    for radius in range(2, WIN_RADIUS + 1):
        score_radius = calculate_score(board, player_piece, radius)
        score += weight * score_radius
        weight *= radius  # Increase weight for larger radius
    return score


def heuristic_convolution(board, player_piece):
    # Define kernels for horizontal, vertical, and diagonal checks
    kernel_horiz = np.array([[1, 1, 1, 1]])
    kernel_vert = np.array([[1], [1], [1], [1]])
    kernel_diag = np.eye(WIN_RADIUS)
    kernel_inv_diag = np.fliplr(np.eye(WIN_RADIUS))

    next_four = 0
    kernels = [kernel_horiz, kernel_vert, kernel_diag, kernel_inv_diag]

    for k in kernels:
        four_conv = convolve2d(board == player_piece, k, mode='valid')
        empty_conv = convolve2d(board == PIECE.EMPTY_CELL, k, mode='valid')

        next_four += np.sum((four_conv == WIN_RADIUS - 1) & (empty_conv == 1)) * WIN_RADIUS # test for every convolution is it have 3 in a row and 1 empty space on that exact line and count it as 4 in a row potential

    return next_four  # Return the score based on potential winning positions

# the heuristics the player can choose from in the setup window
HEURISTICS = {
    "Consecutive pieces": player_heuristic,
    "Potential fours (convolution)": heuristic_convolution,
}

def evaluate_board(board, player_piece, heuristic):
    return heuristic(board, ai_color(player_piece)) - heuristic(board, player_piece)
# to enforce that ai always we calculate score for it
# subtract so also ai focus on oponent score to block it not his only