import unittest
from pathlib import Path
from musicsort.database.db_manager import DBManager

class TestDBManager(unittest.TestCase):
    def setUp(self):
        # Reset DBManager singleton for testing
        DBManager._instance = None
        self.db_test_path = Path("test_musicsort.db")
        if self.db_test_path.exists():
            try:
                self.db_test_path.unlink()
            except Exception:
                pass
        self.db = DBManager(db_path=self.db_test_path)

    def tearDown(self):
        # Close connection and clean up database file
        DBManager._instance = None
        if hasattr(self, "db_test_path") and self.db_test_path.exists():
            try:
                self.db_test_path.unlink()
            except Exception:
                pass

    def test_categories_seeding(self):
        cats = self.db.get_categories()
        self.assertIn("Romantic", cats)
        self.assertIn("Chill", cats)
        self.assertIn("Others", cats)

    def test_dynamic_categories(self):
        # Create
        self.assertTrue(self.db.add_category("Workout"))
        self.assertIn("Workout", self.db.get_categories())
        
        # Prevent duplicates
        self.assertTrue(self.db.add_category("Workout"))
        
        # Delete
        self.assertTrue(self.db.delete_category("Workout"))
        self.assertNotIn("Workout", self.db.get_categories())
        
        # Prevent core delete
        self.assertFalse(self.db.delete_category("Others"))

    def test_song_inserts_and_updates(self):
        song_data = {
            "id": "test_uuid_1",
            "current_path": "/path/to/test.mp3",
            "original_path": "/path/to/test.mp3",
            "title": "Test Title",
            "artist": "Test Artist",
            "album": "Test Album",
            "album_artist": "",
            "track_num": "1",
            "disc_num": "",
            "genre": "Rock",
            "year": "2023",
            "composer": "",
            "lyrics": "",
            "comment": "",
            "duration": 240.5,
            "bitrate": 320,
            "sample_rate": 44100,
            "channels": 2,
            "file_hash": "dummy_sha256",
            "artwork_hash": "",
            "folder_assignment": "Others",
            "custom_tags": "[]",
            "user_notes": "",
            "rating": 4,
            "favorite": 1,
            "times_organized": 0,
            "last_scan": "2026-07-11T19:30:00",
            "created_date": "2026-07-11T19:30:00",
            "modified_date": "2026-07-11T19:30:00"
        }
        
        # Insert
        self.assertTrue(self.db.insert_or_update_song(song_data))
        
        # Retrieve by ID
        song = self.db.get_song("test_uuid_1")
        self.assertIsNotNone(song)
        self.assertEqual(song["title"], "Test Title")
        self.assertEqual(song["favorite"], 1)

        # Update field
        self.assertTrue(self.db.update_song_field("test_uuid_1", "folder_assignment", "Chill"))
        song = self.db.get_song("test_uuid_1")
        self.assertEqual(song["folder_assignment"], "Chill")

        # Search song
        results = self.db.search_songs("Title", {"favorite": True})
        self.assertEqual(len(results), 1)

    def test_backup_indexing(self):
        backup_entries = [
            ("song_1", "/old/path/1.mp3", "/backup/path/1.mp3"),
            ("song_2", "/old/path/2.mp3", "/backup/path/2.mp3")
        ]
        
        self.assertTrue(self.db.add_backup(
            backup_id="backup_session_1",
            timestamp="20260711_193000",
            backup_dir="/backup/dir",
            description="Unit Test Backup",
            entries=backup_entries
        ))
        
        backups = self.db.get_backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0]["id"], "backup_session_1")

        entries = self.db.get_backup_entries("backup_session_1")
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["song_id"], "song_1")

if __name__ == "__main__":
    unittest.main()
