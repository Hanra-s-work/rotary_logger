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
# LAST Modified: 9:14:51 01-11-2025
# DESCRIPTION:
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the file containing the class that is in charge of handling writing and rotating files regardless of the number of external processes calling it
# // AR
# +==== END rotary_logger =================+
"""

import os
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
    """Manage buffered writes, file descriptors, and log rotation.

    Public methods are thread-safe and documented below. Writes are
    appended to an in-memory buffer and flushed to disk when the
    configured flush size is reached. Rotation is performed when the
    underlying file grows beyond `max_size`.
    """

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
        folder_prefix: Optional[CONST.StdMode] = None,
        log_to_file: bool = True
    ) -> None:
        """Create a FileInstance wrapper.

        Args:
            file_path: initial file path, Path or FileInfo, or None to defer.
            override: when True open files for write ('w') instead of append ('a').
            merged: whether multiple streams should share the same file.
            encoding: text encoding to use for file I/O.
            prefix: optional Prefix to use when teeing.
            max_size_mb: optional maximum logfile size in MB.
            flush_size_kb: optional buffer flush size in KB.
            folder_prefix: optional StdMode to segregate per-stream folders.
        """

        # per-instance mutable defaults (avoid sharing across instances)
        self._file_lock: RLock = RLock()
        self._mode: str = "a"
        self._log_to_file: bool = log_to_file
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
        """Best-effort cleanup on object deletion.

        Attempt to close the current file descriptor if it exists and is
        open. This method must never raise during interpreter shutdown
        (where `__del__` may be called), so IO-related errors are
        swallowed. After attempting to close the descriptor the internal
        `file` reference is cleared.
        """
        if self.file and self.file.descriptor:
            if not self.file.descriptor.closed:
                try:
                    self._close_file()
                except OSError:
                    # Swallow errors during destructor cleanup
                    pass
        self.file = None

    def set_log_to_file(self, log_to_file: bool, *, lock: bool = True) -> None:
        """Public wrapper to set the maximum logfile size.

        Args:
            max_size_mb: maximum size in megabytes (or an absolute byte
                value). The value will be normalised by
                `_set_max_size` and stored in `self.max_size` as
                bytes.
            lock: when True the instance lock is acquired while
                updating the configuration.
        """
        if lock:
            with self._file_lock:
                self._log_to_file: bool = log_to_file
                return
        self._log_to_file: bool = log_to_file

    def set_max_size(self, max_size_mb: int, *, lock: bool = True) -> None:
        """Public wrapper to set the maximum logfile size.

        Args:
            max_size_mb: maximum size in megabytes (or an absolute byte
                value). The value will be normalised by
                `_set_max_size` and stored in `self.max_size` as
                bytes.
            lock: when True the instance lock is acquired while
                updating the configuration.
        """
        if lock:
            with self._file_lock:
                self._set_max_size(max_size_mb)
                return
        self._set_max_size(max_size_mb)

    def set_folder_prefix(self, folder_prefix: Optional[CONST.StdMode], *, lock: bool = True) -> None:
        """Public setter for `folder_prefix`.

        When `lock` is True the instance lock is held while the value is
        updated. The internal method `_set_folder_prefix` performs the
        validation and assignment.
        """
        if lock:
            with self._file_lock:
                self._set_folder_prefix(folder_prefix)
                return
        self._set_folder_prefix(folder_prefix)

    def set_flush_size(self, flush_size: int, *, lock: bool = True) -> None:
        """Public wrapper to configure the buffer flush threshold.

        `flush_size` is provided as a KB-like value and normalised by
        `_set_flush_size`. If `lock` is True the operation is
        performed while holding the instance lock.
        """
        if lock:
            with self._file_lock:
                self._set_flush_size(flush_size)
                return
        self._set_flush_size(flush_size)

    def set_merged(self, merged: bool, *, lock: bool = True) -> None:
        """Enable or disable stream merging.

        When `merged` is True multiple streams may share a single log
        file; when False separate per-stream files are used. The
        `lock` parameter controls whether the instance lock is
        acquired.
        """
        if lock:
            with self._file_lock:
                self.merged = bool(merged)
                return
        self.merged = bool(merged)

    def set_encoding(self, encoding: str, *, lock: bool = True) -> None:
        """Set the text encoding used for file I/O.

        Args:
            encoding: a codec name such as 'utf-8'. When `lock` is True
                the change is performed while holding the lock.
        """
        if lock:
            with self._file_lock:
                self.encoding = encoding
                return
        self.encoding = encoding

    def set_prefix(self, prefix: Optional[CONST.Prefix], *, lock: bool = True) -> None:
        """Public setter for `Prefix` configuration.

        Copies the provided `prefix` into an internal `CONST.Prefix`
        object. Use `get_prefix()` to obtain a safe copy of the
        current configuration.
        """
        if lock:
            with self._file_lock:
                self._set_prefix(prefix)
                return
        self._set_prefix(prefix)
        return

    def set_override(self, override: bool = False, *, lock: bool = True) -> None:
        """Public setter for the file open mode.

        When `override` is True files will be opened with mode 'w'
        (overwrite); otherwise 'a' (append) is used. The lock
        behaviour is controlled by `lock`.
        """
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
        """Set or clear the active file/file path for this instance.

        Args:
            file_path: a path-like object, a `CONST.FileInfo` instance
                describing an already-open file, or None to clear the
                current file. When `lock` is True the instance lock is
                held while the change is applied.
        """
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

    def get_log_to_file(self, *, lock: bool = True) -> bool:
        if lock:
            with self._file_lock:
                return self._log_to_file
        return self._log_to_file

    def get_mode(self, *, lock: bool = True) -> str:
        """Return the current file open mode ('w' or 'a').

        When `lock` is True the instance lock is acquired prior to
        reading the value.
        """
        if lock:
            with self._file_lock:
                return self._mode
        return self._mode

    def get_merged(self, *, lock: bool = True) -> bool:
        """Return the merged flag (True when streams share a file).

        The optional `lock` parameter controls whether the instance
        lock is held while reading the value.
        """
        if lock:
            with self._file_lock:
                return self.merged
        return self.merged

    def get_encoding(self, *, lock: bool = True) -> str:
        """Return the configured text encoding for file writes.

        When `lock` is True the instance lock is held while the value
        is read.
        """
        if lock:
            with self._file_lock:
                return self.encoding
        return self.encoding

    def get_prefix(self, *, lock: bool = True) -> Optional[CONST.Prefix]:
        """Return a safe copy of the current `Prefix` configuration.

        The returned `CONST.Prefix` is a fresh object to avoid exposing
        internal references. If no prefix is configured None is
        returned. When `lock` is True the instance lock is held while
        copying the object.
        """
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
        """Return True when override mode ('w') is active.

        This convenience maps internal mode strings to a boolean.
        When `lock` is True the instance lock is held for the check.
        """
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
        """Return the internal `FileInfo` reference (may be None).

        Note: the returned object may be shared; callers that need to
        mutate it should take care to hold the instance lock or use
        `copy()` to obtain an independent view.
        """
        if lock:
            with self._file_lock:
                return self.file
        return self.file

    def get_flush_size(self, *, lock: bool = True) -> int:
        """Return the configured buffer flush threshold in bytes."""
        if lock:
            with self._file_lock:
                return self.flush_size
        return self.flush_size

    def get_max_size(self, *, lock: bool = True) -> int:
        """Return the configured maximum file size in bytes."""
        if lock:
            with self._file_lock:
                return self.max_size
        return self.max_size

    def get_folder_prefix(self, *, lock: bool = True) -> Optional[CONST.StdMode]:
        """Return the configured folder prefix (StdMode) or None."""
        if lock:
            with self._file_lock:
                return self.folder_prefix
        return self.folder_prefix

    def update(self, file_data: Optional['FileInstance'], *, lock: bool = True) -> None:
        """Public method to copy configuration from another instance.

        This method acquires the lock by default and delegates to the
        `_update` implementation which performs the actual field
        assignments.
        """
        if lock:
            with self._file_lock:
                self._update(file_data)
                return
        self._update(file_data)

    def copy(self, *, lock: bool = True) -> "FileInstance":
        """Return a shallow copy of this instance's configuration.

        The returned `FileInstance` is a new object populated from the
        current instance. By default the instance lock is acquired to
        provide a consistent snapshot.
        """
        if lock:
            with self._file_lock:
                return self._copy()
        return self._copy()

    def write(self, message: str) -> None:
        """Append `message` to the internal buffer (thread-safe).

        The message is encoded and counted toward `flush_size`. When the
        buffer reaches the configured threshold a background flush is
        triggered (performed synchronously inside `_flush_buffer()` but
        with I/O outside the main lock to minimize blocking).
        """
        # append under lock, then decide whether to flush
        with self._file_lock:
            self._buffer.append(message)
            should = self._should_flush()
        if should:
            self._flush_buffer()

    def flush(self):
        """Flush any buffered log lines to disk immediately.

        This is a blocking call that performs disk I/O; callers should
        avoid calling it too frequently. Errors raised by the underlying
        I/O are propagated as OSError or ValueError when appropriate.
        """
        self._flush_buffer()

    def _set_prefix(self, prefix: Optional[CONST.Prefix]) -> None:
        """Set the internal `Prefix` object from an external one.

        This internal setter copies boolean flag values from `prefix`
        into a fresh `CONST.Prefix()` instance. The caller is
        responsible for holding any required locks; this routine does
        not perform locking itself.
        """
        if not prefix:
            self.prefix = None
            return
        # internal setter assumes caller handles locking
        self.prefix = CONST.Prefix()
        self.prefix.std_in = prefix.std_in
        self.prefix.std_out = prefix.std_out
        self.prefix.std_err = prefix.std_err

    def _set_folder_prefix(self, folder_prefix: Optional[CONST.StdMode]) -> None:
        """Configure the per-stream folder prefix.

        If `folder_prefix` is a valid `CONST.StdMode` value present in
        `CONST.CORRECT_FOLDER`, it is stored; otherwise the stored
        `folder_prefix` is cleared (set to None).
        """
        if folder_prefix and folder_prefix in CONST.CORRECT_FOLDER:
            self.folder_prefix = folder_prefix
            return
        self.folder_prefix = None

    def _set_mode(self, mode: str, *, lock: bool = True) -> None:
        """Set the file mode to 'w' (overwrite) or 'a' (append).

        The `lock` parameter indicates whether this function should
        acquire `self._file_lock` before updating the internal mode.
        Invalid input is ignored.
        """
        if lock:
            with self._file_lock:
                if mode in ("w", "a"):
                    self._mode = mode
                return
        if mode in ("w", "a"):
            self._mode = mode

    def _set_max_size(self, max_size_mb: int) -> None:
        """Configure the maximum file size used for rotation.

        `max_size_mb` is interpreted as megabytes when reasonable; the
        function attempts to coerce the input to an integer. Negative
        or too-small values are corrected with warnings. The resulting
        internal `self.max_size` is stored in bytes.
        """
        # Treat parameter as a count of megabytes (MB)
        try:
            _resp: int = int(max_size_mb)
        except (ValueError, TypeError):
            _resp = CONST.DEFAULT_LOG_MAX_FILE_SIZE
        if _resp < 0:
            warn("Max provided size cannot be negative, converting to positive")
            _resp = abs(_resp)
        if _resp < 1:
            warn("Max provided size is smaller than 1 MB, using default max file size")
            _resp = CONST.DEFAULT_LOG_MAX_FILE_SIZE
        # Convert MB to bytes (if the provided number looks like MB)
        if _resp < CONST.MB1:
            self.max_size = _resp * CONST.MB1
        else:
            self.max_size = _resp

    def _set_flush_size(self, flush_size_kb: int) -> None:
        """Configure the flush threshold for buffered writes.

        `flush_size_kb` is interpreted as kilobytes when reasonable; the
        function coerces input to int, normalises negative values and
        ensures the internal `self.flush_size` is stored in bytes.
        """
        # Treat parameter as a count of kilobytes (KB)
        try:
            _resp = int(flush_size_kb)
        except (ValueError, TypeError):
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
        """Internal routine to set the instance's file reference.

        This method closes any previously-open file, clears internal
        state, and opens the provided `file_path`. The `file_path` may
        be a string/Path (in which case a new `FileInfo` is created)
        or an existing `CONST.FileInfo` instance which may be re-opened
        if necessary.
        """
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
        """Copy configuration values from another FileInstance.

        This helper updates the receiver to match the provided
        `file_data`. The method is intended to be called while holding
        the caller's lock; it delegates to public setters with the
        `lock=False` flag to avoid deadlocks.
        """
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
        self.set_log_to_file(file_data.get_log_to_file(), lock=False)

    def _copy(self) -> "FileInstance":
        """Return a shallow copy of this FileInstance configuration.

        The returned `FileInstance` will share the same `FileInfo`
        reference but will otherwise have the same configuration
        values (mode, encoding, prefix, sizes). The copy is useful for
        creating per-stream views of shared configuration.
        """
        tmp = FileInstance(None)
        tmp.set_filepath(self.get_filepath(), lock=False)
        tmp.set_override(self.get_override(), lock=False)
        tmp.set_merged(self.get_merged(), lock=False)
        tmp.set_encoding(self.get_encoding(), lock=False)
        tmp.set_prefix(self.get_prefix(), lock=False)
        tmp.set_flush_size(self.get_flush_size(), lock=False)
        tmp.set_max_size(self.get_max_size(), lock=False)
        tmp.set_folder_prefix(self.get_folder_prefix(), lock=False)
        tmp.set_log_to_file(self.get_log_to_file(), lock=False)
        return tmp

    def _get_current_date(self) -> datetime:
        """Return the current UTC datetime used for naming files.

        Centralising the time provider makes it easier to test
        filename generation and ensures all timestamps use UTC.
        """
        return datetime.now(timezone.utc)

    def _get_filename(self) -> str:
        """Construct a timestamped log filename.

        The filename format is driven by `CONST.FILE_LOG_DATE_FORMAT` and
        uses the current UTC time returned by `_get_current_date()`.
        """
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
        """Add the sizes of buffered lines to `file.written_bytes`.

        This method is called after a successful write to update the
        persisted byte counter. It encodes lines using the configured
        encoding and falls back to 'utf-8' on lookup errors. The in-
        memory buffer is cleared after accounting.
        """
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
        """Rotate the current file if the bytes threshold is exceeded.

        When rotation is needed the current descriptor is closed and a
        fresh `FileInfo` is opened at a newly-created path returned by
        `_create_log_path()`.
        """
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

        if _root.suffix == "" and CONST.LOG_FOLDER_BASE_NAME != _root.name:
            _root = _root / CONST.LOG_FOLDER_BASE_NAME
        elif _root.suffix != "" and CONST.LOG_FOLDER_BASE_NAME != _root.parent:
            _root = _root.parent / CONST.LOG_FOLDER_BASE_NAME / _root.name

        year_dir = _root / str(now.year)
        month_dir = year_dir / f"{now.month:02d}"
        day_dir = month_dir / f"{now.day:02d}"
        if self.folder_prefix and self.folder_prefix in CONST.CORRECT_FOLDER:
            day_dir = day_dir / CONST.CORRECT_FOLDER[self.folder_prefix]
        with self._file_lock:
            if self._log_to_file:
                day_dir.mkdir(parents=True, exist_ok=True)
        filename = self._get_filename()
        return day_dir / filename

    def _looks_like_directory(self, dir_path: Path) -> bool:
        if not str(dir_path):
            return False
        if dir_path.suffix == "":
            return True
        # If it already exists and is a directory, fine
        if dir_path.exists():
            return dir_path.is_dir()

        # If the parent exists and is writable, assume it *could* be a directory
        str_path: str = str(dir_path)
        return str_path.endswith(os.sep) or str_path.endswith("/") or str_path.endswith("\\")

    def _open_file(self, file_path: Path) -> CONST.FileInfo:
        """Function in charge of opening a file instance so that the program can write to it.
        """
        _node: CONST.FileInfo = CONST.FileInfo()
        _node.path = Path(file_path)
        if self._looks_like_directory(_node.path):
            _node.path = self._create_log_path()
        _node.path.parent.mkdir(parents=True, exist_ok=True)
        with self._file_lock:
            if self._log_to_file:
                _node.descriptor = open(
                    _node.path,
                    self._mode,
                    encoding=self.encoding,
                    newline="\n"
                )
            else:
                _node.descriptor = None
        if file_path.exists():
            _node.written_bytes = file_path.stat().st_size
        else:
            _node.written_bytes = 0
        return _node

    def _close_file_inner(self) -> bool:
        """Close the underlying file descriptor without acquiring locks.

        This inner helper is used by `_close_file()`; it performs the
        actual descriptor close and clears the reference. It is safe to
        call when already closed. Errors during close are suppressed
        because this is a best-effort operation.
        """
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
        """Close the current file descriptor, optionally acquiring a lock.

        When `lock` is True the instance lock `self._file_lock` is
        acquired before closing the file. Returns True on completion.
        """
        if lock:
            with self._file_lock:
                return self._close_file_inner()
        return self._close_file_inner()

    def _flush_buffer(self) -> None:
        """Internal: detach pending buffer and write to disk.

        Implements the swap-buffer pattern: capture and clear the in-memory
        buffer while holding the lock, perform I/O outside the lock, then
        update counters and rotate under lock.
        """
        # Swap-buffer pattern: capture pending writes under lock, then perform I/O
        with self._file_lock:
            if not self._buffer:
                return
            to_write = self._buffer
            # detach buffer so writers won't block on I/O
            self._buffer = []

            if not self._log_to_file:
                return

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
