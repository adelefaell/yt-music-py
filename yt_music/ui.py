import sys
from collections import Counter
from typing import Any


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


def cprint(msg: str, color: str = "") -> None:
    """Print a message with ANSI color codes."""
    print(f"{color}{msg}{Color.RESET}")


def format_bytes(bytes_val: float) -> str:
    """Format byte count into a human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def format_time(seconds: float | None) -> str:
    """Format seconds into MM:SS string."""
    if seconds is None or seconds < 0:
        return "--:--"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


class ProgressTracker:
    """Track and display download progress for multiple tracks."""

    def __init__(self, total_tracks: int) -> None:
        self.total_tracks = total_tracks
        self.current_track = 0
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed: float = 0
        self.eta: float = 0
        self.status = "waiting"
        self.filename = ""
        self.last_print_len = 0

    def update(self, d: dict[str, Any]) -> None:
        """Update progress from yt-dlp progress hook."""
        if d["status"] == "downloading":
            self.status = "downloading"
            self.filename = d.get("filename", "").split("/")[-1]
            self.downloaded_bytes = d.get("downloaded_bytes", 0)
            self.total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            self.speed = d.get("speed", 0) or 0
            self.eta = d.get("eta", 0) or 0
            self._print_progress()
        elif d["status"] == "finished":
            self.status = "finished"
            self._clear_line()
            cprint(
                f"  ✓ Downloaded: {d.get('filename', '').split('/')[-1]}", Color.GREEN
            )

    def _print_progress(self) -> None:
        if self.total_bytes > 0:
            pct = self.downloaded_bytes / self.total_bytes
            bar_len = 30
            filled = int(bar_len * pct)
            bar = "█" * filled + "░" * (bar_len - filled)
            pct_str = f"{pct * 100:5.1f}%"
            speed_str = f"{format_bytes(self.speed)}/s" if self.speed else "-- B/s"
            eta_str = format_time(self.eta)

            dl = format_bytes(self.downloaded_bytes)
            tot = format_bytes(self.total_bytes)
            line = (
                f"\r  {Color.CYAN}[{bar}]{Color.RESET}"
                f" {pct_str} {dl}/{tot} @ {speed_str} ETA {eta_str}"
            )

            padding = max(0, self.last_print_len - len(line))
            sys.stdout.write(line + " " * padding)
            sys.stdout.flush()
            self.last_print_len = len(line)

    def _clear_line(self) -> None:
        sys.stdout.write("\r" + " " * (self.last_print_len + 10) + "\r")
        sys.stdout.flush()
        self.last_print_len = 0

    def next_track(self, url: str) -> None:
        """Advance to the next track and print the track header."""
        self.current_track += 1
        self.status = "waiting"
        cprint(
            f"\n{Color.BOLD}"
            f"[{self.current_track}/{self.total_tracks}]"
            f"{Color.RESET} {url}",
            Color.BLUE,
        )


class Summary:
    """Collect and print download session summary."""

    def __init__(self) -> None:
        self.successful: list[tuple[str, str]] = []
        self.skipped: list[tuple[str, str]] = []
        self.failed: list[tuple[str, str]] = []
        self.lyrics_found: list[str] = []
        self.lyrics_missing: list[str] = []
        self.cover_source: dict[str, str] = {}
        self.lyrics_source: dict[str, str] = {}

    def add_success(self, url: str, title: str) -> None:
        """Record a successful download."""
        self.successful.append((url, title))

    def add_skipped(self, url: str, reason: str) -> None:
        """Record a skipped download."""
        self.skipped.append((url, reason))

    def add_failed(self, url: str, error: str) -> None:
        """Record a failed download."""
        self.failed.append((url, error))

    def add_lyrics_found(self, title: str) -> None:
        """Record that lyrics were found for a track."""
        self.lyrics_found.append(title)

    def add_lyrics_missing(self, title: str) -> None:
        """Record that lyrics were not found for a track."""
        self.lyrics_missing.append(title)

    def add_cover_source(self, title: str, provider: str) -> None:
        """Record the cover art source for a track."""
        self.cover_source[title] = provider

    def add_lyrics_source(self, title: str, provider: str) -> None:
        """Record the lyrics source for a track."""
        self.lyrics_source[title] = provider

    def print_summary(self) -> None:
        """Print the full download session summary."""
        print(f"\n{Color.BOLD}{'=' * 60}{Color.RESET}")
        cprint("DOWNLOAD SUMMARY", Color.BOLD)
        print(f"{Color.BOLD}{'=' * 60}{Color.RESET}")

        total = len(self.successful) + len(self.skipped) + len(self.failed)

        if self.successful:
            cprint(f"\n✓ Downloaded: {len(self.successful)}/{total}", Color.GREEN)
            for _url, title in self.successful:
                print(f"  • {title}")

        if self.skipped:
            cprint(f"\n⊘ Skipped: {len(self.skipped)}/{total}", Color.YELLOW)
            for url, reason in self.skipped:
                print(f"  • {url} ({reason})")

        if self.failed:
            cprint(f"\n✗ Failed: {len(self.failed)}/{total}", Color.RED)
            for url, error in self.failed:
                print(f"  • {url}")
                print(f"    {Color.GRAY}{error}{Color.RESET}")

        if self.lyrics_found or self.lyrics_missing:
            print()
            cprint(
                f"Lyrics: {len(self.lyrics_found)} found,"
                f" {len(self.lyrics_missing)} missing",
                Color.MAGENTA,
            )

        if self.cover_source:
            counts = Counter(self.cover_source.values())
            parts = [f"{name} {count}" for name, count in counts.most_common()]
            cprint(f"Cover sources: {', '.join(parts)}", Color.CYAN)

        if self.lyrics_source:
            counts = Counter(self.lyrics_source.values())
            parts = [f"{name} {count}" for name, count in counts.most_common()]
            cprint(f"Lyrics sources: {', '.join(parts)}", Color.MAGENTA)

        print(f"{Color.BOLD}{'=' * 60}{Color.RESET}\n")
