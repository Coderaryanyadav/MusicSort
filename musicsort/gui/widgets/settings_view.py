from pathlib import Path
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QComboBox, QFrame, QFileDialog, QMessageBox, QListWidget)
from musicsort.core.config import ALLOWED_FOLDERS, DEFAULT_BACKUP_DIR

class SettingsView(QWidget):
    """
    View managing settings like Target Library folder,
    Backup directories, default conflict resolution modes, and allowed folders.
    """
    settings_saved = Signal(dict) # Emits dict of new settings

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        header_lbl = QLabel("App Settings")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # 1. Paths settings card
        paths_card = QFrame()
        paths_card.setObjectName("CardFrame")
        paths_layout = QVBoxLayout(paths_card)
        paths_layout.setSpacing(12)
        
        lbl_paths = QLabel("System Paths")
        lbl_paths.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        paths_layout.addWidget(lbl_paths)

        # Target directory row
        target_row = QHBoxLayout()
        target_lbl = QLabel("Default Target:")
        target_lbl.setFixedWidth(120)
        target_row.addWidget(target_lbl)
        
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Select default library folder...")
        target_row.addWidget(self.target_input)
        
        target_btn = QPushButton("Browse")
        target_btn.clicked.connect(self.browse_target)
        target_row.addWidget(target_btn)
        paths_layout.addLayout(target_row)

        # Backup directory row
        backup_row = QHBoxLayout()
        backup_lbl = QLabel("Backup Storage:")
        backup_lbl.setFixedWidth(120)
        backup_row.addWidget(backup_lbl)
        
        self.backup_input = QLineEdit()
        self.backup_input.setText(str(DEFAULT_BACKUP_DIR))
        backup_row.addWidget(self.backup_input)
        
        backup_btn = QPushButton("Browse")
        backup_btn.clicked.connect(self.browse_backup)
        backup_row.addWidget(backup_btn)
        paths_layout.addLayout(backup_row)

        layout.addWidget(paths_card)

        # 2. Defaults Settings Card
        defaults_card = QFrame()
        defaults_card.setObjectName("CardFrame")
        def_layout = QVBoxLayout(defaults_card)
        def_layout.setSpacing(12)
        
        lbl_def = QLabel("Default Behaviors")
        lbl_def.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        def_layout.addWidget(lbl_def)

        # Conflict mode row
        conflict_row = QHBoxLayout()
        conflict_lbl = QLabel("Conflict Mode:")
        conflict_lbl.setFixedWidth(120)
        conflict_row.addWidget(conflict_lbl)
        
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItems(["Rename", "Skip", "Replace"])
        conflict_row.addWidget(self.conflict_combo)
        conflict_row.addStretch()
        def_layout.addLayout(conflict_row)

        layout.addWidget(defaults_card)

        # 3. Allowed Folders display
        folders_card = QFrame()
        folders_card.setObjectName("CardFrame")
        fol_layout = QVBoxLayout(folders_card)
        
        lbl_fol = QLabel("Allowed Target Folders (Fixed)")
        lbl_fol.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        fol_layout.addWidget(lbl_fol)
        
        fol_desc = QLabel("Each song must belong to exactly one of these folders. These folders will be auto-created in your library root:")
        fol_desc.setStyleSheet("color: #b3b3b3; font-style: italic;")
        fol_layout.addWidget(fol_desc)
        
        self.folders_list = QListWidget()
        self.folders_list.addItems(ALLOWED_FOLDERS)
        self.folders_list.setFixedHeight(120)
        fol_layout.addWidget(self.folders_list)
        
        layout.addWidget(folders_card)

        # Save Button Row
        save_row = QHBoxLayout()
        save_row.addStretch()
        
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.save_settings)
        save_row.addWidget(save_btn)
        
        layout.addLayout(save_row)
        layout.addStretch()

    def browse_target(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Default Target Folder")
        if dir_path:
            self.target_input.setText(dir_path)

    def browse_backup(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Backup Storage Folder")
        if dir_path:
            self.backup_input.setText(dir_path)

    def save_settings(self):
        target = self.target_input.text().strip()
        backup = self.backup_input.text().strip()
        conflict = self.conflict_combo.currentText()
        
        if not target:
            QMessageBox.warning(self, "Validation Error", "Default Target folder cannot be empty!")
            return
            
        settings = {
            "default_target_dir": target,
            "backup_dir": backup,
            "default_conflict_mode": conflict
        }
        self.settings_saved.emit(settings)
        QMessageBox.information(self, "Success", "Settings saved successfully.")

    def set_settings(self, target_dir: str, backup_dir: str, conflict_mode: str):
        self.target_input.setText(target_dir)
        self.backup_input.setText(backup_dir)
        self.conflict_combo.setCurrentText(conflict_mode)
