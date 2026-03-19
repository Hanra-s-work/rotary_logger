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
# LAST Modified: 5:14:10 19-03-2026
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
    from .rogger import Rogger, RI
except ImportError:
    import constants as CONST
    from tee_stream import TeeStream
    from file_instance import FileInstance
    from rogger import Rogger, RI


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
        merge_stdin: bool = False,
        capture_stdin: bool = False,
        capture_stdout: bool = True,
        capture_stderr: bool = True,
        prefix_in_stream: bool = True,
        prefix_out_stream: bool = True,
        prefix_err_stream: bool = True,
        log_function_calls_stdin: bool = False,
        log_function_calls_stdout: bool = False,
        log_function_calls_stderr: bool = False,
        program_log: bool = False,
        program_debug_log: bool = False,
        suppress_program_warning_logs: bool = False,
        suppress_program_error_logs: bool = False,
    ) -> None:
        """Initialise a new RotaryLogger.

        Does not start logging; call start_logging() to install TeeStream
        wrappers and begin mirroring output.

        Arguments:
            log_to_file (bool): Whether file logging is enabled. Default: CONST.LOG_TO_FILE_ENV
            override (bool): Whether existing log files may be overwritten. Default: False
            raw_log_folder (str): Raw path string for the log folder. Default: CONST.RAW_LOG_FOLDER_ENV
            default_log_folder (Path): Fallback log folder path. Default: CONST.DEFAULT_LOG_FOLDER
            default_max_filesize (int): Maximum log file size in MB before rotation. Default: CONST.DEFAULT_LOG_MAX_FILE_SIZE
            merge_streams (bool): Whether stdout and stderr share a single log file. Default: True

        Keyword Arguments:
            encoding (str): File encoding for log files. Default: CONST.DEFAULT_ENCODING
            merge_stdin (bool): Whether stdin is merged into the shared log file. Default: False
            capture_stdin (bool): Whether stdin is wrapped with a TeeStream. Default: False
            capture_stdout (bool): Whether stdout is wrapped with a TeeStream. Default: True
            capture_stderr (bool): Whether stderr is wrapped with a TeeStream. Default: True
            prefix_in_stream (bool): Whether stdin entries are prefixed. Default: True
            prefix_out_stream (bool): Whether stdout entries are prefixed. Default: True
            prefix_err_stream (bool): Whether stderr entries are prefixed. Default: True
            log_function_calls_stdin (bool): Whether TeeStream function calls on stdin are logged. Default: False
            log_function_calls_stdout (bool): Whether TeeStream function calls on stdout are logged. Default: False
            log_function_calls_stderr (bool): Whether TeeStream function calls on stderr are logged. Default: False
            program_log (bool): Whether to let the module (rotary_logger) output status logs about what it is doing. Default: False
            program_debug_log (bool): Whether to let the module (rotary_logger) output debug logs. Default: False
            suppress_program_warning_logs (bool): Whether to prevent the module (rotary_logger) from outputing warnings (ex: initialising an already initialised stream). Default: False
            suppress_program_error_logs (bool): Whether to prevent the module (rotary_logger) from outputing error (ex: a broken pipe). Default: False

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
        self.file_data.set_merge_stdin(merge_stdin)
        # Toggles to specify whether to capture a stream or not; used by start_logging to determine which streams to wrap.
        self.capture_stdin: bool = capture_stdin
        self.capture_stdout: bool = capture_stdout
        self.capture_stderr: bool = capture_stderr
        # Log the std function calls configuration
        self.log_function_calls_stdin = log_function_calls_stdin
        self.log_function_calls_stdout = log_function_calls_stdout
        self.log_function_calls_stderr = log_function_calls_stderr
        # File stream instances are created in start_logging and assigned to these attributes for later reference and cleanup.
        self._file_stream_instances: CONST.FileStreamInstances = CONST.FileStreamInstances()
        # Stream instance tracking
        self.stdout_stream: Optional[TeeStream] = None
        self.stderr_stream: Optional[TeeStream] = None
        self.stdin_stream: Optional[TeeStream] = None
        # Logging status
        self.paused: bool = False
        # Track whether we've registered atexit handlers to avoid duplicates
        self._atexit_registered: bool = False
        self._registered_flushers: List[Callable] = []
        # Logging section
        self.program_log = program_log
        self.program_debug_log = program_debug_log
        self.suppress_program_warning_logs = suppress_program_warning_logs
        self.suppress_program_error_logs = suppress_program_error_logs
        self.rogger: Rogger = RI
        self.rogger.re_toggle(
            self.program_log,
            self.program_debug_log,
            self.suppress_program_warning_logs,
            self.suppress_program_error_logs
        )
        # Internal module startup log
        self.rogger.log_info("RotaryLogger initialized", stream=sys.stdout)

    def __del__(self) -> None:
        """Best-effort cleanup on object deletion.

        Calls stop_logging() to restore original streams. Errors are not
        raised since __del__ may run during interpreter shutdown.
        """
        self.stop_logging()

    def __call__(self, *args: Any, **kwds: Any) -> None:
        """Allow the instance to be called as a function to start logging.

        Calling the instance is equivalent to calling start_logging() and
        is provided for compact initialisation patterns.

        Arguments:
            *args (Any): Ignored positional arguments.
            **kwds (Any): Ignored keyword arguments.
        """
        with self._file_lock:
            self.start_logging()

    def _get_user_max_file_size(self) -> int:
        """Return the maximum log file size from the environment or the current default.

        Reads the `LOG_MAX_SIZE` environment variable and coerces it to an
        integer. Falls back to the value stored in `file_data` if the variable
        is absent or non-numeric.

        Returns:
            The resolved maximum log file size in bytes (as stored by `FileInstance`).
        """
        default_max_log_size: int = self.file_data.get_max_size()
        try:
            val = int(
                os.environ.get(
                    "LOG_MAX_SIZE",
                    str(default_max_log_size)
                )
            )
            self.rogger.log_debug(
                f"Resolved user max file size: {val}",
                stream=sys.stdout
            )
            return val
        except ValueError:
            self.rogger.log_warning(
                f"Invalid LOG_MAX_SIZE env value, falling back to default: {default_max_log_size}",
                stream=sys.stderr
            )
            return default_max_log_size

    def _verify_user_log_path(self, raw_log_folder: Path = CONST.DEFAULT_LOG_FOLDER) -> Path:
        """Validate, resolve and ensure writability of the requested log folder.

        Resolves relative paths against the package directory, appends the
        standard base-folder name when missing, and performs a write-test.
        Falls back to the default log folder on any validation failure.

        Keyword Arguments:
            raw_log_folder (Path): Candidate log folder path. Default: CONST.DEFAULT_LOG_FOLDER

        Raises:
            RuntimeError: If both the requested path and the default fallback are not writable.

        Returns:
            The validated, writable, resolved log folder path.
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
                self.rogger.log_info(
                    f"Verified writable log folder: {candidate}",
                    stream=sys.stdout
                )
            except OSError as e:
                self.rogger.log_error(
                    f"Log folder not writable: {candidate} -> {e}",
                    stream=sys.stderr
                )
                raise ValueError(
                    f"{CONST.MODULE_NAME} Path not writable: {e}") from e

            return candidate
        except ValueError as e:
            self.rogger.log_warning(
                f"Invalid LOG_FOLDER_NAME ({raw_log_folder!r}): {e}. Falling back to default.",
                stream=sys.stderr
            )
            warn(
                f"{CONST.MODULE_NAME} [WARN] Invalid LOG_FOLDER_NAME ({raw_log_folder!r}): {e}. Falling back to default."
            )
            try:
                CONST.DEFAULT_LOG_FOLDER.mkdir(parents=True, exist_ok=True)
                self.rogger.log_info(
                    f"Falling back to default log folder: {CONST.DEFAULT_LOG_FOLDER}",
                    stream=sys.stdout
                )
            except OSError as err:
                raise RuntimeError(
                    f"{CONST.MODULE_NAME} The provided and default folder paths are not writable"
                ) from err
            return CONST.DEFAULT_LOG_FOLDER

    def _resolve_log_folder(self, log_folder: Optional[Path]) -> Path:
        """Resolve and verify the final log folder to use.

        Centralises the logic of falling back to the configured default and
        delegates validation to _verify_user_log_path().

        Arguments:
            log_folder (Optional[Path]): Requested log folder, or None to use the default.

        Returns:
            The validated, writable, resolved log folder path.
        """
        with self._file_lock:
            if log_folder is None:
                log_folder = self.default_log_folder
            return self._verify_user_log_path(log_folder)

    def _handle_stream_assignments(self, log_folder: Path) -> None:
        """Create `FileInstance` objects and store them in `self._file_stream_instances`.

        Reads the current configuration snapshot from `self.file_data` (outside the
        lock) and constructs either a single shared `FileInstance` (when `merged` is True)
        or three separate per-stream instances for stdin, stdout, and stderr.

        When merged, stdout and stderr share the same descriptor. stdin is also merged
        into that file when `merge_stdin` is True; otherwise its own unmerged instance
        is created. Merged/unmerged state is recorded in
        `self._file_stream_instances.merged_streams`.

        Arguments:
            log_folder (Path): The validated, writable root folder for log files.
        """
        with self._file_lock:
            _override = self.file_data.get_override()
            _encoding = self.file_data.get_encoding()
            _prefix = self.file_data.get_prefix()
            _max_size_mb = self.file_data.get_max_size()
            _flush_size_kb = self.file_data.get_flush_size()
            _merged_flag = self.file_data.get_merged()
            _merge_stdin_flag = self.file_data.get_merge_stdin()

        self.rogger.log_debug(
            f"Handling stream assignments (merged={_merged_flag}, merge_stdin={_merge_stdin_flag})",
            stream=sys.stdout
        )
        if _merged_flag:
            mixed_inst: FileInstance = FileInstance(
                file_path=log_folder,
                override=_override,
                merged=True,
                encoding=_encoding,
                prefix=_prefix,
                max_size_mb=_max_size_mb,
                flush_size_kb=_flush_size_kb,
                folder_prefix=None,
                merge_stdin=_merge_stdin_flag
            )

            self._file_stream_instances.stdout = mixed_inst
            self._file_stream_instances.stderr = mixed_inst
            self._file_stream_instances.merged_streams[CONST.StdMode.STDOUT] = True
            self._file_stream_instances.merged_streams[CONST.StdMode.STDERR] = True
            if _merge_stdin_flag:
                self._file_stream_instances.stdin = mixed_inst
                self._file_stream_instances.merged_streams[CONST.StdMode.STDIN] = True
            else:
                self._file_stream_instances.stdin = FileInstance(
                    file_path=log_folder,
                    override=_override,
                    merged=False,
                    encoding=_encoding,
                    prefix=_prefix,
                    max_size_mb=_max_size_mb,
                    flush_size_kb=_flush_size_kb,
                    folder_prefix=CONST.StdMode.STDIN,
                    merge_stdin=False
                )
            self.rogger.log_info(
                f"Created merged FileInstance for stdout/stderr at {log_folder}",
                stream=sys.stdout
            )
        else:
            self._file_stream_instances.stdin = FileInstance(
                file_path=log_folder,
                override=_override,
                merged=False,
                encoding=_encoding,
                prefix=_prefix,
                max_size_mb=_max_size_mb,
                flush_size_kb=_flush_size_kb,
                folder_prefix=CONST.StdMode.STDIN,
                merge_stdin=False
            )
            self._file_stream_instances.stdout = FileInstance(
                file_path=log_folder,
                override=_override,
                merged=False,
                encoding=_encoding,
                prefix=_prefix,
                max_size_mb=_max_size_mb,
                flush_size_kb=_flush_size_kb,
                folder_prefix=CONST.StdMode.STDOUT,
                merge_stdin=_merge_stdin_flag
            )
            self._file_stream_instances.stderr = FileInstance(
                file_path=log_folder,
                override=_override,
                merged=False,
                encoding=_encoding,
                prefix=_prefix,
                max_size_mb=_max_size_mb,
                flush_size_kb=_flush_size_kb,
                folder_prefix=CONST.StdMode.STDERR,
                merge_stdin=_merge_stdin_flag
            )

            self._file_stream_instances.merged_streams[CONST.StdMode.STDOUT] = False
            self._file_stream_instances.merged_streams[CONST.StdMode.STDERR] = False
            self._file_stream_instances.merged_streams[CONST.StdMode.STDIN] = False
            self.rogger.log_info(
                f"Created separate FileInstance objects for each stream at {log_folder}",
                stream=sys.stdout
            )

    def start_logging(
        self,
        *,
        log_folder: Optional[Path] = None,
        max_filesize: Optional[int] = None,
        merged: Optional[bool] = None,
        log_to_file: bool = True,
        merge_stdin: Optional[bool] = None,
        skip_redirect_check_stdin: bool = False,
        skip_redirect_check_stdout: bool = False,
        skip_redirect_check_stderr: bool = False,
    ) -> None:
        """Start capturing stdout and stderr and configure file output.

        Installs TeeStream wrappers for sys.stdout and sys.stderr so output
        continues to appear on the terminal while being mirrored to rotating
        files on disk. Configuration snapshots are taken under the internal
        lock; filesystem operations (mkdir, write-test) are performed outside
        it to keep critical sections short. The sys.* assignments are made
        while holding the lock to keep the replacement atomic.

        Keyword Arguments:
            log_folder (Optional[Path]): Base folder to write logs; falls back to configured defaults. Default: None
            max_filesize (Optional[int]): Override for the rotation size in MB. Default: None
            merged (Optional[bool]): Whether to merge stdout and stderr into one file. Default: None
            log_to_file (bool): Whether file writes are enabled. Default: True
            merge_stdin (Optional[bool]): Whether to merge stdin into the shared log file. Default: None
            skip_redirect_check_stdin (bool, optional):  Skip the existing redirection check for stdin, allowing multiple logger instances to redirect the same stream (legacy behavior). Default: False
            skip_redirect_check_stdout (bool, optional): Skip the existing redirection check for stdout, allowing multiple logger instances to redirect the same stream (legacy behavior). Default: False,
            skip_redirect_check_stderr (bool, optional): Skip the existing redirection check for stderr, allowing multiple logger instances to redirect the same stream (legacy behavior). Default: False,
        """

        # Entry log
        self.rogger.log_info(
            f"start_logging called (log_folder={log_folder}, max_filesize={max_filesize}, merged={merged}, log_to_file={log_to_file})",
            stream=sys.stdout
        )

        # Prepare FileInstance configurations based on the provided arguments and current settings.
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
            # Apply user-provided max size
            self.file_data.set_max_size(self._get_user_max_file_size())

            # snapshot file_data-derived configuration to avoid nested locks
            if merged is not None:
                self.file_data.set_merged(merged)
            if merge_stdin is not None:
                self.file_data.set_merge_stdin(merge_stdin)

        # Determine final log folder using the built-in verification (outside lock)
        _log_folder: Path = self._verify_user_log_path(_raw_folder)
        _log_folder.mkdir(parents=True, exist_ok=True)

        # Create the file descriptor instances based on the current configuration (outside lock)
        self._handle_stream_assignments(_log_folder)
        # Construct TeeStream instances outside the lock to avoid holding
        # `RotaryLogger._file_lock` while the TeeStream initializer may
        # acquire `FileInstance` locks. Then assign the globals under the
        # lock to keep the replacement atomic.
        _stdin_stream: Optional[TeeStream] = None
        _stdout_stream: Optional[TeeStream] = None
        _stderr_stream: Optional[TeeStream] = None
        if self._file_stream_instances.stdin:
            if skip_redirect_check_stdin:
                self.rogger.log_warning(
                    "Skipping redirect check for stdin because 'skip_redirect_check_stdin' is True",
                    stream=sys.stderr
                )
            if not skip_redirect_check_stdin and isinstance(sys.stdin, TeeStream):
                self.rogger.log_warning(
                    "Stdin stream is already being redirected, skipping redirection",
                    stream=sys.stderr
                )
                _stdin_stream = sys.stdin
            else:
                self.rogger.log_info(
                    "Stdin is not yet being redirected, redirecting",
                    stream=sys.stdout
                )
                _stdin_stream = TeeStream(
                    self._file_stream_instances.stdin,
                    sys.stdin,
                    mode=CONST.StdMode.STDIN,
                    log_to_file=log_to_file,
                    log_function_calls=self.log_function_calls_stdin
                )
                self.rogger.log_debug(
                    "Constructed TeeStream for stdin",
                    stream=sys.stdout
                )
        if self._file_stream_instances.stdout:
            if skip_redirect_check_stdout:
                self.rogger.log_warning(
                    "Skipping redirect check for stdout because 'skip_redirect_check_stdin' is True",
                    stream=sys.stderr
                )
            if not skip_redirect_check_stdout and isinstance(sys.stdout, TeeStream):
                self.rogger.log_warning(
                    "Stdout stream is already being redirected, skipping redirection",
                    stream=sys.stderr
                )
                _stdin_stream = sys.stdout
            else:
                self.rogger.log_info(
                    "Stdout is not yet being redirected, redirecting",
                    stream=sys.stdout
                )
                _stdout_stream = TeeStream(
                    self._file_stream_instances.stdout,
                    sys.stdout,
                    mode=CONST.StdMode.STDOUT,
                    log_to_file=log_to_file,
                    log_function_calls=self.log_function_calls_stdout
                )
                self.rogger.log_debug(
                    "Constructed TeeStream for stdout",
                    stream=sys.stdout
                )
        if self._file_stream_instances.stderr:
            if skip_redirect_check_stderr:
                self.rogger.log_warning(
                    "Skipping redirect check for stderr because 'skip_redirect_check_stderr' is True",
                    stream=sys.stderr
                )
            if not skip_redirect_check_stderr and isinstance(sys.stderr, TeeStream):
                self.rogger.log_warning(
                    "Stderr stream is already being redirected, skipping redirection",
                    stream=sys.stderr
                )
                _stderr_stream = sys.stderr
            else:
                self.rogger.log_info(
                    "Stderr is not yet being redirected, redirecting",
                    stream=sys.stdout
                )
                _stderr_stream = TeeStream(
                    self._file_stream_instances.stderr,
                    sys.stderr,
                    mode=CONST.StdMode.STDERR,
                    log_to_file=log_to_file,
                    log_function_calls=self.log_function_calls_stderr
                )
                self.rogger.log_debug(
                    "Constructed TeeStream for stderr",
                    stream=sys.stdout
                )

        with self._file_lock:
            self.rogger.log_info("redirecting streams", stream=sys.stdout)
            self.rogger.log_debug(
                f"Will assign streams: stdin={bool(_stdin_stream)}, stdout={bool(_stdout_stream)}, stderr={bool(_stderr_stream)}",
                stream=sys.stdout
            )
            if _stdin_stream:
                sys.stdin = _stdin_stream
                self.stdin_stream = _stdin_stream
            if _stdout_stream:
                sys.stdout = _stdout_stream
                self.stdout_stream = _stdout_stream
            if _stderr_stream:
                sys.stderr = _stderr_stream
                self.stderr_stream = _stderr_stream

            # Ensure final flush at exit, but only register once
            if not self._atexit_registered:
                self._registered_flushers = []
                if self.stdin_stream:
                    self._registered_flushers.append(self.stdin_stream.flush)
                if self.stdout_stream:
                    self._registered_flushers.append(self.stdout_stream.flush)
                if self.stderr_stream:
                    self._registered_flushers.append(self.stderr_stream.flush)
                try:
                    for f in self._registered_flushers:
                        atexit.register(f)
                    self._atexit_registered = True
                except (TypeError, AttributeError):
                    # Registration may fail if the objects are not callable
                    # or lack attributes; handle only the expected errors.
                    # Clear the list to avoid false expectations.
                    self._registered_flushers = []
                else:
                    self.rogger.log_info(
                        "Registered atexit flush handlers",
                        stream=sys.stdout
                    )

    def _resume_logging_locked(self, to_flush: List[TeeStream]) -> None:
        """Restore TeeStream wrappers on sys.stdin/stdout/stderr.

        Must be called while `self._file_lock` is already held. Sets
        `self.paused` to False and reassigns `sys.stdout`, `sys.stderr`,
        and `sys.stdin` to their respective TeeStream instances. Each
        stream that is reinstalled is appended to `to_flush` so the
        caller can flush them after releasing the lock.

        Arguments:
            to_flush (List[TeeStream]): Accumulator list; streams to flush after the lock is released.
        """
        self.paused = False
        self.rogger.log_info(
            "Resuming logging (reinstalling TeeStream wrappers)",
            stream=sys.stdout
        )
        out = self.stdout_stream
        err = self.stderr_stream
        inn = self.stdin_stream
        # currently pause -> resume logging
        if out is not None:
            sys.stdout = out
            to_flush.append(out)
        if err is not None:
            sys.stderr = err
            to_flush.append(err)
        if inn is not None:
            sys.stdin = inn
            to_flush.append(inn)
            self.rogger.log_debug(
                "Reinstalled stdin TeeStream", stream=sys.stdout)

    def _pause_logging_locked(self, to_flush: List[TeeStream]) -> None:
        """Replace TeeStream wrappers with the original standard streams.

        Must be called while `self._file_lock` is already held. Sets
        `self.paused` to True and reassigns `sys.stdout`, `sys.stderr`,
        and `sys.stdin` back to their original (pre-TeeStream) counterparts.
        Each stream that is uninstalled is appended to `to_flush` so the
        caller can flush buffered data after releasing the lock.

        Arguments:
            to_flush (List[TeeStream]): Accumulator list; streams to flush after the lock is released.
        """
        self.paused = True
        self.rogger.log_info(
            "Pausing logging (restoring original streams)",
            stream=sys.stdout
        )
        out = self.stdout_stream
        err = self.stderr_stream
        inn = self.stdin_stream
        # currently running -> pause logging
        if out is not None:
            sys.stdout = out.original_stream
            to_flush.append(out)
            self.rogger.log_debug(
                "Uninstalled stdout TeeStream",
                stream=sys.stdout
            )
        if err is not None:
            sys.stderr = err.original_stream
            to_flush.append(err)
        if inn is not None:
            sys.stdin = inn.original_stream
            to_flush.append(inn)
            self.rogger.log_debug(
                "Uninstalled stdin TeeStream",
                stream=sys.stdout
            )

    def _flush_streams(self, to_flush: List[TeeStream]) -> None:
        """Flush a list of TeeStream instances, suppressing expected I/O errors.

        Iterates over `to_flush` and calls `flush()` on each stream. `OSError`
        and `ValueError` (e.g. broken pipe, closed file descriptor) are caught
        and silently ignored; all other exceptions propagate.

        Arguments:
            to_flush (List[TeeStream]): Streams to flush.
        """
        # Perform flushes outside the lock (may do I/O)
        for s in to_flush:
            try:
                self.rogger.log_debug(
                    f"Flushing stream: {getattr(s, 'mode', 'unknown')}",
                    stream=sys.stdout
                )
                s.flush()
                self.rogger.log_debug(
                    f"Flushed stream: {getattr(s, 'mode', 'unknown')}",
                    stream=sys.stdout
                )
            except (OSError, ValueError) as e:
                self.rogger.log_warning(
                    f"Ignored flush error for stream: {getattr(s, 'mode', 'unknown')} -> {e}",
                    stream=sys.stderr
                )

    def pause_logging(self, *, toggle: bool = True) -> bool:
        """Toggle the logger pause state.

        When the logger is paused the TeeStream objects are uninstalled and
        the original streams restored. When called again the TeeStream objects
        are reinstalled. sys.* assignments are performed while holding the
        internal lock; flushing is done afterwards to keep critical sections
        short.

        Keyword Arguments:
            toggle (bool): When True and the logger is currently running, pause it; when True and already paused, resume it. When False, always pause. Default: True

        Returns:
            The new paused state (True when now paused, False when now resumed).
        """
        # Snapshot streams and current state under the lock, and perform
        # the sys.* assignment while still holding the lock to avoid races.
        to_flush = []
        with self._file_lock:
            if toggle is True and self.paused is True:
                self.rogger.log_debug(
                    "pause_logging: toggle requested and currently paused -> resume",
                    stream=sys.stdout
                )
                self._resume_logging_locked(to_flush)
            else:
                self.rogger.log_debug(
                    "pause_logging: pausing or toggling into pause",
                    stream=sys.stdout
                )
                self._pause_logging_locked(to_flush)
            _paused = self.paused
        self._flush_streams(to_flush)
        return _paused

    def resume_logging(self, *, toggle: bool = False) -> bool:
        """Explicitly resume logging (idempotent).

        Equivalent to calling pause_logging() while paused, but provided as
        a convenience. sys.* assignments are made under the internal lock;
        flushing is done afterwards.

        Keyword Arguments:
            toggle (bool): When True and the logger is not paused, pause it instead of resuming. When False, always resume. Default: False

        Returns:
            The paused state after the call (False when logging was resumed, True when toggled into pause).
        """
        to_flush = []
        with self._file_lock:
            if toggle is True and self.paused is False:
                self.rogger.log_debug(
                    "resume_logging: toggle requested and currently running -> pause",
                    stream=sys.stdout
                )
                self._pause_logging_locked(to_flush)
            else:
                self.rogger.log_debug(
                    "resume_logging: resuming logging",
                    stream=sys.stdout
                )
                self._resume_logging_locked(to_flush)
            _paused = self.paused
        self._flush_streams(to_flush)
        return _paused

    def is_redirected(self, stream: CONST.StdMode) -> bool:
        """Return whether the given standard stream is currently redirected.

        Lightweight query; safe to call concurrently.

        Arguments:
            stream (CONST.StdMode): One of CONST.StdMode.STDOUT, STDERR, or STDIN.

        Returns:
            True if the corresponding stream has a TeeStream installed, False otherwise.
        """
        _stderr_stream: Optional[TeeStream] = None
        _stdout_stream: Optional[TeeStream] = None
        _stdin_stream: Optional[TeeStream] = None
        with self._file_lock:
            _stderr_stream = self.stderr_stream
            _stdout_stream = self.stdout_stream
            _stdin_stream = self.stdin_stream
        if stream == CONST.StdMode.STDERR:
            return _stderr_stream is not None
        if stream == CONST.StdMode.STDOUT:
            return _stdout_stream is not None
        if stream == CONST.StdMode.STDIN:
            return _stdin_stream is not None
        return False

    def is_logging(self) -> bool:
        """Return True if logging is currently active (not paused).

        Checks whether any TeeStream is installed and the logger is not
        marked as paused. Safe to call concurrently.

        Returns:
            True if at least one TeeStream is installed and the logger is not paused.
        """
        with self._file_lock:
            has_stream = (
                self.stdout_stream is not None
            ) or (
                self.stderr_stream is not None
            ) or (
                self.stdin_stream is not None
            )

        return has_stream and (not bool(self.paused))

    def stop_logging(self) -> None:
        """Stop logging and restore the original standard streams.

        Restores sys.stdout, sys.stderr, and sys.stdin to their original
        values, attempts to unregister any atexit flush handlers registered
        by start_logging(), and flushes remaining buffers. Stream replacement
        and atexit unregistration are done under the internal lock; flushing
        is performed afterwards.
        """
        to_flush = []
        with self._file_lock:
            if self.stdout_stream is not None:
                sys.stdout = self.stdout_stream.original_stream
                to_flush.append(self.stdout_stream)
                self.stdout_stream = None
            if self.stderr_stream is not None:
                sys.stderr = self.stderr_stream.original_stream
                to_flush.append(self.stderr_stream)
                self.stderr_stream = None
            if self.stdin_stream is not None:
                sys.stdin = self.stdin_stream.original_stream
                to_flush.append(self.stdin_stream)
                self.stdin_stream = None
            self.paused = False

            if getattr(self, "_atexit_registered", False):
                self.rogger.log_debug(
                    "Unregistering atexit flush handlers",
                    stream=sys.stdout
                )
                for f in getattr(self, "_registered_flushers", []):
                    try:
                        atexit.unregister(f)
                    except ValueError:
                        pass
                    except AttributeError:
                        pass
                self._registered_flushers = []
                self._atexit_registered = False
                self.rogger.log_info(
                    "Unregistered atexit flush handlers",
                    stream=sys.stdout
                )

        for s in to_flush:
            try:
                self.rogger.log_debug(
                    f"stop_logging: flushing stream {getattr(s, 'mode', 'unknown')}",
                    stream=sys.stdout
                )
                s.flush()
            except (OSError, ValueError):
                self.rogger.log_warning(
                    f"stop_logging: ignored flush error for {getattr(s, 'mode', 'unknown')}",
                    stream=sys.stderr
                )


if __name__ == "__main__":
    RotaryLogger().start_logging()
