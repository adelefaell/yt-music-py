import os
import tempfile
from typing import Any

from yt_dlp.postprocessor import PostProcessor

from ..coverart import fetch_cover_art_chain
from ..imaging import crop_to_square
from ..lyrics import fetch_lyrics_chain
from ..ui import Color, cprint
from .embedders import embed_cover, embed_lyrics


class LyricsFetcherPP(PostProcessor):
    """Fetch lyrics for a track and store them in the info dict."""

    def __init__(self, summary: Any = None, providers: list[str] | None = None) -> None:
        super().__init__()
        self.summary = summary
        self.providers: list[str] = providers or []

    def run(self, info: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
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
    """Embed previously fetched lyrics into the audio file."""

    def run(self, info: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
        lyrics = info.get("meta_lyrics")
        filepath = info.get("filepath") or info.get("_filename")
        if filepath and lyrics:
            embed_lyrics(str(filepath), str(lyrics))
        return [], info


class CoverArtFetcherPP(PostProcessor):
    """Fetch external cover art for a track and store it in the info dict."""

    def __init__(self, summary: Any = None, providers: list[str] | None = None) -> None:
        super().__init__()
        self.summary = summary
        self.providers: list[str] = providers or []

    def run(self, info: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
        artist = (info.get("artist") or info.get("uploader") or "").strip()
        title = (info.get("title") or "").strip()

        image_bytes, provider, is_square = fetch_cover_art_chain(
            artist, title, self.providers
        )
        if image_bytes:
            fd, tmp_path = tempfile.mkstemp(suffix=".jpg", prefix="ytmusic_cover_")
            with os.fdopen(fd, "wb") as f:
                f.write(image_bytes)
            info["meta_cover_temp_path"] = tmp_path
            info["meta_cover_provider"] = provider
            info["meta_cover_is_square"] = "true" if is_square else "false"
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


class EmbedCoverArtPP(PostProcessor):
    """Embed fetched cover art into the audio file and clean up temp files."""

    def run(self, info: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
        filepath = info.get("filepath") or info.get("_filename")
        tmp_cover_path = info.get("meta_cover_temp_path")

        if not filepath or not os.path.exists(filepath):
            if tmp_cover_path and os.path.exists(tmp_cover_path):
                os.unlink(tmp_cover_path)
            return [], info

        is_square = info.get("meta_cover_is_square", "false") == "true"

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

    def _find_best_thumbnail(self, info: dict[str, Any]) -> str | None:
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
    """Crop YouTube thumbnails to square for consistent cover art."""

    def run(self, info: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
        thumbnails = info.get("thumbnails", [])
        for thumb in thumbnails:
            filepath = thumb.get("filepath")
            if filepath and os.path.exists(filepath):
                crop_to_square(filepath)
        return [], info
