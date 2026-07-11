import sys
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QLabel, QStackedWidget, QFrame, QProgressBar)

from musicsort.gui.style import get_dark_stylesheet, get_light_stylesheet
from musicsort.gui.widgets import (DashboardView, LibraryView, CategoriesView, ScanView,
                                 CSVView, PreviewView, DuplicateView, RestoreView, 
                                 SettingsView, ConsoleView)
from musicsort.core.config import APP_NAME, APP_VERSION

class MainWindow(QMainWindow):
    """
    Main Application Window for MusicSort.
    Sets up a responsive sidebar, a central QStackedWidget containing all views,
    global workers progress trackers, and dynamic theme switching.
    """
    theme_changed = Signal(str)  # Emits theme name when changed

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - Music Organizer (v{APP_VERSION})")
        self.resize(1100, 720)
        self.init_ui()

    def init_ui(self):
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main Layout (Horizontal split between Sidebar and Main Content)
        main_layout = QHBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Frame
        self.sidebar = QFrame()
        self.sidebar.setObjectName("SidebarFrame")
        self.sidebar.setFixedWidth(220)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(6)

        # App Brand Title
        app_title = QLabel(APP_NAME)
        app_title.setObjectName("AppTitle")
        app_title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(app_title)

        # Navigation Buttons list
        self.nav_buttons: list[QPushButton] = []
        
        # Define menu items (label, page index)
        menu_items = [
            ("Dashboard", 0),
            ("Songs Library", 1),
            ("Categories", 2),
            ("Scan Folders", 3),
            ("CSV Manager", 4),
            ("Preview Moves", 5),
            ("Duplicates", 6),
            ("Backups & Undo", 7),
            ("Settings", 8),
            ("System Logs", 9)
        ]

        for label, index in menu_items:
            btn = QPushButton(label)
            btn.setObjectName("SidebarLink")
            btn.setProperty("page_idx", index)
            btn.setProperty("active", "false")
            btn.clicked.connect(self.on_nav_clicked)
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()
        
        # Branding note
        version_lbl = QLabel(f"Version {APP_VERSION}")
        version_lbl.setStyleSheet("color: #666666; font-size: 10px; margin-bottom: 5px;")
        version_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version_lbl)
        
        main_layout.addWidget(self.sidebar)

        # 2. Main Content Split (Title + Stacked Views + Progress Bar)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Stacked Views Widget
        self.stacked_widget = QStackedWidget()
        
        # Instantiate views
        self.dashboard_view = DashboardView()
        self.library_view = LibraryView()
        self.categories_view = CategoriesView()
        self.scan_view = ScanView()
        self.csv_view = CSVView()
        self.preview_view = PreviewView()
        self.duplicate_view = DuplicateView()
        self.restore_view = RestoreView()
        self.settings_view = SettingsView()
        self.console_view = ConsoleView()

        # Add to stack
        self.stacked_widget.addWidget(self.dashboard_view) # 0
        self.stacked_widget.addWidget(self.library_view)   # 1
        self.stacked_widget.addWidget(self.categories_view)# 2
        self.stacked_widget.addWidget(self.scan_view)       # 3
        self.stacked_widget.addWidget(self.csv_view)        # 4
        self.stacked_widget.addWidget(self.preview_view)    # 5
        self.stacked_widget.addWidget(self.duplicate_view)  # 6
        self.stacked_widget.addWidget(self.restore_view)    # 7
        self.stacked_widget.addWidget(self.settings_view)    # 8
        self.stacked_widget.addWidget(self.console_view)     # 9

        content_layout.addWidget(self.stacked_widget)

        # Global thread progress bar (at the bottom)
        self.progress_panel = QFrame()
        self.progress_panel.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #2d2d2d; padding: 8px 15px;")
        self.progress_panel.setFixedHeight(40)
        self.progress_panel.setVisible(False)
        
        prog_layout = QHBoxLayout(self.progress_panel)
        prog_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_msg = QLabel("Idle...")
        self.progress_msg.setStyleSheet("color: #e0e0e0; font-size: 11px;")
        prog_layout.addWidget(self.progress_msg)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar)
        
        content_layout.addWidget(self.progress_panel)

        main_layout.addLayout(content_layout)

        # Default Active page
        self.switch_page(0)
        self.apply_theme("dark")

    def on_nav_clicked(self):
        btn = self.sender()
        if btn:
            idx = btn.property("page_idx")
            self.switch_page(idx)

    def switch_page(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        
        # Update active properties on buttons to trigger QSS styles
        for btn in self.nav_buttons:
            if btn.property("page_idx") == index:
                btn.setProperty("active", "true")
            else:
                btn.setProperty("active", "false")
                
            # Force stylesheet refresh
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def apply_theme(self, theme_name: str):
        """Applies light or dark QSS stylesheet based on setting."""
        if theme_name == "light":
            self.setStyleSheet(get_light_stylesheet())
            # Adapt background panel color
            self.progress_panel.setStyleSheet("background-color: #e4e4e7; border-top: 1px solid #d4d4d8; padding: 8px 15px;")
            self.progress_msg.setStyleSheet("color: #333333; font-size: 11px;")
        else:
            self.setStyleSheet(get_dark_stylesheet())
            self.progress_panel.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #2d2d2d; padding: 8px 15px;")
            self.progress_msg.setStyleSheet("color: #e0e0e0; font-size: 11px;")

    def show_progress(self, show: bool, message: str = "", val: int = 0):
        self.progress_panel.setVisible(show)
        if show:
            self.progress_msg.setText(message)
            self.progress_bar.setValue(val)
