import argparse
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


def _load_config(config_path=None):
    path = Path(config_path) if config_path else _CONFIG_PATH
    if not path.exists():
        return {}
    with open(path, 'rb') as f:
        return tomllib.load(f)


def _resolve_settings(args):
    cfg = _load_config(getattr(args, 'config', None))
    general = cfg.get('general', {})

    fmt = args.format or general.get('format', _DEFAULTS['format'])

    raw_output = args.output or general.get('download_path', _DEFAULTS['download_path'])
    dl_path = str(_PROJECT_ROOT / raw_output) if not os.path.isabs(raw_output) else raw_output

    lyrics_providers = args.lyrics or cfg.get('lyrics', {}).get('providers') or _DEFAULTS['lyrics_providers']
    cover_providers = args.cover or cfg.get('cover', {}).get('providers') or _DEFAULTS['cover_providers']

    return fmt, dl_path, lyrics_providers, cover_providers


def _build_parser():
    parser = argparse.ArgumentParser(
        prog='yt-music',
        description='Download music from YouTube with lyrics and cover art.',
    )
    subparsers = parser.add_subparsers(dest='command')

    dl = subparsers.add_parser('download', help='Download tracks from URLs')
    dl.add_argument('urls', nargs='*', help='YouTube URLs to download')
    dl.add_argument('--file', '-F', metavar='PATH', help='File with URLs (one per line)')
    dl.add_argument('--format', '-f', metavar='FMT', help='Audio format (e.g. mp3, flac, opus)')
    dl.add_argument('--output', '-o', metavar='DIR', help='Download directory')
    dl.add_argument('--config', '-c', metavar='PATH', help='Path to config.toml')
    dl.add_argument('--lyrics', nargs='+', metavar='PROV', help='Lyrics providers (e.g. lrclib)')
    dl.add_argument('--cover', nargs='+', metavar='PROV', help='Cover art providers (e.g. musicbrainz deezer)')
    dl.add_argument('--verbose', '-v', action='store_true', help='Show yt-dlp output')

    cfg = subparsers.add_parser('config', help='Show or manage configuration')
    cfg.add_argument('--show', action='store_true', help='Print resolved config')
    cfg.add_argument('--config', '-c', metavar='PATH', help='Path to config.toml')
    cfg.add_argument('--format', '-f', metavar='FMT')
    cfg.add_argument('--output', '-o', metavar='DIR')
    cfg.add_argument('--lyrics', nargs='+', metavar='PROV')
    cfg.add_argument('--cover', nargs='+', metavar='PROV')

    parser.add_argument('urls', nargs='*', help='YouTube URLs to download')
    parser.add_argument('--file', '-F', metavar='PATH', help='File with URLs (one per line)')
    parser.add_argument('--format', '-f', metavar='FMT', help='Audio format (e.g. mp3, flac, opus)')
    parser.add_argument('--output', '-o', metavar='DIR', help='Download directory')
    parser.add_argument('--config', '-c', metavar='PATH', help='Path to config.toml')
    parser.add_argument('--lyrics', nargs='+', metavar='PROV', help='Lyrics providers (e.g. lrclib)')
    parser.add_argument('--cover', nargs='+', metavar='PROV', help='Cover art providers (e.g. musicbrainz deezer)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show yt-dlp output')

    return parser


def _collect_urls(args):
    urls = list(getattr(args, 'urls', []) or [])
    filepath = getattr(args, 'file', None)
    if filepath:
        try:
            with open(filepath) as f:
                file_urls = [line.strip() for line in f if line.strip()]
                urls.extend(file_urls)
                cprint(f"[info] Loaded {len(file_urls)} URLs from {filepath}", Color.CYAN)
        except FileNotFoundError:
            cprint(f"[error] File not found: {filepath}", Color.RED)
            sys.exit(1)
    return urls


def _cmd_download(args):
    fmt, dl_path, lyrics_providers, cover_providers = _resolve_settings(args)
    urls = _collect_urls(args)

    if not urls:
        cprint("No URLs provided. Use: yt-music download <url> [url...] --file <path>", Color.YELLOW)
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

    verbose = getattr(args, 'verbose', False)

    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(dl_path, '%(title)s.%(ext)s'),
        'writethumbnail': True,
        'postprocessors': pps,
        'ignoreerrors': True,
        'noplaylist': True,
        'progress_hooks': [progress.update],
        'quiet': not verbose,
        'no_warnings': not verbose,
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


def _cmd_config(args):
    fmt, dl_path, lyrics_providers, cover_providers = _resolve_settings(args)

    cprint("Resolved configuration:", Color.BOLD)
    print(f"  format:          {fmt}")
    print(f"  download_path:   {dl_path}")
    print(f"  lyrics_providers: {lyrics_providers}")
    print(f"  cover_providers:  {cover_providers}")

    cfg_path = getattr(args, 'config', None) or _CONFIG_PATH
    print(f"  config_file:     {cfg_path} ({'found' if Path(cfg_path).exists() else 'not found'})")


def main():
    parser = _build_parser()
    args = parser.parse_args()

    cmd = args.command

    if cmd == 'config':
        _cmd_config(args)
    elif cmd == 'download' or (cmd is None and (args.urls or args.file)):
        _cmd_download(args)
    else:
        parser.print_help()
        sys.exit(1)
