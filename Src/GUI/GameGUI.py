import sys
import math

import numpy as np
from PySide6.QtCore import Qt, Signal, QEventLoop, QRectF
from PySide6.QtGui import QPainter, QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QLabel, QRadioButton, QSpinBox, QPushButton, QMessageBox,
    QButtonGroup, QComboBox,
)

from system.constants import PIECE, RESULT
from system.Heuristic import HEURISTICS
from GUI.MinimaxTreeGUI import MinimaxTreeView

# colors, same ones as the tree view
BG_COLOR = "#0F172A"
BOARD_COLOR = "#1D4ED8"
RED_COLOR = "#EF4444"
YELLOW_COLOR = "#FACC15"
TEXT_COLOR = "#E2E8F0"

PIECE_COLORS = {
    PIECE.RED_PLAYER: RED_COLOR,
    PIECE.YELLOW_PLAYER: YELLOW_COLOR,
}

STYLE = f"""
    QDialog, QMainWindow, QWidget#central {{ background-color: {BG_COLOR}; }}
    QLabel {{ color: {TEXT_COLOR}; font-size: 14px; }}
    QRadioButton {{ color: {TEXT_COLOR}; font-size: 14px; spacing: 8px; }}
    QSpinBox {{
        background: #1E293B; color: {TEXT_COLOR};
        border: 1px solid #334155; border-radius: 4px; padding: 4px;
    }}
    QPushButton {{
        background: #38BDF8; color: #0F172A; font-weight: bold;
        border: none; border-radius: 6px; padding: 8px 20px; font-size: 14px;
    }}
    QPushButton:hover {{ background: #7DD3FC; }}
"""

# the game engine only uses functions, so the window is kept here as a global
_app = None
_window = None
_player_color = None


def _get_app():
    global _app
    _app = QApplication.instance() or QApplication(sys.argv)
    _app.setStyleSheet(STYLE)
    return _app


# first window: choose color, depth and board size
class SetupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connect 4 - Setup")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("Connect 4 vs Minimax AI")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addWidget(QLabel("Choose your color:"))

        self.red_radio = QRadioButton("Red (moves first)")
        self.red_radio.setStyleSheet(f"QRadioButton {{ color: {RED_COLOR}; font-weight: bold; }}")
        self.yellow_radio = QRadioButton("Yellow (moves second)")
        self.yellow_radio.setStyleSheet(f"QRadioButton {{ color: {YELLOW_COLOR}; font-weight: bold; }}")
        self.red_radio.setChecked(True)

        # the group makes sure only one of them is selected
        group = QButtonGroup(self)
        group.addButton(self.red_radio)
        group.addButton(self.yellow_radio)

        layout.addWidget(self.red_radio)
        layout.addWidget(self.yellow_radio)

        form = QFormLayout()

        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 10)
        self.depth_spin.setValue(4)
        self.depth_spin.setToolTip("Max depth (k) of the minimax tree. Bigger is smarter but slower.")
        form.addRow("Max depth (k):", self.depth_spin)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(4, 10)
        self.rows_spin.setValue(6)
        form.addRow("Rows:", self.rows_spin)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(4, 10)
        self.cols_spin.setValue(7)
        form.addRow("Columns:", self.cols_spin)

        # which heuristic the AI uses
        self.heuristic_combo = QComboBox()
        self.heuristic_combo.addItems(list(HEURISTICS.keys()))
        form.addRow("Heuristic:", self.heuristic_combo)

        layout.addLayout(form)

        hint = QLabel("Higher depth makes the AI stronger but slower.")
        hint.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(hint)

        start = QPushButton("Start Game")
        start.clicked.connect(self.accept)
        layout.addWidget(start)

    def heuristic_name(self):
        return self.heuristic_combo.currentText()

    def values(self):
        color = PIECE.RED_PLAYER if self.red_radio.isChecked() else PIECE.YELLOW_PLAYER
        return self.rows_spin.value(), self.cols_spin.value(), self.depth_spin.value(), color


# the board that is drawn and clicked
class BoardWidget(QWidget):
    column_clicked = Signal(int)

    def __init__(self, rows, cols, player_color):
        super().__init__()
        self.board = np.zeros((rows, cols), dtype=int)
        self.player_color = player_color
        self.input_enabled = False
        self.hover_col = -1

        self.setMouseTracking(True)
        self.setMinimumSize(cols * 70, (rows + 1) * 70)

    # one extra row on top is used to show where the piece will drop
    def _layout(self):
        rows, cols = self.board.shape
        cell = min(self.width() / cols, self.height() / (rows + 1))
        x0 = (self.width() - cell * cols) / 2
        y0 = (self.height() - cell * (rows + 1)) / 2
        return cell, x0, y0

    # which column is under this x position (-1 if none)
    def _column_at(self, x):
        cell, x0, _ = self._layout()
        col = int((x - x0) // cell)
        if 0 <= col < self.board.shape[1]:
            return col
        return -1

    def set_board(self, board):
        self.board = board.copy()
        self.update()

    def set_input_enabled(self, enabled):
        self.input_enabled = enabled
        self.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        self.update()

    def mouseMoveEvent(self, event):
        self.hover_col = self._column_at(event.position().x())
        self.update()

    def leaveEvent(self, event):
        self.hover_col = -1
        self.update()

    def mousePressEvent(self, event):
        if not self.input_enabled or event.button() != Qt.MouseButton.LeftButton:
            return

        col = self._column_at(event.position().x())
        # ignore full columns, otherwise the engine waits forever for a valid move
        if col != -1 and self.board[0][col] == PIECE.EMPTY_CELL:
            self.column_clicked.emit(col)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rows, cols = self.board.shape
        cell, x0, y0 = self._layout()
        margin = cell * 0.08
        board_top = y0 + cell

        # blue board
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(BOARD_COLOR)))
        painter.drawRoundedRect(QRectF(x0, board_top, cell * cols, cell * rows), 14, 14)

        # circles
        for r in range(rows):
            for c in range(cols):
                piece = self.board[r][c]
                color = PIECE_COLORS.get(piece, BG_COLOR)

                painter.setBrush(QBrush(QColor(color)))
                painter.drawEllipse(QRectF(
                    x0 + c * cell + margin,
                    board_top + r * cell + margin,
                    cell - 2 * margin,
                    cell - 2 * margin,
                ))

        # faded piece above the column the mouse is on
        if self.input_enabled and self.hover_col != -1 and self.board[0][self.hover_col] == PIECE.EMPTY_CELL:
            preview = QColor(PIECE_COLORS[self.player_color])
            preview.setAlpha(180)
            painter.setBrush(QBrush(preview))
            painter.drawEllipse(QRectF(
                x0 + self.hover_col * cell + margin,
                y0 + margin,
                cell - 2 * margin,
                cell - 2 * margin,
            ))


# the main game window
class GameWindow(QMainWindow):
    closed = Signal()

    def __init__(self, rows, cols, depth, player_color):
        super().__init__()
        self.setWindowTitle("Connect 4")

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)

        # top bar: my color and the depth
        info = QHBoxLayout()
        you = "Red" if player_color == PIECE.RED_PLAYER else "Yellow"
        you_color = PIECE_COLORS[player_color]

        you_label = QLabel(f"You: <b style='color:{you_color}'>{you}</b>")
        depth_label = QLabel(f"AI depth (k): <b>{depth}</b>")
        depth_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        info.addWidget(you_label)
        info.addWidget(depth_label)
        layout.addLayout(info)

        self.board_widget = BoardWidget(rows, cols, player_color)
        layout.addWidget(self.board_widget, stretch=1)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.status)

        self.score_label = QLabel("Score  -  You: 0   |   AI: 0")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.score_label)

        self.stats_label = QLabel("AI minimax value: -   |   Expanded nodes: -")
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stats_label)

        self.time_label = QLabel("AI thinking time: -")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        # the button stays disabled until the AI has made a move (no tree before that)
        self.last_root = None
        self.tree_button = QPushButton("Visualize Minimax Tree")
        self.tree_button.setEnabled(False)
        self.tree_button.clicked.connect(lambda: gui_show_tree(self.last_root))
        layout.addWidget(self.tree_button)

        self.resize(cols * 90 + 60, (rows + 1) * 90 + 140)

    def set_status(self, text):
        self.status.setText(text)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


# functions below are the ones GameEngine.py calls

# show the setup dialog then open the game window
def get_gui_setup():
    global _window, _player_color

    _get_app()

    dialog = SetupDialog()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    length, width, limit, player_color = dialog.values()
    heuristic = HEURISTICS[dialog.heuristic_name()]
    _player_color = player_color

    _window = GameWindow(length, width, limit, player_color)
    _window.show()
    _app.processEvents()

    return length, width, limit, player_color, heuristic


# wait here until the player clicks a column, then return that column
def get_gui_input():
    loop = QEventLoop()
    chosen = {}

    def on_click(col):
        chosen["col"] = col
        loop.quit()

    _window.board_widget.column_clicked.connect(on_click)
    _window.closed.connect(loop.quit)

    _window.set_status("Your turn - click a column")
    _window.board_widget.set_input_enabled(True)

    loop.exec()

    _window.board_widget.set_input_enabled(False)
    _window.board_widget.column_clicked.disconnect(on_click)
    _window.closed.disconnect(loop.quit)

    # no column means the window was closed
    if "col" not in chosen:
        sys.exit(0)

    return chosen["col"]


# keep the last tree so the button can show it
def gui_set_tree(root):
    _window.last_root = root
    _window.tree_button.setEnabled(root is not None)


def gui_set_stats(value, expanded_nodes):
    _window.stats_label.setText(f"AI minimax value: {value}   |   Expanded nodes: {expanded_nodes}")


def gui_set_scores(player_score, ai_score):
    _window.score_label.setText(f"Score  -  You: {player_score}   |   AI: {ai_score}")


# called when the AI starts thinking: the tree button is disabled until it finishes
def gui_set_thinking():
    _window.tree_button.setEnabled(False)
    _window.time_label.setText("AI thinking time: ...")
    _window.set_status("AI is thinking...")
    _app.processEvents()


# called when the AI finishes: show how long it took (in milliseconds)
def gui_set_time(seconds):
    # round to 4 significant figures (and never use scientific notation like 1e+04)
    ms = float(f"{seconds * 1000:.4g}")
    decimals = max(0, 3 - math.floor(math.log10(ms))) if ms > 0 else 0
    _window.time_label.setText(f"AI thinking time: {ms:.{decimals}f} ms")


# redraw after every move
def gui_show_board(board):
    _window.board_widget.set_board(board)
    _window.set_status("AI is thinking...")
    _app.processEvents()  # so the board is drawn before the AI starts searching


# result is from the human player's point of view
def gui_game_over(result, board):
    _window.board_widget.set_board(board)
    _window.board_widget.set_input_enabled(False)

    if result == RESULT.WIN:
        message = "You win!"
    elif result == RESULT.LOSE:
        message = "The AI wins!"
    else:
        message = "It's a draw!"

    _window.set_status(f"Game over - {message}")
    _app.processEvents()

    QMessageBox.information(_window, "Game Over", message)


# open the minimax tree of the last AI move in a new window
def gui_show_tree(root):
    dialog = QDialog(_window)
    dialog.setWindowTitle("Minimax Tree")
    dialog.resize(1200, 800)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(0, 0, 0, 0)

    view = MinimaxTreeView()
    view.draw_tree(root)
    layout.addWidget(view)

    dialog.exec()