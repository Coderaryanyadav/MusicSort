from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List

@dataclass
class Song:
    id: str  # Unique MD5/hash of path or file hash
    path: Path
    original_path: Optional[Path] = None
    title: str = ""
    artist: str = "Unknown Artist"
    album: str = ""
    album_artist: str = ""
    track_num: str = ""
    disc_num: str = ""
    genre: str = ""
    year: str = ""
    composer: str = ""
    lyrics: str = ""
    comment: str = ""
    duration: float = 0.0
    bitrate: int = 0
    sample_rate: int = 0
    channels: int = 0
    file_hash: str = ""
    artwork_hash: str = ""
    folder_assignment: str = "Others"
    custom_tags: List[str] = field(default_factory=list)
    user_notes: str = ""
    rating: int = 0
    favorite: int = 0
    times_organized: int = 0
    last_scan: str = ""
    created_date: str = ""
    modified_date: str = ""
    size_bytes: int = 0
    is_metadata_cleaned: bool = False

@dataclass
class CSVRecord:
    filename: str
    new_filename: str
    folder: str

@dataclass
class ValidationIssue:
    type: str  # e.g., "duplicate_row", "duplicate_filename", "duplicate_destination", "missing_file", "extra_file", "invalid_folder", "empty_field"
    message: str
    severity: str  # "error", "warning"
    row_index: Optional[int] = None
    details: str = ""

@dataclass
class OperationPreview:
    original_path: Path
    target_path: Path
    operation_type: str  # "rename", "move", "rename_and_move"
    song_id: str = ""
    status: str = "pending"  # "pending", "success", "skipped", "failed", "conflict"
    error_message: Optional[str] = None

@dataclass
class DuplicateGroup:
    id: str
    criteria: str  # "hash", "size", "metadata", "filename", "fingerprint"
    confidence: int  # 0 to 100
    files: List[Song] = field(default_factory=list)

@dataclass
class BackupEntry:
    song_id: str
    original_path: Path
    backup_path: Path

@dataclass
class BackupIndex:
    id: str
    timestamp: str
    backup_dir: Path
    description: str = ""
    entries: List[BackupEntry] = field(default_factory=list)
