# AGENTS.md

## Project Overview

YouTube Music downloader CLI. Downloads audio from YouTube, fetches lyrics and cover art from external providers, embeds metadata into audio files.

## Tech Stack

- Python 3.11+
- yt-dlp (download engine)
- mutagen (audio metadata)
- ffmpeg/ffprobe (image processing, audio conversion)
- ruff (linter + formatter)
- uv (package manager)

## Commands

```bash
make lint          # check code quality
make fix           # auto-fix lint + format
uv run yt-music download <url>   # download a track
uv run yt-music config           # show config
uv run yt-music fix              # fix missing lyrics/covers
```

## Code Conventions

- Line length: 88
- Double quotes for strings
- Imports sorted by ruff (I rule)
- Type hints on public functions
- No comments unless asked

## Before Committing

Always run:

```bash
make lint
```
