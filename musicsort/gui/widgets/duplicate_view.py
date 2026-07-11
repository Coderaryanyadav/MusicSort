import datetime
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QTreeWidget, QTreeWidgetItem, QTabWidget, QFrame, QMessageBox)
from musicsort.models.domain import DuplicateGroup, Song

class DuplicateTab(QWidget):
    """Sub-widget representing a single duplicate criteria (e.g. Hash, Size) inside a tab."""
    delete_triggered = Signal(list) # Emits list of Path objects to delete

    def __init__(self, criteria_label: str):
        super().__init__()
        self.criteria_label = criteria_label
        self.groups: list[DuplicateGroup] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header description
        self.desc_lbl = QLabel(f"Showing duplicate songs identified by {self.criteria_label}.")
        self.desc_lbl.setStyleSheet("color: #b3b3b3; font-style: italic;")
        layout.addWidget(self.desc_lbl)

        # Tree Widget for groups and files
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Filename / Path", "Details / Size", "Date Modified"])
        self.tree.setHeaderHidden(False)
        self.tree.setColumnWidth(0, 400)
        layout.addWidget(self.tree)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        self.stats_lbl = QLabel("0 groups detected")
        self.stats_lbl.setStyleSheet("font-weight: bold; color: #00adb5;")
        btn_row.addWidget(self.stats_lbl)
        
        btn_row.addStretch()

        self.select_extra_btn = QPushButton("Select Extra Copies")
        self.select_extra_btn.clicked.connect(self.select_extra_copies)
        btn_row.addWidget(self.select_extra_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setObjectName("DangerButton")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.trigger_delete)
        btn_row.addWidget(self.delete_btn)
        
        layout.addLayout(btn_row)
        self.tree.itemChanged.connect(self.on_item_changed)

    def populate_groups(self, groups: list[DuplicateGroup]):
        self.tree.blockSignals(True)
        self.groups = groups
        self.tree.clear()
        self.stats_lbl.setText(f"{len(groups)} duplicate groups found")
        
        if not groups:
            self.delete_btn.setEnabled(False)
            self.select_extra_btn.setEnabled(False)
            item = QTreeWidgetItem(self.tree)
            item.setText(0, "No duplicates found for this criteria.")
            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
            return

        self.delete_btn.setEnabled(True)
        self.select_extra_btn.setEnabled(True)

        for group in groups:
            # Create Parent Item representing the Group
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, f"Group: {group.id}")
            group_item.setText(1, f"{len(group.files)} copies matching")
            group_item.setFlags(group_item.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable)
            group_item.setCheckState(0, Qt.Unchecked)
            group_item.setExpanded(True)
            
            # Change background to make groups visually distinct
            for col in range(3):
                group_item.setBackground(col, Qt.darkGray)
                group_item.setForeground(col, Qt.white)
            
            for song in group.files:
                # Create Child Item representing the File
                child_item = QTreeWidgetItem(group_item)
                child_item.setText(0, song.path.name)
                child_item.setToolTip(0, str(song.path))
                
                size_mb = song.size_bytes / (1024 * 1024)
                child_item.setText(1, f"{size_mb:.2f} MB | {song.artist} - {song.title}")
                
                # Checkbox
                child_item.setFlags(child_item.flags() | Qt.ItemIsUserCheckable)
                child_item.setCheckState(0, Qt.Unchecked)
                child_item.setData(0, Qt.UserRole, song.path)
                
                # Try getting last modified date
                try:
                    mtime = song.path.stat().st_mtime
                    dt = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                    child_item.setText(2, dt)
                except Exception:
                    child_item.setText(2, "Unknown")

        self.tree.blockSignals(False)
        self.on_item_changed(None, 0)

    def on_item_changed(self, item: QTreeWidgetItem, column: int):
        # Enable/disable delete button based on whether anything is checked
        checked_files = self.get_checked_paths()
        self.delete_btn.setEnabled(len(checked_files) > 0)

    def get_checked_paths(self) -> list:
        checked = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                if file_item.checkState(0) == Qt.Checked:
                    path = file_item.data(0, Qt.UserRole)
                    if path:
                        checked.append(path)
        return checked

    def select_extra_copies(self):
        """Automatically select all but the first copy in each duplicate group."""
        self.tree.blockSignals(True)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                if j == 0:
                    # Keep the first copy
                    file_item.setCheckState(0, Qt.Unchecked)
                else:
                    # Mark other copies for deletion
                    file_item.setCheckState(0, Qt.Checked)
        self.tree.blockSignals(False)
        # Manually trigger checked change logic
        self.on_item_changed(None, 0)

    def trigger_delete(self):
        checked_paths = self.get_checked_paths()
        if not checked_paths:
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to permanently delete {len(checked_paths)} duplicate files from disk?\n\nThis action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.delete_triggered.emit(checked_paths)


class DuplicateView(QWidget):
    """
    Main widget housing tabs for various duplicate detection strategies.
    Coordinates re-running scan checks.
    """
    scan_triggered = Signal()  # Emits to ask Controller to re-run duplicate detection
    delete_triggered = Signal(list) # Emits list of Path objects to delete

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title Row
        header_row = QHBoxLayout()
        header_lbl = QLabel("Duplicate Manager")
        header_lbl.setObjectName("SectionHeader")
        header_row.addWidget(header_lbl)
        
        header_row.addStretch()
        
        self.rescan_btn = QPushButton("Scan Duplicates")
        self.rescan_btn.clicked.connect(self.scan_triggered.emit)
        header_row.addWidget(self.rescan_btn)
        layout.addLayout(header_row)

        # Tab layout for the 4 duplicate styles
        self.tabs = QTabWidget()
        
        self.tab_hash = DuplicateTab("SHA256 File Hashes")
        self.tab_hash.delete_triggered.connect(self.delete_triggered.emit)
        
        self.tab_metadata = DuplicateTab("Metadata (Artist + Title)")
        self.tab_metadata.delete_triggered.connect(self.delete_triggered.emit)
        
        self.tab_size = DuplicateTab("File Sizes")
        self.tab_size.delete_triggered.connect(self.delete_triggered.emit)
        
        self.tab_filename = DuplicateTab("Filenames")
        self.tab_filename.delete_triggered.connect(self.delete_triggered.emit)

        self.tabs.addTab(self.tab_hash, "By SHA256 Hash")
        self.tabs.addTab(self.tab_metadata, "By Artist & Title")
        self.tabs.addTab(self.tab_size, "By File Size")
        self.tabs.addTab(self.tab_filename, "By Filename")
        
        layout.addWidget(self.tabs)

    def populate_duplicates(self, hash_g: list, meta_g: list, size_g: list, name_g: list):
        """Dispatches duplicate groups to respective tab widgets."""
        self.tab_hash.populate_groups(hash_g)
        self.tab_metadata.populate_groups(meta_g)
        self.tab_size.populate_groups(size_g)
        self.tab_filename.populate_groups(name_g)
