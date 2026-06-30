import argparse
import os
import sys
import tomllib
from importlib.metadata import version
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


def cmd_download(args):
    fmt, dl_path, lyrics_providers, cover_providers = _resolve_settings()

    urls = list(args.urls) if args.urls else []

    if args.files:
        for filepath in args.files:
            try:
                with open(filepath) as f:
                    file_urls = [line.strip() for line in f if line.strip()]
                    urls.extend(file_urls)
                    cprint(f"[info] Loaded {len(file_urls)} URLs from {filepath}", Color.CYAN)
            except FileNotFoundError:
                cprint(f"[error] File not found: {filepath}", Color.RED)
                sys.exit(1)

    if not urls:
        cprint("No URLs provided. Use 'yt-music download <url>...' or 'yt-music download --file <path>'.", Color.YELLOW)
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


def cmd_config():
    fmt, dl_path, lyrics_providers, cover_providers = _resolve_settings()
    cprint("[info] Current configuration:", Color.CYAN)
    cprint(f"  format:          {fmt}", '')
    cprint(f"  download_path:   {dl_path}", '')
    cprint(f"  lyrics_providers: {lyrics_providers}", '')
    cprint(f"  cover_providers:  {cover_providers}", '')


def main():
    parser = argparse.ArgumentParser(prog='yt-music', description='YouTube Music downloader')
    parser.add_argument('--version', action='version', version=f'%(prog)s {version("yt-music")}')
    sub = parser.add_subparsers(dest='command')

    dl = sub.add_parser('download', help='Download tracks from YouTube')
    dl.add_argument('urls', nargs='*', help='YouTube URLs to download')
    dl.add_argument('--file', action='append', dest='files', metavar='PATH',
                    help='File containing URLs (one per line)')

    sub.add_parser('config', help='Show current configuration')

    args = parser.parse_args()

    if args.command == 'download':
        cmd_download(args)
    elif args.command == 'config':
        cmd_config()
    else:
        parser.print_help()
