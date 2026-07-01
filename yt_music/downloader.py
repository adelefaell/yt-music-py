import importlib.util
import os

import yt_dlp

from .postprocessors import (
    CoverArtFetcherPP,
    CropThumbnailPP,
    EmbedCoverArtPP,
    EmbedLyricsPP,
    LyricsFetcherPP,
)
from .ui import Color, ProgressTracker, Summary, cprint


def download_tracks(
    urls: list[str],
    fmt: str,
    dl_path: str,
    user_agent: str,
    lyrics_providers: list[str],
    cover_providers: list[str],
) -> None:
    """Download tracks from YouTube URLs with metadata enrichment.

    Args:
        urls: List of YouTube URLs to download.
        fmt: Audio format (e.g., "mp3", "m4a").
        dl_path: Directory path for downloaded files.
        user_agent: User-Agent header for API requests.
        lyrics_providers: List of lyrics provider names to use.
        cover_providers: List of cover art provider names to use.
    """
    os.makedirs(dl_path, exist_ok=True)

    have_mutagen = importlib.util.find_spec("mutagen") is not None
    if not have_mutagen:
        cprint(
            "[warning] python-mutagen is missing. Lyrics embedding will be skipped.",
            Color.YELLOW,
        )

    summary = Summary()
    progress = ProgressTracker(len(urls))

    pps = [
        {"key": "FFmpegExtractAudio", "preferredcodec": fmt},
        {"key": "FFmpegMetadata"},
        {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
    ]

    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(dl_path, "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "postprocessors": pps,
        "ignoreerrors": True,
        "noplaylist": True,
        "progress_hooks": [progress.update],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.add_post_processor(
            LyricsFetcherPP(summary, lyrics_providers, user_agent), when="pre_process"
        )
        ydl.add_post_processor(
            CoverArtFetcherPP(summary, cover_providers, user_agent), when="pre_process"
        )
        ydl.add_post_processor(CropThumbnailPP(), when="after_move")
        ydl.add_post_processor(EmbedCoverArtPP(), when="after_move")
        if have_mutagen:
            ydl.add_post_processor(EmbedLyricsPP(), when="after_move")

        for url in urls:
            progress.next_track(url)

            try:
                info = ydl.extract_info(url, download=False, process=False)
                if info:
                    title = info.get("title", "Unknown")
                    expected_file = os.path.join(dl_path, f"{title}.{fmt}")
                    if os.path.exists(expected_file):
                        cprint(f"  ⊘ Skipped (already exists): {title}", Color.YELLOW)
                        summary.add_skipped(url, "duplicate")
                        continue

                    try:
                        ydl.download([url])
                        summary.add_success(url, title)
                    except Exception as e:
                        cprint(f"  ✗ Failed: {e}", Color.RED)
                        summary.add_failed(url, str(e))
                else:
                    cprint("  ✗ Could not extract info", Color.RED)
                    summary.add_failed(url, "Could not extract info")
            except Exception as e:
                cprint(f"  ✗ Error: {e}", Color.RED)
                summary.add_failed(url, str(e))

    summary.print_summary()
