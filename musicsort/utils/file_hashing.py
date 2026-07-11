import hashlib
from pathlib import Path

def calculate_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """
    Computes the SHA256 checksum of a file by reading it in chunks.
    Returns the hex digest string.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        # Fallback or empty if unreadable
        return ""
