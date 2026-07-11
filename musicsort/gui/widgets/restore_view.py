from datetime import datetime
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox)
from musicsort.models.domain import BackupIndex

class RestoreView(QWidget):
    """
    View managing backup inspection, file restoration (undo operations),
    and cleanup of backup directories.
    """
    restore_triggered = Signal(str)  # Emits backup folder path to restore
    delete_triggered = Signal(str)   # Emits backup folder path to delete
    refresh_triggered = Signal()     # Emits to refresh list of backups

    def __init__(self):
        super().__init__()
        self.backups_list: list[BackupIndex] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title Row
        header_row = QHBoxLayout()
        header_lbl = QLabel("Backup History & Undo")
        header_lbl.setObjectName("SectionHeader")
        header_row.addWidget(header_lbl)
        
        header_row.addStretch()
        
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.refresh_triggered.emit)
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        # Info card
        info_card = QFrame()
        info_card.setObjectName("CardFrame")
        info_layout = QVBoxLayout(info_card)
        info_lbl = QLabel(
            "Every time you run an organization process, MusicSort automatically creates a backup of the original files.\n"
            "If you make a mistake or want to undo the moves, you can restore files back to their exact original paths here."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #b3b3b3; line-height: 18px;")
        info_layout.addWidget(info_lbl)
        layout.addWidget(info_card)

        # Backups Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Session Timestamp", "Backup Path", "File Count"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Actions Row
        action_row = QHBoxLayout()
        self.status_lbl = QLabel("0 backup sessions found")
        self.status_lbl.setStyleSheet("font-weight: bold; color: #b3b3b3;")
        action_row.addWidget(self.status_lbl)
        
        action_row.addStretch()

        self.delete_btn = QPushButton("Delete Session")
        self.delete_btn.setObjectName("DangerButton")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.trigger_delete)
        action_row.addWidget(self.delete_btn)

        self.restore_btn = QPushButton("Undo & Restore Files")
        self.restore_btn.setObjectName("PrimaryButton")
        self.restore_btn.setEnabled(False)
        self.restore_btn.clicked.connect(self.trigger_restore)
        action_row.addWidget(self.restore_btn)
        
        layout.addLayout(action_row)

        # Listen to selection changes to toggle buttons
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

    def populate_backups(self, backups: list[BackupIndex]):
        """Populates backups list in table."""
        self.backups_list = backups
        self.status_lbl.setText(f"{len(backups)} backup sessions found")
        
        self.table.setRowCount(len(backups))
        for i, b in enumerate(backups):
            # Parse timestamp to readable format
            # Format: backup_YYYYMMDD_HHMMSS
            ts_str = b.timestamp
            try:
                dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                readable_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                readable_ts = ts_str
                
            self.table.setItem(i, 0, QTableWidgetItem(readable_ts))
            self.table.setItem(i, 1, QTableWidgetItem(str(b.backup_dir)))
            self.table.setItem(i, 2, QTableWidgetItem(f"{len(b.entries)} files"))
            
        self.on_selection_changed()

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        has_selection = len(selected_rows) > 0
        self.restore_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

    def get_selected_backup_path(self) -> str:
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if row < len(self.backups_list):
                return str(self.backups_list[row].backup_dir)
        return ""

    def trigger_restore(self):
        path = self.get_selected_backup_path()
        if not path:
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Restore",
            "Are you sure you want to restore these files back to their original locations?\n\nThis will move the backup files back.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.restore_triggered.emit(path)

    def trigger_delete(self):
        path = self.get_selected_backup_path()
        if not path:
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Delete Session",
            "Are you sure you want to permanently delete this backup session from disk?\n\nThis will free up disk space but you will no longer be able to undo those operations.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.delete_triggered.emit(path)
            
