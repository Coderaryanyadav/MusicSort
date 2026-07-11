import sys
from PySide6.QtWidgets import QApplication
from musicsort.gui.main_window import MainWindow
from musicsort.app.controller import AppController

def run_app():
    """Main application loop runner."""
    app = QApplication(sys.argv)
    
    # Note: AA_EnableHighDpiScaling and AA_UseHighDpiPixmaps are
    # removed in Qt6/PySide6 — high-DPI scaling is always enabled.

    # Create Main Window & Controller
    main_win = MainWindow()
    controller = AppController(main_win)
    
    main_win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()
