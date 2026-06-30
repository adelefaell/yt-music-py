import sys
from collections import Counter


class Color:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    GRAY = '\033[90m'


def cprint(msg, color=''):
    print(f"{color}{msg}{Color.RESET}")


def format_bytes(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"


def format_time(seconds):
    if seconds is None or seconds < 0:
        return '--:--'
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


class ProgressTracker:
    def __init__(self, total_tracks):
        self.total_tracks = total_tracks
        self.current_track = 0
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed = 0
        self.eta = 0
        self.status = 'waiting'
        self.filename = ''
        self.last_print_len = 0

    def update(self, d):
        if d['status'] == 'downloading':
            self.status = 'downloading'
            self.filename = d.get('filename', '').split('/')[-1]
            self.downloaded_bytes = d.get('downloaded_bytes', 0)
            self.total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            self.speed = d.get('speed', 0) or 0
            self.eta = d.get('eta', 0) or 0
            self._print_progress()
        elif d['status'] == 'finished':
            self.status = 'finished'
            self._clear_line()
            cprint(f"  ✓ Downloaded: {d.get('filename', '').split('/')[-1]}", Color.GREEN)

    def _print_progress(self):
        if self.total_bytes > 0:
            pct = self.downloaded_bytes / self.total_bytes
            bar_len = 30
            filled = int(bar_len * pct)
            bar = '█' * filled + '░' * (bar_len - filled)
            pct_str = f"{pct*100:5.1f}%"
            speed_str = f"{format_bytes(self.speed)}/s" if self.speed else '-- B/s'
            eta_str = format_time(self.eta)

            line = f"\r  {Color.CYAN}[{bar}]{Color.RESET} {pct_str} {format_bytes(self.downloaded_bytes)}/{format_bytes(self.total_bytes)} @ {speed_str} ETA {eta_str}"

            padding = max(0, self.last_print_len - len(line))
            sys.stdout.write(line + ' ' * padding)
            sys.stdout.flush()
            self.last_print_len = len(line)

    def _clear_line(self):
        sys.stdout.write('\r' + ' ' * (self.last_print_len + 10) + '\r')
        sys.stdout.flush()
        self.last_print_len = 0

    def next_track(self, url):
        self.current_track += 1
        self.status = 'waiting'
        cprint(f"\n{Color.BOLD}[{self.current_track}/{self.total_tracks}]{Color.RESET} {url}", Color.BLUE)


class Summary:
    def __init__(self):
        self.successful = []
        self.skipped = []
        self.failed = []
        self.lyrics_found = []
        self.lyrics_missing = []
        self.cover_source = {}
        self.lyrics_source = {}

    def add_success(self, url, title):
        self.successful.append((url, title))

    def add_skipped(self, url, reason):
        self.skipped.append((url, reason))

    def add_failed(self, url, error):
        self.failed.append((url, error))

    def add_lyrics_found(self, title):
        self.lyrics_found.append(title)

    def add_lyrics_missing(self, title):
        self.lyrics_missing.append(title)

    def add_cover_source(self, title, provider):
        self.cover_source[title] = provider

    def add_lyrics_source(self, title, provider):
        self.lyrics_source[title] = provider

    def print_summary(self):
        print(f"\n{Color.BOLD}{'='*60}{Color.RESET}")
        cprint("DOWNLOAD SUMMARY", Color.BOLD)
        print(f"{Color.BOLD}{'='*60}{Color.RESET}")

        total = len(self.successful) + len(self.skipped) + len(self.failed)

        if self.successful:
            cprint(f"\n✓ Downloaded: {len(self.successful)}/{total}", Color.GREEN)
            for url, title in self.successful:
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
            cprint(f"Lyrics: {len(self.lyrics_found)} found, {len(self.lyrics_missing)} missing", Color.MAGENTA)

        if self.cover_source:
            counts = Counter(self.cover_source.values())
            parts = [f"{name} {count}" for name, count in counts.most_common()]
            cprint(f"Cover sources: {', '.join(parts)}", Color.CYAN)

        if self.lyrics_source:
            counts = Counter(self.lyrics_source.values())
            parts = [f"{name} {count}" for name, count in counts.most_common()]
            cprint(f"Lyrics sources: {', '.join(parts)}", Color.MAGENTA)

        print(f"{Color.BOLD}{'='*60}{Color.RESET}\n")
