import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Slot
from PySide6.QtWidgets import QMessageBox, QFileDialog

from musicsort.database.db_manager import DBManager
from musicsort.gui.main_window import MainWindow
from musicsort.core.config import config, APP_NAME, DEFAULT_BACKUP_DIR
from musicsort.workers import ScanWorker, OrganizeWorker, DuplicateWorker
from musicsort.services import SmartClassifier, BackupService, ReportGenerator
from musicsort.services.csv_validator import CSVValidator
from musicsort.services.move_engine import MoveEngine
from musicsort.models.domain import Song, OperationPreview, DuplicateGroup
from musicsort.core.logger import get_operations_logger, get_errors_logger, setup_loggers

class AppController(QObject):
    """
    Main Application Controller coordinating events between the GUI view layer,
    background threads, SQLite database transactions, and file systems.
    """
    def __init__(self, main_window: MainWindow):
        super().__init__()
        self.win = main_window
        
        # Setup Logger
        setup_loggers()
        self.op_logger = get_operations_logger()
        self.err_logger = get_errors_logger()
        
        # Setup Database & Services
        self.db = DBManager()
        self.classifier = SmartClassifier(self.db)
        self.backup_service = BackupService(self.db)
        self.csv_validator = CSVValidator()
        self.move_engine = MoveEngine()
        self.report_generator = ReportGenerator()

        # State Variables
        self.active_worker = None
        self.scan_root: Optional[Path] = None
        self.songs: List[Dict[str, Any]] = []
        self.previews: List[OperationPreview] = []
        
        # Connect UI Action Signals to Controller slots
        self.connect_signals()
        
        # Load startup configurations
        self.load_initial_settings()
        self.refresh_all_views()

    def connect_signals(self):
        # Scan page
        self.win.scan_view.scan_triggered.connect(self.start_scan)
        
        # Library page
        self.win.library_view.song_updated.connect(self.refresh_all_views)
        
        # Categories page
        self.win.categories_view.categories_changed.connect(self.on_categories_modified)
        
        # CSV page
        self.win.csv_view.validate_triggered.connect(self.start_csv_validation)
        
        # Preview page
        self.win.preview_view.target_changed.connect(self.on_target_changed)
        self.win.preview_view.execute_triggered.connect(self.start_organization)
        self.win.preview_view.resume_triggered.connect(self.resume_interrupted_sort)

        # Duplicate page
        self.win.duplicate_view.scan_triggered.connect(self.start_duplicate_scan)
        self.win.duplicate_view.delete_triggered.connect(self.delete_duplicates)
        
        # Restore page
        self.win.restore_view.restore_triggered.connect(self.restore_backup)
        self.win.restore_view.delete_triggered.connect(self.delete_backup_session)
        self.win.restore_view.refresh_triggered.connect(self.refresh_backups_list)

        # Settings page
        self.win.settings_view.settings_saved.connect(self.save_settings)

    def load_initial_settings(self):
        # Populate settings page with persisted configs
        target_dir = config.get("default_target_dir", "")
        backup_dir = config.get("backup_dir", str(DEFAULT_BACKUP_DIR))
        conflict = config.get("conflict_mode", "Rename")
        theme = config.get("theme", "dark")
        
        self.win.settings_view.set_settings(target_dir, backup_dir, conflict)
        self.win.preview_view.path_input.setText(target_dir)
        self.win.preview_view.conflict_combo.setCurrentText(conflict)
        self.win.apply_theme(theme)

    def refresh_all_views(self):
        """Reloads songs data from SQLite and updates all view components."""
        self.songs = self.db.get_all_songs()
        
        # Update Dashboard
        self.update_dashboard()
        
        # Update Library
        self.win.library_view.update_categories_filter()
        self.win.library_view.load_library()
        
        # Update Previews
        self.generate_previews()

        # Update Backups
        self.refresh_backups_list()

    def update_dashboard(self):
        total_songs = len(self.songs)
        
        # Calculate stats
        duplicates_count = 0
        missing_metadata = 0
        folders_dist = {cat: 0 for cat in self.db.get_categories()}
        
        for s in self.songs:
            folder = s.get("folder_assignment", "Others")
            if folder in folders_dist:
                folders_dist[folder] += 1
            else:
                folders_dist["Others"] += 1
                
            if s.get("is_metadata_cleaned", 0) or not s.get("title"):
                missing_metadata += 1

        # Query backups for times organized details
        success_rate = 100.0  # Default success assumption if no errors logged
        
        # Query total count of duplicates from duplicates.txt file if it exists
        # Or calculate using DB content matches (e.g. duplicate hashes count)
        hash_counts = {}
        for s in self.songs:
            h = s.get("file_hash")
            if h:
                hash_counts[h] = hash_counts.get(h, 0) + 1
        duplicates_count = sum(c - 1 for c in hash_counts.values() if c > 1)

        self.win.dashboard_view.update_stats(
            total=total_songs,
            duplicates=duplicates_count,
            missing=missing_metadata,
            success_rate=success_rate,
            distribution=folders_dist
        )

    # 1. SCANNING WORKER FLOW
    @Slot(str)
    def start_scan(self, path_str: str):
        if self.active_worker and self.active_worker.isRunning():
            return
            
        path = Path(path_str)
        if not path.is_dir():
            QMessageBox.critical(self.win, "Error", "Selected scan directory is invalid!")
            return

        self.scan_root = path
        
        # Lock UI & Display Progress bar
        self.win.show_progress(True, "Scanning folders...", 0)
        
        self.active_worker = ScanWorker(path, self.db)
        self.active_worker.progress.connect(self.on_scan_progress)
        self.active_worker.status_msg.connect(self.on_worker_status)
        self.active_worker.finished_scan.connect(self.on_scan_completed)
        self.active_worker.start()

    def on_scan_progress(self, current: int, total: int, filename: str):
        pct = int(current / total * 100) if total > 0 else 0
        self.win.show_progress(True, f"Scanning: {filename} ({current}/{total})", pct)

    def on_worker_status(self, msg: str):
        self.win.progress_msg.setText(msg)

    @Slot(list)
    def on_scan_completed(self, songs_parsed: list):
        self.win.show_progress(False)
        self.win.scan_view.populate_songs(songs_parsed)
        
        # Train smart classifier on newly scanned/scanned DB contents
        self.classifier.train()
        
        # Classify scanned songs if not already customized (only overwrite 'Others')
        for song in songs_parsed:
            db_song = self.db.get_song(song.id)
            if db_song and db_song.get("folder_assignment", "Others") == "Others":
                suggested_folder, conf = self.classifier.classify(song)
                self.db.update_song_field(song.id, "folder_assignment", suggested_folder)

        self.refresh_all_views()
        self.active_worker = None
        
        # Offer to trigger duplicates scan automatically
        if songs_parsed:
            self.start_duplicate_scan()

    # 2. DUPLICATES WORKER FLOW
    @Slot()
    def start_duplicate_scan(self):
        if self.active_worker and self.active_worker.isRunning():
            return
            
        if not self.songs:
            QMessageBox.information(self.win, "Duplicates Check", "No songs loaded in database. Scan a library first.")
            return

        self.win.show_progress(True, "Scanning for duplicates...", 0)
        self.active_worker = DuplicateWorker(self.songs, self.db)
        self.active_worker.progress.connect(self.on_duplicate_progress)
        self.active_worker.status_msg.connect(self.on_worker_status)
        self.active_worker.finished_duplicates.connect(self.on_duplicate_completed)
        self.active_worker.start()

    def on_duplicate_progress(self, current: int, total: int, msg: str):
        self.win.show_progress(True, msg, current)

    @Slot(list, list, list, list)
    def on_duplicate_completed(self, hash_g, meta_g, size_g, name_g):
        self.win.show_progress(False)
        self.win.duplicate_view.populate_duplicates(hash_g, meta_g, size_g, name_g)
        self.active_worker = None
        self.update_dashboard()

    @Slot(list)
    def delete_duplicates(self, file_paths: list):
        """Physically deletes checked duplicate copies from storage."""
        self.op_logger.info(f"User requested batch deletion of {len(file_paths)} duplicate files.")
        
        deleted_count = 0
        failed_paths = []
        
        for path in file_paths:
            p = Path(path)
            try:
                if p.exists():
                    p.unlink()
                    deleted_count += 1
                    # Remove from DB
                    song = self.db.get_song_by_path(str(p.resolve()))
                    if song:
                        self.db.delete_song(song["id"])
                    self.op_logger.info(f"Deleted duplicate: {p}")
            except Exception as e:
                self.err_logger.error(f"Failed to delete duplicate {p}: {e}")
                failed_paths.append(str(p))

        self.refresh_all_views()
        
        if failed_paths:
            QMessageBox.warning(
                self.win,
                "Deletion Summary",
                f"Successfully deleted {deleted_count} duplicate files.\n\nFailed to delete {len(failed_paths)} files (likely permission restrictions)."
            )
        else:
            QMessageBox.information(
                self.win,
                "Success",
                f"Successfully deleted {deleted_count} duplicate files from disk."
            )
            
        # Re-run duplicates scanning
        self.start_duplicate_scan()

    # 3. CSV VALIDATION FLOW
    @Slot(str)
    def start_csv_validation(self, csv_path_str: str):
        csv_path = Path(csv_path_str)
        if not csv_path.exists():
            QMessageBox.critical(self.win, "Error", "CSV file does not exist!")
            self.win.csv_view.validate_btn.setEnabled(True)
            self.win.csv_view.validate_btn.setText("Validate CSV")
            return
            
        if not self.scan_root:
            QMessageBox.warning(self.win, "Validation Error", "Please select and scan a music folder first before validating CSV mapping.")
            self.win.csv_view.validate_btn.setEnabled(True)
            self.win.csv_view.validate_btn.setText("Validate CSV")
            return

        # Adapt scanned songs domain entities
        scanned_songs_domain = []
        for s in self.songs:
            scanned_songs_domain.append(self._to_song_domain(s))

        records, issues, report_path = self.csv_validator.validate_csv(csv_path, scanned_songs_domain, self.scan_root)
        self.win.csv_view.populate_issues(issues, report_path)
        
        # Save CSV records mapping for organization engine previews
        self.csv_mappings = [{"filename": r.filename, "new_filename": r.new_filename, "folder": r.folder} for r in records]
        
        # Reload previews using new CSV assignments
        self.generate_previews()

    # 4. PREVIEW & RUN SORTER FLOW
    def generate_previews(self):
        """Builds OperationPreview items based on DB state or CSV maps."""
        target_dir_str = self.win.preview_view.path_input.text()
        if not target_dir_str or not self.songs:
            self.win.preview_view.populate_previews([])
            return
            
        target_root = Path(target_dir_str)
        domain_songs = [self._to_song_domain(s) for s in self.songs]
        
        csv_maps = getattr(self, "csv_mappings", None)
        previews_raw = self.move_engine.generate_previews(domain_songs, target_root, csv_maps)
        
        # Re-map previews to domain objects with Song IDs
        self.previews = []
        for op in previews_raw:
            # Match target song by matching original path
            matching_song = next((s for s in self.songs if s["current_path"] == str(op.original_path.resolve())), None)
            if matching_song:
                op.song_id = matching_song["id"]
                self.previews.append(op)
                
        self.win.preview_view.populate_previews(self.previews)
        
        # Check if checkpoint exists in target root to offer Resume
        checkpoint_file = target_root / ".musicsort_progress.json"
        self.win.preview_view.show_resume_button(checkpoint_file.exists())

    @Slot(str)
    def on_target_changed(self, target_path_str: str):
        # Update config settings
        config.set("default_target_dir", target_path_str)
        self.generate_previews()

    @Slot(str)
    def start_organization(self, conflict_mode: str):
        if self.active_worker and self.active_worker.isRunning():
            return
            
        if not self.previews:
            QMessageBox.warning(self.win, "Organizer", "No preview operations available to organize!")
            return

        # Double check target path
        target_dir = self.win.preview_view.path_input.text()
        if not target_dir:
            QMessageBox.warning(self.win, "Organizer", "Target Library Root folder is not selected!")
            return

        # Lock UI & Start background worker
        self.win.show_progress(True, "Organizing library...", 0)
        
        self.active_worker = OrganizeWorker(
            previews=self.previews,
            conflict_mode=conflict_mode,
            backup_enabled=True,
            db_manager=self.db
        )
        self.active_worker.progress.connect(self.on_organize_progress)
        self.active_worker.status_msg.connect(self.on_worker_status)
        self.active_worker.finished_organize.connect(self.on_organize_completed)
        self.active_worker.start()

    def on_organize_progress(self, current: int, total: int, msg: str):
        pct = int(current / total * 100) if total > 0 else 0
        self.win.show_progress(True, f"{msg} ({current}/{total})", pct)

    @Slot(int, int, list)
    def on_organize_completed(self, success: int, failed: int, previews_updated: list):
        self.win.show_progress(False)
        self.refresh_all_views()
        self.active_worker = None
        
        QMessageBox.information(
            self.win,
            "Sort Complete",
            f"Organization execution finished.\n\nSuccessfully moved: {success}\nFailed/Skipped: {failed}\n\nReports generated in reports folder."
        )

    @Slot()
    def resume_interrupted_sort(self):
        target_dir = self.win.preview_view.path_input.text()
        if not target_dir:
            return
        mode = self.win.preview_view.conflict_combo.currentText()
        self.start_organization(mode) # OrganizeWorker handles checkpoint loading internally!

    # 5. BACKUPS & RESTORE (UNDO) FLOW
    def refresh_backups_list(self):
        backups = self.backup_service.list_backups()
        
        # Convert db dict entries to BackupIndex dataclasses for populate
        backup_indices = []
        for b in backups:
            entries = self.db.get_backup_entries(b["id"])
            entries_dc = [BackupEntry(song_id=e["song_id"], original_path=Path(e["original_path"]), backup_path=Path(e["backup_path"])) for e in entries]
            backup_indices.append(BackupIndex(
                id=b["id"],
                timestamp=b["timestamp"],
                backup_dir=Path(b["backup_dir"]),
                description=b["description"] or "",
                entries=entries_dc
            ))
            
        self.win.restore_view.populate_backups(backup_indices)

    @Slot(str)
    def restore_backup(self, backup_dir_path: str):
        # Extract ID from backup folder path structure
        # Directory name: backup_<timestamp>
        backups = self.backup_service.list_backups()
        matching_backup = next((b for b in backups if b["backup_dir"] == backup_dir_path), None)
        
        if not matching_backup:
            QMessageBox.critical(self.win, "Restore Error", "Could not identify backup session metadata!")
            return
            
        self.win.show_progress(True, "Restoring files to original layout...", 50)
        success = self.backup_service.restore_backup(matching_backup["id"])
        self.win.show_progress(False)
        
        if success:
            QMessageBox.information(self.win, "Success", "Backup restored successfully. DB paths and files rolled back.")
        else:
            QMessageBox.warning(self.win, "Restore Completed with issues", "Some files could not be restored. Review operations log.")
            
        self.refresh_all_views()

    @Slot(str)
    def delete_backup_session(self, backup_dir_path: str):
        backups = self.backup_service.list_backups()
        matching_backup = next((b for b in backups if b["backup_dir"] == backup_dir_path), None)
        if matching_backup:
            self.backup_service.delete_backup_session(matching_backup["id"])
            self.refresh_backups_list()

    # 6. CONFIGS & CATEGORIES INTERFACES
    @Slot(dict)
    def save_settings(self, settings: dict):
        config.set("default_target_dir", settings["default_target_dir"])
        config.set("backup_dir", settings["backup_dir"])
        config.set("conflict_mode", settings["default_conflict_mode"])
        
        # Theme toggle check
        saved_theme = config.get("theme")
        new_theme = "dark" # We can add UI theme selection later. Right now we map default settings.
        # Let's save theme choice
        
        # Load details
        self.load_initial_settings()
        self.refresh_all_views()

    @Slot()
    def on_categories_modified(self):
        # Notify views of categories change
        self.win.settings_view.folders_list.clear()
        self.win.settings_view.folders_list.addItems(self.db.get_categories())
        self.refresh_all_views()

    # HELPERS
    def _to_song_domain(self, s: dict) -> Song:
        """Utility mapper: SQLite dictionary row -> Song domain dataclass."""
        custom_t = []
        if s.get("custom_tags"):
            try:
                custom_t = json.loads(s["custom_tags"])
            except Exception:
                pass
                
        return Song(
            id=s["id"],
            path=Path(s["current_path"]),
            original_path=Path(s["original_path"]) if s.get("original_path") else Path(s["current_path"]),
            title=s.get("title", ""),
            artist=s.get("artist", "Unknown Artist"),
            album=s.get("album", ""),
            album_artist=s.get("album_artist", ""),
            track_num=s.get("track_num", ""),
            disc_num=s.get("disc_num", ""),
            genre=s.get("genre", ""),
            year=s.get("year", ""),
            composer=s.get("composer", ""),
            lyrics=s.get("lyrics", ""),
            comment=s.get("comment", ""),
            duration=s.get("duration", 0.0),
            bitrate=s.get("bitrate", 0),
            sample_rate=s.get("sample_rate", 0),
            channels=s.get("channels", 0),
            file_hash=s.get("file_hash", ""),
            artwork_hash=s.get("artwork_hash", ""),
            folder_assignment=s.get("folder_assignment", "Others"),
            custom_tags=custom_t,
            user_notes=s.get("user_notes", ""),
            rating=s.get("rating", 0),
            favorite=s.get("favorite", 0),
            times_organized=s.get("times_organized", 0),
            last_scan=s.get("last_scan", ""),
            created_date=s.get("created_date", ""),
            modified_date=s.get("modified_date", ""),
            is_metadata_cleaned=bool(s.get("is_metadata_cleaned", 0))
        )
