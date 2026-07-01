import re


def normalize(s: str) -> str:
    """Normalize a string for comparison by removing metadata and lowercasing."""
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
    s = re.sub(r"\s*\[[^\]]*\]\s*", " ", s)
    s = re.sub(r"\s*- Topic\s*", " ", s)
    s = re.sub(r"\s*feat\.?\s+[^,)\]]+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*ft\.?\s+[^,)\]]+", " ", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip().lower()


def score_match(
    artist: str, title: str, search_artist: str, search_title: str
) -> float:
    """Score how well an artist/title pair matches a search query.

    Returns a float score where higher is better. Scores >= 2.0 are typically
    considered good matches.
    """
    norm_artist = normalize(artist)
    norm_title = normalize(title)
    search_norm_artist = normalize(search_artist)
    search_norm_title = normalize(search_title)

    score = 0.0
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
