# MusicSort 🎵

MusicSort is a production-ready, fully offline desktop application designed for macOS (Apple Silicon), Windows, and Linux. Built with **Python 3.13+** and **PySide6 (Qt6)**, it follows clean architecture principles to automatically scan, analyze, validate, classify, and organize local music libraries safely.

---

## Key Features

- **100% Offline & Private:** No internet connection required, no cloud services, and zero telemetry collection.
- **SQLite Single Source of Truth:** Relies on a robust SQLite database index rather than mutable filesystems or CSV caches.
- **Dynamic Smart Classification:** Learns from historical choices (using local Artist/Genre frequency analysis) and dynamically suggests category destinations.
- **Multi-pass CSV Validator:** Validates CSV mappings checking for row duplications, missing files, folder checks, and output path collisions.
- **Dry Run & Preview Mode:** Colors matching conflicts (Rename / Skip / Replace / Merge) in preview tables prior to execution.
- **Fail-safe Backup & Restore:** Automatically creates session restoration points before modifying any filesystem paths. Supports one-click rollback.
- **High-Performance Multi-threading:** Heavy scan, sorting, and duplicate checks run on background worker threads (`QThread`) keeping the GUI responsive and stable for 100,000+ tracks.
- **Comprehensive Duplicate Detector:** Groups files based on SHA256 hashes, metadata tags, durations, or filename similarities, offering quality/newness comparison metrics.

---

## Directory Structure

```
musicsort/
├── app/
│   ├── controller.py      # Main application state coordinator
│   └── main.py            # QApplication initialization
├── core/
│   ├── config.py          # Settings and paths manager
│   └── logger.py          # Log channels redirector
├── database/
│   └── db_manager.py      # SQLite connection pool & queries
├── gui/
│   ├── main_window.py     # macOS design sidebar navigation layout
│   ├── style.py           # Dark & Light stylesheet switchers
│   └── widgets/           # Sub-page layout UI components
├── models/
│   └── domain.py          # Dataclasses (Song, DuplicateGroup, etc.)
├── services/
│   ├── backup_service.py  # Session restore points copy engine
│   ├── classifier.py      # Local frequency prediction service
│   ├── csv_validator.py   # Multi-pass row mapping inspector
│   ├── move_engine.py     # Preview generator & conflict solver
│   └── report_generator.py# Writes report.txt and organization_history.json
├── utils/
│   ├── file_hashing.py    # Chunk-based SHA256 calculator
│   └── filename_cleaner.py# Middle-track and collab reformat cleaner
├── workers/
│   ├── duplicate_worker.py# Threaded duplicates checker
│   ├── organize_worker.py # Threaded file moves runner
│   └── scan_worker.py     # Threaded Mutagen scanner
├── tests/                 # Unit and integration test suite
│   ├── database_test.py
│   └── filename_cleaner_test.py
├── run.py                 # Application root entry point
└── requirements.txt       # Dependencies
```

---

## Installation & Setup

### Prerequisites
- **macOS (Apple Silicon)** or modern Windows/Linux.
- **Python 3.13+** installed.

### Step 1: Clone and Enter Directory
```bash
git clone https://github.com/your-username/MusicSort.git
cd MusicSort
```

### Step 2: Establish Virtual Environment & Install Dependencies
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip and install libraries
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Run Unit Tests
Verify the installation by running the test suite:
```bash
python3 -m unittest discover -s musicsort/tests -p "*_test.py"
```

### Step 4: Run Application
```bash
python3 run.py
```

---

## Packaging Installer (PyInstaller)

To build a standalone macOS application bundle:

1. Install PyInstaller in your virtual environment:
   ```bash
   pip install pyinstaller
   ```

2. Compile application:
   ```bash
   pyinstaller --windowed \
               --name="MusicSort" \
               --clean \
               --noconfirm \
               run.py
   ```

This will output a standalone `MusicSort.app` bundle inside the `dist/` directory, optimized for Apple Silicon macOS architectures.
