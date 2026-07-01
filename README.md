# yt-music

YouTube Music downloader with automatic lyrics and cover art embedding.

## Requirements

- Python 3.11+
- ffmpeg

## Installation

```bash
uv sync
```

## Usage

### Download tracks

```bash
yt-music download <url> [url ...]
yt-music download --file links.txt
```

### Fix missing metadata

Scan already-downloaded tracks and fill in missing lyrics or cover art:

```bash
yt-music fix                    # fix both lyrics and covers
yt-music fix --lyrics           # lyrics only
yt-music fix --covers           # cover art only
yt-music fix --path ./music     # custom directory
yt-music fix --force            # overwrite existing tags
```

### Show configuration

```bash
yt-music config
```

## Configuration

Edit `config.toml` in the project root:

```toml
[general]
format = "mp3"
download_path = "./downloaded"

[lyrics]
providers = ["lrclib"]

[cover]
providers = ["musicbrainz", "deezer", "discogs"]
```

| Key | Values |
|-----|--------|
| `format` | `mp3`, `m4a`, `flac`, `ogg`, `opus` |
| `lyrics.providers` | `lrclib` |
| `cover.providers` | `musicbrainz`, `deezer`, `discogs` |

Remove a provider from the list to disable it. Set to `[]` to skip fetching entirely.

## Supported formats

| Format | Lyrics | Cover Art |
|--------|--------|-----------|
| MP3 | USLT tag | APIC tag |
| M4A/MP4 | `\xa9lyr` tag | `covr` atom |
| FLAC | `lyrics` field | Picture block |
| OGG/Opus | `lyrics` field | metadata_block_picture |

## Development

```bash
uv sync --dev
make lint
make fix
```
