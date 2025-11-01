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
# LAST Modified: 2:8:56 01-11-2025
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
    """Redirects stdout/stderr to a file while keeping normal output, buffered, and rotating by max size."""

    def __init__(
        self,
        root: Union[Path, FileInstance],
        original_stream: TextIO,
        *,
        max_size_mb: Optional[int] = None,
        flush_size: Optional[int] = None,
        mode: CONST.StdMode = CONST.StdMode.STDUNKNOWN,
        error_mode: CONST.ErrorMode = CONST.ErrorMode.WARN_NO_PIPE,
        encoding: Optional[str] = None
    ):
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
        self.mode: CONST.StdMode = mode
        self.original_stream: TextIO = original_stream
        self.error_mode: CONST.ErrorMode = error_mode

    def __del__(self):
        """Function in charge of cleanup in case the class is deleted.
        """
        try:
            self.flush()
        except (OSError, ValueError):
            # best-effort flush; ignore expected I/O errors during interpreter shutdown
            pass
        # avoid deleting attributes in __del__; simply drop the reference
        self.file_instance = None

    def _get_correct_prefix(self) -> str:
        # ensure we have a file instance and a valid StdMode enum value
        with self._file_lock:
            if not self.file_instance or not isinstance(self.mode, CONST.StdMode):
                return ""
            _prefix: Optional[CONST.Prefix] = self.file_instance.get_prefix()
            if not _prefix:
                return ""
            if _prefix.std_err and self.mode == CONST.StdMode.STDERR:
                return CONST.CORRECT_PREFIX[CONST.StdMode.STDERR] + CONST.SPACE
            if _prefix.std_in and self.mode == CONST.StdMode.STDIN:
                return CONST.CORRECT_PREFIX[CONST.StdMode.STDIN] + CONST.SPACE
            if _prefix.std_out and self.mode == CONST.StdMode.STDOUT:
                return CONST.CORRECT_PREFIX[CONST.StdMode.STDOUT] + CONST.SPACE
            if _prefix.std_in or _prefix.std_err or _prefix.std_out:
                return CONST.CORRECT_PREFIX[CONST.StdMode.STDUNKNOWN] + CONST.SPACE
            return ""

    def write(self, message: str) -> None:
        """Function in charge of writing content to a stream a file if present and buffer hit, otherwise, appends values to the buffer.

        Args:
            message (str): The message to be displayed
        """
        with self._file_lock:
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

            # If no file instance configured, nothing more to do
            if not self.file_instance:
                return

            _prefix: str = self._get_correct_prefix()
            self.file_instance.write(f"{_prefix}{message}")

    def flush(self):
        """Function that can be used to force the program to flush it's current stream and buffer
        """
        # Attempt to flush the original stream and always attempt to flush the file instance.
        with self._file_lock:
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
                if self.file_instance:
                    try:
                        self.file_instance.flush()
                    except (OSError, ValueError):
                        # don't let file flush failures propagate from a best-effort flush
                        pass
