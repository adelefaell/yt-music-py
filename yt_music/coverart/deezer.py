import json
import re
import urllib.parse
import urllib.request

from ..ui import Color, cprint

USER_AGENT = "yt-music/1.0 (https://github.com/adelfael)"


def _normalize(s):
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
    s = re.sub(r"\s*\[[^\]]*\]\s*", " ", s)
    s = re.sub(r"\s*- Topic\s*", " ", s)
    s = re.sub(r"\s*feat\.?\s.*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*ft\.?\s.*", "", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip().lower()


def _score_match(track_artist, track_title, search_artist, search_title):
    norm_artist = _normalize(track_artist)
    norm_title = _normalize(track_title)
    search_norm_artist = _normalize(search_artist)
    search_norm_title = _normalize(search_title)

    score = 0
    if search_norm_title in norm_title or norm_title in search_norm_title:
        score += 2
    if search_norm_artist in norm_artist or norm_artist in search_norm_artist:
        score += 2

    artist_words = set(search_norm_artist.split())
    title_words = set(search_norm_title.split())
    track_artist_words = set(norm_artist.split())
    track_title_words = set(norm_title.split())

    artist_overlap = len(artist_words & track_artist_words)
    title_overlap = len(title_words & track_title_words)

    if artist_words:
        score += artist_overlap / len(artist_words)
    if title_words:
        score += title_overlap / len(title_words)

    return score


def fetch_cover_deezer(artist, title):
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
            score = _score_match(track_artist, track_title, artist, title)
            cover_url = track.get("album", {}).get("cover_xl")
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
                return img_resp.read()

    except Exception as e:
        cprint(f"[cover] Deezer error: {e}", Color.GRAY)
    return None
