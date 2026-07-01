import os

import mutagen

from .coverart import fetch_cover_art_chain
from .lyrics import fetch_lyrics_chain
from .postprocessors import (
    SUPPORTED_EXTS,
    embed_cover,
    embed_lyrics,
    has_cover,
    has_lyrics,
)
from .ui import Color, cprint

MP4_TAG_ARTIST = "\xa9ART"
MP4_TAG_TITLE = "\xa9nam"


def extract_tags(filepath: str) -> tuple[str, str]:
    """Extract artist and title tags from an audio file."""
    try:
        audio = mutagen.File(filepath)
        if audio is None:
            return "", ""

        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".mp3":
            artist = str(audio.get("TPE1", "")).strip()
            title = str(audio.get("TIT2", "")).strip()
        elif ext in {".m4a", ".mp4"}:
            from mutagen.mp4 import MP4

            if isinstance(audio, MP4):
                artist = next(iter(audio.get(MP4_TAG_ARTIST, [])), "")
                title = next(iter(audio.get(MP4_TAG_TITLE, [])), "")
            else:
                artist, title = "", ""
        else:
            artist_tag = audio.get("artist")
            title_tag = audio.get("title")
            artist = (
                artist_tag[0] if isinstance(artist_tag, list) else str(artist_tag or "")
            )
            title = (
                title_tag[0] if isinstance(title_tag, list) else str(title_tag or "")
            )
            artist = artist.strip()
            title = title.strip()

        return artist, title
    except Exception as e:
        cprint(f"[fix] \u2717 Failed to read tags from {filepath}: {e}", Color.RED)
        return "", ""


def fix_folder(
    path: str,
    fix_lyrics: bool,
    fix_covers: bool,
    lyrics_providers: list[str],
    cover_providers: list[str],
    force: bool,
) -> None:
    """Scan a folder for audio files and fix missing lyrics or cover art."""
    if not os.path.isdir(path):
        cprint(f"[fix] \u2717 Path not found: {path}", Color.RED)
        return

    files = [
        f for f in os.listdir(path) if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
    ]
    files.sort()

    if not files:
        cprint(f"[fix] No supported audio files found in {path}", Color.YELLOW)
        return

    cprint(f"[fix] Scanning {len(files)} file(s) in {path}", Color.CYAN)

    stats = {"lyrics": 0, "covers": 0, "skipped": 0}

    for filename in files:
        filepath = os.path.join(path, filename)

        artist, title = extract_tags(filepath)
        if not artist or not title:
            cprint(
                f"[fix] \u2298 Skipped (no artist/title tags): {filename}", Color.YELLOW
            )
            stats["skipped"] += 1
            continue

        cprint(f"\n[fix] {artist} - {title}", Color.BOLD)

        if fix_lyrics:
            if has_lyrics(filepath) and not force:
                cprint("  [lyrics] \u2298 Already has lyrics", Color.YELLOW)
            else:
                lyrics, _ = fetch_lyrics_chain(artist, title, lyrics_providers)
                if lyrics:
                    if embed_lyrics(filepath, lyrics):
                        stats["lyrics"] += 1
                else:
                    cprint("  [lyrics] \u2298 Not found", Color.YELLOW)

        if fix_covers:
            if has_cover(filepath) and not force:
                cprint("  [cover] \u2298 Already has artwork", Color.YELLOW)
            else:
                image_bytes, _, is_square = fetch_cover_art_chain(
                    artist, title, cover_providers
                )
                if image_bytes:
                    if embed_cover(filepath, image_bytes, is_square):
                        stats["covers"] += 1
                else:
                    cprint("  [cover] \u2298 Not found", Color.YELLOW)

    cprint(
        f"\n[fix] Done. Lyrics: {stats['lyrics']} fixed,"
        f" Cover art: {stats['covers']} fixed,"
        f" {stats['skipped']} skipped",
        Color.CYAN,
    )
