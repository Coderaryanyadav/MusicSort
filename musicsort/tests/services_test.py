import unittest
import shutil
import tempfile
from pathlib import Path
from musicsort.database.db_manager import DBManager
from musicsort.models.domain import Song, CSVRecord, OperationPreview
from musicsort.services.move_engine import MoveEngine
from musicsort.services.csv_validator import CSVValidator
from musicsort.services.backup_service import BackupService

class TestServices(unittest.TestCase):
    def setUp(self):
        # Create temp workspace directories for scan root and target root
        self.temp_dir = tempfile.mkdtemp()
        self.scan_root = Path(self.temp_dir) / "scan_root"
        self.target_root = Path(self.temp_dir) / "target_root"
        self.backup_root = Path(self.temp_dir) / "backup_root"
        
        self.scan_root.mkdir()
        self.target_root.mkdir()
        self.backup_root.mkdir()

        # Reset DBManager singleton for testing
        DBManager._instance = None
        self.db_path = Path(self.temp_dir) / "test_services.db"
        self.db = DBManager(db_path=self.db_path)

        # Create dummy audio files
        self.file1 = self.scan_root / "Eminem - Love The Way You Lie.mp3"
        self.file1.write_text("dummy audio data")
        
        self.file2 = self.scan_root / "01 - Kesariya.flac"
        self.file2.write_text("dummy audio data 2")

        # Convert to domain Song objects
        self.song1 = Song(
            id="hash_eminem_love",
            path=self.file1,
            original_path=self.file1,
            title="Love the Way You Lie",
            artist="Eminem feat. Rihanna",
            album="Recovery",
            folder_assignment="Rap",
            size_bytes=len(self.file1.read_text())
        )
        
        self.song2 = Song(
            id="hash_kesariya",
            path=self.file2,
            original_path=self.file2,
            title="Kesariya",
            artist="Arijit Singh",
            album="Brahmastra",
            folder_assignment="Romantic",
            size_bytes=len(self.file2.read_text())
        )

        # Populate tables
        self.db.add_category("Rap")
        self.db.add_category("Romantic")
        self.db.add_category("Workout")

        # Insert songs into test DB
        self._insert_song_db(self.song1)
        self._insert_song_db(self.song2)

    def tearDown(self):
        # Reset DBManager singleton and clean up temp files
        DBManager._instance = None
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def _insert_song_db(self, song: Song):
        """Helper to insert full record matching SQLite schema."""
        data = {
            "id": song.id,
            "current_path": str(song.path.resolve()),
            "original_path": str(song.original_path.resolve()) if song.original_path else str(song.path.resolve()),
            "title": song.title,
            "artist": song.artist,
            "album": song.album,
            "album_artist": "",
            "track_num": "",
            "disc_num": "",
            "genre": "",
            "year": "",
            "composer": "",
            "lyrics": "",
            "comment": "",
            "duration": 0.0,
            "bitrate": 0,
            "sample_rate": 0,
            "channels": 0,
            "file_hash": "",
            "artwork_hash": "",
            "folder_assignment": song.folder_assignment,
            "custom_tags": "[]",
            "user_notes": "",
            "rating": 0,
            "favorite": 0,
            "times_organized": 0,
            "last_scan": "",
            "created_date": "",
            "modified_date": ""
        }
        self.db.insert_or_update_song(data)

    def test_move_engine_preview_generation(self):
        engine = MoveEngine()
        
        # Test preview with standard metadata names
        previews = engine.generate_previews([self.song1, self.song2], self.target_root)
        self.assertEqual(len(previews), 2)
        
        # Check generated paths
        preview_map = {p.original_path.name: p for p in previews}
        self.assertIn(self.file1.name, preview_map)
        self.assertIn(self.file2.name, preview_map)
        
        # Kesariya should end up in target_root/Romantic/Arijit Singh - Kesariya.flac
        p_kesariya = preview_map[self.file2.name]
        self.assertEqual(p_kesariya.target_path.parent.name, "Romantic")
        self.assertEqual(p_kesariya.target_path.name, "Arijit Singh - Kesariya.flac")
        self.assertEqual(p_kesariya.operation_type, "rename_and_move")

    def test_move_engine_csv_overrides(self):
        engine = MoveEngine()
        csv_mappings = [
            {"filename": self.file1.name, "new_filename": "override_love.mp3", "folder": "Workout"}
        ]
        
        previews = engine.generate_previews([self.song1], self.target_root, csv_mappings)
        self.assertEqual(len(previews), 1)
        self.assertEqual(previews[0].target_path.name, "override_love.mp3")
        self.assertEqual(previews[0].target_path.parent.name, "Workout")

    def test_csv_validator(self):
        validator = CSVValidator()
        
        # Create a test CSV mapping file
        csv_path = Path(self.temp_dir) / "mappings.csv"
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("filename,new_filename,folder\n")
            f.write(f"{self.file1.name},Custom Love.mp3,Rap\n")
            f.write(f"{self.file2.name},Custom Kesariya.flac,Romantic\n")

        records, issues, report_path = validator.validate_csv(csv_path, [self.song1, self.song2], self.scan_root)
        
        # No errors should be found
        errors = [i for i in issues if i.severity == "error"]
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(records), 2)
        self.assertTrue(report_path.exists())

        # Test duplicate destination error validation
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("filename,new_filename,folder\n")
            f.write(f"{self.file1.name},Conflict.mp3,Workout\n")
            f.write(f"{self.file2.name},Conflict.mp3,Workout\n")

        records, issues, report_path = validator.validate_csv(csv_path, [self.song1, self.song2], self.scan_root)
        dup_dest_issues = [i for i in issues if i.type == "duplicate_destination"]
        self.assertTrue(len(dup_dest_issues) > 0)

    def test_backup_and_restore_service(self):
        backup = BackupService(db_manager=self.db, backup_root=self.backup_root)
        
        # Retrieve db format dictionaries
        songs_to_backup = [self.db.get_song(self.song1.id)]
        
        # Create restore point backup session
        backup_id = backup.create_backup_session(songs_to_backup, "Test Restore Session")
        self.assertIsNotNone(backup_id)
        
        # Verify files were copied inside backup folder
        backups = backup.list_backups()
        self.assertEqual(len(backups), 1)
        
        # Modify path (simulate move operation)
        new_path = self.target_root / "Workout" / "Eminem - Target.mp3"
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(self.file1, new_path)
        self.db.update_song_field(self.song1.id, "current_path", str(new_path))
        
        # Restore backup
        success = backup.restore_backup(backup_id)
        self.assertTrue(success)
        
        # Original file should be back in original path, target path should be empty
        self.assertTrue(self.file1.exists())
        self.assertFalse(new_path.exists())
        
        # DB path should be rolled back to original
        song = self.db.get_song(self.song1.id)
        self.assertEqual(song["current_path"], str(self.file1.resolve()))

    def test_physical_tag_writing_on_invalid_file(self):
        from musicsort.utils.tag_writer import write_tags_to_file
        # A dummy file will fail mutagen parsing, returning False
        res = write_tags_to_file(self.file1, {"title": "New Title"})
        self.assertFalse(res)

if __name__ == "__main__":
    unittest.main()
