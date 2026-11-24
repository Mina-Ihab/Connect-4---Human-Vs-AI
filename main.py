# Starts the application and opens the setup dialog before the main window
import sys
from PySide6.QtWidgets import QApplication
from GUI import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    if not win.new_game():
        sys.exit(0)
    win.show()
    sys.exit(app.exec())
