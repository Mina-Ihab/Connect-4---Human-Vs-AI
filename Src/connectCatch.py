# we implement here winning and lose and draw condition and how to calculate the score
# test can be by convolution but not thought of exact way yet
from Src.constnats import RESULT, WIN_RADIUS

def test_down(start_position, search_radius, board, player_piece): 
    # we walk in single direction and check if we have enough consecutive pieces of same color
    # as not return back in the main loop when check all directions go one direction no cycles or cacl cell many times
    # radius means edge number 
    start_row, column = start_position

    if board[start_row][column] != player_piece:
        return False

    last_row = start_row + search_radius - 1
    if last_row >= len(board):
        return False

    for row in range(start_row, last_row + 1):
        if board[row][column] != player_piece:
            return False

    return True

def test_right(start_position, search_radius, board, player_piece): 
    row, start_column = start_position

    if board[row][start_column] != player_piece:
        return False

    last_column = start_column + search_radius - 1
    if last_column >= len(board[0]):
        return False

    for column in range(start_column, last_column + 1):
        if board[row][column] != player_piece:
            return False

    return True

def test_diagonal_down_right(start_position, search_radius, board, player_piece):
    start_row, start_column = start_position

    if board[start_row][start_column] != player_piece:
        return False

    last_row = start_row + search_radius - 1
    last_column = start_column + search_radius - 1

    if last_row >= len(board) or last_column >= len(board[0]):
        return False

    for step in range(search_radius):
        if board[start_row + step][start_column + step] != player_piece:
            return False

    return True

def test_diagonal_down_left(start_position, search_radius, board, player_piece):
    start_row, start_column = start_position

    if board[start_row][start_column] != player_piece:
        return False

    last_row = start_row + search_radius - 1
    last_column = start_column - (search_radius - 1)

    if last_row >= len(board) or last_column < 0:
        return False

    for step in range(search_radius):
        if board[start_row + step][start_column - step] != player_piece:
            return False

    return True

def test_winning_condition(start_position, search_radius, board, player_piece):
    count = 0
    count += test_down(start_position, search_radius, board, player_piece)
    count += test_right(start_position, search_radius, board, player_piece)
    count += test_diagonal_down_right(start_position, search_radius, board, player_piece)
    count += test_diagonal_down_left(start_position, search_radius, board, player_piece)

    return count

def calculate_score(board, player_piece, search_radius=WIN_RADIUS): # go brute force but because the original ones is one direction so not calc cell may times
    score = 0

    for row in range(len(board)):
        for col in range(len(board[0])):
            if board[row][col] == player_piece:
                score += test_winning_condition((row, col), search_radius, board, player_piece)

    return score

def result(board, player, ai, search_radius= WIN_RADIUS):
    # the scores are equal
    # equal scores alone is not enough, it is 0 to 0 at the start of the game

    first_score = calculate_score(board, player, search_radius)
    second_score = calculate_score(board, ai, search_radius)

    if first_score == second_score:
        return RESULT.DRAW

    return RESULT.WIN if first_score > second_score else RESULT.LOSE 