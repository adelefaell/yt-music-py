import time

from .musicbrainz import fetch_cover_musicbrainz
from .deezer import fetch_cover_deezer
from .discogs import fetch_cover_discogs

_PROVIDERS = {
    'musicbrainz': ('MusicBrainz', fetch_cover_musicbrainz, False),
    'deezer': ('Deezer', fetch_cover_deezer, True),
    'discogs': ('Discogs', fetch_cover_discogs, False),
}

DEFAULT_PROVIDERS = ['musicbrainz', 'deezer', 'discogs']


def fetch_cover_art_chain(artist, title, providers=None):
    names = providers or DEFAULT_PROVIDERS
    for i, name in enumerate(names):
        entry = _PROVIDERS.get(name)
        if not entry:
            continue
        if i > 0:
            time.sleep(0.3)
        display_name, fn, is_square = entry
        result = fn(artist, title)
        if result:
            return (result, display_name, is_square)
    return (None, None, False)
