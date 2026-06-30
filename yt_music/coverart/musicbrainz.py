import json
import re
import urllib.request
import urllib.parse

from ..ui import cprint, Color

USER_AGENT = 'yt-music/1.0 (https://github.com/adelfael)'


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
            'limit': '5'
        })
        req = urllib.request.Request(
            f'https://musicbrainz.org/ws/2/recording/?{query}',
            headers={'User-Agent': USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        recordings = data.get('recordings', [])
        for rec in recordings:
            for release in rec.get('releases', []):
                mbid = release.get('id')
                if not mbid:
                    continue
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
