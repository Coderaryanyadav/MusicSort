import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

from musicsort.core.config import DEFAULT_BACKUP_DIR
from musicsort.database.db_manager import DBManager
from musicsort.models.domain import BackupIndex, BackupEntry
from musicsort.core.logger import get_operations_logger, get_errors_logger

class BackupService:
    """
    Handles file backups prior to move/rename actions, logging sessions in SQLite.
    Allows atomic restores to original paths and DB state rollback.
    """
    def __init__(self, db_manager: Optional[DBManager] = None, backup_root: Path = DEFAULT_BACKUP_DIR):
        self.db = db_manager if db_manager else DBManager()
        self.backup_root = backup_root
        self.op_logger = get_operations_logger()
        self.err_logger = get_errors_logger()
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def create_backup_session(self, songs_to_backup: List[Dict[str, Any]], description: str = "") -> Optional[str]:
        """
        Copies songs to the backup session directory and logs the records in SQLite.
        Returns the backup session ID (UUID) if successful, None otherwise.
        """
        backup_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.backup_root / f"backup_{timestamp}"
        
        try:
            session_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.err_logger.error(f"Failed to create backup directory {session_dir}: {e}")
            return None

        self.op_logger.info(f"Starting database-backed backup session: {backup_id}")
        
        entries: List[Tuple[str, str, str]] = []
        
        for song in songs_to_backup:
            song_id = song["id"]
            current_path = Path(song["current_path"])
            
            if not current_path.exists():
                self.err_logger.error(f"Backup source file missing: {current_path}")
                continue
                
            unique_filename = f"{uuid.uuid4().hex}{current_path.suffix}"
            backup_file_path = session_dir / unique_filename
            
            try:
                # Copy file and preserve metadata
                shutil.copy2(current_path, backup_file_path)
                entries.append((song_id, str(current_path), str(backup_file_path)))
                self.op_logger.info(f"Backup copied: {current_path.name} -> {unique_filename}")
            except Exception as e:
                self.err_logger.error(f"Failed to copy backup for song {song_id} ({current_path}): {e}")

        if not entries:
            # Clean empty directory
            try:
                session_dir.rmdir()
            except Exception:
                pass
            return None

        # Record in DB
        success = self.db.add_backup(
            backup_id=backup_id,
            timestamp=timestamp,
            backup_dir=str(session_dir),
            description=description,
            entries=entries
        )
        
        if success:
            return backup_id
        else:
            # DB entry failed, clean copied files
            try:
                shutil.rmtree(session_dir)
            except Exception:
                pass
            return None

    def restore_backup(self, backup_id: str) -> bool:
        """
        Restores a backup session from SQLite logs, copying files back to original paths,
        updating songs DB paths, and clean up backup files.
        """
        backups = self.db.get_backups()
        backup_meta = next((b for b in backups if b["id"] == backup_id), None)
        if not backup_meta:
            self.err_logger.error(f"Backup session not found in database: {backup_id}")
            return False
            
        entries = self.db.get_backup_entries(backup_id)
        if not entries:
            self.err_logger.error(f"No backup entries recorded for session {backup_id}")
            return False
            
        self.op_logger.info(f"Restoring backup session {backup_id} ({backup_meta['timestamp']})")
        
        success = True
        restored_count = 0
        
        for entry in entries:
            song_id = entry["song_id"]
            orig_path = Path(entry["original_path"])
            back_path = Path(entry["backup_path"])
            
            if not back_path.exists():
                self.err_logger.error(f"Backup file not found on disk: {back_path}")
                success = False
                continue
                
            try:
                # Ensure parents exist
                orig_path.parent.mkdir(parents=True, exist_ok=True)
                # Move back
                shutil.copy2(back_path, orig_path)
                
                # Update SQLite database path reference
                self.db.update_song_field(song_id, "current_path", str(orig_path))
                
                restored_count += 1
                self.op_logger.info(f"Restored file and DB path for song {song_id} -> {orig_path}")
            except Exception as e:
                self.err_logger.error(f"Failed to restore file {orig_path}: {e}")
                success = False
                
        if success:
            # Delete backup files and directory
            backup_dir = Path(backup_meta["backup_dir"])
            try:
                shutil.rmtree(backup_dir)
                self.op_logger.info(f"Removed backup files at {backup_dir}")
            except Exception as e:
                self.err_logger.error(f"Failed to remove backup session directory {backup_dir}: {e}")
                
            # Remove DB records
            self.db.delete_backup(backup_id)
            self.op_logger.info(f"Deleted backup session registry {backup_id}")
            return True
        else:
            self.err_logger.error(f"Backup restore finished with errors. Restored {restored_count}/{len(entries)} files.")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """Returns list of backups from database."""
        return self.db.get_backups()

    def delete_backup_session(self, backup_id: str) -> bool:
        """Deletes a backup session directory and its registry from DB."""
        backups = self.db.get_backups()
        backup_meta = next((b for b in backups if b["id"] == backup_id), None)
        if not backup_meta:
            return False
            
        # Remove files
        backup_dir = Path(backup_meta["backup_dir"])
        if backup_dir.exists():
            try:
                shutil.rmtree(backup_dir)
            except Exception as e:
                self.err_logger.error(f"Failed to delete backup files at {backup_dir}: {e}")
                
        # Remove DB reference
        return self.db.delete_backup(backup_id)
