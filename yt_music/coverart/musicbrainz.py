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


def _score_match(rec_artist, rec_title, search_artist, search_title):
    norm_artist = _normalize(rec_artist)
    norm_title = _normalize(rec_title)
    search_norm_artist = _normalize(search_artist)
    search_norm_title = _normalize(search_title)

    score = 0
    if search_norm_title in norm_title or norm_title in search_norm_title:
        score += 2
    if search_norm_artist in norm_artist or norm_artist in search_norm_artist:
        score += 2

    artist_words = set(search_norm_artist.split())
    title_words = set(search_norm_title.split())
    rec_artist_words = set(norm_artist.split())
    rec_title_words = set(norm_title.split())

    artist_overlap = len(artist_words & rec_artist_words)
    title_overlap = len(title_words & rec_title_words)

    if artist_words:
        score += artist_overlap / len(artist_words)
    if title_words:
        score += title_overlap / len(title_words)

    return score


def fetch_cover_musicbrainz(artist, title):
    if not artist or not title:
        return None
    try:
        clean_title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
        clean_title = re.sub(r'\s*\[[^\]]*\]\s*$', '', clean_title).strip()
        clean_artist = re.sub(r'\s*- Topic\s*$', '', artist).strip()

        query = urllib.parse.urlencode({
            'query': f'recording:"{clean_title}" AND artist:"{clean_artist}"',
            'fmt': 'json',
            'limit': '10'
        })
        req = urllib.request.Request(
            f'https://musicbrainz.org/ws/2/recording/?{query}',
            headers={'User-Agent': USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        recordings = data.get('recordings', [])
        scored_releases = []

        for rec in recordings:
            rec_title = rec.get('title', '')
            rec_artist = ''
            artist_credit = rec.get('artist-credit', [])
            if artist_credit:
                rec_artist = artist_credit[0].get('artist', {}).get('name', '')

            score = _score_match(rec_artist, rec_title, artist, title)
            if score < 2.0:
                continue

            for release in rec.get('releases', []):
                mbid = release.get('id')
                if mbid:
                    scored_releases.append((score, mbid))

        scored_releases.sort(key=lambda x: x[0], reverse=True)

        for score, mbid in scored_releases:
            cover_url = f'https://coverartarchive.org/release/{mbid}/front-500'
            img_req = urllib.request.Request(cover_url, headers={'User-Agent': USER_AGENT})
            try:
                with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                    if img_resp.status == 200:
                        return img_resp.read()
            except Exception:
                continue
    except Exception as e:
        cprint(f"[cover] MusicBrainz error: {e}", Color.GRAY)
    return None
