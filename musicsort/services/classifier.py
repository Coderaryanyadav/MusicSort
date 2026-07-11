from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from musicsort.models.domain import Song
from musicsort.database.db_manager import DBManager

class SmartClassifier:
    """
    Classifier engine that learns from historical category assignments stored in SQLite.
    Predicts and suggests folder classifications based on multiple features (Artist, Genre, Album, Keywords).
    """
    def __init__(self, db_manager: Optional[DBManager] = None):
        self.db = db_manager if db_manager else DBManager()
        self.artist_model: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.genre_model: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.album_model: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.trained = False

    def train(self):
        """Loads historical decisions from the DB and trains the frequency models."""
        songs = self.db.get_all_songs()
        
        # Reset frequencies
        self.artist_model.clear()
        self.genre_model.clear()
        self.album_model.clear()
        
        trained_count = 0
        for s in songs:
            # We train only on files that have been explicitly classified by the user
            # (ignoring default 'Others' classification unless it was explicitly kept,
            # but usually songs that have times_organized > 0 are perfect training samples)
            if s.get("times_organized", 0) > 0 or s.get("folder_assignment") != "Others":
                folder = s.get("folder_assignment", "Others")
                
                artist = s.get("artist", "").strip().lower()
                genre = s.get("genre", "").strip().lower()
                album = s.get("album", "").strip().lower()
                
                if artist and artist != "unknown artist":
                    self.artist_model[artist][folder] += 1
                if genre:
                    self.genre_model[genre][folder] += 1
                if album:
                    self.album_model[album][folder] += 1
                    
                trained_count += 1
                
        self.trained = True

    def classify(self, song: Song) -> Tuple[str, int]:
        """
        Classifies a song based on historical probability, falling back to keywords matching.
        Returns a tuple of (Suggested Category, Confidence Score %).
        """
        if not self.trained:
            self.train()

        artist = song.artist.strip().lower()
        genre = song.genre.strip().lower()
        album = song.album.strip().lower()
        title = song.title.strip().lower()

        # 1. Match by Album
        if album and album in self.album_model:
            folders = self.album_model[album]
            best_folder = max(folders, key=folders.get)
            return best_folder, 95

        # 2. Match by Artist
        if artist and artist != "unknown artist" and artist in self.artist_model:
            folders = self.artist_model[artist]
            best_folder = max(folders, key=folders.get)
            return best_folder, 90

        # 3. Match by Genre
        if genre and genre in self.genre_model:
            folders = self.genre_model[genre]
            best_folder = max(folders, key=folders.get)
            return best_folder, 80

        # 4. Fallback Keyword Matcher (Rule-based guesses)
        # Check title, genre, and path for category indicator keywords
        keywords_map = {
            "Romantic": ["love", "romantic", "romance", "dil", "pyar", "ishq", "heart", "valentines"],
            "Heartbreak": ["sad", "broken", "heartbreak", "judai", "dard", "gam", "alone"],
            "Chill": ["chill", "ambient", "peaceful", "lofi", "relax", "meditation", "calm", "sleep", "study"],
            "Party": ["party", "dance", "club", "edm", "remix", "beat", "house", "techno", "dhamaka"],
            "Punjabi": ["punjabi", "bhangra", "diljit", "sidhu", "ap dhillon", "dhol"],
            "Rap": ["rap", "hip hop", "hiphop", "eminem", "tupac", "beats", "trap", "flow"]
        }

        for folder, keywords in keywords_map.items():
            for kw in keywords:
                if kw in title or kw in genre:
                    return folder, 70

        # 5. Default Category
        return "Others", 50
