import queue
import threading
import traceback

import numpy as np
from PySide6.QtCore import (Qt, Signal, QObject, QRectF, QPointF,
                            QVariantAnimation, QEasingCurve, QAbstractAnimation)
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen, QFont
from PySide6.QtWidgets import (QComboBox, QWidget, QMainWindow, QDialog, QVBoxLayout,
                               QHBoxLayout, QFormLayout, QLabel, QPushButton, QSpinBox,
                               QSplitter, QFrame, QDialogButtonBox)

from Src.constnats import PIECE, RESULT
from Src.connectCatch import calculate_score

COLOR_BG_TOP     = "#0a1c45"
COLOR_BG_BOTTOM  = "#14336b"
COLOR_BOARD      = QColor(47, 96, 140, 235)
COLOR_BOARD_EDGE = QColor("#7fb2da")
COLOR_HOLE       = QColor("#0d2147")
COLOR_ACCENT     = "#4fd8f5"
COLOR_PRUNED     = "#c0391b"
PIECE_COLORS = {
    int(PIECE.RED_PLAYER):    (QColor("#ffc4a3"), QColor("#f08a5d")),
    int(PIECE.YELLOW_PLAYER): (QColor("#fff3b0"), QColor("#ffd84a")),
}

STYLE = f"""
QMainWindow, QDialog {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 {COLOR_BG_TOP}, stop:1 {COLOR_BG_BOTTOM}); }}
QLabel {{ color: #e8f1ff; font-size: 14px; }}
QLabel#title {{ color: {COLOR_ACCENT}; font-size: 16px; font-weight: bold; }}
QFrame#panel {{ background: rgba(255,255,255,0.05); border: 1px solid #3b6aa3; border-radius: 10px; }}
QPushButton {{ background: #1d447f; color: white; border: 1px solid #4a7fc0; border-radius: 8px;
               padding: 8px 14px; font-size: 14px; }}
QPushButton:hover {{ background: #2a5ca3; }}
QPushButton:checked {{ background: {COLOR_ACCENT}; color: #06204a; font-weight: bold; }}
QPushButton:disabled {{ background: #17294d; color: #6f84a8; border-color: #2c4670; }}
QSpinBox {{ background: #0d2147; color: white; border: 1px solid #4a7fc0; border-radius: 6px; padding: 4px; }}
QSplitter::handle {{ background: #2c4670; width: 3px; }}
"""

# Shared game settings written by the GUI thread and read by the backend thread
class Settings:
    length = 6
    width = 7
    limit = 4
    player_color = PIECE.RED_PLAYER

settings = Settings()


# Raised inside the backend thread to stop an old game
class GameAborted(Exception):
    pass


# One game session that owns the click queue and the signals to the GUI
class GameSession(QObject):
    board_changed = Signal(object)
    human_turn    = Signal(bool)
    game_over     = Signal(object)
    tree_ready    = Signal(object)
    error         = Signal(str)

    def __init__(self):
        super().__init__()
        self.inbox = queue.Queue()
        self.aborted = False

    # Stops the session and wakes the backend if it waits for a click
    def abort(self):
        self.aborted = True
        self.inbox.put(None)


_local = threading.local()


# Returns the session of the current backend thread or stops the thread if it was aborted
def _session() -> GameSession:
    s = getattr(_local, "session", None)
    if s is None or s.aborted:
        raise GameAborted()
    return s

# Returns the board size, limit and player color chosen in the setup dialog
def get_gui_setup():
    return settings.length, settings.width, settings.limit, settings.player_color


# Waits until the human clicks a column and returns its index
def get_gui_input() -> int:
    s = _session()
    s.human_turn.emit(True)
    col = s.inbox.get()
    if col is None or s.aborted:
        raise GameAborted()
    return col


# Sends the current board to the GUI after every placed piece
def gui_show_board(board: np.ndarray):
    _session().board_changed.emit(board.copy())


# Sends the final result and scores to the GUI
def gui_game_over(result, board: np.ndarray):
    s = _session()
    human = int(calculate_score(board, int(settings.player_color)))
    ai = int(calculate_score(board, 3 - int(settings.player_color)))
    s.game_over.emit({"result": int(result), "human": human, "ai": ai})


# Sends the minimax tree of the last AI move to the GUI
def gui_set_tree(tree):
    _session().tree_ready.emit(tree)


# Runs the game engine inside the backend thread
def _run_game(session: GameSession):
    _local.session = session
    try:
        from Src import GameEngine
        GameEngine.main_game_loop()
    except GameAborted:
        pass
    except Exception:
        traceback.print_exc()
        session.error.emit(traceback.format_exc(limit=1))

# Draws the board, animates falling discs and reports column clicks
class BoardWidget(QWidget):
    column_clicked = Signal(int)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self.setMinimumSize(380, 330)
        self.input_enabled = False
        self.hover_col = -1
        self._falling = {}
        self.reset(settings.length, settings.width)

    # Clears the board to the given size
    def reset(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.cells = np.zeros((rows, cols), dtype=int)
        self._falling.clear()
        self.update()

    # Enables or disables clicking on the board
    def set_input_enabled(self, enabled: bool):
        self.input_enabled = enabled
        self.update()

    # Shows the backend board and animates the new discs
    def set_board(self, board: np.ndarray):
        if board.shape != self.cells.shape:
            self.reset(*board.shape)
        for r, c in zip(*np.where(board != self.cells)):
            self.cells[r, c] = board[r, c]
            if board[r, c] != int(PIECE.EMPTY_CELL):
                self._animate_drop(int(r), int(c))
        self.update()

    # Returns the cell size and the top left corner of the board
    def _geometry(self):
        pad = 14
        cell = min((self.width() - 2 * pad) / self.cols, (self.height() - 2 * pad) / self.rows)
        x0 = (self.width() - cell * self.cols) / 2
        y0 = (self.height() - cell * self.rows) / 2
        return cell, x0, y0

    # Returns the column under the given x position or -1
    def _col_at(self, x):
        cell, x0, _ = self._geometry()
        col = int((x - x0) // cell)
        return col if 0 <= col < self.cols else -1

    # Returns the lowest empty row in a column or -1 if it is full
    def _lowest_empty(self, col):
        for r in range(self.rows - 1, -1, -1):
            if self.cells[r, col] == int(PIECE.EMPTY_CELL):
                return r
        return -1

    # Starts the falling animation of one disc
    def _animate_drop(self, r, c):
        key = (r, c)
        self._falling[key] = 0.0
        anim = QVariantAnimation(self)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setDuration(220 + 50 * r)
        anim.setEasingCurve(QEasingCurve.OutBounce)
        anim.valueChanged.connect(lambda v, k=key: (self._falling.__setitem__(k, float(v)), self.update()))
        anim.finished.connect(lambda k=key: (self._falling.pop(k, None), self.update()))
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    # Tracks the hovered column
    def mouseMoveEvent(self, e):
        col = self._col_at(e.position().x())
        if col != self.hover_col:
            self.hover_col = col
            self.update()

    # Clears the hovered column when the mouse leaves
    def leaveEvent(self, e):
        self.hover_col = -1
        self.update()

    # Drops the human disc and sends the clicked column to the backend
    def mousePressEvent(self, e):
        if not self.input_enabled or e.button() != Qt.LeftButton:
            return
        col = self._col_at(e.position().x())
        if col < 0:
            return
        row = self._lowest_empty(col)
        if row < 0:
            return
        self.cells[row, col] = int(settings.player_color)
        self._animate_drop(row, col)
        self.input_enabled = False
        self.column_clicked.emit(col)

    # Draws one disc with a gradient
    def _draw_disc(self, p, center, radius, piece):
        light, base = PIECE_COLORS[int(piece)]
        g = QRadialGradient(center - QPointF(radius * 0.3, radius * 0.3), radius * 1.3)
        g.setColorAt(0, light)
        g.setColorAt(1, base)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(center, radius, radius)

    # Paints the board plate, holes, hover preview and discs
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cell, x0, y0 = self._geometry()
        radius = cell * 0.40
        plate = QRectF(x0 - 8, y0 - 8, cell * self.cols + 16, cell * self.rows + 16)
        p.setPen(QPen(COLOR_BOARD_EDGE, 2))
        p.setBrush(COLOR_BOARD)
        p.drawRoundedRect(plate, 14, 14)

        p.setClipRect(plate)
        center = lambda r, c: QPointF(x0 + (c + 0.5) * cell, y0 + (r + 0.5) * cell)

        p.setPen(Qt.NoPen)
        p.setBrush(COLOR_HOLE)
        for r in range(self.rows):
            for c in range(self.cols):
                p.drawEllipse(center(r, c), radius, radius)

        if self.input_enabled and self.hover_col >= 0:
            p.setBrush(QColor(255, 255, 255, 28))
            p.drawRect(QRectF(x0 + self.hover_col * cell, y0, cell, cell * self.rows))
            r = self._lowest_empty(self.hover_col)
            if r >= 0:
                p.setOpacity(0.35)
                self._draw_disc(p, center(r, self.hover_col), radius, settings.player_color)
                p.setOpacity(1.0)

        for r in range(self.rows):
            for c in range(self.cols):
                piece = self.cells[r, c]
                if piece == int(PIECE.EMPTY_CELL):
                    continue
                ctr = center(r, c)
                prog = self._falling.get((r, c))
                if prog is not None:
                    start_y = y0 - cell * 0.5
                    ctr = QPointF(ctr.x(), start_y + (ctr.y() - start_y) * prog)
                self._draw_disc(p, ctr, radius, piece)

# Dialog to choose color, rows, columns and limit
class SetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Connect 4 game")
        self.rows = QSpinBox(); self.rows.setRange(6, 12);  self.rows.setValue(settings.length)
        self.cols = QSpinBox(); self.cols.setRange(7, 12);  self.cols.setValue(settings.width)
        self.limit = QSpinBox(); self.limit.setRange(1, 12); self.limit.setValue(settings.limit)

        self.color = QComboBox(); self.color.addItems(["Red (orange)", "Yellow"])
        self.color.setCurrentIndex(0 if settings.player_color == PIECE.RED_PLAYER else 1)

        form = QFormLayout()
        form.addRow("Your color (Red moves first):", self.color)
        form.addRow("Board length (rows, ≥ 6):", self.rows)
        form.addRow("Board width (columns, ≥ 7):", self.cols)
        form.addRow("Alpha-beta limit K:", self.limit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

    # Copies the dialog values to the shared settings
    def apply(self):
        settings.length, settings.width, settings.limit = self.rows.value(), self.cols.value(), self.limit.value()
        settings.player_color = PIECE.RED_PLAYER if self.color.currentIndex() == 0 else PIECE.YELLOW_PLAYER

# Prepares the tree for drawing on a worker thread
class TreeLoader(QObject):
    done = Signal(object)

    # Starts the worker thread that prepares the tree
    def load(self, tree):
        threading.Thread(target=lambda: self.done.emit(prepare_tree_layout(tree)), daemon=True).start()


# Does the heavy tree layout work away from the GUI thread
def prepare_tree_layout(tree):
    return tree


# Widget that will draw the minimax tree
class TreeView(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel("No tree yet — play a move.")
        self.label.setAlignment(Qt.AlignCenter)
        QVBoxLayout(self).addWidget(self.label)

    # Shows the received tree
    def set_tree(self, tree):
        self.label.setText("Tree received (drawing not implemented yet)." if tree is not None
                           else "No tree yet — play a move.")


# Separate window that shows the minimax tree
class TreeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minimax tree — last move")
        self.resize(1000, 600)
        self.setStyleSheet(STYLE + f"TreeWindow {{ background: {COLOR_BG_TOP}; }}")
        self.view = TreeView()
        QVBoxLayout(self).addWidget(self.view)
        self.loader = TreeLoader()
        self.loader.done.connect(self.view.set_tree)

    # Opens the window and loads the tree
    def show_tree(self, tree):
        self.show(); self.raise_(); self.activateWindow()
        self.loader.load(tree)

# Main window with the board, settings, tree button and status
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connect 4 — Minimax AI")
        self.resize(900, 640)
        self.setStyleSheet(STYLE)
        self.session = None
        self.last_tree = None
        self.tree_window = TreeWindow()

        self.board = BoardWidget()
        self.board.column_clicked.connect(self._on_column_clicked)

        side = QFrame(); side.setObjectName("panel")
        sl = QVBoxLayout(side)
        t = QLabel("Settings"); t.setObjectName("title"); sl.addWidget(t)
        self.tree_btn = QPushButton("Show minimax tree")
        self.tree_btn.clicked.connect(lambda: self.tree_window.show_tree(self.last_tree))
        sl.addWidget(self.tree_btn)
        sl.addStretch()

        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.board); split.addWidget(side)
        split.setStretchFactor(0, 4); split.setStretchFactor(1, 1)
        split.setCollapsible(0, False)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setFont(QFont(self.font().family(), 16, QFont.Bold))
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(lambda: self.new_game())
        bottom = QHBoxLayout(); bottom.addWidget(self.status, 1); bottom.addWidget(self.reset_btn)

        root = QWidget(); lay = QVBoxLayout(root)
        lay.addWidget(split, 1); lay.addLayout(bottom)
        self.setCentralWidget(root)

    # Asks for the setup and starts a new game in a new backend thread
    def new_game(self) -> bool:
        dlg = SetupDialog(self if self.isVisible() else None)
        if dlg.exec() != QDialog.Accepted:
            return False
        dlg.apply()

        if self.session:
            self.session.abort()
        self.board.reset(settings.length, settings.width)
        self.last_tree = None

        s = self.session = GameSession()
        s.board_changed.connect(lambda b, s=s: s is self.session and self.board.set_board(b))
        s.human_turn.connect(lambda on, s=s: s is self.session and self._on_human_turn(on))
        s.game_over.connect(lambda r, s=s: s is self.session and self._on_game_over(r))
        s.tree_ready.connect(lambda t, s=s: s is self.session and self._on_tree(t))
        s.error.connect(lambda m, s=s: s is self.session and self._set_status(f"Backend error: {m}", "#ff8080"))
        self._set_status("Starting…" if settings.player_color == PIECE.RED_PLAYER else "AI is thinking…", COLOR_ACCENT)
        threading.Thread(target=_run_game, args=(s,), daemon=True).start()
        return True

    # Sends the clicked column to the backend
    def _on_column_clicked(self, col):
        self.session.inbox.put(col)
        self._set_status("AI is thinking…", COLOR_ACCENT)

    # Enables the board when it is the human turn
    def _on_human_turn(self, on):
        self.board.set_input_enabled(on)
        if on:
            self._set_status("Your turn — click a column", "#ffe27a")

    # Shows the result and the scores
    def _on_game_over(self, info):
        self.board.set_input_enabled(False)
        text, color = {int(RESULT.WIN): ("YOU WIN!", "#7dff9b"),
                       int(RESULT.LOSE): ("YOU LOSE", "#ff7d7d"),
                       int(RESULT.DRAW): ("DRAW", "#ffe27a")}[info["result"]]
        self._set_status(f"{text}   (you {info['human']} – AI {info['ai']})", color)

    # Stores the last tree and enables the tree button
    def _on_tree(self, tree):
        self.last_tree = tree
        if self.tree_window.isVisible():
            self.tree_window.show_tree(tree)

    # Updates the status text and color
    def _set_status(self, text, color="#e8f1ff"):
        self.status.setText(text)
        self.status.setStyleSheet(f"color: {color};")

    # Stops the game and the tree window when the window closes
    def closeEvent(self, e):
        if self.session:
            self.session.abort()
        self.tree_window.close()
        super().closeEvent(e)