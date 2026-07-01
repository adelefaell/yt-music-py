import argparse
import importlib.util
import os
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path
from typing import Any

from .downloader import download_tracks
from .fixer import fix_folder
from .ui import Color, cprint

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.toml"

_DEFAULTS: dict[str, Any] = {
    "format": "mp3",
    "download_path": str(_PROJECT_ROOT / "downloaded"),
    "lyrics_providers": ["lrclib"],
    "cover_providers": ["deezer", "musicbrainz", "discogs"],
}


def _load_config() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def _resolve_settings() -> tuple[str, str, list[str], list[str]]:
    cfg = _load_config()
    general = cfg.get("general", {})

    fmt = general.get("format", _DEFAULTS["format"])

    raw = general.get("download_path", _DEFAULTS["download_path"])
    dl_path = str(_PROJECT_ROOT / raw) if not os.path.isabs(raw) else raw

    lyrics_providers = (
        cfg.get("lyrics", {}).get("providers") or _DEFAULTS["lyrics_providers"]
    )
    cover_providers = (
        cfg.get("cover", {}).get("providers") or _DEFAULTS["cover_providers"]
    )

    return fmt, dl_path, lyrics_providers, cover_providers


def cmd_download(args: argparse.Namespace) -> None:
    """Download tracks from YouTube URLs."""
    fmt, dl_path, lyrics_providers, cover_providers = _resolve_settings()

    urls = list(args.urls) if args.urls else []

    if args.files:
        for filepath in args.files:
            try:
                with open(filepath) as f:
                    file_urls = [line.strip() for line in f if line.strip()]
                    urls.extend(file_urls)
                    cprint(
                        f"[info] Loaded {len(file_urls)} URLs from {filepath}",
                        Color.CYAN,
                    )
            except FileNotFoundError:
                cprint(f"[error] File not found: {filepath}", Color.RED)
                sys.exit(1)

    if not urls:
        cprint(
            "No URLs provided. Use 'yt-music download <url>...'"
            " or 'yt-music download --file <path>'.",
            Color.YELLOW,
        )
        sys.exit(1)

    download_tracks(urls, fmt, dl_path, lyrics_providers, cover_providers)


def cmd_config() -> None:
    """Print current configuration settings."""
    fmt, dl_path, lyrics_providers, cover_providers = _resolve_settings()
    cprint("[info] Current configuration:", Color.CYAN)
    cprint(f"  format:          {fmt}", "")
    cprint(f"  download_path:   {dl_path}", "")
    cprint(f"  lyrics_providers: {lyrics_providers}", "")
    cprint(f"  cover_providers:  {cover_providers}", "")


def cmd_fix(args: argparse.Namespace) -> None:
    """Fix missing lyrics and cover art for downloaded tracks."""
    if importlib.util.find_spec("mutagen") is None:
        cprint(
            "[fix] \u26a0 python-mutagen is required."
            " Install with: pip install mutagen",
            Color.RED,
        )
        sys.exit(1)

    _, dl_path, lyrics_providers, cover_providers = _resolve_settings()
    path = args.path or dl_path

    fix_lyrics = args.lyrics or not args.covers
    fix_covers = args.covers or not args.lyrics

    fix_folder(
        path, fix_lyrics, fix_covers, lyrics_providers, cover_providers, args.force
    )


def main() -> None:
    """Entry point for the yt-music CLI."""
    parser = argparse.ArgumentParser(
        prog="yt-music", description="YouTube Music downloader"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('yt-music')}",
    )
    sub = parser.add_subparsers(dest="command")

    dl = sub.add_parser("download", help="Download tracks from YouTube")
    dl.add_argument("urls", nargs="*", help="YouTube URLs to download")
    dl.add_argument(
        "--file",
        action="append",
        dest="files",
        metavar="PATH",
        help="File containing URLs (one per line)",
    )

    sub.add_parser("config", help="Show current configuration")

    fix = sub.add_parser(
        "fix", help="Fix missing lyrics/cover art for downloaded tracks"
    )
    fix.add_argument("--lyrics", action="store_true", help="Fix missing lyrics only")
    fix.add_argument("--covers", action="store_true", help="Fix missing cover art only")
    fix.add_argument("--path", help="Path to downloaded tracks directory")
    fix.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing lyrics/cover art",
    )

    args = parser.parse_args()

    if args.command == "download":
        cmd_download(args)
    elif args.command == "config":
        cmd_config()
    elif args.command == "fix":
        cmd_fix(args)
    else:
        parser.print_help()
