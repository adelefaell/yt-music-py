# AGENTS.md

## Setup

- System dep: `ffmpeg` required (not installable via pip)
- Install: `pip install -e .` (registers `yt-music` console script)
- Python >=3.11 (uses `tomllib`)

## Commands

```bash
yt-music download <url>              # download a track
yt-music download --file links.txt   # batch download
yt-music config --show               # print resolved config
python -m yt_music --help            # module entrypoint
```

No test suite, linter, or typechecker configured.

## Architecture

- **Entry points**: `yt_music.cli:main` (console_scripts) and `yt_music/__main__.py`
- **Config resolution**: CLI flags → `config.toml` → `_DEFAULTS` in `cli.py`
- **Post-processor pipeline** (order matters):
  1. `pre_process`: `LyricsFetcherPP` → `CoverArtFetcherPP` (fetch metadata, store in `info['meta_*']` keys)
  2. yt-dlp built-ins: `FFmpegExtractAudio` → `FFmpegMetadata` → `FFmpegThumbnailsConvertor`
  3. `after_move`: `CropThumbnailPP` → `EmbedCoverArtPP` → `EmbedLyricsPP`
- **PP communication**: custom `meta_lyrics`, `meta_cover_temp_path`, `meta_cover_provider` keys injected into yt-dlp info dicts
- **Cover embedders** in `postprocessors.py:_EMBEDDERS` — supports mp3, m4a/mp4, flac, ogg/opus only
- **Duplicate detection**: checks `{dl_path}/{title}.{fmt}` exists before downloading

## Conventions

- Package uses relative imports (`.ui`, `.postprocessors`, etc.) — must be installed or run as module
- `config.toml` lives at project root; paths in it are relative to project root
- `downloaded/` is gitignored — output dir
