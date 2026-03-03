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
# FILE: tee_stream.py
# CREATION DATE: 29-10-2025
# LAST Modified: 14:49:6 03-03-2026
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: The file containing the code that is actually doing the heavy lifting, this is the file that takes a stream, logs it to a file while outputting it to the terminal.
# // AR
# +==== END rotary_logger =================+
"""

import sys
from pathlib import Path
from typing import TextIO, Optional, Union, BinaryIO, List, Any
from threading import RLock

try:
    from . import constants as CONST
    from .file_instance import FileInstance
except ImportError:
    import constants as CONST
    from file_instance import FileInstance


class TeeStream:
    """Mirror a TextIO stream to disk while preserving normal output.

    This class is intentionally lightweight: it captures short-lived
    references under a tiny lock and then performs I/O without holding
    that lock. Terminal writes are performed on the caller thread and
    are wrapped to avoid raising unexpected errors back into the
    application; disk writes are delegated to a `FileInstance` which
    buffers and handles rotation.
    """

    def __init__(
        self,
        root: Union[str, Path, FileInstance],
        original_stream: TextIO,
        *,
        max_size_mb: Optional[int] = None,
        flush_size: Optional[int] = None,
        mode: CONST.StdMode = CONST.StdMode.STDUNKNOWN,
        error_mode: CONST.ErrorMode = CONST.ErrorMode.WARN_NO_PIPE,
        encoding: Optional[str] = None,
        log_to_file: bool = True
    ):
        """Create a TeeStream.

        Args:
            root: a `Path` or `FileInstance` describing the destination.
            original_stream: the TextIO to mirror (usually sys.stdout).
            max_size_mb: optional maximum logfile size in MB (passed to FileInstance).
            flush_size: optional buffer flush threshold (passed to FileInstance).
            mode: which standard stream this wraps (StdMode).
            error_mode: Broken-pipe handling policy (ErrorMode).
            encoding: optional file encoding override.
        """

        self._file_lock: RLock = RLock()
        if isinstance(root, (Path, str)):
            self.file_instance = FileInstance(Path(root))
        elif isinstance(root, FileInstance):
            self.file_instance = root
        else:
            raise ValueError(
                f"{CONST.MODULE_NAME} Unsupported type for the file {type(root)}"
            )
        if max_size_mb:
            self.file_instance.set_max_size(max_size_mb)
        if flush_size:
            self.file_instance.set_flush_size(flush_size)
        if encoding:
            self.file_instance.set_encoding(encoding)
        self.file_instance.set_log_to_file(log_to_file)
        self.stream_mode: CONST.StdMode = mode
        self.original_stream: TextIO = original_stream
        self.error_mode: CONST.ErrorMode = error_mode
        self.stream_not_present: AttributeError = AttributeError(
            f"{CONST.MODULE_NAME} No stream available"
        )

    def __del__(self):
        """Best-effort cleanup on object deletion.

        Attempt to flush buffered data but never raise. Note that
        ``__del__`` may not be called at interpreter shutdown; callers
        that need deterministic flushing should call ``flush()``
        explicitly.
        """
        try:
            self.flush()
        except (OSError, ValueError):
            # best-effort flush; ignore expected I/O errors during interpreter shutdown
            pass
        # avoid deleting attributes in __del__; simply drop the reference
        self.file_instance = None

    def _get_correct_prefix(self) -> str:
        """Return the correct prefix string for the configured StdMode.

        The result will already contain a trailing space when non-empty.
        """
        # ensure we have a file instance and a valid StdMode enum value
        _file_inst: Optional[FileInstance] = None
        _prefix: Optional[CONST.Prefix] = None
        _mode: Optional[CONST.StdMode] = None
        with self._file_lock:
            if not self.file_instance:
                return ""
            _file_inst = self.file_instance
            if not isinstance(self.stream_mode, CONST.StdMode):
                return ""
            _mode = self.stream_mode

        # Fast-path: if logging to file is disabled, skip prefix work.
        try:
            if not _file_inst.get_log_to_file():
                return ""
        except (OSError, ValueError, AttributeError):
            # Defensive: don't allow file-side errors to break stdout/stderr
            return ""

        try:
            _prefix = _file_inst.get_prefix()
        except (OSError, ValueError, AttributeError):
            # Defensive: if FileInstance misbehaves, return no prefix
            return ""

        if not _prefix:
            return ""
        if _prefix.std_err and _mode == CONST.StdMode.STDERR:
            return CONST.CORRECT_PREFIX[CONST.StdMode.STDERR] + CONST.SPACE
        if _prefix.std_in and _mode == CONST.StdMode.STDIN:
            return CONST.CORRECT_PREFIX[CONST.StdMode.STDIN] + CONST.SPACE
        if _prefix.std_out and _mode == CONST.StdMode.STDOUT:
            return CONST.CORRECT_PREFIX[CONST.StdMode.STDOUT] + CONST.SPACE
        if _prefix.std_in or _prefix.std_err or _prefix.std_out:
            return CONST.CORRECT_PREFIX[CONST.StdMode.STDUNKNOWN] + CONST.SPACE
        return ""

    def _get_stream_if_present(self) -> TextIO:
        """Get the io stream if it exists, otherwise, raise an attribut error.

        Raises:
            self.stream_not_present (AttributeError) : The error raised when the stream is missing.

        Returns:
            TextIO: The io stream used in for forwarding the call.
        """
        if self.original_stream is not None:
            return self.original_stream
        raise self.stream_not_present

    def write(self, message: str) -> None:
        """Write `message` to the original stream and buffer it to file.

        This method is safe to call from multiple threads. It captures the
        necessary references under a short lock, performs the terminal
        write on the caller thread (with known error handling), then
        delegates buffered file writes to `FileInstance.write()`.
        """
        _tmp_message: str = message
        _file_instance: Optional[FileInstance] = None
        with self._file_lock:
            _file_instance = self.file_instance

        try:
            # Always attempt to write to the original stream
            self.original_stream.write(_tmp_message)
        except BrokenPipeError:
            if self.error_mode in (CONST.ErrorMode.EXIT, CONST.ErrorMode.EXIT_NO_PIPE):
                sys.exit(CONST.ERROR)
            elif self.error_mode in (CONST.ErrorMode.WARN, CONST.ErrorMode.WARN_NO_PIPE):
                try:
                    sys.stderr.write(CONST.BROKEN_PIPE_ERROR)
                except OSError:
                    pass
        except OSError as exc:
            # Unexpected I/O error writing to original stream: report and continue
            try:
                sys.stderr.write(
                    f"{CONST.MODULE_NAME} I/O error writing to original stream: {exc}\n"
                )
            except OSError:
                # swallow any errors writing to stderr during shutdown
                pass

        # If there's no file instance configured, nothing more to do
        if not _file_instance:
            return

        # Check whether file logging is enabled on the instance
        try:
            if not _file_instance.get_log_to_file():
                return
        except (OSError, ValueError, AttributeError):
            # Defensive: don't allow file-side errors to break stdout/stderr
            return

        # Compute prefix and write to file; protect against file-side errors
        try:
            _prefix: str = self._get_correct_prefix()
        except (OSError, ValueError, AttributeError):
            _prefix = ""

        try:
            _file_instance.write(f"{_prefix}{_tmp_message}")
        except (OSError, ValueError):
            try:
                sys.stderr.write(
                    f"{CONST.MODULE_NAME} Error writing to log file\n")
            except OSError:
                pass

    def writelines(self, lines: List[str]) -> None:
        """Write `message` to the original stream and buffer it to file.

        This method is safe to call from multiple threads. It captures the
        necessary references under a short lock, performs the terminal
        write on the caller thread (with known error handling), then
        delegates buffered file writes to `FileInstance.write()`.
        """
        _tmp_message: List[str] = lines.copy()
        _file_instance: Optional[FileInstance] = None
        with self._file_lock:
            _file_instance = self.file_instance
        try:
            # Always attempt to write to the original stream
            self.original_stream.writelines(_tmp_message)
        except BrokenPipeError:
            if self.error_mode in (CONST.ErrorMode.EXIT, CONST.ErrorMode.EXIT_NO_PIPE):
                sys.exit(CONST.ERROR)
            elif self.error_mode in (CONST.ErrorMode.WARN, CONST.ErrorMode.WARN_NO_PIPE):
                try:
                    sys.stderr.write(CONST.BROKEN_PIPE_ERROR)
                except OSError:
                    pass
        except OSError as exc:
            # Unexpected I/O error writing to original stream: report and continue
            try:
                sys.stderr.writelines(
                    f"{CONST.MODULE_NAME} I/O error writing to original stream: {exc}\n"
                )
            except OSError:
                # swallow any errors writing to stderr during shutdown
                pass
        # If there's no file instance configured, nothing more to do
        if not _file_instance:
            return

        # Check whether file logging is enabled on the instance
        try:
            if not _file_instance.get_log_to_file():
                return
        except (OSError, ValueError, AttributeError):
            # Defensive: don't allow file-side errors to break stdout/stderr
            return

        # Compute prefix and write to file; protect against file-side errors
        try:
            _prefix: str = self._get_correct_prefix()
        except (OSError, ValueError, AttributeError):
            _prefix = ""

        try:
            for i in _tmp_message:
                _file_instance.write(f"{_prefix}{i}")
        except (OSError, ValueError):
            try:
                sys.stderr.write(
                    f"{CONST.MODULE_NAME} Error writing to log file\n"
                )
            except OSError:
                pass

    def flush(self) -> None:
        """Best-effort flush of terminal and buffered file output.

        The call will attempt to flush both the original stream and
        the associated `FileInstance`. Errors are swallowed to avoid
        crashing the caller; use `FileInstance.flush()` directly for
        stricter guarantees.
        """
        _file_instance: Optional[FileInstance] = None
        # Snapshot the file instance under lock
        with self._file_lock:
            if self.file_instance:
                _file_instance = self.file_instance

        # Flush the original stream first (best-effort)
        if not self.original_stream.closed:
            try:
                self.original_stream.flush()
            except OSError as exc:
                try:
                    sys.stderr.write(
                        f"{CONST.MODULE_NAME} I/O error flushing original stream: {exc}\n"
                    )
                except OSError:
                    pass

        if _file_instance:
            try:
                if not _file_instance.get_log_to_file():
                    return
            except (OSError, ValueError, AttributeError):
                # If the check fails, continue and attempt a flush anyway.
                pass

            try:
                _file_instance.flush()
            except (OSError, ValueError):
                # don't let file flush failures propagate from a best-effort flush
                pass

    # sys.TextIO rebinds so the redirection is transparent to the caller

    @property
    def buffer(self) -> BinaryIO:
        data = self._get_stream_if_present().buffer
        return data

    @property
    def closed(self) -> bool:
        data = self._get_stream_if_present().closed
        return data

    @property
    def errors(self) -> Optional[str]:
        data = self._get_stream_if_present().errors
        return data

    @property
    def encoding(self) -> str:
        data = self._get_stream_if_present().encoding
        return data

    @property
    def line_buffering(self) -> int:
        data = self._get_stream_if_present().line_buffering
        return data

    @property
    def mode(self) -> str:
        data = self._get_stream_if_present().mode
        return data

    @property
    def name(self) -> Union[str, Any]:
        data = self._get_stream_if_present().name
        return data

    @property
    def newlines(self) -> Any:
        data = self._get_stream_if_present().newlines
        return data

    def close(self) -> None:
        self.flush()
        self._get_stream_if_present().close()

    def fileno(self) -> int:
        data = self._get_stream_if_present().fileno()
        return data

    def isatty(self) -> bool:
        data = self._get_stream_if_present().isatty()
        return data

    def read(self, size: int = -1) -> str:
        data = self._get_stream_if_present().read(size)
        return data

    def readable(self) -> bool:
        data = self._get_stream_if_present().readable()
        return data

    def readline(self, size: int = -1) -> str:
        data = self._get_stream_if_present().readline(size)
        return data

    def readlines(self, hint: int = -1) -> list[str]:
        data = self._get_stream_if_present().readlines(hint)
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        data = self._get_stream_if_present().seek(offset, whence)
        return data

    def seekable(self) -> bool:
        data = self._get_stream_if_present().seekable()
        return data

    def tell(self) -> int:
        data = self._get_stream_if_present().tell()
        return data

    def truncate(self, size: Optional[int] = None) -> int:
        data = self._get_stream_if_present().truncate(size)
        return data

    def writable(self) -> bool:
        data = self._get_stream_if_present().writable()
        return data

    def __enter__(self) -> TextIO:
        data = self._get_stream_if_present().__enter__()
        return data
