import re

# Minor words that should not be capitalized unless they start a title or artist name
MINOR_WORDS = {"a", "an", "the", "and", "but", "or", "for", "nor", "on", "in", "at", "to", "by", "of", "with", "from", "up", "prod"}

# Version markers to preserve
VERSION_MARKERS = [
    r"remaster(?:ed)?", r"live", r"acoustic", r"version", r"radio\s*edit", r"mix", r"remix", r"prod\b", r"ft\b", r"feat\b"
]

def clean_filename(filename: str) -> str:
    """
    Intelligently cleans a music filename by:
    1. Removing extensions.
    2. Parsing composite names (e.g. 'Atif_Aslam_Greatest_Hits_09_Bheegi_Yaadein') by identifying
       embedded track numbers.
    3. Standardizing collaborations to 'feat.'.
    4. Preserving version information, acronyms, and formatting.
    """
    if not filename:
        return ""

    # Remove extension
    name = filename
    for ext in [".mp3", ".m4a", ".flac", ".aac", ".alac", ".wav", ".aiff", ".ogg", ".opus", ".ape"]:
        if name.lower().endswith(ext):
            name = name[:-len(ext)]
            break
    else:
        if "." in name:
            name = name.rsplit(".", 1)[0]

    # Clean underscores and normalize spaces
    name = name.replace("_", " ")

    # Check for version indicators in parentheses/brackets (e.g. '(Live)', '[Remastered 2020]')
    # We want to preserve them. Let's extract them first and append them back later if they match version info.
    versions_found = []
    
    # Locate all content inside (...) and [...]
    brackets = re.findall(r'([\(\[][^\]\)]+[\]\)])', name)
    for bracket in brackets:
        bracket_content = bracket[1:-1].strip().lower()
        # If the content matches version keywords, we preserve a cleaned version of it
        matches_version = any(re.search(marker, bracket_content) for marker in VERSION_MARKERS)
        if matches_version:
            # Reformat inside, e.g. title-case
            words = bracket_content.split()
            cleaned_words = [w.capitalize() if w.lower().strip(".,;:!?") not in MINOR_WORDS else w.lower() for w in words]
            # Retain brackets
            opening = bracket[0]
            closing = bracket[-1]
            versions_found.append(f"{opening}{' '.join(cleaned_words)}{closing}")
        # Strip all brackets for clean parsing, we'll append the preserved versions back at the end
        name = name.replace(bracket, "")

    # Clean extra dashes and spaces
    name = re.sub(r'\s+', ' ', name).strip()

    # 1. Parse track number at the start
    # Matches zero-padded track numbers (e.g., "01 Song") or any track number with a separator (e.g., "1 - Song", "12. Song")
    # Prevents false positives on names like "50 Cent" or "3 Doors Down"
    start_match = re.match(r'^(0\d{1,2}\s+|(\d{1,3})\s*[-–—.]|(\d{1,3})\s+[-–—])\s*', name)
    if start_match:
        name = name[start_match.end():]
        # Strip leading delimiters
        name = re.sub(r'^[-–—.\s]+', '', name).strip()
    else:
        # 2. Parse embedded middle track numbers (e.g., "Atif Aslam Greatest Hits 09 Bheegi Yaadein")
        # Only matches if zero-padded or enclosed in separators to prevent false positives like "Summer of 69"
        middle_match = re.search(r'\b(0\d{1,2}|-\s*\d{1,3}\s*-)\b', name)
        if middle_match:
            span = middle_match.span()
            left = name[:span[0]].strip()
            right = name[span[1]:].strip()
            
            # Clean delimiters
            left = re.sub(r'[-–—.\s]+$', '', left).strip()
            right = re.sub(r'^[-–—.\s]+', '', right).strip()
            
            # If the right side has words, it represents the song title
            if right:
                name = right

    # Standardize collaborations: ft, ft., feat, featuring, with -> feat.
    name = re.sub(r'\b(feat|ft|featuring|with)\b\.?', 'feat.', name, flags=re.IGNORECASE)

    # Re-case name, preserving acronyms and title-casing others
    words = name.split()
    cleaned_words = []
    
    for i, word in enumerate(words):
        stripped_word = word.strip(".,()[]{}!?;:\"'")
        is_acronym = len(stripped_word) >= 2 and stripped_word.isupper()
        
        # Check normalized lowercase string for keyword matches
        stripped_lower = stripped_word.lower()
        
        if is_acronym:
            cleaned_words.append(word)
        elif stripped_lower in ("feat", "feat."):
            cleaned_words.append("feat.")
        elif stripped_lower in MINOR_WORDS and i > 0 and i < len(words) - 1:
            cleaned_words.append(word.lower())
        else:
            prefix = word[:word.index(stripped_word)] if stripped_word in word and word.index(stripped_word) > 0 else ""
            suffix = word[word.index(stripped_word)+len(stripped_word):] if stripped_word in word else ""
            cleaned_words.append(f"{prefix}{stripped_word.capitalize()}{suffix}")
            
    name = " ".join(cleaned_words)
    
    # Append version tags back
    if versions_found:
        name = f"{name} {' '.join(versions_found)}"

    # Clean double spaces
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'^[-–—\s]+|[-–—\s]+$', '', name).strip()
    
    return name

def split_artist_title(cleaned_name: str) -> tuple[str, str]:
    """
    Splits a cleaned name into (Artist, Title).
    Matches common separators.
    """
    separators = [" - ", " – ", " — "]
    for sep in separators:
        if sep in cleaned_name:
            parts = cleaned_name.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return "", cleaned_name
