import base64
import os
import shutil
import tempfile

import mutagen
from yt_dlp.postprocessor import PostProcessor

from .coverart import fetch_cover_art_chain
from .imaging import crop_to_square, resize_square
from .lyrics import fetch_lyrics_chain
from .ui import Color, cprint

_KNOWN_SQUARE_COVER = {"deezer"}

MP4_TAG_LYRICS = "\xa9lyr"


class LyricsFetcherPP(PostProcessor):
    def __init__(self, summary=None, providers=None):
        super().__init__()
        self.summary = summary
        self.providers = providers

    def run(self, info):
        artist = (info.get("artist") or info.get("uploader") or "").strip()
        title = (info.get("title") or "").strip()

        lyrics, provider = fetch_lyrics_chain(artist, title, self.providers)
        if lyrics:
            info["meta_lyrics"] = lyrics
            cprint(
                f"[lyrics] ✓ Found via {provider} for: {artist} - {title}",
                Color.MAGENTA,
            )
            if self.summary:
                self.summary.add_lyrics_found(title)
                self.summary.add_lyrics_source(title, provider)
        else:
            cprint(f"[lyrics] ⊘ No lyrics found for: {artist} - {title}", Color.YELLOW)
            if self.summary:
                self.summary.add_lyrics_missing(title)
        return [], info


class EmbedLyricsPP(PostProcessor):
    def run(self, info):
        lyrics = info.get("meta_lyrics")
        filepath = info.get("filepath") or info.get("_filename")
        embed_lyrics(filepath, lyrics)
        return [], info


class CoverArtFetcherPP(PostProcessor):
    def __init__(self, summary=None, providers=None):
        super().__init__()
        self.summary = summary
        self.providers = providers

    def run(self, info):
        artist = (info.get("artist") or info.get("uploader") or "").strip()
        title = (info.get("title") or "").strip()

        image_bytes, provider, _is_square = fetch_cover_art_chain(
            artist, title, self.providers
        )
        if image_bytes:
            fd, tmp_path = tempfile.mkstemp(suffix=".jpg", prefix="ytmusic_cover_")
            with os.fdopen(fd, "wb") as f:
                f.write(image_bytes)
            info["meta_cover_temp_path"] = tmp_path
            info["meta_cover_provider"] = provider
            cprint(f"[cover] ✓ Found via {provider}", Color.CYAN)
            if self.summary:
                self.summary.add_cover_source(title, provider)
        else:
            cprint(
                "[cover] ⊘ No external cover found, using YouTube thumbnail",
                Color.YELLOW,
            )
            if self.summary:
                self.summary.add_cover_source(title, "YouTube fallback")
        return [], info


def _embed_thumbnail_mp3(audio_path, image_data):
    import mutagen.mp3
    from mutagen.id3 import APIC

    audio = mutagen.mp3.MP3(audio_path)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.delall("APIC")
    audio.tags.add(
        APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=image_data)
    )
    audio.save()


def _embed_thumbnail_m4a(audio_path, image_data):
    from mutagen.mp4 import MP4, MP4Cover

    audio = MP4(audio_path)
    audio["covr"] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()


def _embed_thumbnail_flac(audio_path, image_data):
    from mutagen.flac import FLAC, Picture

    audio = FLAC(audio_path)
    pic = Picture()
    pic.type = 3
    pic.mime = "image/jpeg"
    pic.data = image_data
    audio.clear_pictures()
    audio.add_picture(pic)
    audio.save()


def _embed_thumbnail_ogg(audio_path, image_data):
    import mutagen
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

SUPPORTED_EXTS = {".mp3", ".m4a", ".mp4", ".flac", ".ogg", ".opus"}


def has_lyrics(filepath: str) -> bool:
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
            return any(k.startswith("USLT") for k in audio.tags.keys())
        elif ext in {".m4a", ".mp4"}:
            return bool(audio.get(MP4_TAG_LYRICS))
        else:
            return bool(audio.get("lyrics"))
    except Exception as e:
        cprint(f"[check] \u26a0 Error reading {filepath}: {e}", Color.YELLOW)
        return False


def has_cover(filepath: str) -> bool:
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
            return any(k.startswith("APIC") for k in audio.tags.keys())
        elif ext in {".m4a", ".mp4"}:
            return bool(audio.get("covr"))
        elif ext == ".flac":
            return bool(audio.pictures)
        elif ext in {".ogg", ".opus"}:
            return bool(audio.get("metadata_block_picture"))
        return False
    except Exception as e:
        cprint(f"[check] \u26a0 Error reading {filepath}: {e}", Color.YELLOW)
        return False


def embed_lyrics(filepath: str, lyrics: str) -> bool:
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
        if is_square:
            success = resize_square(tmp_path)
        else:
            success = crop_to_square(tmp_path)

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


class EmbedCoverArtPP(PostProcessor):
    def run(self, info):
        filepath = info.get("filepath") or info.get("_filename")
        tmp_cover_path = info.get("meta_cover_temp_path")

        if not filepath or not os.path.exists(filepath):
            if tmp_cover_path and os.path.exists(tmp_cover_path):
                os.unlink(tmp_cover_path)
            return [], info

        provider = info.get("meta_cover_provider", "")
        is_square = provider.lower() in _KNOWN_SQUARE_COVER

        image_data = None
        if tmp_cover_path and os.path.exists(tmp_cover_path):
            with open(tmp_cover_path, "rb") as f:
                image_data = f.read()
            cprint("[cover] ✓ Using external cover art", Color.CYAN)
        else:
            thumb_path = self._find_best_thumbnail(info)
            if thumb_path and os.path.exists(thumb_path):
                with open(thumb_path, "rb") as f:
                    image_data = f.read()

        if image_data:
            embed_cover(filepath, image_data, is_square)

        info.pop("meta_cover_temp_path", None)
        info.pop("meta_cover_provider", None)
        info.pop("meta_cover_is_square", None)
        for thumb in info.get("thumbnails", []):
            fp = thumb.get("filepath")
            if fp and os.path.exists(fp):
                os.unlink(fp)

        return [], info

    def _find_best_thumbnail(self, info):
        thumbnails = info.get("thumbnails", [])
        if not thumbnails:
            return None
        best = None
        best_pref = -1
        for thumb in thumbnails:
            fp = thumb.get("filepath", "")
            if not fp or not os.path.exists(fp):
                continue
            pref = thumb.get("preference", 0) or 0
            if pref > best_pref:
                best = fp
                best_pref = pref
        return best or (thumbnails[0].get("filepath") if thumbnails else None)


class CropThumbnailPP(PostProcessor):
    def run(self, info):
        thumbnails = info.get("thumbnails", [])
        for thumb in thumbnails:
            filepath = thumb.get("filepath")
            if filepath and os.path.exists(filepath):
                crop_to_square(filepath)
        return [], info
