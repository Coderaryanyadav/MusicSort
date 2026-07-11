#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to python path to resolve local imports cleanly
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from musicsort.app.main import run_app

if __name__ == "__main__":
    run_app()
