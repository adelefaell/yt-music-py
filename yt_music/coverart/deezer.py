import json
import re
import urllib.parse
import urllib.request

from ..ui import Color, cprint
from .scoring import score_match

USER_AGENT = "yt-music/1.0 (https://github.com/adelfael)"


def fetch_cover_deezer(artist: str, title: str) -> bytes | None:
    """Fetch cover art from the Deezer API."""
    if not artist or not title:
        return None
    try:
        clean_title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
        clean_title = re.sub(r"\s*\[[^\]]*\]\s*$", "", clean_title).strip()
        clean_artist = re.sub(r"\s*- Topic\s*$", "", artist).strip()

        query = urllib.parse.urlencode(
            {"q": f'artist:"{clean_artist}" track:"{clean_title}"'}
        )
        req = urllib.request.Request(
            f"https://api.deezer.com/search?{query}", headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        tracks = data.get("data", [])
        if not tracks:
            return None

        scored = []
        for track in tracks[:10]:
            track_artist = track.get("artist", {}).get("name", "")
            track_title = track.get("title", "")
            score = score_match(track_artist, track_title, artist, title)
            cover_url = (track.get("album") or {}).get("cover_xl")
            if cover_url:
                scored.append((score, cover_url))

        scored.sort(key=lambda x: x[0], reverse=True)

        for score, cover_url in scored:
            if score < 2.0:
                continue
            img_req = urllib.request.Request(
                cover_url, headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                return bytes(img_resp.read())

    except Exception as e:
        cprint(f"[cover] Deezer error: {e}", Color.GRAY)
    return None
