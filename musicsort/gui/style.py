def get_dark_stylesheet() -> str:
    """
    Returns the modern dark-themed QSS (Qt Style Sheet) for MusicSort.
    Implements glassmorphism aesthetics, clean gradients, rounded corners,
    and responsive hover effects.
    """
    return """
    /* Global Styles */
    QWidget {
        background-color: #121212;
        color: #e0e0e0;
        font-family: "Outfit", "Inter", "Segoe UI", "SF Pro Display", -apple-system, sans-serif;
        font-size: 13px;
    }
    
    /* Sidebar styling */
    QFrame#SidebarFrame {
        background-color: #181818;
        border-right: 1px solid #2a2a2a;
    }
    
    /* Header/Title */
    QLabel#AppTitle {
        font-size: 22px;
        font-weight: 800;
        color: #00adb5;
        margin-bottom: 20px;
        background: transparent;
    }
    
    QLabel#SectionHeader {
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
        background: transparent;
    }

    /* Cards / Sub-containers */
    QFrame#CardFrame {
        background-color: #1e1e1e;
        border: 1px solid #2d2d2d;
        border-radius: 12px;
        padding: 15px;
    }
    
    QFrame#CardFrame:hover {
        border: 1px solid #3d3d3d;
    }

    /* Primary and Secondary Buttons */
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1a1a, stop:1 #2d2d2d);
        border: 1px solid #3d3d3d;
        border-radius: 8px;
        color: #ffffff;
        padding: 8px 16px;
        font-weight: 600;
        min-height: 20px;
    }
    
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2b2b2b, stop:1 #3d3d3d);
        border-color: #555555;
    }
    
    QPushButton:pressed {
        background-color: #1a1a1a;
    }
    
    QPushButton#PrimaryButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00adb5, stop:1 #008f95);
        border: none;
        color: #000000;
        font-weight: 700;
    }
    
    QPushButton#PrimaryButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00c4ce, stop:1 #00adb5);
    }
    
    QPushButton#PrimaryButton:pressed {
        background-color: #008f95;
    }

    QPushButton#DangerButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4b2b, stop:1 #ff416c);
        border: none;
        color: #ffffff;
    }
    
    QPushButton#DangerButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5e3a, stop:1 #ff4b2b);
    }

    /* Sidebar Navigation Link Buttons */
    QPushButton#SidebarLink {
        background: transparent;
        border: none;
        color: #b3b3b3;
        text-align: left;
        padding: 12px 16px;
        font-size: 14px;
        font-weight: 500;
        border-radius: 8px;
    }
    
    QPushButton#SidebarLink:hover {
        background-color: #252525;
        color: #ffffff;
    }
    
    QPushButton#SidebarLink[active="true"] {
        background-color: #2d2d2d;
        color: #00adb5;
        font-weight: 700;
        border-left: 4px solid #00adb5;
        border-top-left-radius: 0px;
        border-bottom-left-radius: 0px;
    }

    /* Inputs & Textboxes */
    QLineEdit {
        background-color: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 6px;
        padding: 8px 12px;
        color: #ffffff;
    }
    
    QLineEdit:focus {
        border: 1px solid #00adb5;
    }

    QComboBox {
        background-color: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 6px;
        padding: 6px 12px;
        color: #ffffff;
    }
    
    QComboBox:focus {
        border: 1px solid #00adb5;
    }
    
    QComboBox::drop-down {
        border: none;
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 25px;
    }
    
    QComboBox QAbstractItemView {
        background-color: #1e1e1e;
        border: 1px solid #2d2d2d;
        selection-background-color: #2d2d2d;
        selection-color: #00adb5;
    }

    /* Lists, Tables, and Headers */
    QTableWidget, QListWidget, QTreeWidget {
        background-color: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 8px;
        gridline-color: #2a2a2a;
        color: #e0e0e0;
    }
    
    QTableWidget::item:selected, QListWidget::item:selected {
        background-color: #2c2c2c;
        color: #00adb5;
    }
    
    QHeaderView::section {
        background-color: #252525;
        color: #ffffff;
        padding: 6px;
        border: 1px solid #1a1a1a;
        font-weight: 600;
    }

    /* Progress Bar */
    QProgressBar {
        background-color: #1e1e1e;
        border: 1px solid #2d2d2d;
        border-radius: 8px;
        text-align: center;
        color: #ffffff;
        font-weight: bold;
    }
    
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00adb5, stop:1 #008f95);
        border-radius: 6px;
    }

    /* Scrollbars */
    QScrollBar:vertical {
        border: none;
        background-color: #121212;
        width: 10px;
        margin: 0px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #2d2d2d;
        min-height: 20px;
        border-radius: 5px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #3e3e3e;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    QScrollBar:horizontal {
        border: none;
        background-color: #121212;
        height: 10px;
        margin: 0px;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #2d2d2d;
        min-width: 20px;
        border-radius: 5px;
    }
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0px;
    }

    /* Logs & Console */
    QPlainTextEdit#ConsoleOutput {
        background-color: #0d0d0d;
        border: 1px solid #2d2d2d;
        font-family: "Courier New", Courier, monospace;
        font-size: 12px;
        color: #00ff66;
        border-radius: 8px;
    }

    /* Tab Widget styling */
    QTabWidget::pane {
        border: 1px solid #2d2d2d;
        border-radius: 8px;
        background-color: #1e1e1e;
    }

    QTabBar::tab {
        background-color: #181818;
        border: 1px solid #2d2d2d;
        border-bottom-color: transparent;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 16px;
        color: #b3b3b3;
    }

    QTabBar::tab:selected {
        background-color: #1e1e1e;
        color: #00adb5;
        font-weight: 700;
        border-bottom-color: #1e1e1e;
    }

    QTabBar::tab:hover:!selected {
        background-color: #222222;
        color: #ffffff;
    }
    """


def get_light_stylesheet() -> str:
    """
    Returns the light-themed QSS (Qt Style Sheet) for MusicSort.
    Sleek macOS silver/light-gray layout with vibrant cyan accents.
    """
    return """
    /* Global Styles */
    QWidget {
        background-color: #f4f4f5;
        color: #333333;
        font-family: "Outfit", "Inter", "Segoe UI", "SF Pro Display", -apple-system, sans-serif;
        font-size: 13px;
    }
    
    /* Sidebar styling */
    QFrame#SidebarFrame {
        background-color: #e4e4e7;
        border-right: 1px solid #d4d4d8;
    }
    
    /* Header/Title */
    QLabel#AppTitle {
        font-size: 22px;
        font-weight: 800;
        color: #008f95;
        margin-bottom: 20px;
        background: transparent;
    }
    
    QLabel#SectionHeader {
        font-size: 18px;
        font-weight: 700;
        color: #111111;
        background: transparent;
    }

    /* Cards / Sub-containers */
    QFrame#CardFrame {
        background-color: #ffffff;
        border: 1px solid #e4e4e7;
        border-radius: 12px;
        padding: 15px;
    }
    
    QFrame#CardFrame:hover {
        border: 1px solid #d4d4d8;
    }

    /* Primary and Secondary Buttons */
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f4f4f5);
        border: 1px solid #e4e4e7;
        border-radius: 8px;
        color: #333333;
        padding: 8px 16px;
        font-weight: 600;
        min-height: 20px;
    }
    
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f4f4f5, stop:1 #e4e4e7);
        border-color: #d4d4d8;
    }
    
    QPushButton:pressed {
        background-color: #e4e4e7;
    }
    
    QPushButton#PrimaryButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00adb5, stop:1 #008f95);
        border: none;
        color: #ffffff;
        font-weight: 700;
    }
    
    QPushButton#PrimaryButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00c4ce, stop:1 #00adb5);
    }
    
    QPushButton#PrimaryButton:pressed {
        background-color: #008f95;
    }

    QPushButton#DangerButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff4b2b, stop:1 #ff416c);
        border: none;
        color: #ffffff;
    }
    
    QPushButton#DangerButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff5e3a, stop:1 #ff4b2b);
    }

    /* Sidebar Navigation Link Buttons */
    QPushButton#SidebarLink {
        background: transparent;
        border: none;
        color: #666666;
        text-align: left;
        padding: 12px 16px;
        font-size: 14px;
        font-weight: 500;
        border-radius: 8px;
    }
    
    QPushButton#SidebarLink:hover {
        background-color: #d4d4d8;
        color: #111111;
    }
    
    QPushButton#SidebarLink[active="true"] {
        background-color: #f4f4f5;
        color: #008f95;
        font-weight: 700;
        border-left: 4px solid #008f95;
        border-top-left-radius: 0px;
        border-bottom-left-radius: 0px;
    }

    /* Inputs & Textboxes */
    QLineEdit {
        background-color: #ffffff;
        border: 1px solid #d4d4d8;
        border-radius: 6px;
        padding: 8px 12px;
        color: #333333;
    }
    
    QLineEdit:focus {
        border: 1px solid #008f95;
    }

    QComboBox {
        background-color: #ffffff;
        border: 1px solid #d4d4d8;
        border-radius: 6px;
        padding: 6px 12px;
        color: #333333;
    }
    
    QComboBox:focus {
        border: 1px solid #008f95;
    }
    
    QComboBox::drop-down {
        border: none;
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 25px;
    }
    
    QComboBox QAbstractItemView {
        background-color: #ffffff;
        border: 1px solid #d4d4d8;
        selection-background-color: #f4f4f5;
        selection-color: #008f95;
    }

    /* Lists, Tables, and Headers */
    QTableWidget, QListWidget, QTreeWidget {
        background-color: #ffffff;
        border: 1px solid #e4e4e7;
        border-radius: 8px;
        gridline-color: #f4f4f5;
        color: #333333;
    }
    
    QTableWidget::item:selected, QListWidget::item:selected {
        background-color: #e4e4e7;
        color: #008f95;
    }
    
    QHeaderView::section {
        background-color: #f4f4f5;
        color: #111111;
        padding: 6px;
        border: 1px solid #e4e4e7;
        font-weight: 600;
    }

    /* Progress Bar */
    QProgressBar {
        background-color: #e4e4e7;
        border: 1px solid #d4d4d8;
        border-radius: 8px;
        text-align: center;
        color: #111111;
        font-weight: bold;
    }
    
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00adb5, stop:1 #008f95);
        border-radius: 6px;
    }

    /* Scrollbars */
    QScrollBar:vertical {
        border: none;
        background-color: #f4f4f5;
        width: 10px;
        margin: 0px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #d4d4d8;
        min-height: 20px;
        border-radius: 5px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #a1a1aa;
    }
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    /* Logs & Console */
    QPlainTextEdit#ConsoleOutput {
        background-color: #1e1e1e;
        border: 1px solid #d4d4d8;
        font-family: "Courier New", Courier, monospace;
        font-size: 12px;
        color: #00ff66;
        border-radius: 8px;
    }

    /* Tab Widget styling */
    QTabWidget::pane {
        border: 1px solid #e4e4e7;
        border-radius: 8px;
        background-color: #ffffff;
    }

    QTabBar::tab {
        background-color: #e4e4e7;
        border: 1px solid #d4d4d8;
        border-bottom-color: transparent;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 16px;
        color: #666666;
    }

    QTabBar::tab:selected {
        background-color: #ffffff;
        color: #008f95;
        font-weight: 700;
        border-bottom-color: #ffffff;
    }
    """
