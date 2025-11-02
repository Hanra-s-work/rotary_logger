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
# LAST Modified: 5:11:57 02-11-2025
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
import sys
import atexit
from warnings import warn
from pathlib import Path
from typing import Any, Optional, List, Callable
from threading import RLock

try:
    from . import constants as CONST
    from .tee_stream import TeeStream
    from .file_instance import FileInstance
except ImportError:
    import constants as CONST
    from tee_stream import TeeStream
    from file_instance import FileInstance


class RotaryLogger:
    """High-level coordinator that installs `TeeStream` wrappers.

    Responsibilities:
    - Validate and create the target log folder.
    - Configure a `FileInstance` with encoding, prefix and rotation policy.
    - Replace `sys.stdout` and `sys.stderr` with `TeeStream` instances.
    """

    def __init__(
        self,
        log_to_file: bool = CONST.LOG_TO_FILE_ENV,
        override: bool = False,
        raw_log_folder: str = CONST.RAW_LOG_FOLDER_ENV,
        default_log_folder: Path = CONST.DEFAULT_LOG_FOLDER,
        default_max_filesize: int = CONST.DEFAULT_LOG_MAX_FILE_SIZE,
        merge_streams: bool = True,
        *,
        encoding: str = CONST.DEFAULT_ENCODING,
        prefix_in_stream: bool = True,
        prefix_out_stream: bool = True,
        prefix_err_stream: bool = True,
    ) -> None:
        """Create a RotaryLogger using the provided defaults.

        The constructor does not start logging; call `start_logging()` to
        install the `TeeStream` wrappers and begin mirroring output.
        """
        self._file_lock: RLock = RLock()
        self.log_to_file: bool = log_to_file
        self.raw_log_folder: Path = Path(raw_log_folder)
        self.default_log_folder: Path = default_log_folder
        self.default_max_filesize: int = default_max_filesize
        # Prefix tracker
        self.prefix: CONST.Prefix = CONST.Prefix()
        self.prefix.std_in = prefix_in_stream
        self.prefix.std_out = prefix_out_stream
        self.prefix.std_err = prefix_err_stream
        # The general file config
        self.file_data: FileInstance = FileInstance(None)
        self.file_data.set_encoding(encoding)
        self.file_data.set_merged(merge_streams)
        self.file_data.set_prefix(self.prefix)
        self.file_data.set_override(override)
        # Stream instance tracking
        self.stdout_stream: Optional[TeeStream] = None
        self.stderr_stream: Optional[TeeStream] = None
        self.stdin_stream: Optional[TeeStream] = None
        # Logging status
        self.paused: bool = False
        # Track whether we've registered atexit handlers to avoid duplicates
        self._atexit_registered: bool = False
        self._registered_flushers: List[Callable] = []

    def __del__(self) -> None:
        self.stop_logging()

    def __call__(self, *args: Any, **kwds: Any) -> None:
        """Convenience: allow the instance to be called to start logging.

        Calling the instance is equivalent to calling `start_logging()`
        and is provided for compact initialization patterns.
        """
        with self._file_lock:
            self.start_logging()

    def _get_user_max_file_size(self) -> int:
        """Function in charge of checking that the provided filesize is a number and only a number.

        Args:
            default_log_max_file_size (int, optional): The default filesize if the user input is incorrect. Defaults to CONST.DEFAULT_LOG_MAX_FILE_SIZE.

        Returns:
            int: The final size.
        """
        default_max_log_size: int = self.file_data.get_max_size()
        try:
            return int(os.environ.get("LOG_MAX_SIZE", str(default_max_log_size)))
        except ValueError:
            return default_max_log_size

    def _verify_user_log_path(self, raw_log_folder: Path = CONST.DEFAULT_LOG_FOLDER) -> Path:
        """Make sure that the path provided by the user is valid and within bounds.

        Args:
            raw_log_folder (Path, optional): The path provided by the user. Defaults to CONST.DEFAULT_LOG_FOLDER.

        Raises:
            ValueError: If the provided paths are wrong.

        Returns:
            Path: The checked path.
        """
        # Snapshot inputs and minimal state under lock, then perform
        # filesystem operations outside the lock to avoid blocking other
        # threads. Any path validation/mkdir/write attempts happen below
        # without holding `self._file_lock`.
        try:
            raw = Path(raw_log_folder)
            if raw.is_absolute():
                candidate = raw.resolve(strict=False)
            else:
                candidate = (
                    Path(__file__).parent /
                    raw
                ).resolve(strict=False)

            # If the user didn't explicitly end with our base folder name, append it.
            if candidate.name != CONST.LOG_FOLDER_BASE_NAME:
                candidate = candidate / CONST.LOG_FOLDER_BASE_NAME

            # Basic validation: protect against overly long paths.
            if len(str(candidate)) > 255:
                raise ValueError(f"{CONST.MODULE_NAME} Path too long")

            # Ensure we can create and write into the folder. Do I/O here
            # outside of any locks to avoid blocking other threads.
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                testfile = candidate / ".rotary_write_test"
                with open(testfile, "w", encoding="utf-8") as fh:
                    fh.write("x")
                testfile.unlink()
            except OSError as e:
                raise ValueError(
                    f"{CONST.MODULE_NAME} Path not writable: {e}") from e

            return candidate
        except ValueError as e:
            warn(
                f"{CONST.MODULE_NAME} [WARN] Invalid LOG_FOLDER_NAME ({raw_log_folder!r}): {e}. Falling back to default."
            )
            try:
                CONST.DEFAULT_LOG_FOLDER.mkdir(parents=True, exist_ok=True)
            except OSError as err:
                raise RuntimeError(
                    f"{CONST.MODULE_NAME} The provided and default folder paths are not writable"
                ) from err
            return CONST.DEFAULT_LOG_FOLDER

    def _resolve_log_folder(self, log_folder: Optional[Path]) -> Path:
        """Resolve and verify the final log folder to use.

        This centralises the logic of falling back to defaults and keeps
        start_logging concise.
        """
        with self._file_lock:
            if log_folder is None:
                log_folder = self.default_log_folder
            return self._verify_user_log_path(log_folder)

    def start_logging(
        self,
        *,
        log_folder: Optional[Path] = None,
        max_filesize: Optional[int] = None,
        merged: Optional[bool] = None,
        log_to_file: bool = True
    ) -> None:
        """Start capturing stdout/stderr and configure file output.

        This installs `TeeStream` wrappers for `sys.stdout` and
        `sys.stderr` so output continues to appear on the terminal while
        being mirrored to rotating files on disk.

        Thread-safety and behaviour
        - Performs light configuration snapshots under an internal lock
          and does filesystem checks (mkdir, write-test) outside the
          lock to avoid long-held critical sections.
        - The actual assignment of `sys.stdout`/`sys.stderr` is done
          while holding the internal lock to make the replacement
          atomic relative to other control operations.

        Parameters
        - log_folder: Optional[Path] base folder to write logs. When
          omitted, falls back to the configured defaults.
        - max_filesize: Optional[int] override for the rotation size.
        - merged: Optional[bool] whether to merge stdout and stderr.
        - log_to_file: bool: whether file writes are enabled.

        Returns
        - None. After successful return, `is_logging()` should be True.
        """
        with self._file_lock:
            # Defaults (snapshot)
            if log_folder is None:
                if self.raw_log_folder == "":
                    _raw_folder = self.default_log_folder
                else:
                    _raw_folder = self.raw_log_folder
            else:
                _raw_folder = log_folder

            if max_filesize is not None:
                self.file_data.set_max_size(max_filesize)

            # snapshot file_data-derived configuration to avoid nested locks
            _override = self.file_data.get_override()
            _encoding = self.file_data.get_encoding()
            _prefix = self.file_data.get_prefix()
            _max_size_mb = self.file_data.get_max_size()
            _flush_size_kb = self.file_data.get_flush_size()
            if merged is None:
                _merged_flag = self.file_data.merged
            else:
                _merged_flag = bool(merged)

        # Determine final log folder using the built-in verification (outside lock)
        _log_folder = self._verify_user_log_path(_raw_folder)
        _log_folder.mkdir(parents=True, exist_ok=True)

        # Apply user-provided max size
        self.file_data.set_max_size(self._get_user_max_file_size())

        if _merged_flag:
            mixed_inst: FileInstance = FileInstance(
                file_path=_log_folder,
                override=_override,
                merged=True,
                encoding=_encoding,
                prefix=_prefix,
                max_size_mb=_max_size_mb,
                flush_size_kb=_flush_size_kb,
                folder_prefix=None
            )

            stdout_inst = mixed_inst
            stderr_inst = mixed_inst
        else:
            out_inst: FileInstance = FileInstance(
                file_path=_log_folder,
                override=_override,
                merged=False,
                encoding=_encoding,
                prefix=_prefix,
                max_size_mb=_max_size_mb,
                flush_size_kb=_flush_size_kb,
                folder_prefix=CONST.StdMode.STDOUT
            )
            err_inst: FileInstance = FileInstance(
                file_path=_log_folder,
                override=_override,
                merged=False,
                encoding=_encoding,
                prefix=_prefix,
                max_size_mb=_max_size_mb,
                flush_size_kb=_flush_size_kb,
                folder_prefix=CONST.StdMode.STDERR
            )

            stdout_inst = out_inst
            stderr_inst = err_inst

        # Construct TeeStream instances outside the lock to avoid holding
        # `RotaryLogger._file_lock` while the TeeStream initializer may
        # acquire `FileInstance` locks. Then assign the globals under the
        # lock to keep the replacement atomic.
        _stdout_stream = TeeStream(
            stdout_inst,
            sys.stdout,
            mode=CONST.StdMode.STDOUT,
            log_to_file=log_to_file
        )
        _stderr_stream = TeeStream(
            stderr_inst,
            sys.stderr,
            mode=CONST.StdMode.STDERR,
            log_to_file=log_to_file
        )

        with self._file_lock:
            sys.stdout = _stdout_stream
            sys.stderr = _stderr_stream
            self.stdout_stream = _stdout_stream
            self.stderr_stream = _stderr_stream

            # Ensure final flush at exit, but only register once
            if not self._atexit_registered:
                self._registered_flushers = [
                    self.stdout_stream.flush, self.stderr_stream.flush
                ]
                try:
                    for f in self._registered_flushers:
                        atexit.register(f)
                    self._atexit_registered = True
                except (TypeError, AttributeError):
                    # Registration may fail if the objects are not callable
                    # or lack attributes; handle only the expected errors.
                    # Clear the list to avoid false expectations.
                    self._registered_flushers = []

    def pause_logging(self) -> bool:
        """Toggle the logger pause state.

        When the logger is paused the `TeeStream` objects are uninstalled
        and the original streams restored. When resumed the `TeeStream`
        objects are reinstalled.

        Returns
        - bool: the new paused state (True when paused).

        Thread-safety
        - Updates to `self.paused` and global `sys.*` assignments are
            performed while holding the internal lock to avoid races.
        - Any blocking I/O (flushes) is performed after the lock is
            released to keep critical sections short.
        """
        # Snapshot streams and current state under the lock, and perform
        # the sys.* assignment while still holding the lock to avoid races.
        to_flush = []
        with self._file_lock:
            current = self.paused
            out = self.stdout_stream
            err = self.stderr_stream
            inn = self.stdin_stream
            if current:
                # currently paused -> resume logging
                self.paused = False
                if out:
                    sys.stdout = out
                if err:
                    sys.stderr = err
                if inn:
                    sys.stdin = inn
                # after resuming, we want to flush the streams to ensure
                # no buffered data is left behind
                if out:
                    to_flush.append(out)
                if err:
                    to_flush.append(err)
                if inn:
                    to_flush.append(inn)
            else:
                # currently running -> pause logging
                self.paused = True
                if out:
                    sys.stdout = out.original_stream
                    to_flush.append(out)
                if err:
                    sys.stderr = err.original_stream
                    to_flush.append(err)
                if inn:
                    sys.stdin = inn.original_stream
                    to_flush.append(inn)

        # Perform flushes outside the lock (may do I/O)
        for s in to_flush:
            try:
                s.flush()
            except (OSError, ValueError):
                # I/O related issues (broken pipe, closed file, etc.)
                # may be raised during flush. Catch those specifically.
                pass

        return self.paused

    def resume_logging(self) -> bool:
        """Explicitly resume logging (idempotent).

        This is equivalent to calling `pause_logging()` when the logger
        is paused, but provided as a convenience. Returns the paused
        state after resuming (False).

        Thread-safety: same guarantees as `pause_logging()`.
        """
        to_flush = []
        with self._file_lock:
            self.paused = False
            out = self.stdout_stream
            err = self.stderr_stream
            inn = self.stdin_stream
            if out:
                sys.stdout = out
                to_flush.append(out)
            if err:
                sys.stderr = err
                to_flush.append(err)
            if inn:
                sys.stdin = inn
                to_flush.append(inn)

        for s in to_flush:
            try:
                s.flush()
            except (OSError, ValueError):
                pass
        return self.paused

    def is_redirected(self, stream: CONST.StdMode) -> bool:
        """Return whether the given standard stream is redirected.

        Parameters
        - stream: one of `CONST.StdMode.STDOUT`, `STDERR` or `STDIN`.

        Returns
        - True if the corresponding stream currently has a `TeeStream` installed; False otherwise.

        This is a lightweight query and safe to call concurrently.
        """
        _stderr_stream: Optional[TeeStream] = None
        _stdout_stream: Optional[TeeStream] = None
        _stdin_stream: Optional[TeeStream] = None
        with self._file_lock:
            _stderr_stream = self.stderr_stream
            _stdout_stream = self.stdout_stream
            _stdin_stream = self.stdin_stream
        if stream == CONST.StdMode.STDERR:
            return bool(_stderr_stream)
        if stream == CONST.StdMode.STDOUT:
            return bool(_stdout_stream)
        if stream == CONST.StdMode.STDIN:
            return bool(_stdin_stream)
        return False

    def is_logging(self) -> bool:
        """Return True if logging is currently active (not paused).

        The function checks whether any TeeStream is installed and the
        logger is not marked as paused. Safe to call concurrently.
        """
        with self._file_lock:
            has_stream = bool(
                self.stdout_stream or self.stderr_stream or self.stdin_stream
            )
            return has_stream and (not bool(self.paused))

    def stop_logging(self) -> None:
        """Stop logging and restore original std streams.

        Behaviour
        - Restores the original `sys.stdout`/`sys.stderr`/`sys.stdin`.
        - Attempts to unregister any atexit flush handlers previously
            registered by `start_logging()`.
        - Flushes any remaining buffers after releasing the lock.

        Thread-safety
        - Stream replacement and atexit unregistration are done while
            holding the internal lock to avoid races; flushing is
            performed outside the lock.
        """
        to_flush = []
        with self._file_lock:
            if self.stdout_stream:
                sys.stdout = self.stdout_stream.original_stream
                to_flush.append(self.stdout_stream)
                self.stdout_stream = None
            if self.stderr_stream:
                sys.stderr = self.stderr_stream.original_stream
                to_flush.append(self.stderr_stream)
                self.stderr_stream = None
            if self.stdin_stream:
                sys.stdin = self.stdin_stream.original_stream
                to_flush.append(self.stdin_stream)
                self.stdin_stream = None
            self.paused = False

            if getattr(self, "_atexit_registered", False):
                for f in getattr(self, "_registered_flushers", []):
                    try:
                        atexit.unregister(f)
                    except ValueError:
                        pass
                    except AttributeError:
                        pass
                self._registered_flushers = []
                self._atexit_registered = False

        for s in to_flush:
            try:
                s.flush()
            except (OSError, ValueError):
                pass


if __name__ == "__main__":
    RotaryLogger().start_logging()
