""" 
# +==== BEGIN rotary_logger =================+
# LOGO: 
# ..........####...####..........
# ......###.....#.#########......
# ....##........#.###########....
# ...#..........#.############...
# ...#..........#.#####.######...
# ..#.....##....#.###..#...####..
# .#.....#.##...#.##..##########.
# #.....##########....##...######
# #.....#...##..#.##..####.######
# .#...##....##.#.##..###..#####.
# ..#.##......#.#.####...######..
# ..#...........#.#############..
# ..#...........#.#############..
# ...##.........#.############...
# ......#.......#.#########......
# .......#......#.########.......
# .........#####...#####.........
# /STOP
# PROJECT: rotary_logger
# FILE: rotary_logger.py
# CREATION DATE: 29-10-2025
# LAST Modified: 5:52:21 29-10-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the main file of the module, it contains the core code for the module.
# // AR
# +==== END rotary_logger =================+
#
"""

import os

class RotaryLogger:
    """ This is the main class of the program that will be called in order to initialise everything """
    def __init__(self) -> None:
        print("Implementation in progress, nothing to see yet")

LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "").lower() in ("1", "true", "yes")

if LOG_TO_FILE:
    import sys
    import atexit
    from pathlib import Path
    from typing import Optional
    from io import TextIOWrapper
    from datetime import datetime

    _LOG_FOLDER_BASE_NAME: str = "logs"
    _DEFAULT_LOG_MAX_FILE_SIZE: int = 2000  # MB ~ 2 GB
    _DEFAULT_LOG_FOLDER: Path = Path(__file__).parent / _LOG_FOLDER_BASE_NAME
    _BUFFER_FLUSH_SIZE: int = 8 * 1024  # flush every 8 KB

    class TeeStream:
        """Redirects stdout/stderr to a file while keeping normal output, buffered, and rotating by max size."""

        def __init__(self, root: Path, original_stream, max_size_mb: int = 50):
            self.root = Path(root)
            self.original_stream = original_stream
            self.max_size = max_size_mb * 1024 * 1024  # bytes
            self.file: Optional[TextIOWrapper] = None
            self.file_path: Path = self._create_log_path()
            self._buffer: list[str] = []
            self._written_bytes = 0
            self._open_file()

        def _create_log_path(self) -> Path:
            now = datetime.now()
            year_dir = self.root / str(now.year)
            month_dir = year_dir / f"{now.month:02d}"
            day_dir = month_dir / f"{now.day:02d}"
            day_dir.mkdir(parents=True, exist_ok=True)
            filename = now.strftime("%Y_%m_%dT%Hh%Mm%Ss.log")
            return day_dir / filename

        def _open_file(self) -> None:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file = open(self.file_path, "a", encoding="utf-8", newline="\n")
            self._written_bytes = self.file_path.stat().st_size if self.file_path.exists() else 0

        def _rotate_file(self):
            """Close current file and open a new one with fresh timestamp."""
            if self.file:
                self.file.close()
            self.file_path = self._create_log_path()
            self._open_file()
            self._buffer.clear()

        def _flush_buffer(self):
            if not self.file or not self._buffer:
                return
            self.file.writelines(self._buffer)
            self.file.flush()
            self._written_bytes += sum(len(line.encode("utf-8")) for line in self._buffer)
            self._buffer.clear()
            # Rotate if exceeded
            if self._written_bytes > self.max_size:
                self._rotate_file()

        def write(self, message):
            self.original_stream.write(message)
            if not self.file:
                return
            self._buffer.append(message)
            if sum(len(line.encode("utf-8")) for line in self._buffer) >= _BUFFER_FLUSH_SIZE:
                self._flush_buffer()

        def flush(self):
            self.original_stream.flush()
            self._flush_buffer()

    def _get_user_max_file_size(default_log_max_file_size: int = _DEFAULT_LOG_MAX_FILE_SIZE) -> int:
        try:
            return int(os.environ.get("LOG_MAX_SIZE", str(default_log_max_file_size)))
        except ValueError:
            return default_log_max_file_size

    def _verify_user_log_path(default_log_folder: Path = _DEFAULT_LOG_FOLDER) -> Path:
        raw_log_folder = os.environ.get("LOG_FOLDER_NAME", str(default_log_folder))
        try:
            candidate = (Path(__file__).parent / raw_log_folder).resolve(strict=False)
            # Keep within project root
            if not str(candidate).startswith(str(Path(__file__).parent.resolve())):
                raise ValueError("Unsafe path traversal detected")
            if len(str(candidate)) > 255:
                raise ValueError("Path too long")
            return candidate
        except ValueError as e:
            print(f"[WARN] Invalid LOG_FOLDER_NAME ({raw_log_folder!r}): {e}. Falling back to default.")
            return default_log_folder

    def start_logging(default_log_folder: Path = _DEFAULT_LOG_FOLDER, default_max_filesize: int = _DEFAULT_LOG_MAX_FILE_SIZE) -> None:
        _log_folder: Path = _verify_user_log_path(default_log_folder)
        _max_file_size: int = _get_user_max_file_size(default_max_filesize)
        _log_folder.mkdir(parents=True, exist_ok=True)

        sys.stdout = TeeStream(_log_folder, sys.stdout, _max_file_size)
        sys.stderr = TeeStream(_log_folder, sys.stderr, _max_file_size)

        # Ensure final flush at exit
        atexit.register(sys.stdout.flush)
        atexit.register(sys.stderr.flush)

    if __name__ == "__main__":
        start_logging(_DEFAULT_LOG_FOLDER, _DEFAULT_LOG_MAX_FILE_SIZE)
