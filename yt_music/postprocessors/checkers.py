import os

import mutagen

from ..ui import Color, cprint
from .embedders import MP4_TAG_LYRICS


def has_lyrics(filepath: str) -> bool:
    """Check whether an audio file already contains embedded lyrics."""
    if not filepath or not os.path.exists(filepath):
        return False
    try:
        ext = os.path.splitext(filepath)[1].lower()
        audio = mutagen.File(filepath)
        if audio is None:
            return False
        if ext == ".mp3":
            if audio.tags is None:
                return False
            return any(k.startswith("USLT") for k in audio.tags)
        elif ext in {".m4a", ".mp4"}:
            return bool(audio.get(MP4_TAG_LYRICS))
        else:
            return bool(audio.get("lyrics"))
    except Exception as e:
        cprint(f"[check] ⚠ Error reading {filepath}: {e}", Color.YELLOW)
        return False


def has_cover(filepath: str) -> bool:
    """Check whether an audio file already contains embedded cover art."""
    if not filepath or not os.path.exists(filepath):
        return False
    try:
        ext = os.path.splitext(filepath)[1].lower()
        audio = mutagen.File(filepath)
        if audio is None:
            return False
        if ext == ".mp3":
            if audio.tags is None:
                return False
            return any(k.startswith("APIC") for k in audio.tags)
        elif ext in {".m4a", ".mp4"}:
            return bool(audio.get("covr"))
        elif ext == ".flac":
            return bool(audio.pictures)
        elif ext in {".ogg", ".opus"}:
            return bool(audio.get("metadata_block_picture"))
        return False
    except Exception as e:
        cprint(f"[check] ⚠ Error reading {filepath}: {e}", Color.YELLOW)
        return False
