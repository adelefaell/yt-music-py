from .lrclib import fetch_lyrics_lrclib

_PROVIDERS: dict[str, tuple[str, object]] = {
    "lrclib": ("LrcLib", fetch_lyrics_lrclib),
}


def fetch_lyrics_chain(
    artist: str, title: str, providers: list[str], user_agent: str
) -> tuple[str | None, str | None]:
    """Try each lyrics provider in order. Returns (lyrics, provider_name)."""
    for name in providers:
        entry = _PROVIDERS.get(name)
        if not entry:
            continue
        display_name, fn = entry
        lyrics = fn(artist, title, user_agent)  # type: ignore[operator]
        if lyrics:
            return (lyrics, display_name)
    return (None, None)
