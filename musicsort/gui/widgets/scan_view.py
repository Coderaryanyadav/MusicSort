from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, QFileDialog, QFrame, QHeaderView)
from musicsort.models.domain import Song

class DropArea(QFrame):
    """Custom area supporting folder Drag & Drop."""
    folder_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("CardFrame")
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.label = QLabel("Drag and Drop your Music Folder here\n- or -")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; font-weight: 500; color: #888888; background: transparent;")
        
        self.browse_btn = QPushButton("Browse Folder")
        self.browse_btn.setObjectName("PrimaryButton")
        self.browse_btn.setFixedWidth(160)
        
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        layout.addWidget(self.browse_btn, alignment=Qt.AlignCenter)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and Path(urls[0].toLocalFile()).is_dir():
                self.setStyleSheet("border: 2px dashed #00adb5; background-color: #1e2e30;")
                event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            folder_path = urls[0].toLocalFile()
            if Path(folder_path).is_dir():
                self.folder_dropped.emit(folder_path)


class ScanView(QWidget):
    """
    View managing library scanning, folder drag/drop, and song table representation.
    """
    scan_triggered = Signal(str)  # Emits target path string when scanning starts
    
    def __init__(self):
        super().__init__()
        self.songs_list: list[Song] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        header_lbl = QLabel("Scan Library")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # Drag and Drop Area
        self.drop_area = DropArea()
        self.drop_area.browse_btn.clicked.connect(self.browse_folder)
        self.drop_area.folder_dropped.connect(self.on_folder_selected)
        layout.addWidget(self.drop_area)

        # Selected Folder Row
        folder_row = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setStyleSheet("color: #b3b3b3; font-style: italic;")
        folder_row.addWidget(self.folder_label)
        
        self.scan_btn = QPushButton("Scan Folder")
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self.trigger_scan)
        folder_row.addWidget(self.scan_btn)
        layout.addLayout(folder_row)

        # List Header / Filters
        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter scanned songs by title, artist, or file path...")
        self.search_input.textChanged.connect(self.filter_table)
        filter_row.addWidget(self.search_input)
        
        self.count_label = QLabel("0 songs found")
        self.count_label.setStyleSheet("color: #00adb5; font-weight: bold;")
        filter_row.addWidget(self.count_label)
        layout.addLayout(filter_row)

        # Songs Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Filename", "Title", "Artist", "Size", "Cleaned Metadata"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

    def browse_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Music Library Folder")
        if dir_path:
            self.on_folder_selected(dir_path)

    def on_folder_selected(self, path: str):
        self.selected_path = path
        self.folder_label.setText(f"Selected: {path}")
        self.folder_label.setStyleSheet("color: #ffffff; font-weight: 600;")
        self.scan_btn.setEnabled(True)

    def trigger_scan(self):
        if hasattr(self, "selected_path") and self.selected_path:
            self.scan_btn.setEnabled(False)
            self.scan_btn.setText("Scanning...")
            self.scan_triggered.emit(self.selected_path)

    def populate_songs(self, songs: list[Song]):
        """Populates the scan table with Song records."""
        self.songs_list = songs
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan Folder")
        self.count_label.setText(f"{len(songs)} songs found")
        
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(songs))
        
        for i, song in enumerate(songs):
            # Filename
            self.table.setItem(i, 0, QTableWidgetItem(song.path.name))
            # Title
            self.table.setItem(i, 1, QTableWidgetItem(song.title))
            # Artist
            self.table.setItem(i, 2, QTableWidgetItem(song.artist))
            # Size
            size_mb = song.size_bytes / (1024 * 1024)
            size_item = QTableWidgetItem(f"{size_mb:.2f} MB")
            size_item.setData(Qt.UserRole, song.size_bytes)
            self.table.setItem(i, 3, size_item)
            # Cleaned Status
            cleaned_str = "Yes" if song.is_metadata_cleaned else "No"
            cleaned_item = QTableWidgetItem(cleaned_str)
            if song.is_metadata_cleaned:
                cleaned_item.setForeground(Qt.yellow)
            self.table.setItem(i, 4, cleaned_item)
            
        self.table.setSortingEnabled(True)

    def filter_table(self):
        """Filters table rows dynamically based on user search term."""
        search_term = self.search_input.text().strip().lower()
        visible_count = 0
        
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and search_term in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
            if match:
                visible_count += 1
                
        self.count_label.setText(f"Showing {visible_count} of {len(self.songs_list)} songs")
