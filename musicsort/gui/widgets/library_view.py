from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, QComboBox, 
                             QHeaderView, QDialog, QFormLayout, QCheckBox, QMessageBox)
from typing import Optional
from musicsort.database.db_manager import DBManager

class TagEditDialog(QDialog):
    """Dialog for manual editing of song tags, rating, and classification."""
    def __init__(self, song_data: dict, categories: list[str], parent=None):
        super().__init__(parent)
        self.song_data = song_data
        self.categories = categories
        self.saved_data = {}
        self.setWindowTitle("Edit Song Details")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.title_input = QLineEdit(self.song_data.get("title", ""))
        self.artist_input = QLineEdit(self.song_data.get("artist", ""))
        self.album_input = QLineEdit(self.song_data.get("album", ""))
        self.genre_input = QLineEdit(self.song_data.get("genre", ""))
        
        self.folder_combo = QComboBox()
        self.folder_combo.addItems(self.categories)
        self.folder_combo.setCurrentText(self.song_data.get("folder_assignment", "Others"))

        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["0", "1", "2", "3", "4", "5"])
        self.rating_combo.setCurrentText(str(self.song_data.get("rating", 0)))

        self.fav_check = QCheckBox("Add to Favorites")
        self.fav_check.setChecked(bool(self.song_data.get("favorite", 0)))

        self.notes_input = QLineEdit(self.song_data.get("user_notes", ""))

        layout.addRow("Song Title:", self.title_input)
        layout.addRow("Artist:", self.artist_input)
        layout.addRow("Album:", self.album_input)
        layout.addRow("Genre:", self.genre_input)
        layout.addRow("Category Folder:", self.folder_combo)
        layout.addRow("Rating (Stars):", self.rating_combo)
        layout.addRow("", self.fav_check)
        layout.addRow("User Notes:", self.notes_input)

        # Buttons row
        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addRow(btn_row)

    def save(self):
        self.saved_data = {
            "title": self.title_input.text().strip(),
            "artist": self.artist_input.text().strip(),
            "album": self.album_input.text().strip(),
            "genre": self.genre_input.text().strip(),
            "folder_assignment": self.folder_combo.currentText(),
            "rating": int(self.rating_combo.currentText()),
            "favorite": 1 if self.fav_check.isChecked() else 0,
            "user_notes": self.notes_input.text().strip()
        }
        self.accept()


class LibraryView(QWidget):
    """
    Library view displaying a list of all audio files registered in SQLite.
    Supports real-time search, dropdown metadata filters, and double-click tag edits.
    """
    song_updated = Signal()  # Emitted when a song is updated in the DB

    def __init__(self, db_manager: Optional[DBManager] = None):
        super().__init__()
        self.db = db_manager if db_manager else DBManager()
        self.songs_list = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        header_lbl = QLabel("Music Library")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # Search and Filters Panel
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search songs by title, artist, album...")
        self.search_input.textChanged.connect(self.load_library)
        filter_layout.addWidget(self.search_input)

        self.folder_filter = QComboBox()
        self.folder_filter.addItem("All Categories")
        self.folder_filter.currentTextChanged.connect(self.load_library)
        filter_layout.addWidget(self.folder_filter)

        self.fav_filter = QComboBox()
        self.fav_filter.addItems(["All Songs", "Favorites Only"])
        self.fav_filter.currentTextChanged.connect(self.load_library)
        filter_layout.addWidget(self.fav_filter)

        layout.addLayout(filter_layout)

        # Song List Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Title", "Artist", "Album", "Genre", "Category", "Rating", "Fav", "Original Path"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.on_row_double_clicked)
        layout.addWidget(self.table)

        # Statistics summary
        self.status_lbl = QLabel("0 songs in library")
        self.status_lbl.setStyleSheet("color: #b3b3b3; font-weight: bold;")
        layout.addWidget(self.status_lbl)

    def update_categories_filter(self):
        """Reloads folder filters based on the DB categories list."""
        self.folder_filter.blockSignals(True)
        self.folder_filter.clear()
        self.folder_filter.addItem("All Categories")
        self.folder_filter.addItems(self.db.get_categories())
        self.folder_filter.blockSignals(False)

    def load_library(self):
        """Loads and filters songs from database, displaying them in the table."""
        query = self.search_input.text().strip()
        
        filters = {}
        # Folder filter
        folder = self.folder_filter.currentText()
        if folder and folder != "All Categories":
            filters["folder"] = folder
            
        # Favorite filter
        fav = self.fav_filter.currentText()
        if fav == "Favorites Only":
            filters["favorite"] = True

        self.songs_list = self.db.search_songs(query, filters)
        self.status_lbl.setText(f"{len(self.songs_list)} songs listed")

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(self.songs_list))
        
        for i, s in enumerate(self.songs_list):
            self.table.setItem(i, 0, QTableWidgetItem(s.get("title", "")))
            self.table.setItem(i, 1, QTableWidgetItem(s.get("artist", "")))
            self.table.setItem(i, 2, QTableWidgetItem(s.get("album", "")))
            self.table.setItem(i, 3, QTableWidgetItem(s.get("genre", "")))
            self.table.setItem(i, 4, QTableWidgetItem(s.get("folder_assignment", "Others")))
            
            # Rating stars
            stars = "★" * s.get("rating", 0) + "☆" * (5 - s.get("rating", 0))
            self.table.setItem(i, 5, QTableWidgetItem(stars))
            
            # Favorite indicator
            fav_str = "❤" if s.get("favorite", 0) else "-"
            fav_item = QTableWidgetItem(fav_str)
            if s.get("favorite", 0):
                fav_item.setForeground(Qt.red)
            self.table.setItem(i, 6, fav_item)
            
            path_item = QTableWidgetItem(s.get("current_path", ""))
            path_item.setToolTip(s.get("current_path", ""))
            self.table.setItem(i, 7, path_item)
            
        self.table.setSortingEnabled(True)

    def on_row_double_clicked(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return
        row = selected_ranges[0].topRow()
        if row >= len(self.songs_list):
            return
            
        song_data = self.songs_list[row]
        cats = self.db.get_categories()
        
        dialog = TagEditDialog(song_data, cats, self)
        if dialog.exec() == QDialog.Accepted:
            # Update database
            song_id = song_data["id"]
            saved = dialog.saved_data
            
            for field, val in saved.items():
                self.db.update_song_field(song_id, field, val)
                
            self.load_library()
            self.song_updated.emit()
