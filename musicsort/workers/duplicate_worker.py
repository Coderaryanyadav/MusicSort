import difflib
import json
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QThread, Signal

from musicsort.models.domain import Song, DuplicateGroup
from musicsort.utils.file_hashing import calculate_sha256
from musicsort.database.db_manager import DBManager
from musicsort.services.report_generator import ReportGenerator
from musicsort.core.logger import get_operations_logger

class DuplicateWorker(QThread):
    """
    Background worker thread detecting duplicate songs across the library.
    Compares using SHA256 hashes (optimized), metadata tags, file size, duration/bitrate, and filename similarity.
    Calculates duplicate confidence scores and writes duplicates.txt.
    """
    progress = Signal(int, int, str) # (current, total, message)
    status_msg = Signal(str)
    finished_duplicates = Signal(list, list, list, list) # (hash_groups, meta_groups, size_groups, name_groups)

    def __init__(self, songs: List[Dict[str, Any]], db_manager: Optional[DBManager] = None):
        super().__init__()
        self.raw_songs = songs
        self.db = db_manager if db_manager else DBManager()
        self.report_generator = ReportGenerator()
        self.op_logger = get_operations_logger()
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        self.status_msg.emit("Analyzing library for duplicates...")
        total_songs = len(self.raw_songs)
        self.op_logger.info(f"DuplicateWorker started. Total songs to analyze: {total_songs}")

        # Convert DB dictionary representations to Song domain objects
        songs: List[Song] = []
        for s in self.raw_songs:
            # Custom tags unpacking
            custom_t = []
            if s.get("custom_tags"):
                try:
                    custom_t = json.loads(s["custom_tags"])
                except Exception:
                    pass
                    
            songs.append(Song(
                id=s["id"],
                path=Path(s["current_path"]),
                original_path=Path(s["original_path"]) if s.get("original_path") else Path(s["current_path"]),
                title=s.get("title", ""),
                artist=s.get("artist", ""),
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
                is_metadata_cleaned=False
            ))

        # Size check for size-optimized hashing
        self.progress.emit(10, 100, "Calculating file hashes...")
        
        # 1. HASH DUPLICATE STRATEGY (100% confidence)
        # Pre-group by size to avoid hashing unique files
        size_to_songs = defaultdict(list)
        for s in songs:
            try:
                size = s.path.stat().st_size
                s.size_bytes = size
                size_to_songs[size].append(s)
            except Exception:
                s.size_bytes = 0

        # Calculate hashes for files sharing identical size
        candidate_count = sum(len(lst) for size, lst in size_to_songs.items() if len(lst) > 1)
        hashed_count = 0
        
        for size, lst in size_to_songs.items():
            if self.is_cancelled:
                return
            if len(lst) > 1:
                for s in lst:
                    if not s.file_hash:
                        s.file_hash = calculate_sha256(s.path)
                        # Save hash to DB cache immediately
                        self.db.update_song_field(s.id, "file_hash", s.file_hash)
                    hashed_count += 1
                    self.progress.emit(
                        int(10 + (hashed_count / max(1, candidate_count) * 40)),
                        100,
                        f"Hashing candidate files: {hashed_count}/{candidate_count}"
                    )

        hash_groups: List[DuplicateGroup] = []
        hash_dict = defaultdict(list)
        for s in songs:
            if s.file_hash:
                hash_dict[s.file_hash].append(s)
        for f_hash, flist in hash_dict.items():
            if len(flist) > 1:
                hash_groups.append(DuplicateGroup(
                    id=f"hash_{f_hash[:12]}",
                    criteria="SHA256 File Hash",
                    confidence=100,
                    files=flist
                ))

        if self.is_cancelled:
            return
        self.progress.emit(50, 100, "Analyzing metadata...")

        # 2. METADATA DUPLICATE STRATEGY (90% confidence)
        meta_groups: List[DuplicateGroup] = []
        meta_dict = defaultdict(list)
        for s in songs:
            title_clean = s.title.strip().lower()
            artist_clean = s.artist.strip().lower()
            if title_clean and artist_clean and artist_clean != "unknown artist":
                meta_dict[(artist_clean, title_clean)].append(s)
        for (artist, title), flist in meta_dict.items():
            if len(flist) > 1:
                meta_groups.append(DuplicateGroup(
                    id=f"meta_{artist.replace(' ', '_')}_{title.replace(' ', '_')}",
                    criteria="Metadata (Artist & Title)",
                    confidence=90,
                    files=flist
                ))

        if self.is_cancelled:
            return
        self.progress.emit(70, 100, "Comparing filenames...")

        # 3. FILENAME SIMILARITY STRATEGY (80% confidence)
        # Groups files with size match and name similarity >= 85%
        name_groups: List[DuplicateGroup] = []
        # Group by size to double check potential candidates
        size_groups_dict = defaultdict(list)
        for s in songs:
            size_groups_dict[s.size_bytes].append(s)
            
        size_duplicates_idx = 0
        for size, flist in size_groups_dict.items():
            if len(flist) > 1:
                # Compare filenames using SequenceMatcher
                # If similarity > 85%, group them
                used_indices = set()
                for i in range(len(flist)):
                    if i in used_indices:
                        continue
                    group_files = [flist[i]]
                    for j in range(i + 1, len(flist)):
                        if j in used_indices:
                            continue
                        # Calculate similarity score
                        ratio = difflib.SequenceMatcher(None, flist[i].path.name.lower(), flist[j].path.name.lower()).ratio()
                        if ratio >= 0.85:
                            group_files.append(flist[j])
                            used_indices.add(j)
                    if len(group_files) > 1:
                        size_duplicates_idx += 1
                        name_groups.append(DuplicateGroup(
                            id=f"similarity_{size_duplicates_idx}",
                            criteria="Filename Similarity & Size Match",
                            confidence=80,
                            files=group_files
                        ))

        if self.is_cancelled:
            return
        self.progress.emit(90, 100, "Correlating duration and bitrates...")

        # 4. DURATION & BITRATE STRATEGY (60% confidence)
        size_groups: List[DuplicateGroup] = []
        dur_bit_dict = defaultdict(list)
        for s in songs:
            if s.duration > 0 and s.bitrate > 0:
                # Round duration to nearest integer to group matching duration ranges (e.g. ±1 second)
                key = (int(round(s.duration)), s.bitrate)
                dur_bit_dict[key].append(s)
        for key, flist in dur_bit_dict.items():
            if len(flist) > 1:
                # Extra check: make sure they aren't already categorized under higher confidence strategies
                size_groups.append(DuplicateGroup(
                    id=f"technical_dur_{key[0]}_br_{key[1]}",
                    criteria="Duration & Bitrate Correlation",
                    confidence=60,
                    files=flist
                ))

        # Generate report file duplicates.txt
        all_groups = hash_groups + meta_groups + name_groups + size_groups
        self.report_generator.generate_duplicates_report(all_groups)

        self.progress.emit(100, 100, "Done!")
        self.status_msg.emit(f"Duplicates analysis completed! Found {len(all_groups)} groups.")
        self.finished_duplicates.emit(hash_groups, meta_groups, name_groups, size_groups)
