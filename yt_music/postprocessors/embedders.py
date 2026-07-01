import base64
import os
import shutil
import tempfile

import mutagen

from ..imaging import crop_to_square, resize_square
from ..ui import Color, cprint

MP4_TAG_LYRICS = "\xa9lyr"

SUPPORTED_EXTS = {".mp3", ".m4a", ".mp4", ".flac", ".ogg", ".opus"}


def _embed_thumbnail_mp3(audio_path: str, image_data: bytes) -> None:
    import mutagen.mp3
    from mutagen.id3 import APIC

    audio = mutagen.mp3.MP3(audio_path)
    if audio.tags is None:
        audio.add_tags()
    assert audio.tags is not None
    audio.tags.delall("APIC")
    audio.tags.add(
        APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=image_data)
    )
    audio.save()


def _embed_thumbnail_m4a(audio_path: str, image_data: bytes) -> None:
    from mutagen.mp4 import MP4, MP4Cover

    audio = MP4(audio_path)
    audio["covr"] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()


def _embed_thumbnail_flac(audio_path: str, image_data: bytes) -> None:
    from mutagen.flac import FLAC, Picture

    audio = FLAC(audio_path)
    pic = Picture()
    pic.type = 3
    pic.mime = "image/jpeg"
    pic.data = image_data
    audio.clear_pictures()
    audio.add_picture(pic)
    audio.save()


def _embed_thumbnail_ogg(audio_path: str, image_data: bytes) -> None:
    from mutagen.flac import Picture

    pic = Picture()
    pic.type = 3
    pic.mime = "image/jpeg"
    pic.data = image_data
    audio = mutagen.File(audio_path)
    if audio is None:
        return
    audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode("ascii")]
    audio.save()


_EMBEDDERS = {
    ".mp3": _embed_thumbnail_mp3,
    ".m4a": _embed_thumbnail_m4a,
    ".mp4": _embed_thumbnail_m4a,
    ".flac": _embed_thumbnail_flac,
    ".ogg": _embed_thumbnail_ogg,
    ".opus": _embed_thumbnail_ogg,
}


def embed_lyrics(filepath: str, lyrics: str) -> bool:
    """Embed lyrics into an audio file. Returns True on success."""
    if not lyrics or not filepath or not os.path.exists(filepath):
        return False
    try:
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".mp3":
            from mutagen.id3 import USLT

            audio = mutagen.File(filepath)
            if audio is None:
                return False
            if audio.tags is None:
                audio.add_tags()
            audio.tags.delall("USLT")
            audio.tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics))
            audio.save()
            cprint("[lyrics] ✓ Embedded USLT tag into MP3.", Color.MAGENTA)
        elif ext in {".m4a", ".mp4"}:
            from mutagen.mp4 import MP4

            audio = MP4(filepath)
            audio[MP4_TAG_LYRICS] = [lyrics]
            audio.save()
            cprint("[lyrics] ✓ Embedded lyrics tag into MP4/M4A.", Color.MAGENTA)
        else:
            audio = mutagen.File(filepath)
            if audio is not None:
                audio["lyrics"] = lyrics
                audio.save()
                cprint(
                    f"[lyrics] ✓ Embedded lyric tag into {ext.upper()}.", Color.MAGENTA
                )
        return True
    except ImportError:
        cprint("[lyrics] ⚠ Mutagen not installed. Skipping lyrics embed.", Color.YELLOW)
    except Exception as e:
        cprint(f"[lyrics] ✗ Failed to embed lyrics in {filepath}: {e}", Color.RED)
    return False


def embed_cover(filepath: str, image_data: bytes, is_square: bool = False) -> bool:
    """Embed cover art into an audio file. Returns True on success."""
    if not image_data or not filepath or not os.path.exists(filepath):
        return False

    ext = os.path.splitext(filepath)[1].lower()
    embedder = _EMBEDDERS.get(ext)
    if embedder is None:
        cprint(f"[cover] ⊘ No embedder for {ext}, skipping", Color.YELLOW)
        return False

    fd, tmp_path = tempfile.mkstemp(suffix=".jpg", prefix="ytmusic_cover_")
    os.close(fd)
    with open(tmp_path, "wb") as f:
        f.write(image_data)

    cover_path = filepath + ".cover.jpg"
    try:
        success = resize_square(tmp_path) if is_square else crop_to_square(tmp_path)

        if not success:
            cprint("[cover] ⚠ Image processing failed, using original", Color.YELLOW)

        shutil.move(tmp_path, cover_path)

        with open(cover_path, "rb") as f:
            processed_data = f.read()

        if not processed_data.startswith(b"\xff\xd8"):
            cprint("[cover] ⊘ Invalid JPEG data, skipping embed", Color.YELLOW)
            return False

        embedder(filepath, processed_data)
        cprint("[cover] ✓ Embedded thumbnail into audio", Color.CYAN)
        return True
    except Exception as e:
        cprint(f"[cover] ✗ Failed to embed thumbnail: {e}", Color.RED)
        return False
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if os.path.exists(cover_path):
            os.unlink(cover_path)
