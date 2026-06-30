# yt-music

Download music from YouTube with automatic lyrics and cover art embedding.

## Install

```bash
pip install -e .
```

Requires `ffmpeg` on your system.

## Usage

```bash
# Download tracks
yt-music download <url> [url...]

# Download from file (one URL per line)
yt-music download --file links.txt

# Override format and output directory
yt-music download <url> --format flac --output ~/Music

# Verbose output
yt-music download <url> --verbose

# Show resolved configuration
yt-music config --show

# Run as module
python -m yt_music download <url>
```

## Configuration

Edit `config.toml`:

```toml
[general]
format = "mp3"
download_path = "./downloaded"

[lyrics]
providers = ["lrclib"]

[cover]
providers = ["musicbrainz", "deezer", "discogs"]
```

CLI flags override config values. Use `--config <path>` to point to a different file.

## CLI Options

| Flag | Description |
|------|-------------|
| `--format, -f` | Audio format (mp3, flac, opus, etc.) |
| `--output, -o` | Download directory |
| `--file, -F` | File with URLs (one per line) |
| `--config, -c` | Path to config.toml |
| `--lyrics` | Lyrics providers |
| `--cover` | Cover art providers |
| `--verbose, -v` | Show yt-dlp output |

## Features

- Audio extraction via yt-dlp + ffmpeg
- Synced lyrics fetching (LRC) from lrclib
- Cover art from MusicBrainz, Deezer, Discogs
- Lyrics and cover art embedded into audio files
- Duplicate detection (skips already downloaded tracks)
- Download summary with source stats
