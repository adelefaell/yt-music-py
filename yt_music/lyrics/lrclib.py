import json
import re
import urllib.parse
import urllib.request

from ..ui import Color, cprint


def fetch_lyrics_lrclib(artist: str, title: str) -> str | None:
    """Fetch lyrics from the LrcLib API."""
    if not artist or not title:
        return None

    clean_title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
    clean_title = re.sub(r"\s*\[[^\]]*\]\s*$", "", clean_title).strip()
    clean_artist = re.sub(r"\s*- Topic\s*$", "", artist).strip()

    if not clean_title or not clean_artist:
        return None

    for sep in (",", "&", " x ", " feat. ", " ft. "):
        if sep in clean_artist:
            clean_artist = clean_artist.split(sep)[0].strip()
            break

    try:
        url = "https://lrclib.net/api/get?" + urllib.parse.urlencode(
            {"artist_name": clean_artist, "track_name": clean_title}
        )
        req = urllib.request.Request(url, headers={"User-Agent": "yt-music/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

            lyrics = data.get("plainLyrics") or data.get("syncedLyrics")
            if lyrics and lyrics.strip():
                cleaned = re.sub(r"\[\d+:\d+\.\d+\]\s*", "", lyrics.strip())
                return cleaned.strip()
    except Exception as e:
        cprint(f"[lyrics] Error fetching lyrics: {e}", Color.YELLOW)
    return None
