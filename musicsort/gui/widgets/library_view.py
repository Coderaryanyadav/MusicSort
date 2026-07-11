from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, QComboBox, 
                             QHeaderView, QDialog, QFormLayout, QCheckBox, QMessageBox,
                             QSlider, QMenu)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from musicsort.database.db_manager import DBManager
from typing import Optional, List, Dict

class TagEditDialog(QDialog):
    """Dialog for manual editing of song tags, rating, and classification."""
    def __init__(self, song_data: dict, categories: List[str], parent=None):
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
    Includes right-click context actions and a built-in media audio player.
    """
    song_updated = Signal(str, dict)  # Emitted when a song is updated (song_id, field_values)

    def __init__(self, db_manager: Optional[DBManager] = None):
        super().__init__()
        self.db = db_manager if db_manager else DBManager()
        self.songs_list: List[Dict[str, Any]] = []
        
        # Audio Player Backend
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Connect player signals
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        
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
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.doubleClicked.connect(self.on_row_double_clicked)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.table)

        # ==========================================
        # Dynamic Interactive Audio Mini-Player
        # ==========================================
        self.player_panel = QWidget()
        self.player_panel.setObjectName("CardFrame")
        self.player_panel.setStyleSheet("""
            QWidget#CardFrame {
                background-color: #1e1e1e;
                border: 1px solid #2d2d2d;
                border-radius: 12px;
            }
        """)
        player_layout = QVBoxLayout(self.player_panel)
        player_layout.setContentsMargins(15, 12, 15, 12)
        player_layout.setSpacing(8)

        # Row 1: Track Details and Control Buttons
        top_player_row = QHBoxLayout()
        self.player_track_lbl = QLabel("Select a song to play")
        self.player_track_lbl.setStyleSheet("font-weight: 600; color: #00adb5; font-size: 13px;")
        top_player_row.addWidget(self.player_track_lbl, stretch=1)

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setFixedWidth(80)
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self.toggle_playback)
        top_player_row.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_playback)
        top_player_row.addWidget(self.stop_btn)

        player_layout.addLayout(top_player_row)

        # Row 2: Seeking Slider & Time label & Volume controller
        bottom_player_row = QHBoxLayout()
        
        self.player_time_lbl = QLabel("00:00 / 00:00")
        self.player_time_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        bottom_player_row.addWidget(self.player_time_lbl)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.setValue(0)
        self.seek_slider.sliderMoved.connect(self.on_seek_moved)
        bottom_player_row.addWidget(self.seek_slider, stretch=1)

        self.vol_lbl = QLabel("Vol: 70%")
        self.vol_lbl.setStyleSheet("color: #888888; font-size: 11px;")
        bottom_player_row.addWidget(self.vol_lbl)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(70)
        self.vol_slider.valueChanged.connect(self.on_volume_changed)
        self.audio_output.setVolume(0.7)  # Match default slider value
        bottom_player_row.addWidget(self.vol_slider)

        player_layout.addLayout(bottom_player_row)
        layout.addWidget(self.player_panel)

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

    def on_selection_changed(self):
        """Prepares selected song details for the audio player."""
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return
        row = selected_ranges[0].topRow()
        if row >= len(self.songs_list):
            return
            
        song_data = self.songs_list[row]
        self.selected_song_path = song_data.get("current_path")
        self.player_track_lbl.setText(f"Ready: {song_data.get('artist')} - {song_data.get('title')}")
        self.play_btn.setEnabled(True)

    def show_context_menu(self, pos):
        """Displays right-click context actions on table rows."""
        item = self.table.itemAt(pos)
        if not item:
            return
            
        row = item.row()
        menu = QMenu(self)
        
        play_action = menu.addAction("Play Song")
        edit_action = menu.addAction("Edit Details")
        
        action = menu.exec(self.table.mapToGlobal(pos))
        if action == play_action:
            self.play_song_at_row(row)
        elif action == edit_action:
            self.edit_song_at_row(row)

    def play_song_at_row(self, row: int):
        if row >= len(self.songs_list):
            return
        song_data = self.songs_list[row]
        path_str = song_data.get("current_path")
        
        if path_str:
            self.player_track_lbl.setText(f"Playing: {song_data.get('artist')} - {song_data.get('title')}")
            self.player.setSource(QUrl.fromLocalFile(path_str))
            self.player.play()
            self.play_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)

    def edit_song_at_row(self, row: int):
        if row >= len(self.songs_list):
            return
        song_data = self.songs_list[row]
        cats = self.db.get_categories()
        
        dialog = TagEditDialog(song_data, cats, self)
        if dialog.exec() == QDialog.Accepted:
            song_id = song_data["id"]
            saved = dialog.saved_data
            self.song_updated.emit(song_id, saved)

    def on_row_double_clicked(self):
        selected_ranges = self.table.selectedRanges()
        if not selected_ranges:
            return
        row = selected_ranges[0].topRow()
        self.edit_song_at_row(row)

    # ==========================================
    # Audio Player Event Slots
    # ==========================================
    def toggle_playback(self):
        state = self.player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if hasattr(self, "selected_song_path") and self.selected_song_path:
                # If player has no source or source is different, load it
                if self.player.source().toLocalFile() != self.selected_song_path:
                    self.player.setSource(QUrl.fromLocalFile(self.selected_song_path))
                self.player.play()
                self.stop_btn.setEnabled(True)

    def stop_playback(self):
        self.player.stop()
        self.stop_btn.setEnabled(False)

    def on_volume_changed(self, value: int):
        self.audio_output.setVolume(value / 100.0)
        self.vol_lbl.setText(f"Vol: {value}%")

    def on_seek_moved(self, value: int):
        self.player.setPosition(value)

    def on_position_changed(self, position: int):
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(position)
        self.update_time_label(position, self.player.duration())

    def on_duration_changed(self, duration: int):
        self.seek_slider.setRange(0, duration)
        self.update_time_label(self.player.position(), duration)

    def on_playback_state_changed(self, state: QMediaPlayer.PlaybackState):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸ Pause")
        else:
            self.play_btn.setText("▶ Play")

    def update_time_label(self, position: int, duration: int):
        pos_sec = position // 1000
        dur_sec = duration // 1000
        
        pos_min = pos_sec // 60
        pos_sec_rem = pos_sec % 60
        
        dur_min = dur_sec // 60
        dur_sec_rem = dur_sec % 60
        
        self.player_time_lbl.setText(
            f"{pos_min:02d}:{pos_sec_rem:02d} / {dur_min:02d}:{dur_sec_rem:02d}"
        )
