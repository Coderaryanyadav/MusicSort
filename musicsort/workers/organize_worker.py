import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal

from musicsort.models.domain import OperationPreview
from musicsort.database.db_manager import DBManager
from musicsort.services.backup_service import BackupService
from musicsort.services.report_generator import ReportGenerator
from musicsort.core.logger import get_operations_logger, get_errors_logger

class OrganizeWorker(QThread):
    """
    Background worker thread executing renames and moves.
    Integrates with BackupService and ReportGenerator, and updates SQLite paths.
    """
    progress = Signal(int, int, str)  # (current, total, progress_message)
    status_msg = Signal(str)
    finished_organize = Signal(int, int, list)  # (success_count, failed_count, updated_previews)

    def __init__(
        self,
        previews: List[OperationPreview],
        conflict_mode: str,
        backup_enabled: bool = True,
        db_manager: Optional[DBManager] = None
    ):
        super().__init__()
        self.previews = previews
        self.conflict_mode = conflict_mode
        self.backup_enabled = backup_enabled
        self.db = db_manager if db_manager else DBManager()
        self.backup_service = BackupService(self.db)
        self.report_generator = ReportGenerator()
        self.op_logger = get_operations_logger()
        self.err_logger = get_errors_logger()
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        total = len(self.previews)
        success_count = 0
        failed_count = 0
        
        self.status_msg.emit("Preparing file organization...")
        self.op_logger.info(f"OrganizeWorker started. Processing {total} file actions.")

        # 1. Automatic Backup before operations
        backup_id = None
        if self.backup_enabled and total > 0:
            self.status_msg.emit("Creating automatic restore point...")
            songs_to_backup = []
            for op in self.previews:
                song = self.db.get_song(op.song_id)
                if song:
                    songs_to_backup.append(song)
            
            if songs_to_backup:
                backup_id = self.backup_service.create_backup_session(
                    songs_to_backup=songs_to_backup,
                    description=f"Auto-backup before organizing {total} songs."
                )
                if backup_id:
                    self.op_logger.info(f"Auto-backup session established: {backup_id}")
                else:
                    self.err_logger.error("Auto-backup session creation failed! Cancelling organize for safety.")
                    self.status_msg.emit("Backup failed! Organization cancelled for data safety.")
                    self.finished_organize.emit(0, total, self.previews)
                    return

        # 2. Process operations one by one
        for idx, op in enumerate(self.previews):
            if self.is_cancelled:
                self.status_msg.emit("Organization cancelled by user.")
                break

            orig_path = op.original_path
            target_path = op.target_path
            
            # Message update
            msg = f"Moving: {orig_path.name} -> {target_path.name}"
            self.progress.emit(idx + 1, total, msg)

            # Verification
            if not orig_path.exists():
                op.status = "failed"
                op.error_message = "Source file missing on disk."
                failed_count += 1
                self.err_logger.error(f"Source file missing: {orig_path}")
                continue

            # Ensure parents exist
            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                op.status = "failed"
                op.error_message = f"Failed to create target directories: {e}"
                failed_count += 1
                self.err_logger.error(f"Failed to create folder {target_path.parent}: {e}")
                continue

            # Handle conflicts
            final_target = target_path
            if final_target.exists() and final_target.resolve() != orig_path.resolve():
                if self.conflict_mode == "Skip":
                    op.status = "skipped"
                    op.error_message = "Destination file exists (skipped)."
                    self.op_logger.info(f"Skipped conflict: {orig_path.name}")
                    continue
                elif self.conflict_mode == "Rename":
                    base = final_target.stem
                    ext = final_target.suffix
                    parent = final_target.parent
                    counter = 1
                    while final_target.exists():
                        final_target = parent / f"{base} - {counter}{ext}"
                        counter += 1
                    op.target_path = final_target
                    self.op_logger.info(f"Conflict renamed: {orig_path.name} -> {final_target.name}")
                elif self.conflict_mode == "Replace":
                    try:
                        final_target.unlink()
                        self.op_logger.info(f"Conflict overwrite delete: {final_target}")
                    except Exception as e:
                        op.status = "failed"
                        op.error_message = f"Failed to delete existing file: {e}"
                        failed_count += 1
                        self.err_logger.error(f"Failed to delete {final_target} for Replace mode: {e}")
                        continue

            # Move file (strict move, never copy/symlink)
            try:
                shutil.move(str(orig_path), str(final_target))
                op.status = "success"
                success_count += 1
                
                # Fetch details for update
                song = self.db.get_song(op.song_id)
                times_org = song["times_organized"] + 1 if song else 1
                new_folder = final_target.parent.name
                
                # Update SQLite DB records immediately (checkpoint mechanism)
                self.db.update_song_field(op.song_id, "current_path", str(final_target.resolve()))
                self.db.update_song_field(op.song_id, "folder_assignment", new_folder)
                self.db.update_song_field(op.song_id, "times_organized", times_org)
                
                self.op_logger.info(f"Moved and updated DB: {orig_path.name} -> {final_target.name} [{new_folder}]")
            except Exception as e:
                op.status = "failed"
                op.error_message = f"Move failed: {e}"
                failed_count += 1
                self.err_logger.error(f"Move failed for {orig_path} to {final_target}: {e}")

        # 3. Generate Execution Reports
        self.status_msg.emit("Writing execution reports...")
        scan_root = Path(self.previews[0].original_path.parent) if total > 0 else Path(".")
        target_root = Path(self.previews[0].target_path.parent.parent) if total > 0 else Path(".")
        
        self.report_generator.generate_execution_report(
            previews=self.previews,
            scan_root=scan_root,
            target_root=target_root,
            conflict_mode=self.conflict_mode,
            backup_id=backup_id
        )

        self.status_msg.emit(f"Organization finished. Success: {success_count}, Failed: {failed_count}.")
        self.finished_organize.emit(success_count, failed_count, self.previews)
