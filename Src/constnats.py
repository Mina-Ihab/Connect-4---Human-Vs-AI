from enum import IntEnum # compare normally than enum

class PIECE(IntEnum):
    RED_PLAYER = 1
    YELLOW_PLAYER = 2
    EMPTY_CELL = 0

class RESULT(IntEnum):
    WIN = 1
    DRAW = 0
    LOSE = -1

FULL_BOARD_CELL = -1 
WIN_RADIUS = 4