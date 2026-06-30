import json
import re
import urllib.request
import urllib.parse

from ..ui import cprint, Color

USER_AGENT = 'yt-music/1.0 (https://github.com/adelfael)'


def fetch_cover_deezer(artist, title):
    if not artist or not title:
        return None
    try:
        clean_title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
        clean_title = re.sub(r'\s*\[[^\]]*\]\s*$', '', clean_title).strip()
        clean_artist = re.sub(r'\s*- Topic\s*$', '', artist).strip()

        query = urllib.parse.urlencode({
            'q': f'artist:"{clean_artist}" track:"{clean_title}"'
        })
        req = urllib.request.Request(
            f'https://api.deezer.com/search?{query}',
            headers={'User-Agent': USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        tracks = data.get('data', [])
        if tracks:
            cover_url = tracks[0].get('album', {}).get('cover_xl')
            if cover_url:
                img_req = urllib.request.Request(cover_url, headers={'User-Agent': USER_AGENT})
                with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                    return img_resp.read()
    except Exception as e:
        cprint(f"[cover] Deezer error: {e}", Color.GRAY)
    return None
