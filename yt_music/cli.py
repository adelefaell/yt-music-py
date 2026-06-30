import os
import sys
import tomllib
from pathlib import Path

import yt_dlp

from .ui import cprint, Color, ProgressTracker, Summary
from .postprocessors import (
    LyricsFetcherPP,
    CoverArtFetcherPP,
    EmbedCoverArtPP,
    CropThumbnailPP,
    EmbedLyricsPP,
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PROJECT_ROOT / 'config.toml'

_DEFAULTS = {
    'format': 'mp3',
    'download_path': str(_PROJECT_ROOT / 'downloaded'),
    'lyrics_providers': None,
    'cover_providers': None,
}


def _load_config():
    if not _CONFIG_PATH.exists():
        return {}
    with open(_CONFIG_PATH, 'rb') as f:
        return tomllib.load(f)


def _resolve_settings():
    cfg = _load_config()
    general = cfg.get('general', {})

    fmt = general.get('format', _DEFAULTS['format'])

    raw = general.get('download_path', _DEFAULTS['download_path'])
    dl_path = str(_PROJECT_ROOT / raw) if not os.path.isabs(raw) else raw

    lyrics_providers = cfg.get('lyrics', {}).get('providers') or _DEFAULTS['lyrics_providers']
    cover_providers = cfg.get('cover', {}).get('providers') or _DEFAULTS['cover_providers']

    return fmt, dl_path, lyrics_providers, cover_providers


def main():
    fmt, dl_path, lyrics_providers, cover_providers = _resolve_settings()

    urls = []
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--file':
            i += 1
            filepath = sys.argv[i]
            try:
                with open(filepath) as f:
                    file_urls = [line.strip() for line in f if line.strip()]
                    urls.extend(file_urls)
                    cprint(f"[info] Loaded {len(file_urls)} URLs from {filepath}", Color.CYAN)
            except FileNotFoundError:
                cprint(f"[error] File not found: {filepath}", Color.RED)
                sys.exit(1)
        else:
            urls.append(arg)
        i += 1

    if not urls:
        cprint(f"Usage: {os.path.basename(sys.argv[0])} [--file <path>] <url> [url...]", Color.YELLOW)
        sys.exit(1)

    os.makedirs(dl_path, exist_ok=True)

    have_mutagen = False
    try:
        import mutagen
        have_mutagen = True
    except ImportError:
        cprint("[warning] python-mutagen is missing. Lyrics embedding will be skipped.", Color.YELLOW)

    summary = Summary()
    progress = ProgressTracker(len(urls))

    pps = [
        {'key': 'FFmpegExtractAudio', 'preferredcodec': fmt},
        {'key': 'FFmpegMetadata'},
        {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
    ]

    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(dl_path, '%(title)s.%(ext)s'),
        'writethumbnail': True,
        'postprocessors': pps,
        'ignoreerrors': True,
        'noplaylist': True,
        'progress_hooks': [progress.update],
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.add_post_processor(LyricsFetcherPP(summary, lyrics_providers), when='pre_process')
        ydl.add_post_processor(CoverArtFetcherPP(summary, cover_providers), when='pre_process')
        ydl.add_post_processor(CropThumbnailPP(), when='after_move')
        ydl.add_post_processor(EmbedCoverArtPP(), when='after_move')
        if have_mutagen:
            ydl.add_post_processor(EmbedLyricsPP(), when='after_move')

        for url in urls:
            progress.next_track(url)

            try:
                info = ydl.extract_info(url, download=False, process=False)
                if info:
                    title = info.get('title', 'Unknown')
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
                    cprint(f"  ✗ Could not extract info", Color.RED)
                    summary.add_failed(url, "Could not extract info")
            except Exception as e:
                cprint(f"  ✗ Error: {e}", Color.RED)
                summary.add_failed(url, str(e))

    summary.print_summary()
