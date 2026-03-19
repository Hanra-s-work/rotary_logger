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
# LAST Modified: 5:49:55 19-03-2026
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
    from .rogger import Rogger, RI
except ImportError:
    import constants as CONST
    from file_instance import FileInstance
    from rogger import Rogger, RI


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
        log_to_file: bool = True,
        log_function_calls: bool = False
    ):
        """Initialise a new TeeStream.

        Mirrors original_stream to disk via a FileInstance while forwarding
        every write transparently to the caller.

        Arguments:
            root (Union[str, Path, FileInstance]): Path, string, or FileInstance describing the log destination.
            original_stream (TextIO): The TextIO stream to mirror (usually sys.stdout).

        Keyword Arguments:
            max_size_mb (Optional[int]): Optional maximum log-file size in MB; forwarded to FileInstance. Default: None
            flush_size (Optional[int]): Optional buffer-flush threshold in bytes; forwarded to FileInstance. Default: None
            mode (CONST.StdMode): Which standard stream this instance wraps. Default: CONST.StdMode.STDUNKNOWN
            error_mode (CONST.ErrorMode): Broken-pipe handling policy. Default: CONST.ErrorMode.WARN_NO_PIPE
            encoding (Optional[str]): Optional file-encoding override; forwarded to FileInstance. Default: None
            log_to_file (bool): Whether disk logging is enabled on construction. Default: True

        Raises:
            ValueError: If root is not a str, Path, or FileInstance.
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
        self.function_calls = log_function_calls
        self.rogger: Rogger = RI
        # Log TeeStream creation
        try:
            self.rogger.log_debug(
                f"TeeStream initialized (mode={self.stream_mode}, log_to_file={log_to_file})",
                stream=sys.stdout
            )
        except (AttributeError, OSError, ValueError):
            # Never allow logging to break stream setup
            pass

    def __del__(self):
        """Best-effort cleanup on object deletion.

        Attempts to flush buffered data but never raises. Note that __del__
        may not be called at interpreter shutdown; callers that need
        deterministic flushing should invoke flush() explicitly before
        releasing the object. OSError and ValueError are intentionally
        swallowed so that interpreter-shutdown teardown cannot trigger
        unexpected tracebacks.
        """
        try:
            self.flush()
        except (OSError, ValueError):
            # best-effort flush; ignore expected I/O errors during interpreter shutdown
            pass
        # avoid deleting attributes in __del__; simply drop the reference
        self.file_instance = None

    def _get_correct_prefix(self, function_call: CONST.PrefixFunctionCall = CONST.PrefixFunctionCall.EMPTY) -> str:
        """Return the correct prefix string for the configured StdMode.

        The returned string already contains a trailing space when non-empty so
        that callers can concatenate it with the message directly. Returns an
        empty string when logging to file is disabled, when no FileInstance is
        set, or when the Prefix configuration has no flags enabled.

        Returns:
            The prefix string (with trailing space) matching the active StdMode,
            or an empty string.
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

        _final_prefix: str = ""
        if not _prefix:
            _final_prefix = ""
        elif _prefix.std_err and _mode == CONST.StdMode.STDERR:
            _final_prefix = CONST.CORRECT_PREFIX[CONST.StdMode.STDERR]
        elif _prefix.std_in and _mode == CONST.StdMode.STDIN:
            _final_prefix = CONST.CORRECT_PREFIX[CONST.StdMode.STDIN]
        elif _prefix.std_out and _mode == CONST.StdMode.STDOUT:
            _final_prefix = CONST.CORRECT_PREFIX[CONST.StdMode.STDOUT]
        elif _prefix.std_in or _prefix.std_err or _prefix.std_out:
            _final_prefix = CONST.CORRECT_PREFIX[CONST.StdMode.STDUNKNOWN]
        else:
            _final_prefix = ""
        if self.function_calls and function_call != CONST.PrefixFunctionCall.EMPTY:
            _final_prefix = f"{_final_prefix}{function_call.value}"
        if _final_prefix != "":
            _final_prefix = f"{_final_prefix}{CONST.SPACE}"
        return _final_prefix

    def _write_to_log(self, data: Union[str, List[str]], function_call: CONST.PrefixFunctionCall) -> None:
        """Write data to the log file if file logging is enabled.

        Shared helper used by write(), writelines(), read(), readline() and
        readlines() to avoid duplicating the snapshot-check-prefix-write
        sequence in every method.

        Arguments:
            data (str): The string to append to the log file.
            function_call (CONST.PrefixFunctionCall): Context passed to
                _get_correct_prefix() to select the right prefix.
        """
        _file_instance: Optional[FileInstance] = None
        with self._file_lock:
            if self.file_instance:
                _file_instance = self.file_instance
        if not _file_instance:
            return
        try:
            if not _file_instance.get_log_to_file():
                return
        except (OSError, ValueError, AttributeError):
            return
        try:
            _prefix: str = self._get_correct_prefix(
                function_call=function_call)
        except (OSError, ValueError, AttributeError):
            _prefix = ""
        try:
            if isinstance(data, list):
                for i in data:
                    _file_instance.write(f"{_prefix}{i}")
            else:
                _file_instance.write(f"{_prefix}{data}")
        except (OSError, ValueError):
            try:
                sys.stderr.write(
                    f"{CONST.MODULE_NAME} Error writing to log file\n"
                )
            except OSError:
                pass

    def _get_stream_if_present(self) -> TextIO:
        """Return the underlying stream, raising if it has been cleared.

        Used as a guard by every delegating method so that operations on an
        uninitialised or already-destroyed TeeStream fail predictably rather
        than with an obscure AttributeError.

        Raises:
            AttributeError: If original_stream is None.

        Returns:
            The original TextIO stream passed at construction time.
        """
        if self.original_stream is not None:
            return self.original_stream
        raise self.stream_not_present

    def write(self, message: str) -> None:
        """Write message to the original stream and buffer it to the log file.

        Thread-safe: the FileInstance reference is captured under a lock before
        any I/O is performed. The terminal write is carried out on the caller
        thread with explicit BrokenPipeError / OSError handling; disk writes
        are delegated to FileInstance.write().

        Arguments:
            message (str): The string to write.
        """
        _tmp_message: str = message

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

        self._write_to_log(_tmp_message, CONST.PrefixFunctionCall.WRITE)
        try:
            # Debug log about the write operation (non-intrusive)
            self.rogger.log_debug(
                f"write: forwarded {len(_tmp_message)} chars to original stream (mode={self.stream_mode})",
                stream=sys.stdout
            )
        except (AttributeError, OSError, ValueError):
            pass

    def writelines(self, lines: List[str]) -> None:
        """Write a list of strings to the original stream and buffer them to the log file.

        Thread-safe: behaves like write() but accepts a sequence of strings,
        forwarding the entire sequence to the original stream via writelines()
        and then writing each element individually to FileInstance with the
        appropriate prefix.

        Arguments:
            lines (List[str]): The sequence of strings to write.
        """
        _tmp_message: List[str] = lines.copy()
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
        self._write_to_log(_tmp_message, CONST.PrefixFunctionCall.WRITELINES)
        try:
            total = 0
            for l in _tmp_message:
                total += len(l)
            self.rogger.log_debug(
                f"writelines: forwarded {total} chars across {len(_tmp_message)} items (mode={self.stream_mode})",
                stream=sys.stdout
            )
        except (AttributeError, OSError, ValueError):
            pass

    def read(self, size: int = -1) -> str:
        """Read and return up to size characters from the original stream.

        Keyword Arguments:
            size (int): Maximum number of characters to read; -1 reads until EOF. Default: -1

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The characters read.
        """

        # Always attempt to read from the original stream first so that we don't lose data if the stream is interactive and the file instance is misconfigured
        data = self._get_stream_if_present().read(size)
        self._write_to_log(data, CONST.PrefixFunctionCall.READ)
        try:
            self.rogger.log_debug(
                f"read: read {len(data)} chars from original stream (mode={self.stream_mode})",
                stream=sys.stdout
            )
        except (AttributeError, OSError, ValueError):
            pass
        return data

    def readline(self, size: int = -1) -> str:
        """Read and return one line from the original stream.

        Keyword Arguments:
            size (int): If non-negative, at most size characters are read; -1 reads until a newline or EOF. Default: -1

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The line read, including the trailing newline if present.
        """
        data = self._get_stream_if_present().readline(size)
        self._write_to_log(data, CONST.PrefixFunctionCall.READLINE)
        try:
            self.rogger.log_debug(
                f"readline: read {len(data)} chars from original stream (mode={self.stream_mode})",
                stream=sys.stdout
            )
        except (AttributeError, OSError, ValueError):
            pass
        return data

    def readlines(self, hint: int = -1) -> list[str]:
        """Read and return a list of lines from the original stream.

        Keyword Arguments:
            hint (int): If non-negative, approximately hint bytes or characters are read; -1 reads until EOF. Default: -1

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            List of lines read from the stream.
        """
        data = self._get_stream_if_present().readlines(hint)
        self._write_to_log(data, CONST.PrefixFunctionCall.READLINES)
        try:
            total = 0
            for d in data:
                total += len(d)
            self.rogger.log_debug(
                f"readlines: read {len(data)} lines, {total} chars (mode={self.stream_mode})",
                stream=sys.stdout
            )
        except (AttributeError, OSError, ValueError):
            pass
        return data

    def flush(self) -> None:
        """Best-effort flush of terminal and buffered file output.

        Attempts to flush both the original stream and the associated
        FileInstance. All OSError and ValueError exceptions are swallowed to
        avoid crashing the caller. For stricter guarantees call
        FileInstance.flush() directly. This method is also called by __del__
        during object teardown.
        """

        # Flush the original stream first (best-effort)
        try:
            self.rogger.log_debug(
                f"Flushing TeeStream (mode={self.stream_mode})",
                stream=sys.stdout
            )
        except (AttributeError, OSError, ValueError):
            pass
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

        _file_instance: Optional[FileInstance] = None
        # Snapshot the file instance under lock
        with self._file_lock:
            if self.file_instance:
                _file_instance = self.file_instance

        if _file_instance:
            try:
                if not _file_instance.get_log_to_file():
                    return
            except (OSError, ValueError, AttributeError):
                # If the check fails, continue and attempt a flush anyway.
                pass

            try:
                if self.function_calls:
                    try:
                        _prefix: str = self._get_correct_prefix(
                            function_call=CONST.PrefixFunctionCall.FLUSH
                        )
                    except (OSError, ValueError, AttributeError):
                        _prefix: str = ""
                    _file_instance.write(_prefix)
                _file_instance.flush()
                try:
                    self.rogger.log_debug(
                        f"Flushed file_instance for mode={self.stream_mode}",
                        stream=sys.stdout
                    )
                except (AttributeError, OSError, ValueError):
                    pass
            except (OSError, ValueError):
                try:
                    self.rogger.log_warning(
                        f"TeeStream flush encountered I/O error for mode={self.stream_mode}",
                        stream=sys.stderr
                    )
                except (AttributeError, OSError, ValueError):
                    pass
                # don't let file flush failures propagate from a best-effort flush

    # sys.TextIO rebinds so the redirection is transparent to the caller

    @property
    def buffer(self) -> BinaryIO:
        """Return the underlying binary buffer of the original stream.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The binary buffer exposed by the wrapped TextIO.
        """
        data = self._get_stream_if_present().buffer
        return data

    @property
    def closed(self) -> bool:
        """Return whether the original stream is closed.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            True if the wrapped stream has been closed, False otherwise.
        """
        data = self._get_stream_if_present().closed
        return data

    @property
    def errors(self) -> Optional[str]:
        """Return the error-handling mode of the original stream.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The error-handling mode string (e.g. 'strict'), or None.
        """
        data = self._get_stream_if_present().errors
        return data

    @property
    def encoding(self) -> str:
        """Return the character encoding of the original stream.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The encoding string (e.g. 'utf-8').
        """
        data = self._get_stream_if_present().encoding
        return data

    @property
    def line_buffering(self) -> int:
        """Return whether line buffering is enabled on the original stream.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            Non-zero if line buffering is active, zero otherwise.
        """
        data = self._get_stream_if_present().line_buffering
        return data

    @property
    def mode(self) -> str:
        """Return the file-mode string of the original stream.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The mode string (e.g. 'w', 'r').
        """
        data = self._get_stream_if_present().mode
        return data

    @property
    def name(self) -> Union[str, Any]:
        """Return the name of the original stream.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The stream name; typically a file path string or an integer file
            descriptor for standard streams.
        """
        data = self._get_stream_if_present().name
        return data

    @property
    def newlines(self) -> Any:
        """Return the newline translation used by the original stream.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            A string, tuple of strings, or None as described by the standard
            io.TextIOBase.newlines attribute.
        """
        data = self._get_stream_if_present().newlines
        return data

    def close(self) -> None:
        """Flush pending data and close the original stream.

        Calls flush() before delegating to the original stream's close()
        method, ensuring buffered log data is written before the stream is
        released.

        Raises:
            AttributeError: If the original stream is not set.
        """
        try:
            self.rogger.log_info(
                f"Closing TeeStream (mode={self.stream_mode})",
                stream=sys.stdout
            )
        except (AttributeError, OSError, ValueError):
            pass
        self.flush()
        self._get_stream_if_present().close()

    def fileno(self) -> int:
        """Return the underlying file descriptor of the original stream.

        Raises:
            AttributeError: If the original stream is not set.
            io.UnsupportedOperation: If the stream has no file descriptor.

        Returns:
            Integer file descriptor.
        """
        data = self._get_stream_if_present().fileno()
        return data

    def isatty(self) -> bool:
        """Return whether the original stream is connected to a TTY device.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            True if the stream is interactive (TTY), False otherwise.
        """
        data = self._get_stream_if_present().isatty()
        return data

    def readable(self) -> bool:
        """Return whether the original stream supports reading.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            True if the stream can be read from, False otherwise.
        """
        data = self._get_stream_if_present().readable()
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        """Move the stream position to the given byte offset.

        Arguments:
            offset (int): Number of bytes to move the position.

        Keyword Arguments:
            whence (int): Reference point: 0 = start, 1 = current, 2 = end. Default: 0

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The new absolute stream position.
        """
        data = self._get_stream_if_present().seek(offset, whence)
        return data

    def seekable(self) -> bool:
        """Return whether the original stream supports random-access seeking.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            True if the stream supports seek() and tell(), False otherwise.
        """
        data = self._get_stream_if_present().seekable()
        return data

    def tell(self) -> int:
        """Return the current stream position of the original stream.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The current byte offset within the stream.
        """
        data = self._get_stream_if_present().tell()
        return data

    def truncate(self, size: Optional[int] = None) -> int:
        """Truncate the original stream to at most size bytes.

        Keyword Arguments:
            size (Optional[int]): Desired size in bytes; defaults to the current stream position. Default: None

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The new file size in bytes.
        """
        data = self._get_stream_if_present().truncate(size)
        return data

    def writable(self) -> bool:
        """Return whether the original stream supports writing.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            True if the stream can be written to, False otherwise.
        """
        data = self._get_stream_if_present().writable()
        return data

    def __enter__(self) -> TextIO:
        """Enter the runtime context for the original stream.

        Delegates to the wrapped stream's __enter__() so that TeeStream can be
        used as a context manager wherever a plain TextIO is expected.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The original stream as returned by its own __enter__().
        """
        data = self._get_stream_if_present().__enter__()
        return data

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        """Exit the runtime context and delegate to the original stream.

        Delegates to the wrapped stream's __exit__() so that TeeStream can be
        used as a context manager wherever a plain TextIO is expected.

        Arguments:
            exc_type (type): The exception type, or None if no exception.
            exc_val (BaseException): The exception instance, or None.
            exc_tb (traceback): The traceback, or None.

        Raises:
            AttributeError: If the original stream is not set.

        Returns:
            The return value of the original stream's __exit__(); True suppresses
            the exception, False or None propagates it.
        """
        data = self._get_stream_if_present().__exit__(exc_type, exc_val, exc_tb)
        return data
