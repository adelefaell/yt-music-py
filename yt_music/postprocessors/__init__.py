from .checkers import has_cover, has_lyrics
from .embedders import SUPPORTED_EXTS, embed_cover, embed_lyrics
from .processors import (
    CoverArtFetcherPP,
    CropThumbnailPP,
    EmbedCoverArtPP,
    EmbedLyricsPP,
    LyricsFetcherPP,
)

__all__ = [
    "CoverArtFetcherPP",
    "CropThumbnailPP",
    "EmbedCoverArtPP",
    "EmbedLyricsPP",
    "LyricsFetcherPP",
    "SUPPORTED_EXTS",
    "embed_cover",
    "embed_lyrics",
    "has_cover",
    "has_lyrics",
]
