from .lrclib import fetch_lyrics_lrclib

_PROVIDERS = {
    'lrclib': ('LrcLib', fetch_lyrics_lrclib),
}

DEFAULT_PROVIDERS = ['lrclib']


def fetch_lyrics_chain(artist, title, providers=None):
    for name in (providers or DEFAULT_PROVIDERS):
        entry = _PROVIDERS.get(name)
        if not entry:
            continue
        display_name, fn = entry
        lyrics = fn(artist, title)
        if lyrics:
            return (lyrics, display_name)
    return (None, None)
