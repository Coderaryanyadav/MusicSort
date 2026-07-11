import os
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from PySide6.QtCore import QThread, Signal
import mutagen

from musicsort.core.config import SUPPORTED_EXTENSIONS, DEFAULT_APP_DIR
from musicsort.database.db_manager import DBManager
from musicsort.models.domain import Song
from musicsort.utils.filename_cleaner import clean_filename, split_artist_title
from musicsort.core.logger import get_operations_logger, get_errors_logger

# Ensure artwork cache folder exists
ARTWORK_CACHE_DIR = DEFAULT_APP_DIR / "artwork_cache"
ARTWORK_CACHE_DIR.mkdir(parents=True, exist_ok=True)

class ScanWorker(QThread):
    """
    Background worker thread that recursively scans directory, reads metadata,
    extracts embedded artwork, and updates the SQLite database.
    """
    progress = Signal(int, int, str)  # (current, total, filename)
    status_msg = Signal(str)
    finished_scan = Signal(list)       # Emits list of parsed Song objects

    def __init__(self, scan_dir: Path, db_manager: Optional[DBManager] = None):
        super().__init__()
        self.scan_dir = scan_dir
        self.db = db_manager if db_manager else DBManager()
        self.op_logger = get_operations_logger()
        self.err_logger = get_errors_logger()
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        self.status_msg.emit("Gathering files to scan...")
        self.op_logger.info(f"ScanWorker started for path: {self.scan_dir}")
        
        # 1. Walk directory and collect matching paths
        files_to_scan: List[Path] = []
        try:
            for root, dirs, files in os.walk(self.scan_dir):
                if self.is_cancelled:
                    return
                # Skip ignore directories
                dirs[:] = [d for d in dirs if d not in [".git", "node_modules", ".musicsort", ".venv", "backups"]]
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        files_to_scan.append(file_path)
        except Exception as e:
            self.err_logger.error(f"Error gathering files to scan: {e}")
            self.status_msg.emit(f"Scan failed: {e}")
            self.finished_scan.emit([])
            return

        total_files = len(files_to_scan)
        self.status_msg.emit(f"Found {total_files} audio files. Parsing metadata...")
        self.op_logger.info(f"Found {total_files} audio files to scan.")

        songs_parsed: List[Song] = []
        
        # 1. Parse all files in background thread (no DB locks, safe and parallel)
        for idx, path in enumerate(files_to_scan):
            if self.is_cancelled:
                self.status_msg.emit("Scan cancelled.")
                self.op_logger.info("Scanning task was cancelled by user.")
                break

            self.progress.emit(idx + 1, total_files, path.name)
            try:
                song = self._parse_file(path)
                songs_parsed.append(song)
            except Exception as e:
                self.err_logger.error(f"Error parsing file {path.name}: {e}")

        if self.is_cancelled:
            self.finished_scan.emit([])
            return

        # 2. Bulk write parsed songs to database under a single thread lock
        self.status_msg.emit("Saving results to library...")
        with self.db._lock:
            conn = sqlite3.connect(self.db.db_path, timeout=30.0, check_same_thread=False)
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            try:
                for song in songs_parsed:
                    self._db_save_song_conn(cursor, song)
                conn.commit()
            except Exception as e:
                self.err_logger.error(f"Error during DB batch commit: {e}")
                conn.rollback()
            finally:
                conn.close()

        self.status_msg.emit(f"Scan complete! Scanned {len(songs_parsed)} files.")
        self.finished_scan.emit(songs_parsed)

    def _parse_file(self, file_path: Path) -> Song:
        """Parses audio file tags using Mutagen."""
        song_id = hashlib.md5(str(file_path.resolve()).encode('utf-8')).hexdigest()
        
        title = ""
        artist = ""
        album = ""
        album_artist = ""
        track_num = ""
        disc_num = ""
        genre = ""
        year = ""
        composer = ""
        comment = ""
        lyrics = ""
        
        duration = 0.0
        bitrate = 0
        sample_rate = 0
        channels = 0
        artwork_hash = ""
        is_metadata_cleaned = False

        # Read stats
        try:
            stat_info = file_path.stat()
            size_bytes = stat_info.st_size
            created_ts = datetime.fromtimestamp(stat_info.st_ctime).isoformat()
            modified_ts = datetime.fromtimestamp(stat_info.st_mtime).isoformat()
        except Exception:
            size_bytes = 0
            created_ts = datetime.now().isoformat()
            modified_ts = datetime.now().isoformat()

        # Try parsing tags with mutagen
        try:
            audio = mutagen.File(file_path)
            if audio is not None:
                # Read properties
                if audio.info:
                    duration = getattr(audio.info, "length", 0.0)
                    # Convert bps to kbps
                    br = getattr(audio.info, "bitrate", 0)
                    bitrate = br // 1000 if br else 0
                    sample_rate = getattr(audio.info, "sample_rate", 0)
                    channels = getattr(audio.info, "channels", 0)

                # Parse Tags by checking type
                # Easy tags interface
                easy_audio = mutagen.File(file_path, easy=True)
                if easy_audio and easy_audio.tags:
                    title = easy_audio.get("title", [""])[0]
                    artist = easy_audio.get("artist", [""])[0]
                    album = easy_audio.get("album", [""])[0]
                    album_artist = easy_audio.get("albumartist", [""])[0]
                    track_num = easy_audio.get("tracknumber", [""])[0]
                    disc_num = easy_audio.get("discnumber", [""])[0]
                    genre = easy_audio.get("genre", [""])[0]
                    year = easy_audio.get("date", [""])[0]

                # Full mutagen tags for specialized items (Lyrics, Composer, Comments, Artwork)
                if audio.tags:
                    # Composer
                    if not composer:
                        for key in ["TCOM", "composer", "©wrt"]:
                            if key in audio.tags:
                                val = audio.tags[key]
                                composer = str(val[0]) if isinstance(val, list) else str(val)
                                break
                    # Comment
                    for key in ["COMM::eng", "comment", "©cmt", "COMM"]:
                        if key in audio.tags:
                            val = audio.tags[key]
                            comment = str(val[0]) if isinstance(val, list) else str(val)
                            break
                    # Lyrics
                    for key in ["USLT::eng", "lyrics", "©lyr", "USLT"]:
                        if key in audio.tags:
                            val = audio.tags[key]
                            lyrics = str(val[0]) if isinstance(val, list) else str(val)
                            break

                    # Artwork
                    artwork_hash = self._extract_artwork(audio)
        except Exception as e:
            self.err_logger.error(f"Mutagen read error for {file_path.name}: {e}")

        # Fallback to cleaning filename
        if not title or not artist or artist.lower() == "unknown artist":
            is_metadata_cleaned = True
            cleaned = clean_filename(file_path.name)
            parsed_artist, parsed_title = split_artist_title(cleaned)
            
            if not title:
                title = parsed_title if parsed_title else cleaned
            if not artist:
                artist = parsed_artist if parsed_artist else "Unknown Artist"

        return Song(
            id=song_id,
            path=file_path,
            original_path=file_path,
            title=title,
            artist=artist,
            album=album,
            album_artist=album_artist,
            track_num=track_num,
            disc_num=disc_num,
            genre=genre,
            year=year,
            composer=composer,
            lyrics=lyrics,
            comment=comment,
            duration=duration,
            bitrate=bitrate,
            sample_rate=sample_rate,
            channels=channels,
            file_hash="",  # Lazy hash evaluation
            artwork_hash=artwork_hash,
            folder_assignment="Others",
            custom_tags=[],
            user_notes="",
            rating=0,
            favorite=0,
            times_organized=0,
            last_scan=datetime.now().isoformat(),
            created_date=created_ts,
            modified_date=modified_ts,
            is_metadata_cleaned=is_metadata_cleaned
        )

    def _extract_artwork(self, audio) -> str:
        """Extracts embedded artwork bytes, writes to cache folder, and returns SHA256 of artwork."""
        img_data = None
        
        try:
            # 1. MP3 (ID3 APIC frames)
            if hasattr(audio, "tags") and audio.tags:
                apics = audio.tags.getall("APIC")
                if apics:
                    img_data = apics[0].data
            # 2. FLAC / OGG Vorbis
            if not img_data and hasattr(audio, "pictures") and audio.pictures:
                img_data = audio.pictures[0].data
            # 3. MP4 / M4A (covr)
            if not img_data and "covr" in audio:
                covr = audio["covr"]
                if covr:
                    img_data = covr[0]
        except Exception:
            pass

        if img_data:
            try:
                # Hash the artwork data
                art_hash = hashlib.sha256(img_data).hexdigest()
                cached_file = ARTWORK_CACHE_DIR / f"{art_hash}.jpg"
                if not cached_file.exists():
                    with open(cached_file, "wb") as f:
                        f.write(img_data)
                return art_hash
            except Exception:
                pass
        return ""

    def _db_save_song_conn(self, cursor, song: Song):
        """Saves song details to SQLite using current transaction cursor."""
        data = {
            "id": song.id,
            "current_path": str(song.path.resolve()),
            "original_path": str(song.original_path.resolve()) if song.original_path else str(song.path.resolve()),
            "title": song.title,
            "artist": song.artist,
            "album": song.album,
            "album_artist": song.album_artist,
            "track_num": song.track_num,
            "disc_num": song.disc_num,
            "genre": song.genre,
            "year": song.year,
            "composer": song.composer,
            "lyrics": song.lyrics,
            "comment": song.comment,
            "duration": song.duration,
            "bitrate": song.bitrate,
            "sample_rate": song.sample_rate,
            "channels": song.channels,
            "file_hash": song.file_hash,
            "artwork_hash": song.artwork_hash,
            "folder_assignment": song.folder_assignment,
            "custom_tags": json.dumps(song.custom_tags),
            "user_notes": song.user_notes,
            "rating": song.rating,
            "favorite": song.favorite,
            "times_organized": song.times_organized,
            "last_scan": song.last_scan,
            "created_date": song.created_date,
            "modified_date": song.modified_date
        }
        cursor.execute("""
        INSERT INTO songs (
            id, current_path, original_path, title, artist, album, album_artist,
            track_num, disc_num, genre, year, composer, lyrics, comment, duration,
            bitrate, sample_rate, channels, file_hash, artwork_hash, folder_assignment,
            custom_tags, user_notes, rating, favorite, times_organized, last_scan,
            created_date, modified_date
        ) VALUES (
            :id, :current_path, :original_path, :title, :artist, :album, :album_artist,
            :track_num, :disc_num, :genre, :year, :composer, :lyrics, :comment, :duration,
            :bitrate, :sample_rate, :channels, :file_hash, :artwork_hash, :folder_assignment,
            :custom_tags, :user_notes, :rating, :favorite, :times_organized, :last_scan,
            :created_date, :modified_date
        )
        ON CONFLICT(id) DO UPDATE SET
            current_path = excluded.current_path,
            title = COALESCE(NULLIF(excluded.title, ''), title),
            artist = COALESCE(NULLIF(excluded.artist, ''), artist),
            album = COALESCE(NULLIF(excluded.album, ''), album),
            album_artist = COALESCE(NULLIF(excluded.album_artist, ''), album_artist),
            track_num = COALESCE(NULLIF(excluded.track_num, ''), track_num),
            disc_num = COALESCE(NULLIF(excluded.disc_num, ''), disc_num),
            genre = COALESCE(NULLIF(excluded.genre, ''), genre),
            year = COALESCE(NULLIF(excluded.year, ''), year),
            composer = COALESCE(NULLIF(excluded.composer, ''), composer),
            lyrics = COALESCE(NULLIF(excluded.lyrics, ''), lyrics),
            comment = COALESCE(NULLIF(excluded.comment, ''), comment),
            duration = COALESCE(NULLIF(excluded.duration, 0.0), duration),
            bitrate = COALESCE(NULLIF(excluded.bitrate, 0), bitrate),
            sample_rate = COALESCE(NULLIF(excluded.sample_rate, 0), sample_rate),
            channels = COALESCE(NULLIF(excluded.channels, 0), channels),
            artwork_hash = COALESCE(NULLIF(excluded.artwork_hash, ''), artwork_hash),
            last_scan = excluded.last_scan,
            modified_date = excluded.modified_date
        """, data)
