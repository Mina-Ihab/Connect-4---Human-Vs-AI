from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QBrush, QPen, QColor

class MinimaxTreeView(QGraphicsView):
    # Size of one node (board + labels)
    NODE_WIDTH = 150
    NODE_HEIGHT = 131
    LABEL_HEIGHT = 50

    # Spacing between nodes
    HORIZONTAL_SPACING = 190
    VERTICAL_SPACING = 260

    # A pruned board takes the same width as a normal leaf
    PRUNED_WEIGHT = 1.0

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumSize(900, 600)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#0F172A"))

        # Drag with the mouse to move, wheel to zoom
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            factor = 1.15
        else:
            factor = 1 / 1.15

        self.scale(factor, factor)

    def draw_board_node(self, board, x, y, border_color="#334155"):
        rows, cols = board.shape

        cell_size = 16
        spacing = 3

        board_width = cols * cell_size + (cols - 1) * spacing
        board_height = rows * cell_size + (rows - 1) * spacing

        # Board background
        self.scene.addRect(
            x, y,
            board_width + 20,
            board_height + 20,
            QPen(QColor(border_color)),
            QBrush(QColor("#1E293B"))
        )

        # Pieces
        for row in range(rows):
            for col in range(cols):
                piece = board[row][col]

                if piece == 1:
                    color = QColor("#EF4444")
                elif piece == 2:
                    color = QColor("#FACC15")
                else:
                    color = QColor("#0F172A")

                cell_x = x + 10 + col * (cell_size + spacing)
                cell_y = y + 10 + row * (cell_size + spacing)

                self.scene.addEllipse(
                    cell_x, cell_y,
                    cell_size, cell_size,
                    QPen(Qt.PenStyle.NoPen),
                    QBrush(color)
                )

    def draw_node(self, node, x, y):
        self.draw_board_node(node.board, x, y)

        # MAX or MIN and depth
        player_text = "MAX" if node.depth % 2 == 0 else "MIN"

        player_item = self.scene.addText(
            f"{player_text} | Depth: {node.depth}"
        )
        player_item.setDefaultTextColor(QColor("#FFFFFF"))
        player_item.setPos(x, y - 45)

        # Minimax value
        if node.value is None:
            value = "Not evaluated"
        else:
            value = str(node.value)

        value_item = self.scene.addText(f"Value: {value}")
        value_item.setDefaultTextColor(QColor("#38BDF8"))
        value_item.setPos(x, y - 25)

    def draw_pruned_node(self, board, depth, value, center_x, y):
        x = center_x - self.NODE_WIDTH / 2

        pen = QPen(QColor("#EF4444"), 2)
        pen.setStyle(Qt.PenStyle.DashLine)

        # Red circle around the whole pruned node
        center_y = y + self.NODE_HEIGHT / 2
        circle_width = 185
        circle_height = 175

        circle = self.scene.addEllipse(
            center_x - circle_width / 2,
            center_y - circle_height / 2,
            circle_width,
            circle_height,
            pen,
            QBrush(QColor("#450A0A"))
        )
        circle.setZValue(-0.5)

        # Board with a red border
        self.draw_board_node(board, x, y, "#EF4444")

        # Labels
        title = self.scene.addText(f"PRUNED | Depth: {depth}")
        title.setDefaultTextColor(QColor("#FCA5A5"))
        title.setPos(x, y - 45)

        if value is None:
            value_text = "Not evaluated"
        else:
            value_text = str(value)

        value_item = self.scene.addText(f"Value: {value_text}")
        value_item.setDefaultTextColor(QColor("#FCA5A5"))
        value_item.setPos(x, y - 25)

    def draw_connection(self, parent_x, parent_y, child_x, child_y):
        pen = QPen(QColor("#38BDF8"), 2)

        line = self.scene.addLine(
            parent_x, parent_y,
            child_x, child_y,
            pen
        )

        # Keep the line behind the boards and text
        line.setZValue(-1)

    def draw_pruned_connection(self, parent_x, parent_y, child_x, child_y):
        pen = QPen(QColor("#EF4444"), 1.5)
        pen.setStyle(Qt.PenStyle.DashLine)

        line = self.scene.addLine(
            parent_x, parent_y,
            child_x, child_y,
            pen
        )
        line.setZValue(-1)

    def get_max_depth(self, node):
        depth = node.depth

        # A node with pruned moves has one more level below it
        if node.pruned_moves:
            depth = node.depth + 1

        for child in node.children:
            depth = max(depth, self.get_max_depth(child))

        return depth

    def subtree_weight(self, node):
        # How much horizontal space this node needs
        pruned_width = len(node.pruned_moves) * self.PRUNED_WEIGHT

        if not node.children:
            return max(1.0, pruned_width)

        children_width = sum(
            self.subtree_weight(child) for child in node.children
        )

        return children_width + pruned_width

    def split_pruned(self, item):
        # item is (board, column) or (board, column, value)
        board = item[0]
        column = item[1]
        depth = item[2]
        value = None

        return board, column, depth, value

    def draw_tree(self, root):
        self.scene.clear()

        total_weight = self.subtree_weight(root)
        max_depth = self.get_max_depth(root)

        scene_width = max(1400, total_weight * self.HORIZONTAL_SPACING + 100)
        scene_height = (max_depth + 1) * self.VERTICAL_SPACING + 150

        self.scene.setSceneRect(0, 0, scene_width, scene_height)

        self.draw_recursive(root, scene_width / 2, 60, scene_width)

        # Start by looking at the root
        self.centerOn(scene_width / 2, 0)

    def draw_recursive(self, node, center_x, y, available_width):
        # Draw this node
        self.draw_node(node, center_x - self.NODE_WIDTH / 2, y)

        child_weights = [self.subtree_weight(c) for c in node.children]
        pruned_total = len(node.pruned_moves) * self.PRUNED_WEIGHT
        total = sum(child_weights) + pruned_total

        if total == 0:
            return

        # Width of one weight unit
        unit = available_width / total

        child_y = y + self.VERTICAL_SPACING
        line_end_y = child_y - self.LABEL_HEIGHT
        parent_bottom = y + self.NODE_HEIGHT

        current_x = center_x - available_width / 2

        # Explored children
        for child, weight in zip(node.children, child_weights):
            child_width = weight * unit
            child_x = current_x + child_width / 2

            self.draw_connection(
                center_x, parent_bottom,
                child_x, line_end_y
            )

            self.draw_recursive(child, child_x, child_y, child_width)

            current_x += child_width

        # Pruned children (full boards inside red circles)
        for item in node.pruned_moves:
            board, _, depth, value = self.split_pruned(item)

            slot_width = self.PRUNED_WEIGHT * unit
            pruned_x = current_x + slot_width / 2

            self.draw_pruned_connection(
                center_x, parent_bottom,
                pruned_x, line_end_y
            )

            self.draw_pruned_node(board, depth, value, pruned_x, child_y)

            current_x += slot_width