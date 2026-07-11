from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QProgressBar, QGridLayout
from typing import List, Dict

class DashboardView(QWidget):
    """
    Dashboard showing high-level stats of the music library:
    Total songs, duplicates, missing files, folder distribution, and progress.
    Supports dynamic categories updates based on SQLite database states.
    """
    def __init__(self):
        super().__init__()
        self.folder_bars: Dict[str, tuple[QProgressBar, QLabel]] = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header Title
        header_lbl = QLabel("Library Dashboard")
        header_lbl.setObjectName("SectionHeader")
        layout.addWidget(header_lbl)

        # 1. Grid of KPI Cards
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        self.card_total, self.val_total = self._create_kpi_card("TOTAL SONGS", "0", "#00adb5")
        self.card_duplicates, self.val_duplicates = self._create_kpi_card("DUPLICATES DETECTED", "0", "#ffc107")
        self.card_missing, self.val_missing = self._create_kpi_card("MISSING METADATA", "0", "#ff4b2b")
        self.card_progress, self.val_progress = self._create_kpi_card("SUCCESS RATE", "0%", "#28a745")

        grid_layout.addWidget(self.card_total, 0, 0)
        grid_layout.addWidget(self.card_duplicates, 0, 1)
        grid_layout.addWidget(self.card_missing, 1, 0)
        grid_layout.addWidget(self.card_progress, 1, 1)
        
        layout.addLayout(grid_layout)

        # 2. Folder Distribution Section
        dist_lbl = QLabel("Folder Distribution")
        dist_lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #ffffff; margin-top: 15px;")
        layout.addWidget(dist_lbl)

        # Container for distribution bars
        self.dist_container = QFrame()
        self.dist_container.setObjectName("CardFrame")
        self.dist_layout = QVBoxLayout(self.dist_container)
        self.dist_layout.setSpacing(12)
        
        layout.addWidget(self.dist_container)
        layout.addStretch()

    def _create_kpi_card(self, title: str, value: str, color_hex: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("CardFrame")
        card.setMinimumHeight(110)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #888888; text-transform: uppercase;")
        
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {color_hex};")
        value_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        
        return card, value_lbl

    def update_stats(self, total: int, duplicates: int, missing: int, success_rate: float, distribution: dict[str, int]):
        """Updates the dashboard metrics and dynamically adjusts distribution progress bars."""
        self.val_total.setText(str(total))
        self.val_duplicates.setText(str(duplicates))
        self.val_missing.setText(str(missing))
        self.val_progress.setText(f"{success_rate:.1f}%" if success_rate > 0 else "0%")

        # Rebuild progress bars if categories list changed
        current_folders = sorted(list(distribution.keys()))
        existing_folders = sorted(list(self.folder_bars.keys()))

        if current_folders != existing_folders:
            # Clear layout elements
            while self.dist_layout.count():
                item = self.dist_layout.takeAt(0)
                sub_layout = item.layout()
                if sub_layout:
                    while sub_layout.count():
                        sub_item = sub_layout.takeAt(0)
                        widget = sub_item.widget()
                        if widget:
                            widget.deleteLater()
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            
            self.folder_bars.clear()
            
            # Rebuild widgets
            for folder in current_folders:
                folder_row = QHBoxLayout()
                
                # Label
                lbl = QLabel(f"{folder}:")
                lbl.setFixedWidth(100)
                lbl.setStyleSheet("font-weight: 600; color: #b3b3b3; background: transparent;")
                
                # Progress bar
                bar = QProgressBar()
                bar.setRange(0, 100)
                bar.setValue(0)
                bar.setFixedHeight(12)
                bar.setTextVisible(False)
                
                # Count label
                cnt_lbl = QLabel("0 songs (0%)")
                cnt_lbl.setFixedWidth(120)
                cnt_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                cnt_lbl.setStyleSheet("color: #e0e0e0; background: transparent;")
                
                folder_row.addWidget(lbl)
                folder_row.addWidget(bar)
                folder_row.addWidget(cnt_lbl)
                
                self.dist_layout.addLayout(folder_row)
                self.folder_bars[folder] = (bar, cnt_lbl)

        # Update distribution bar values
        for folder, (bar, label) in self.folder_bars.items():
            count = distribution.get(folder, 0)
            pct = (count / total * 100) if total > 0 else 0
            bar.setValue(int(pct))
            label.setText(f"{count} songs ({pct:.1f}%)")
