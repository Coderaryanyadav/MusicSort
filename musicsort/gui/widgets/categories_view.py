from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QListWidget, QFrame, QMessageBox)
from typing import Optional
from musicsort.database.db_manager import DBManager

class CategoriesView(QWidget):
    """
    View managing dynamic folder categories list.
    Allows user to create new categories or delete existing ones.
    """
    categories_changed = Signal()  # Emitted when categories list changes

    def __init__(self, db_manager: Optional[DBManager] = None):
        super().__init__()
        self.db = db_manager if db_manager else DBManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        header_lbl = QLabel("Manage Categories")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # Main horizontal layout splits categories list and options
        main_split = QHBoxLayout()
        
        # Left Panel: List
        left_frame = QFrame()
        left_frame.setObjectName("CardFrame")
        left_layout = QVBoxLayout(left_frame)
        
        lbl_list = QLabel("Active Categories:")
        lbl_list.setStyleSheet("font-weight: bold; color: #ffffff;")
        left_layout.addWidget(lbl_list)
        
        self.list_widget = QListWidget()
        left_layout.addWidget(self.list_widget)
        main_split.addWidget(left_frame, stretch=2)

        # Right Panel: Actions
        right_frame = QFrame()
        right_frame.setObjectName("CardFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(15)
        
        lbl_actions = QLabel("Add New Category:")
        lbl_actions.setStyleSheet("font-weight: bold; color: #ffffff;")
        right_layout.addWidget(lbl_actions)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter category name (e.g. Workout, LoFi)...")
        right_layout.addWidget(self.name_input)

        add_btn = QPushButton("Create Category")
        add_btn.setObjectName("PrimaryButton")
        add_btn.clicked.connect(self.create_category)
        right_layout.addWidget(add_btn)
        
        right_layout.addSpacing(20)

        lbl_del = QLabel("Delete Category:")
        lbl_del.setStyleSheet("font-weight: bold; color: #ffffff;")
        right_layout.addWidget(lbl_del)
        
        del_desc = QLabel("Deleting a category will revert its organized songs to 'Others'.")
        del_desc.setWordWrap(True)
        del_desc.setStyleSheet("color: #888888; font-style: italic;")
        right_layout.addWidget(del_desc)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.setObjectName("DangerButton")
        self.delete_btn.clicked.connect(self.delete_category)
        right_layout.addWidget(self.delete_btn)
        
        right_layout.addStretch()
        main_split.addWidget(right_frame, stretch=1)

        layout.addLayout(main_split)
        self.load_categories()

    def load_categories(self):
        self.list_widget.clear()
        cats = self.db.get_categories()
        self.list_widget.addItems(cats)

    def create_category(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Input Error", "Category name cannot be empty!")
            return
            
        # Clean folder name check to prevent folder system issues
        # Remove characters not allowed in directories
        clean_name = "".join(c for c in name if c.isalnum() or c in " _-")
        if not clean_name:
            QMessageBox.warning(self, "Input Error", "Invalid name characters!")
            return
            
        success = self.db.add_category(clean_name)
        if success:
            self.name_input.clear()
            self.load_categories()
            self.categories_changed.emit()
            QMessageBox.information(self, "Success", f"Category '{clean_name}' created successfully.")
        else:
            QMessageBox.warning(self, "Failure", "Category already exists or failed to save.")

    def delete_category(self):
        selected = self.list_widget.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select a category to delete.")
            return
            
        cat_name = selected[0].text()
        if cat_name == "Others":
            QMessageBox.warning(self, "Action Prohibited", "The 'Others' category is a core system default and cannot be deleted.")
            return
            
        confirm = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the category '{cat_name}'?\n\nAny songs classified under this folder will revert to 'Others'.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            success = self.db.delete_category(cat_name)
            if success:
                # Update database for songs matching this folder assignment
                songs = self.db.get_all_songs()
                for s in songs:
                    if s.get("folder_assignment") == cat_name:
                        self.db.update_song_field(s["id"], "folder_assignment", "Others")
                        
                self.load_categories()
                self.categories_changed.emit()
                QMessageBox.information(self, "Deleted", f"Category '{cat_name}' deleted.")
            else:
                QMessageBox.warning(self, "Failure", "Failed to delete category.")
