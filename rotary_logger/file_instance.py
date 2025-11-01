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
# FILE: file_instance.py
# CREATION DATE: 30-10-2025
# LAST Modified: 1:48:48 01-11-2025
# DESCRIPTION:
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the file containing the class that is in charge of handling writing and rotating files regardless of the number of external processes calling it
# // AR
# +==== END rotary_logger =================+
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union, Dict, List, IO, Any
from threading import RLock
from warnings import warn

try:
    from . import constants as CONST
except ImportError:
    import constants as CONST


class FileInstance:

    def __init__(
        self,
        file_path: Optional[Union[str, Path, CONST.FileInfo]],
        override: Optional[bool] = None,
        merged: Optional[bool] = None,
        encoding: Optional[str] = None,
        prefix: Optional[CONST.Prefix] = None,
        *,
        max_size_mb: Optional[int] = None,
        flush_size_kb: Optional[int] = None,
        folder_prefix: Optional[CONST.StdMode] = None
    ) -> None:
        # per-instance mutable defaults (avoid sharing across instances)
        self._file_lock: RLock = RLock()
        self._mode: str = "a"
        self.file: Optional[CONST.FileInfo] = None
        self.override: bool = False
        self.merged: bool = True
        self.encoding: str = CONST.DEFAULT_ENCODING
        self.prefix: Optional[CONST.Prefix] = None
        self.max_size: int = CONST.DEFAULT_LOG_MAX_FILE_SIZE
        self.flush_size: int = CONST.BUFFER_FLUSH_SIZE
        self.folder_prefix: Optional[CONST.StdMode] = None

        self._buffer: List[str] = []
        if override:
            self.set_override(override)
        if merged:
            self.set_merged(merged)
        if encoding:
            self.set_encoding(encoding)
        if prefix:
            self.set_prefix(prefix)
        if max_size_mb:
            self._set_max_size(max_size_mb)
        if flush_size_kb:
            self._set_flush_size(flush_size_kb)
        if folder_prefix:
            self.set_folder_prefix(folder_prefix)
        if file_path:
            self.set_filepath(file_path)

    def __del__(self) -> None:
        if self.file and self.file.descriptor:
            if not self.file.descriptor.closed:
                try:
                    self._close_file()
                except OSError:
                    pass
        self.file = None

    def set_max_size(self, max_size_mb: int, *, lock: bool = True) -> None:
        if lock:
            with self._file_lock:
                self._set_max_size(max_size_mb)
                return
        self._set_max_size(max_size_mb)

    def set_folder_prefix(self, folder_prefix: Optional[CONST.StdMode], *, lock: bool = True) -> None:
        if lock:
            with self._file_lock:
                self._set_folder_prefix(folder_prefix)
                return
        self._set_folder_prefix(folder_prefix)

    def set_flush_size(self, flush_size: int, *, lock: bool = True) -> None:
        if lock:
            with self._file_lock:
                self._set_flush_size(flush_size)
                return
        self._set_flush_size(flush_size)

    def set_merged(self, merged: bool, *, lock: bool = True) -> None:
        if lock:
            with self._file_lock:
                self.merged = bool(merged)
                return
        self.merged = bool(merged)

    def set_encoding(self, encoding: str, *, lock: bool = True) -> None:
        if lock:
            with self._file_lock:
                self.encoding = encoding
                return
        self.encoding = encoding

    def set_prefix(self, prefix: Optional[CONST.Prefix], *, lock: bool = True) -> None:
        if lock:
            with self._file_lock:
                self._set_prefix(prefix)
                return
        self._set_prefix(prefix)
        return

    def set_override(self, override: bool = False, *, lock: bool = True) -> None:
        _value: Dict[bool, str] = {
            True: "w",
            False: "a"
        }
        if lock:
            with self._file_lock:
                self._set_mode(_value[bool(override)], lock=False)
                return
        self._set_mode(_value[bool(override)], lock=False)

    def set_filepath(self, file_path: Optional[Union[str, Path, CONST.FileInfo]], *, lock: bool = True) -> None:
        if not file_path:
            if lock:
                with self._file_lock:
                    self._close_file(lock=False)
                    self.file = None
                    return
            self._close_file(lock=False)
            self.file = None
            return
        if lock:
            with self._file_lock:
                self._set_filepath_child(file_path)
                return
        self._set_filepath_child(file_path)

    def get_mode(self, *, lock: bool = True) -> str:
        if lock:
            with self._file_lock:
                return self._mode
        return self._mode

    def get_merged(self, *, lock: bool = True) -> bool:
        if lock:
            with self._file_lock:
                return self.merged
        return self.merged

    def get_encoding(self, *, lock: bool = True) -> str:
        if lock:
            with self._file_lock:
                return self.encoding
        return self.encoding

    def get_prefix(self, *, lock: bool = True) -> Optional[CONST.Prefix]:
        if self.prefix:
            if lock:
                with self._file_lock:
                    _prefix = CONST.Prefix()
                    _prefix.std_in = self.prefix.std_in
                    _prefix.std_out = self.prefix.std_out
                    _prefix.std_err = self.prefix.std_err
                    return _prefix
            _prefix = CONST.Prefix()
            _prefix.std_in = self.prefix.std_in
            _prefix.std_out = self.prefix.std_out
            _prefix.std_err = self.prefix.std_err
            return _prefix
        return None

    def get_override(self, *, lock: bool = True) -> bool:
        _value: Dict[str, bool] = {
            "w": True,
            "a": False
        }
        if lock:
            with self._file_lock:
                mode: str = self.get_mode(lock=False).lower()
                if mode in _value:
                    return _value[mode]
                raise ValueError("Unsupported mode")
        mode: str = self.get_mode(lock=False).lower()
        if mode in _value:
            return _value[mode]
        raise ValueError("Unsupported mode")

    def get_filepath(self, *, lock: bool = True) -> Optional[CONST.FileInfo]:
        if lock:
            with self._file_lock:
                return self.file
        return self.file

    def get_flush_size(self, *, lock: bool = True) -> int:
        if lock:
            with self._file_lock:
                return self.flush_size
        return self.flush_size

    def get_max_size(self, *, lock: bool = True) -> int:
        if lock:
            with self._file_lock:
                return self.max_size
        return self.max_size

    def get_folder_prefix(self, *, lock: bool = True) -> Optional[CONST.StdMode]:
        if lock:
            with self._file_lock:
                return self.folder_prefix
        return self.folder_prefix

    def update(self, file_data: Optional['FileInstance'], *, lock: bool = True) -> None:
        if lock:
            with self._file_lock:
                self._update(file_data)
                return
        self._update(file_data)

    def copy(self, *, lock: bool = True) -> "FileInstance":
        if lock:
            with self._file_lock:
                return self._copy()
        return self._copy()

    def write(self, message: str) -> None:
        """Function in charge of writing content to a stream a file if present and buffer hit, otherwise, appends values to the buffer.

        Args:
            message (str): The message to be displayed
        """
        # append under lock, then decide whether to flush
        with self._file_lock:
            self._buffer.append(message)
            should = self._should_flush()
        if should:
            self._flush_buffer()

    def flush(self):
        """Function that can be used to force the program to flush it's current stream and buffer
        """
        self._flush_buffer()

    def _set_prefix(self, prefix: Optional[CONST.Prefix]) -> None:
        if not prefix:
            self.prefix = None
            return
        # internal setter assumes caller handles locking
        self.prefix = CONST.Prefix()
        self.prefix.std_in = prefix.std_in
        self.prefix.std_out = prefix.std_out
        self.prefix.std_err = prefix.std_err

    def _set_folder_prefix(self, folder_prefix: Optional[CONST.StdMode]) -> None:
        if folder_prefix and folder_prefix in CONST.CORRECT_FOLDER:
            self.folder_prefix = folder_prefix
            return
        self.folder_prefix = None

    def _set_mode(self, mode: str, *, lock: bool = True) -> None:
        if lock:
            with self._file_lock:
                if mode in ("w", "a"):
                    self._mode = mode
        if mode in ("w", "a"):
            self._mode = mode

    def _set_max_size(self, max_size_mb: int) -> None:
        # Treat parameter as a count of megabytes (MB)
        try:
            _resp: int = int(max_size_mb)
        except ValueError:
            _resp = CONST.DEFAULT_LOG_MAX_FILE_SIZE
        if _resp < 0:
            warn("Max provided size cannot be negative, converting to positive")
            _resp = abs(_resp)
        if _resp < 1:
            warn("Max provided size is smaller than 1 MB, using default max file size")
            _resp = CONST.DEFAULT_LOG_MAX_FILE_SIZE
        # Convert MB to bytes
        if _resp < CONST.MB1:
            self.max_size = _resp * CONST.MB1
        else:
            self.max_size = _resp

    def _set_flush_size(self, flush_size_kb: int) -> None:
        # Treat parameter as a count of kilobytes (KB)
        try:
            _resp = int(flush_size_kb)
        except ValueError:
            _resp = CONST.DEFAULT_LOG_BUFFER_FLUSH_SIZE
        if _resp < 0:
            warn("Flush size cannot be negative, converting to positive")
            _resp = abs(_resp)
        if _resp < 1:
            warn("Flush size is smaller than 1 KB, using default flush size")
            _resp = CONST.DEFAULT_LOG_BUFFER_FLUSH_SIZE
        # Convert KB to bytes
        if _resp < CONST.KB1:
            self.flush_size = _resp * CONST.KB1
        else:
            self.flush_size = _resp

    def _set_filepath_child(self, file_path: Union[str, Path, CONST.FileInfo]) -> None:
        self._close_file(lock=False)
        # ensure the internal reference is cleared
        self.file = None
        if isinstance(file_path, (str, Path)):
            _path = Path(file_path)
            self.file = self._open_file(_path)
        elif isinstance(file_path, CONST.FileInfo):
            self.file = file_path
            if self.file:
                if self.file.path and not self.file.descriptor:
                    self.file = self._open_file(self.file.path)

    def _update(self, file_data: Optional['FileInstance']) -> None:
        if not file_data:
            return
        self.set_filepath(file_data.get_filepath(), lock=False)
        self.set_override(file_data.get_override(), lock=False)
        self.set_merged(file_data.get_merged(), lock=False)
        self.set_encoding(file_data.get_encoding(), lock=False)
        self.set_prefix(file_data.get_prefix(), lock=False)
        self.set_max_size(file_data.get_max_size(), lock=False)
        self.set_flush_size(file_data.get_flush_size(), lock=False)
        self.set_folder_prefix(file_data.get_folder_prefix(), lock=False)

    def _copy(self) -> "FileInstance":
        tmp = FileInstance(None)
        tmp.set_filepath(self.get_filepath(), lock=False)
        tmp.set_override(self.get_override(), lock=False)
        tmp.set_merged(self.get_merged(), lock=False)
        tmp.set_encoding(self.get_encoding(), lock=False)
        tmp.set_prefix(self.get_prefix(), lock=False)
        tmp.set_flush_size(self.get_flush_size(), lock=False)
        tmp.set_max_size(self.get_max_size(), lock=False)
        tmp.set_folder_prefix(self.get_folder_prefix(), lock=False)
        return tmp

    def _get_current_date(self) -> datetime:
        return datetime.now(timezone.utc)

    def _get_filename(self) -> str:
        return self._get_current_date().strftime(f"{CONST.FILE_LOG_DATE_FORMAT}.log")

    def _should_flush(self) -> bool:
        """Function in charge of checking if the buffer size has been hit and thus needs to be cleared.

        Returns:
            bool: True if hit, False otherwise
        """
        _tmp: int = 0
        for line in self._buffer:
            _tmp += len(line.encode(self.encoding))
        return _tmp >= self.flush_size

    def _refresh_written_bytes(self) -> None:
        if not self.file:
            return
        for line in self._buffer:
            try:
                self.file.written_bytes += len(line.encode(self.encoding))
            except LookupError:
                self.file.written_bytes += len(line.encode('utf-8'))
        self._buffer.clear()

    def _should_rotate(self) -> bool:
        """Function in charge of checking if the buffer size has been hit and thus needs to be cleared.

        Returns:
            bool: True if hit, False otherwise
        """
        if self.file:
            return self.file.written_bytes > self.max_size
        return True

    def _rotate_file(self) -> None:
        if self._should_rotate():
            self._close_file()
            log_path: Path = self._create_log_path()
            self.file = self._open_file(log_path)

    def _create_log_path(self) -> Path:
        """Function in charge of creating the log path on disk.

        Returns:
            Path: The log_path
        """
        base = None
        if self.file and isinstance(self.file.path, Path):
            candidate = self.file.path
            if candidate.suffix == '.log':
                candidate.parent.mkdir(parents=True, exist_ok=True)
                return candidate
            base = candidate

        now = self._get_current_date()
        _root: Path = Path(__file__).parent
        if base is not None:
            _root = base
        elif self.file and self.file.path:
            _root = self.file.path

        year_dir = _root / str(now.year)
        month_dir = year_dir / f"{now.month:02d}"
        day_dir = month_dir / f"{now.day:02d}"
        if self.folder_prefix and self.folder_prefix in CONST.CORRECT_FOLDER:
            day_dir = day_dir / CONST.CORRECT_FOLDER[self.folder_prefix]
        day_dir.mkdir(parents=True, exist_ok=True)
        filename = self._get_filename()
        return day_dir / filename

    def _open_file(self, file_path: Path) -> CONST.FileInfo:
        """Function in charge of opening a file instance so that the program can write to it.
        """
        _node: CONST.FileInfo = CONST.FileInfo()
        _node.path = Path(file_path)
        _node.path.parent.mkdir(parents=True, exist_ok=True)
        _node.descriptor = open(
            file_path,
            self._mode,
            encoding=self.encoding,
            newline="\n"
        )
        if file_path.exists():
            _node.written_bytes = file_path.stat().st_size
        else:
            _node.written_bytes = 0
        return _node

    def _close_file_inner(self) -> bool:
        if self.file:
            descriptor = getattr(self.file, "descriptor", None)
            if descriptor:
                try:
                    descriptor.close()
                except (OSError, ValueError):
                    # ignore errors closing the descriptor (IO and value errors)
                    pass
                # clear descriptor reference so subsequent checks see it's closed
                try:
                    self.file.descriptor = None
                except AttributeError:
                    # unlikely, but guard against missing attribute
                    pass
        return True

    def _close_file(self, *, lock: Optional[bool] = True) -> bool:
        if lock:
            with self._file_lock:
                return self._close_file_inner()
        return self._close_file_inner()

    def _flush_buffer(self):
        """Function in charge of 
        """
        # Swap-buffer pattern: capture pending writes under lock, then perform I/O
        with self._file_lock:
            if not self._buffer:
                return
            to_write = self._buffer
            # detach buffer so writers won't block on I/O
            self._buffer = []

            # ensure file and descriptor exist and are open (open under lock)
            if not self.file or not getattr(self.file, "descriptor", None) or getattr(self.file.descriptor, "closed", False):
                log_path: Path = self._create_log_path()
                self.file = self._open_file(log_path)

        # perform actual write outside the lock to avoid blocking writers
        try:
            descriptor: Optional[IO[Any]] = None
            if self.file:
                descriptor = getattr(
                    self.file,
                    "descriptor",
                    None
                )
            if descriptor and not getattr(descriptor, "closed", False):
                descriptor.writelines(to_write)
                descriptor.flush()
        except (ValueError, OSError):
            # try reopening and write again once
            log_path: Path = self._create_log_path()
            self.file = self._open_file(log_path)
            descriptor: Optional[IO[Any]] = None
            if self.file:
                descriptor = getattr(self.file, "descriptor", None)
            if descriptor and not getattr(descriptor, "closed", False):
                descriptor.writelines(to_write)
                descriptor.flush()

        # update counters and rotate under lock
        with self._file_lock:
            if not self.file:
                return
            for line in to_write:
                try:
                    self.file.written_bytes += len(line.encode(self.encoding))
                except LookupError:
                    self.file.written_bytes += len(line.encode('utf-8'))
            # perform rotation if needed
            self._rotate_file()
