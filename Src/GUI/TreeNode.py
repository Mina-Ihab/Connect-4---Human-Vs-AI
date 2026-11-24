class TreeNode:
    def __init__(self, board, depth, player_turn, move=None):
        self.board = board.copy()
        self.depth = depth
        self.player_turn = player_turn
        self.move = move

        self.value = None
        self.children = []

        # Alpha-Beta pruning information
        self.pruned = False
        self.pruned_count = 0
        self.pruned_moves = []