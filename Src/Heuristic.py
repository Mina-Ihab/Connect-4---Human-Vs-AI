# here we try to get best heurestic possible (didnt search but best i know number of consecteve same color)
from Src.connectCatch import calculate_score
from Src.constnats import WIN_RADIUS
from Src.GameEngine import get_opponent_piece

def player_heuristic(board, player_piece):
    score = 0
    weight = 1
    for radius in range(2, WIN_RADIUS + 1):
        score_radius = calculate_score(board, player_piece, radius)
        score += weight * score_radius
        weight *= radius  # Increase weight for larger radius
    return score

def evaluate_board(board, player_piece):
    return player_heuristic(board, player_piece) - player_heuristic(board, get_opponent_piece(player_piece))  # to check other player score so ai try win or make the other lose not focus on itself only
# to check other player score so ai try win or make the other lose not focus on itself only