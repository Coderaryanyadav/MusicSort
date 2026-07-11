import logging
import sys
from pathlib import Path
from musicsort.core.config import DEFAULT_LOGS_DIR

# Global signals or callback for GUI console redirection
_console_callback = None

class CallbackHandler(logging.Handler):
    """Custom logging handler to redirect log entries to a callback (e.g. GUI console)."""
    def emit(self, record):
        try:
            msg = self.format(record)
            if _console_callback:
                _console_callback(msg)
        except Exception:
            self.handleError(record)

def setup_loggers():
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 1. Operations Logger
    op_logger = logging.getLogger("operations")
    op_logger.setLevel(logging.INFO)
    op_logger.propagate = False
    if not op_logger.handlers:
        op_file = logging.FileHandler(DEFAULT_LOGS_DIR / "operations.log", encoding="utf-8")
        op_file.setFormatter(log_format)
        op_logger.addHandler(op_file)
        
        # Add stdout stream
        stdout_h = logging.StreamHandler(sys.stdout)
        stdout_h.setFormatter(log_format)
        op_logger.addHandler(stdout_h)

        # Add Callback handler
        op_logger.addHandler(CallbackHandler())

    # 2. Validation Logger
    val_logger = logging.getLogger("validation")
    val_logger.setLevel(logging.INFO)
    val_logger.propagate = False
    if not val_logger.handlers:
        val_file = logging.FileHandler(DEFAULT_LOGS_DIR / "validation.log", encoding="utf-8")
        val_file.setFormatter(log_format)
        val_logger.addHandler(val_file)
        val_logger.addHandler(CallbackHandler())

    # 3. Errors Logger
    err_logger = logging.getLogger("errors")
    err_logger.setLevel(logging.ERROR)
    err_logger.propagate = False
    if not err_logger.handlers:
        err_file = logging.FileHandler(DEFAULT_LOGS_DIR / "errors.log", encoding="utf-8")
        err_file.setFormatter(log_format)
        err_logger.addHandler(err_file)
        
        # Errors also go to stderr
        stderr_h = logging.StreamHandler(sys.stderr)
        stderr_h.setFormatter(log_format)
        err_logger.addHandler(stderr_h)
        err_logger.addHandler(CallbackHandler())

    # 4. Root Logger (fallback)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        root_h = logging.StreamHandler(sys.stdout)
        root_h.setFormatter(log_format)
        root_logger.addHandler(root_h)

def get_operations_logger():
    return logging.getLogger("operations")

def get_validation_logger():
    return logging.getLogger("validation")

def get_errors_logger():
    return logging.getLogger("errors")

def set_console_callback(callback):
    """Register a callback function that accepts a string to display logs in GUI."""
    global _console_callback
    _console_callback = callback
