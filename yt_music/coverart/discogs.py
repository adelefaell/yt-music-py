import json
import re
import urllib.request
import urllib.parse

from ..ui import cprint, Color

USER_AGENT = 'yt-music/1.0 (https://github.com/adelfael)'


def _normalize(s):
    s = re.sub(r'\s*\([^)]*\)\s*', ' ', s)
    s = re.sub(r'\s*\[[^\]]*\]\s*', ' ', s)
    s = re.sub(r'\s*- Topic\s*', ' ', s)
    s = re.sub(r'\s*feat\.?\s.*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*ft\.?\s.*', '', s, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', s).strip().lower()


def _score_match(result_title, search_artist, search_title):
    norm_result = _normalize(result_title)
    search_norm_artist = _normalize(search_artist)
    search_norm_title = _normalize(search_title)

    score = 0
    if search_norm_title in norm_result:
        score += 2
    if search_norm_artist in norm_result:
        score += 2

    result_words = set(norm_result.split())
    artist_words = set(search_norm_artist.split())
    title_words = set(search_norm_title.split())

    artist_overlap = len(artist_words & result_words)
    title_overlap = len(title_words & result_words)

    if artist_words:
        score += artist_overlap / len(artist_words)
    if title_words:
        score += title_overlap / len(title_words)

    return score


def fetch_cover_discogs(artist, title):
    if not artist or not title:
        return None
    try:
        clean_title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
        clean_title = re.sub(r'\s*\[[^\]]*\]\s*$', '', clean_title).strip()
        clean_artist = re.sub(r'\s*- Topic\s*$', '', artist).strip()

        query = urllib.parse.urlencode({
            'q': f'{clean_artist} - {clean_title}',
            'type': 'release'
        })
        req = urllib.request.Request(
            f'https://api.discogs.com/database/search?{query}',
            headers={'User-Agent': USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        results = data.get('results', [])
        if not results:
            return None

        scored = []
        for result in results[:10]:
            result_title = result.get('title', '')
            score = _score_match(result_title, artist, title)
            cover_url = result.get('cover_image')
            if cover_url:
                scored.append((score, cover_url))

        scored.sort(key=lambda x: x[0], reverse=True)

        for score, cover_url in scored:
            if score < 2.0:
                continue
            img_req = urllib.request.Request(cover_url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                return img_resp.read()

    except Exception as e:
        cprint(f"[cover] Discogs error: {e}", Color.GRAY)
    return None
