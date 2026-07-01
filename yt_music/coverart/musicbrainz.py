import json
import re
import urllib.parse
import urllib.request

from ..ui import Color, cprint
from .scoring import score_match

def fetch_cover_musicbrainz(artist: str, title: str, user_agent: str) -> bytes | None:
    """Fetch cover art via MusicBrainz and the Cover Art Archive."""
    if not artist or not title:
        return None
    try:
        clean_title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
        clean_title = re.sub(r"\s*\[[^\]]*\]\s*$", "", clean_title).strip()
        clean_artist = re.sub(r"\s*- Topic\s*$", "", artist).strip()

        query = urllib.parse.urlencode(
            {
                "query": f'recording:"{clean_title}" AND artist:"{clean_artist}"',
                "fmt": "json",
                "limit": "10",
            }
        )
        req = urllib.request.Request(
            f"https://musicbrainz.org/ws/2/recording/?{query}",
            headers={"User-Agent": user_agent},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        recordings = data.get("recordings", [])
        scored_releases = []
        seen_mbids: set[str] = set()

        for rec in recordings:
            rec_title = rec.get("title", "")
            rec_artist = ""
            artist_credit = rec.get("artist-credit", [])
            if artist_credit:
                rec_artist = artist_credit[0].get("artist", {}).get("name", "")

            score = score_match(rec_artist, rec_title, artist, title)
            if score < 2.0:
                continue

            for release in rec.get("releases", []):
                mbid = release.get("id")
                if not mbid or mbid in seen_mbids:
                    continue
                seen_mbids.add(mbid)

                release_group = release.get("release-group", {})
                primary_type = release_group.get("primary-type", "")
                secondary_types = release_group.get("secondary-types", [])

                release_score = score
                if primary_type != "Album":
                    release_score -= 0.5
                if any(
                    t in secondary_types for t in ("Compilation", "Reissue", "Remaster")
                ):
                    release_score -= 1.0

                if release_score >= 2.0:
                    scored_releases.append((release_score, mbid))

        scored_releases.sort(key=lambda x: x[0], reverse=True)

        for _score, mbid in scored_releases:
            cover_url = f"https://coverartarchive.org/release/{mbid}/front-1200"
            img_req = urllib.request.Request(
                cover_url, headers={"User-Agent": user_agent}
            )
            try:
                with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                    if img_resp.status == 200:
                        return bytes(img_resp.read())
            except Exception:
                continue
    except Exception as e:
        cprint(f"[cover] MusicBrainz error: {e}", Color.GRAY)
    return None
