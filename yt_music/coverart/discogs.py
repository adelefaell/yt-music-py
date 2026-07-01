import json
import re
import urllib.parse
import urllib.request

from ..ui import Color, cprint
from .scoring import score_match

def fetch_cover_discogs(artist: str, title: str, user_agent: str) -> bytes | None:
    """Fetch cover art from the Discogs API."""
    if not artist or not title:
        return None
    try:
        clean_title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
        clean_title = re.sub(r"\s*\[[^\]]*\]\s*$", "", clean_title).strip()
        clean_artist = re.sub(r"\s*- Topic\s*$", "", artist).strip()

        query = urllib.parse.urlencode(
            {"q": f"{clean_artist} - {clean_title}", "type": "release"}
        )
        req = urllib.request.Request(
            f"https://api.discogs.com/database/search?{query}",
            headers={"User-Agent": user_agent},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = data.get("results", [])
        if not results:
            return None

        scored = []
        for result in results[:10]:
            result_title = result.get("title", "")
            parts = result_title.split(" - ", 1)
            result_artist = parts[0] if parts else ""
            result_album = parts[1] if len(parts) > 1 else ""

            score = score_match(result_artist, result_album, artist, title)

            formats = result.get("format", [])
            format_str = " ".join(formats).lower()
            if any(t in format_str for t in ("compilation", "reissue", "remaster")):
                score -= 1.0

            cover_url = result.get("cover_image")
            if cover_url and score >= 2.0:
                scored.append((score, cover_url))

        scored.sort(key=lambda x: x[0], reverse=True)

        for _score, cover_url in scored:
            img_req = urllib.request.Request(
                cover_url, headers={"User-Agent": user_agent}
            )
            with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                return bytes(img_resp.read())

    except Exception as e:
        cprint(f"[cover] Discogs error: {e}", Color.GRAY)
    return None
