from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QPushButton, QLabel
from musicsort.core.logger import set_console_callback

class ConsoleLogSignal(QObject):
    log_emitted = Signal(str)

class ConsoleView(QWidget):
    """
    Console tab displaying live application logs.
    Includes log filtering, search capabilities, and clearing logs.
    """
    def __init__(self):
        super().__init__()
        self.signal_handler = ConsoleLogSignal()
        self.signal_handler.log_emitted.connect(self.append_log)
        set_console_callback(self.signal_handler.log_emitted.emit)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header controls
        ctrl_layout = QHBoxLayout()
        
        search_lbl = QLabel("Filter logs:")
        search_lbl.setStyleSheet("color: #b3b3b3;")
        ctrl_layout.addWidget(search_lbl)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search terms...")
        self.search_input.textChanged.connect(self.filter_logs)
        ctrl_layout.addWidget(self.search_input)
        
        clear_btn = QPushButton("Clear Console")
        clear_btn.clicked.connect(self.clear_console)
        ctrl_layout.addWidget(clear_btn)
        
        layout.addLayout(ctrl_layout)

        # Main Log Output (green-on-black terminal vibe)
        self.console_output = QPlainTextEdit()
        self.console_output.setObjectName("ConsoleOutput")
        self.console_output.setReadOnly(True)
        self.console_output.setMaximumBlockCount(2000) # prevent memory issues
        layout.addWidget(self.console_output)

        # Storage for all logs to support filtering
        self.all_logs = []

    @Slot(str)
    def append_log(self, text: str):
        self.all_logs.append(text)
        if len(self.all_logs) > 2000:
            self.all_logs.pop(0)
            
        search_text = self.search_input.text().strip().lower()
        if not search_text or search_text in text.lower():
            self.console_output.appendPlainText(text)

    def filter_logs(self):
        search_text = self.search_input.text().strip().lower()
        self.console_output.clear()
        
        filtered = [log for log in self.all_logs if not search_text or search_text in log.lower()]
        for log in filtered:
            self.console_output.appendPlainText(log)

    def clear_console(self):
        self.all_logs.clear()
        self.console_output.clear()
