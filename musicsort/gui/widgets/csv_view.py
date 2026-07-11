import os
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView, QFrame)
from musicsort.models.domain import ValidationIssue

class CSVView(QWidget):
    """
    View managing CSV selection, validation triggering, and mapping logs/issues.
    """
    csv_selected = Signal(str)  # Emits selected CSV path
    validate_triggered = Signal(str)  # Emits selected CSV path when validate button is clicked

    def __init__(self):
        super().__init__()
        self.issue_list: list[ValidationIssue] = []
        self.report_path: Optional[Path] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Title
        header_lbl = QLabel("CSV Manager & Validator")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # CSV Selector Card
        selector_card = QFrame()
        selector_card.setObjectName("CardFrame")
        sel_layout = QVBoxLayout(selector_card)
        sel_layout.setSpacing(10)

        lbl = QLabel("Upload a CSV file mapping your library structure:")
        lbl.setStyleSheet("color: #b3b3b3;")
        sel_layout.addWidget(lbl)

        file_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select CSV file path...")
        self.path_input.setReadOnly(True)
        file_row.addWidget(self.path_input)

        browse_btn = QPushButton("Browse CSV")
        browse_btn.clicked.connect(self.browse_csv)
        file_row.addWidget(browse_btn)
        
        self.validate_btn = QPushButton("Validate CSV")
        self.validate_btn.setObjectName("PrimaryButton")
        self.validate_btn.setEnabled(False)
        self.validate_btn.clicked.connect(self.trigger_validation)
        file_row.addWidget(self.validate_btn)
        
        sel_layout.addLayout(file_row)
        layout.addWidget(selector_card)

        # Summary Row
        summary_row = QHBoxLayout()
        self.summary_lbl = QLabel("No CSV validated yet.")
        self.summary_lbl.setStyleSheet("font-weight: 600; color: #b3b3b3;")
        summary_row.addWidget(self.summary_lbl)
        
        self.open_report_btn = QPushButton("View Report File")
        self.open_report_btn.setEnabled(False)
        self.open_report_btn.clicked.connect(self.open_report)
        summary_row.addWidget(self.open_report_btn)
        
        layout.addLayout(summary_row)

        # Issues Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Severity", "Category", "Row", "Message", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def browse_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV Files (*.csv)")
        if file_path:
            self.path_input.setText(file_path)
            self.validate_btn.setEnabled(True)
            self.csv_selected.emit(file_path)

    def trigger_validation(self):
        path = self.path_input.text()
        if path:
            self.validate_btn.setEnabled(False)
            self.validate_btn.setText("Validating...")
            self.validate_triggered.emit(path)

    def populate_issues(self, issues: list[ValidationIssue], report_path: Path):
        """Populates the issues table with validation results."""
        self.issue_list = issues
        self.report_path = report_path
        
        self.validate_btn.setEnabled(True)
        self.validate_btn.setText("Validate CSV")
        self.open_report_btn.setEnabled(True)

        error_count = sum(1 for iss in issues if iss.severity == "error")
        warning_count = sum(1 for iss in issues if iss.severity == "warning")
        
        if error_count == 0:
            self.summary_lbl.setText(f"Validation Completed. 0 Errors, {warning_count} Warnings. Ready to Sort.")
            self.summary_lbl.setStyleSheet("font-weight: 600; color: #28a745;")
        else:
            self.summary_lbl.setText(f"Validation Failed! {error_count} Errors, {warning_count} Warnings. Fix errors before sorting.")
            self.summary_lbl.setStyleSheet("font-weight: 600; color: #ff4b2b;")

        self.table.setRowCount(len(issues))
        for i, issue in enumerate(issues):
            # Severity
            sev_item = QTableWidgetItem(issue.severity.upper())
            if issue.severity == "error":
                sev_item.setForeground(Qt.red)
            else:
                # Warning
                sev_item.setForeground(Qt.yellow)
            self.table.setItem(i, 0, sev_item)
            
            # Category
            self.table.setItem(i, 1, QTableWidgetItem(issue.type.upper()))
            # Row
            row_str = str(issue.row_index) if issue.row_index else "-"
            self.table.setItem(i, 2, QTableWidgetItem(row_str))
            # Message
            self.table.setItem(i, 3, QTableWidgetItem(issue.message))
            # Details
            self.table.setItem(i, 4, QTableWidgetItem(issue.details))

    def open_report(self):
        """Opens validation_report.txt in default text viewer."""
        if self.report_path and self.report_path.exists():
            import subprocess
            import sys
            try:
                if sys.platform == "darwin":
                    subprocess.call(["open", str(self.report_path)])
                elif sys.platform == "win32":
                    os.startfile(str(self.report_path))
                else:
                    subprocess.call(["xdg-open", str(self.report_path)])
            except Exception as e:
                # Fallback if opening failes
                pass
