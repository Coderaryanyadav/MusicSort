import sqlite3
import threading
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from musicsort.core.config import DEFAULT_DB_PATH, DEFAULT_CATEGORIES
from musicsort.core.logger import get_operations_logger, get_errors_logger

class DBManager:
    """
    Thread-safe SQLite Database Manager for MusicSort.
    Serves as the single source of truth for library metadata, backups, and user settings.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(DBManager, cls).__new__(cls)
            return cls._instance

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        # Re-initialize only if the database path changes or not yet initialized
        if hasattr(self, "_initialized") and hasattr(self, "db_path") and self.db_path == db_path:
            return
        self.db_path = db_path
        self.op_logger = get_operations_logger()
        self.err_logger = get_errors_logger()
        self._initialized = True
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns a database connection with dictionary factory enabled."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Enable Foreign Keys support in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        """Initializes database tables, schemas, and seeds default categories."""
        self.op_logger.info(f"Initializing SQLite Database at: {self.db_path}")
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Create categories table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # 2. Create songs table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id TEXT PRIMARY KEY,
                current_path TEXT UNIQUE,
                original_path TEXT,
                title TEXT,
                artist TEXT,
                album TEXT,
                album_artist TEXT,
                track_num TEXT,
                disc_num TEXT,
                genre TEXT,
                year TEXT,
                composer TEXT,
                lyrics TEXT,
                comment TEXT,
                duration REAL,
                bitrate INTEGER,
                sample_rate INTEGER,
                channels INTEGER,
                file_hash TEXT,
                artwork_hash TEXT,
                folder_assignment TEXT DEFAULT 'Others',
                custom_tags TEXT,
                user_notes TEXT,
                rating INTEGER DEFAULT 0,
                favorite INTEGER DEFAULT 0,
                times_organized INTEGER DEFAULT 0,
                last_scan TIMESTAMP,
                created_date TIMESTAMP,
                modified_date TIMESTAMP,
                FOREIGN KEY(folder_assignment) REFERENCES categories(name) ON DELETE SET DEFAULT
            );
            """)

            # 3. Create backups index tables
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backups (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                backup_dir TEXT,
                description TEXT
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS backup_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_id TEXT,
                song_id TEXT,
                original_path TEXT,
                backup_path TEXT,
                FOREIGN KEY(backup_id) REFERENCES backups(id) ON DELETE CASCADE
            );
            """)
            
            conn.commit()

            # Seed default categories
            cursor.execute("SELECT COUNT(*) FROM categories;")
            if cursor.fetchone()[0] == 0:
                self.op_logger.info("Seeding default categories into database.")
                for cat in DEFAULT_CATEGORIES:
                    cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?);", (cat,))
                conn.commit()

        except Exception as e:
            self.err_logger.error(f"Failed to initialize database: {e}")
            conn.rollback()
        finally:
            conn.close()

    # CATEGORY OPERATIONS
    def get_categories(self) -> List[str]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT name FROM categories ORDER BY name ASC;")
                rows = cursor.fetchall()
                return [r["name"] for r in rows]
            except Exception as e:
                self.err_logger.error(f"Failed to load categories: {e}")
                return []
            finally:
                conn.close()

    def add_category(self, name: str) -> bool:
        name = name.strip()
        if not name:
            return False
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?);", (name,))
                conn.commit()
                return True
            except Exception as e:
                self.err_logger.error(f"Failed to add category {name}: {e}")
                return False
            finally:
                conn.close()

    def delete_category(self, name: str) -> bool:
        if name == "Others":
            return False  # "Others" is a mandatory fallback folder
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM categories WHERE name = ?;", (name,))
                conn.commit()
                return True
            except Exception as e:
                self.err_logger.error(f"Failed to delete category {name}: {e}")
                return False
            finally:
                conn.close()

    # SONG OPERATIONS
    def insert_or_update_song(self, data: Dict[str, Any]) -> bool:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
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
                    file_hash = COALESCE(NULLIF(excluded.file_hash, ''), file_hash),
                    artwork_hash = COALESCE(NULLIF(excluded.artwork_hash, ''), artwork_hash),
                    last_scan = excluded.last_scan,
                    modified_date = excluded.modified_date
                """, data)
                conn.commit()
                return True
            except Exception as e:
                self.err_logger.error(f"Failed to save song record {data.get('current_path')}: {e}")
                return False
            finally:
                conn.close()

    def get_song(self, song_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM songs WHERE id = ?;", (song_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
            except Exception as e:
                self.err_logger.error(f"Failed to fetch song {song_id}: {e}")
                return None
            finally:
                conn.close()

    def get_song_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM songs WHERE current_path = ?;", (path,))
                row = cursor.fetchone()
                return dict(row) if row else None
            except Exception as e:
                self.err_logger.error(f"Failed to fetch song by path {path}: {e}")
                return None
            finally:
                conn.close()

    def get_all_songs(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM songs;")
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            except Exception as e:
                self.err_logger.error(f"Failed to fetch all songs: {e}")
                return []
            finally:
                conn.close()

    def delete_song(self, song_id: str) -> bool:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM songs WHERE id = ?;", (song_id,))
                conn.commit()
                return True
            except Exception as e:
                self.err_logger.error(f"Failed to delete song {song_id}: {e}")
                return False
            finally:
                conn.close()

    def update_song_field(self, song_id: str, field_name: str, value: Any) -> bool:
        """Dynamically updates a single field for a song."""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                # Vulnerability prevention: enforce strictly formatted field names
                allowed_fields = {
                    "folder_assignment", "rating", "favorite", "times_organized",
                    "custom_tags", "user_notes", "current_path", "original_path",
                    "title", "artist", "album", "genre", "year", "file_hash"
                }
                if field_name not in allowed_fields:
                    raise ValueError(f"Unauthorized field update requested: {field_name}")
                
                cursor.execute(f"UPDATE songs SET {field_name} = ? WHERE id = ?;", (value, song_id))
                conn.commit()
                return True
            except Exception as e:
                self.err_logger.error(f"Failed to update song {song_id} field {field_name}: {e}")
                return False
            finally:
                conn.close()

    def search_songs(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Advanced thread-safe SQLite search utility supporting text query
        and criteria filtering (Rating, Year, Album, Artist, Genre, Extension, Folder).
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                sql = "SELECT * FROM songs WHERE 1=1"
                params = []

                if query:
                    # Match across title, artist, album, genre, custom tags
                    sql += " AND (title LIKE ? OR artist LIKE ? OR album LIKE ? OR genre LIKE ? OR custom_tags LIKE ? OR current_path LIKE ?)"
                    q = f"%{query}%"
                    params.extend([q, q, q, q, q, q])

                if filters:
                    for key, val in filters.items():
                        if key == "rating":
                            sql += " AND rating >= ?"
                            params.append(val)
                        elif key == "favorite":
                            sql += " AND favorite = ?"
                            params.append(1 if val else 0)
                        elif key == "folder":
                            sql += " AND folder_assignment = ?"
                            params.append(val)
                        elif key == "artist" and val:
                            sql += " AND artist = ?"
                            params.append(val)
                        elif key == "genre" and val:
                            sql += " AND genre = ?"
                            params.append(val)
                        elif key == "extension" and val:
                            sql += " AND current_path LIKE ?"
                            params.append(f"%.{val.lower().strip('.')}")

                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
            except Exception as e:
                self.err_logger.error(f"Search query failed: {e}")
                return []
            finally:
                conn.close()

    # BACKUP INDEX OPERATIONS
    def add_backup(self, backup_id: str, timestamp: str, backup_dir: str, description: str, entries: List[Tuple[str, str, str]]) -> bool:
        """
        Adds a backup session to SQLite index.
        Entries is a list of tuples: (song_id, original_path, backup_path)
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO backups (id, timestamp, backup_dir, description) VALUES (?, ?, ?, ?);",
                    (backup_id, timestamp, backup_dir, description)
                )
                for song_id, orig, back in entries:
                    cursor.execute(
                        "INSERT INTO backup_entries (backup_id, song_id, original_path, backup_path) VALUES (?, ?, ?, ?);",
                        (backup_id, song_id, orig, back)
                    )
                conn.commit()
                return True
            except Exception as e:
                self.err_logger.error(f"Failed to record backup session in DB: {e}")
                conn.rollback()
                return False
            finally:
                conn.close()

    def get_backups(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM backups ORDER BY timestamp DESC;")
                return [dict(r) for r in cursor.fetchall()]
            except Exception as e:
                self.err_logger.error(f"Failed to fetch backups: {e}")
                return []
            finally:
                conn.close()

    def get_backup_entries(self, backup_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM backup_entries WHERE backup_id = ?;", (backup_id,))
                return [dict(r) for r in cursor.fetchall()]
            except Exception as e:
                self.err_logger.error(f"Failed to fetch backup entries: {e}")
                return []
            finally:
                conn.close()

    def delete_backup(self, backup_id: str) -> bool:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM backups WHERE id = ?;", (backup_id,))
                conn.commit()
                return True
            except Exception as e:
                self.err_logger.error(f"Failed to delete backup session {backup_id} in DB: {e}")
                return False
            finally:
                conn.close()
