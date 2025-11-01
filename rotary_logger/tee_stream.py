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
# LAST Modified: 10:11:11 01-11-2025
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
from typing import TextIO, Optional, Union
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
        root: Union[Path, FileInstance],
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
        self.mode: CONST.StdMode = mode
        self.original_stream: TextIO = original_stream
        self.error_mode: CONST.ErrorMode = error_mode

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
            if not isinstance(self.mode, CONST.StdMode):
                return ""
            _mode = self.mode
        _prefix: Optional[CONST.Prefix] = _file_inst.get_prefix()

        if not _prefix or not _file_inst.get_log_to_file():
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

    def write(self, message: str) -> None:
        """Write `message` to the original stream and buffer it to file.

        This method is safe to call from multiple threads. It captures the
        necessary references under a short lock, performs the terminal
        write on the caller thread (with known error handling), then
        delegates buffered file writes to `FileInstance.write()`.
        """
        _tmp_message: str = ""
        _file_instance: Optional[FileInstance] = None
        with self._file_lock:
            _tmp_message = message
            _file_instance = self.file_instance

        try:
            self.original_stream.write(message)
        except BrokenPipeError:
            if self.error_mode in (CONST.ErrorMode.EXIT, CONST.ErrorMode.EXIT_NO_PIPE):
                sys.exit(CONST.ERROR)
            elif self.error_mode in (CONST.ErrorMode.WARN, CONST.ErrorMode.WARN_NO_PIPE):
                sys.stderr.write(CONST.BROKEN_PIPE_ERROR)
        except OSError as exc:
            # Unexpected I/O error writing to original stream: report and continue
            try:
                sys.stderr.write(
                    f"{CONST.MODULE_NAME} I/O error writing to original stream: {exc}\n"
                )
            except OSError:
                # swallow any errors writing to stderr during shutdown
                pass

        if not _file_instance:
            return

        if not _file_instance.get_log_to_file():
            return

        _prefix: str = self._get_correct_prefix()
        _file_instance.write(f"{_prefix}{_tmp_message}")

    def flush(self):
        """Best-effort flush of terminal and buffered file output.

        The call will attempt to flush both the original stream and
        the associated `FileInstance`. Errors are swallowed to avoid
        crashing the caller; use `FileInstance.flush()` directly for
        stricter guarantees.
        """
        _file_instance: Optional[FileInstance] = None
        # Attempt to flush the original stream and always attempt to flush the file instance.
        with self._file_lock:
            if self.file_instance:
                _file_instance = self.file_instance
        try:
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
        finally:
            if _file_instance:
                try:
                    _file_instance.flush()
                except (OSError, ValueError):
                    # don't let file flush failures propagate from a best-effort flush
                    pass
