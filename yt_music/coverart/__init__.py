import time

from .deezer import fetch_cover_deezer
from .discogs import fetch_cover_discogs
from .musicbrainz import fetch_cover_musicbrainz

_PROVIDERS: dict[str, tuple[str, object, bool]] = {
    "musicbrainz": ("MusicBrainz", fetch_cover_musicbrainz, False),
    "deezer": ("Deezer", fetch_cover_deezer, True),
    "discogs": ("Discogs", fetch_cover_discogs, False),
}


def fetch_cover_art_chain(
    artist: str, title: str, providers: list[str]
) -> tuple[bytes | None, str | None, bool]:
    """Try each cover art provider in order.

    Returns (image_bytes, provider_name, is_square).
    """
    for i, name in enumerate(providers):
        entry = _PROVIDERS.get(name)
        if not entry:
            continue
        if i > 0:
            time.sleep(0.3)
        display_name, fn, is_square = entry
        result = fn(artist, title)  # type: ignore[operator]
        if result:
            return (result, display_name, is_square)
    return (None, None, False)
