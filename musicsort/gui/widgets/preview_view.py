from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView, QComboBox, QFrame)
from musicsort.models.domain import OperationPreview

class PreviewView(QWidget):
    """
    View displaying the previewed move/rename operations prior to execution.
    Allows changing destination library path and conflict resolution modes.
    """
    target_changed = Signal(str)  # Emits target path string
    execute_triggered = Signal(str)  # Emits selected conflict mode ("Rename", "Skip", "Replace")
    resume_triggered = Signal()  # Emits when user wants to resume an interrupted operation

    def __init__(self):
        super().__init__()
        self.previews_list: list[OperationPreview] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        header_lbl = QLabel("Preview Operations")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # Library Settings Card
        settings_card = QFrame()
        settings_card.setObjectName("CardFrame")
        set_layout = QVBoxLayout(settings_card)
        set_layout.setSpacing(10)

        # Row 1: Target Folder Selection
        path_row = QHBoxLayout()
        path_lbl = QLabel("Target Library Root:")
        path_lbl.setFixedWidth(130)
        path_row.addWidget(path_lbl)
        
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select destination music library root...")
        self.path_input.setReadOnly(True)
        path_row.addWidget(self.path_input)

        browse_btn = QPushButton("Browse Target")
        browse_btn.clicked.connect(self.browse_target)
        path_row.addWidget(browse_btn)
        set_layout.addLayout(path_row)

        # Row 2: Conflict Mode Selection
        conflict_row = QHBoxLayout()
        conflict_lbl = QLabel("On File Conflict:")
        conflict_lbl.setFixedWidth(130)
        conflict_row.addWidget(conflict_lbl)

        self.conflict_combo = QComboBox()
        self.conflict_combo.addItems(["Rename", "Skip", "Replace"])
        self.conflict_combo.currentTextChanged.connect(self.on_conflict_mode_changed)
        conflict_row.addWidget(self.conflict_combo)
        
        # Spacer
        conflict_row.addStretch()
        
        # Resume button (hidden by default)
        self.resume_btn = QPushButton("Resume Interrupted Sort")
        self.resume_btn.setStyleSheet("background-color: #2b2b2b; color: #ffc107; border-color: #ffc107;")
        self.resume_btn.setVisible(False)
        self.resume_btn.clicked.connect(self.resume_triggered.emit)
        conflict_row.addWidget(self.resume_btn)
        
        set_layout.addLayout(conflict_row)
        layout.addWidget(settings_card)

        # Previews Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Original Filename", "Target Subfolder", "Target Filename", "Operation"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Bottom Row: Execute Operations
        bottom_row = QHBoxLayout()
        self.stats_lbl = QLabel("0 operations pending")
        self.stats_lbl.setStyleSheet("font-weight: bold; color: #b3b3b3;")
        bottom_row.addWidget(self.stats_lbl)
        
        bottom_row.addStretch()
        
        self.run_btn = QPushButton("Confirm & Run Sort")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self.trigger_execution)
        bottom_row.addWidget(self.run_btn)
        layout.addLayout(bottom_row)

    def browse_target(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Target Library Root Folder")
        if dir_path:
            self.path_input.setText(dir_path)
            self.target_changed.emit(dir_path)

    def on_conflict_mode_changed(self, mode: str):
        # We can refresh preview list states on conflict mode toggle
        self.update_previews_list_conflicts(mode)

    def trigger_execution(self):
        mode = self.conflict_combo.currentText()
        self.execute_triggered.emit(mode)

    def populate_previews(self, previews: list[OperationPreview]):
        """Populates table with planned moves."""
        self.previews_list = previews
        self.stats_lbl.setText(f"{len(previews)} operations pending")
        
        # Enable run button if target path is set and there are files to organize
        has_target = bool(self.path_input.text())
        self.run_btn.setEnabled(has_target and len(previews) > 0)
        
        self.table.setRowCount(len(previews))
        for i, op in enumerate(previews):
            # Original Filename
            self.table.setItem(i, 0, QTableWidgetItem(op.original_path.name))
            
            # Target Subfolder
            subfolder = op.target_path.parent.name
            self.table.setItem(i, 1, QTableWidgetItem(subfolder))
            
            # Target Filename
            self.table.setItem(i, 2, QTableWidgetItem(op.target_path.name))
            
            # Operation Type
            self.table.setItem(i, 3, QTableWidgetItem(op.operation_type.upper()))

        self.update_previews_list_conflicts(self.conflict_combo.currentText())

    def update_previews_list_conflicts(self, mode: str):
        """Applies conflict color indicators to table columns based on mode."""
        for i, op in enumerate(self.previews_list):
            target_exists = op.target_path.exists() and op.target_path.resolve() != op.original_path.resolve()
            
            item_target = self.table.item(i, 2)
            if not item_target:
                continue
                
            if target_exists:
                if mode == "Rename":
                    item_target.setForeground(Qt.yellow)
                    item_target.setToolTip("Target file already exists. Will be renamed automatically.")
                elif mode == "Skip":
                    item_target.setForeground(Qt.darkYellow)
                    item_target.setToolTip("Target file already exists. Operation will be skipped.")
                elif mode == "Replace":
                    item_target.setForeground(Qt.red)
                    item_target.setToolTip("Target file already exists. Will be replaced/overwritten.")
            else:
                item_target.setForeground(Qt.white)
                item_target.setToolTip("")

    def show_resume_button(self, visible: bool):
        self.resume_btn.setVisible(visible)
