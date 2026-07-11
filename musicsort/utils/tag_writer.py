import mutagen
from pathlib import Path
from musicsort.core.logger import get_operations_logger, get_errors_logger

def write_tags_to_file(file_path: Path, tags: dict) -> bool:
    """
    Writes metadata tags back to the physical audio file using mutagen.
    Supported keys: title, artist, album, genre, year.
    """
    op_logger = get_operations_logger()
    err_logger = get_errors_logger()
    
    if not file_path.exists():
        err_logger.error(f"Cannot write tags, file not found: {file_path}")
        return False

    try:
        # Easy tags interface simplifies standard tag writing
        easy_audio = mutagen.File(file_path, easy=True)
        if easy_audio is not None:
            if "title" in tags:
                easy_audio["title"] = [tags["title"]]
            if "artist" in tags:
                easy_audio["artist"] = [tags["artist"]]
            if "album" in tags:
                easy_audio["album"] = [tags["album"]]
            if "genre" in tags:
                easy_audio["genre"] = [tags["genre"]]
            
            # Map year/date
            if "year" in tags and tags["year"]:
                # Many tag formats expect 'date' instead of 'year'
                easy_audio["date"] = [tags["year"]]
            
            easy_audio.save()
            op_logger.info(f"Successfully saved physical tags back to disk: {file_path.name}")
            return True
        return False
    except Exception as e:
        err_logger.error(f"Failed to write tags to file {file_path.name}: {e}")
        return False
