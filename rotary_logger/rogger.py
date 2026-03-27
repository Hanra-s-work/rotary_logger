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
# FILE: rogger.py
# CREATION DATE: 18-03-2026
# LAST Modified: 23:13:3 26-03-2026
# DESCRIPTION:
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: A class that is tailored to the module to allow it to log without fering of breaking structure.
# // AR
# +==== END rotary_logger =================+
"""

import sys
import inspect
from threading import RLock
from datetime import datetime
from typing import Optional, TextIO, Union, TYPE_CHECKING
from .constants import MODULE_NAME, LogToggle

if TYPE_CHECKING:
    from .tee_stream import TeeStream


class Rogger:
    """
    This is a custom made class that aims to work seamlessly with the library so that it doesn't break streams.
    """

    _class_lock: RLock = RLock()
    _function_lock: RLock = RLock()
    _instance: Optional["Rogger"] = None

    def __new__(cls) -> "Rogger":
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        program_log: bool = False,
        program_debug_log: bool = False,
        suppress_program_warning_logs: bool = False,
        suppress_program_error_logs: bool = False
    ) -> None:
        # the settings
        self.toggles: LogToggle = self._create_log_toggle(
            program_log,
            program_debug_log,
            suppress_program_warning_logs,
            suppress_program_error_logs
        )
        # The shorthand strings used to build the log
        self.program_name: str = f"{MODULE_NAME}"
        self.success: str = "SUCCESS"
        self.info: str = "INFO"
        self.warning: str = "WARNING"
        self.error: str = "ERROR"
        self.critical: str = "CRITICAL"
        self.debug: str = "DEBUG"

    def re_toggle(
        self,
        program_log: bool = False,
        program_debug_log: bool = False,
        suppress_program_warning_logs: bool = False,
        suppress_program_error_logs: bool = False
    ) -> None:
        """Re-create the toggle settings after the class has already been initialised.

        Args:
            program_log (bool, optional): Wether to log to the terminal. Defaults to False.
            program_debug_log (bool, optional): Wether to log debug. Defaults to False.
            suppress_program_warning_logs (bool, optional): Wether to display warnings or not. Defaults to False.
            suppress_program_error_logs (bool, optional): Wether to display errors or not. Defaults to False.
        """
        new_toggle = self._create_log_toggle(
            program_log,
            program_debug_log,
            suppress_program_warning_logs,
            suppress_program_error_logs
        )
        with self._function_lock:
            self.toggles = new_toggle

    def _create_log_toggle(
        self,
        program_log: bool = False,
        program_debug_log: bool = False,
        suppress_program_warning_logs: bool = False,
        suppress_program_error_logs: bool = False
    ) -> LogToggle:
        """Define which log modes can be used.

        Returns:
            LogToggle: The dataclass to follow.
        """
        _success: bool = True
        _info: bool = True
        _warning: bool = True
        _error: bool = True
        _critical: bool = True
        _debug: bool = True
        if program_debug_log is False:
            _debug = False
        if program_log is False:
            _success = False
            _info = False
            if suppress_program_warning_logs is True:
                _warning = False
            else:
                _warning = True
            if suppress_program_error_logs is True:
                _error = False
                _critical = False
            else:
                _error = True
                _critical = True
        return LogToggle(
            program_log=program_log,
            success=_success,
            info=_info,
            warning=_warning,
            error=_error,
            critical=_critical,
            debug=_debug
        )

    def _get_date(self) -> str:
        """
        The function in charge of returning the date string for the line.

        Returns:
            str: the string ready to be embedded.
        """
        now = datetime.now()
        final = now.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        final += f",{now.microsecond // 1000:03d}"
        return final

    def _get_class_name(self, depth: int = 1) -> Optional[str]:
        """Determine the name of the class that called the log

        Args:
            depth (int, optional): The upstream depth to look into. Defaults to 2.

        Returns:
            Optional[str]: The name of the class (if any)
        """
        if self.toggles.program_log is False:
            return None

        try:
            frame = inspect.currentframe()
        # type: ignore[reportBroadException]  # pylint: disable=broad-exception-caught
        except Exception:
            return None
        if frame is None:
            return None

        try:
            current_depth = 0
            while current_depth < depth:
                if frame and frame.f_back is not None:
                    frame = frame.f_back
                else:
                    frame = None
                    break
                current_depth += 1
        # type: ignore[reportBroadException]  # pylint: disable=broad-exception-caught
        except Exception:
            return None

        if frame is None:
            return None
        try:
            locals_ = frame.f_locals
        # type: ignore[reportBroadException]  # pylint: disable=broad-exception-caught
        except Exception:
            return None

        # Instance method
        if "self" in locals_:
            try:
                return type(locals_["self"]).__name__
        # type: ignore[reportBroadException]  # pylint: disable=broad-exception-caught
            except Exception:
                return None

        # Class method
        if "cls" in locals_:
            try:
                return locals_["cls"].__name__
        # type: ignore[reportBroadException]  # pylint: disable=broad-exception-caught
            except Exception:
                return None

        return None

    def _get_function_name(self, depth: int = 2) -> Optional[str]:
        """Determine the name of the function that called the log

        Args:
            depth (int, optional): The upstream depth to look into. Defaults to 2.

        Returns:
            Optional[str]: The name of the function (if any)
        """
        if self.toggles.program_log is False:
            return None
        try:
            _func_name = inspect.currentframe()
        # type: ignore[reportBroadException]  # pylint: disable=broad-exception-caught
        except Exception:
            return None
        if _func_name is None:
            return None
        current_depth = 0
        try:
            while current_depth < depth:
                if _func_name and _func_name.f_back is not None:
                    _func_name = _func_name.f_back
                else:
                    _func_name = None
                    break
                current_depth += 1
        # type: ignore[reportBroadException]  # pylint: disable=broad-exception-caught
        except Exception:
            return None
        if _func_name is None:
            return None
        try:
            return _func_name.f_code.co_name
        # type: ignore[reportBroadException]  # pylint: disable=broad-exception-caught
        except Exception:
            return None

    def _log_if_possible(self, log_type: str, message: str, function_name: Optional[str], class_name: Optional[str], stream: Union[TextIO, "TeeStream"]) -> None:
        """The generic function to log the message to the provided stream

        Args:
            log_type (str): The type of log message (Info, Warning, Error, etc)
            message (str): The message provided by the user
            function_name (Optional[str]): The name of the function
            stream (Union[TextIO, TeeStream]): The stream to write to
        """
        if function_name is None:
            function_name = self._get_function_name(3) or "Unknown"
        if class_name is None:
            class_name = self._get_class_name(2) or "Unknown"
        date = self._get_date()
        final_msg = f"[{date}] {self.program_name} {log_type} ({class_name}.{function_name}): {message}\n"
        with self._function_lock:
            stream.write(final_msg)

    def log_success(self, message: str, *, function_name: Optional[str] = None, class_name: Optional[str] = None, stream: Union[TextIO, "TeeStream"] = sys.stdout) -> None:
        """Log a success message to the stream (if logging conditions are met)

        Args:
            message (str): The message to display
            function_name (Optional[str], optional): The name of the function calling it. Defaults to None.
            class_name (Optional[str], optional): The name of the class calling it. Defaults to None.
            stream (Union[TextIO, TeeStream], optional): The stream to write to. Defaults to sys.stdout.
        """
        if self.toggles.success is False:
            return
        if function_name is None:
            function_name = self._get_function_name(2)
        if class_name is None:
            class_name = self._get_class_name(2)
        self._log_if_possible(
            log_type=self.success,
            message=message,
            function_name=function_name,
            class_name=class_name,
            stream=stream
        )

    def log_info(self, message: str, *, function_name: Optional[str] = None, class_name: Optional[str] = None, stream: Union[TextIO, "TeeStream"] = sys.stdout) -> None:
        """Log a info message to the stream (if logging conditions are met)

        Args:
            message (str): The message to display
            function_name (Optional[str], optional): The name of the function calling it. Defaults to None.
            class_name (Optional[str], optional): The name of the class calling it. Defaults to None.
            stream (Union[TextIO, TeeStream], optional): The stream to write to. Defaults to sys.stdout.
        """
        if self.toggles.info is False:
            return
        if function_name is None:
            function_name = self._get_function_name(2)
        if class_name is None:
            class_name = self._get_class_name(2)
        self._log_if_possible(
            log_type=self.success,
            message=message,
            function_name=function_name,
            class_name=class_name,
            stream=stream
        )

    def log_warning(self, message: str, *, function_name: Optional[str] = None, class_name: Optional[str] = None, stream: Union[TextIO, "TeeStream"] = sys.stderr) -> None:
        """Log a warning message to the stream (if logging conditions are met)

        Args:
            message (str): The message to display
            function_name (Optional[str], optional): The name of the function calling it. Defaults to None.
            class_name (Optional[str], optional): The name of the class calling it. Defaults to None.
            stream (Union[TextIO, TeeStream], optional): The stream to write to. Defaults to sys.stderr.
        """
        if self.toggles.warning is False:
            return
        if function_name is None:
            function_name = self._get_function_name(2)
        if class_name is None:
            class_name = self._get_class_name(2)
        self._log_if_possible(
            log_type=self.success,
            message=message,
            function_name=function_name,
            class_name=class_name,
            stream=stream
        )

    def log_error(self, message: str, *, function_name: Optional[str] = None, class_name: Optional[str] = None, stream: Union[TextIO, "TeeStream"] = sys.stderr) -> None:
        """Log an error message to the stream (if logging conditions are met)

        Args:
            message (str): The message to display
            function_name (Optional[str], optional): The name of the function calling it. Defaults to None.
            class_name (Optional[str], optional): The name of the class calling it. Defaults to None.
            stream (Union[TextIO, TeeStream], optional): The stream to write to. Defaults to sys.stderr.
        """
        if self.toggles.error is False:
            return
        if function_name is None:
            function_name = self._get_function_name(2)
        if class_name is None:
            class_name = self._get_class_name(2)
        self._log_if_possible(
            log_type=self.success,
            message=message,
            function_name=function_name,
            class_name=class_name,
            stream=stream
        )

    def log_critical(self, message: str, *, function_name: Optional[str] = None, class_name: Optional[str] = None, stream: Union[TextIO, "TeeStream"] = sys.stderr) -> None:
        """Log a critical message to the stream (if logging conditions are met)

        Args:
            message (str): The message to display
            function_name (Optional[str], optional): The name of the function calling it. Defaults to None.
            class_name (Optional[str], optional): The name of the class calling it. Defaults to None.
            stream (Union[TextIO, TeeStream], optional): The stream to write to. Defaults to sys.stderr.
        """
        if self.toggles.critical is False:
            return
        if function_name is None:
            function_name = self._get_function_name(2)
        if class_name is None:
            class_name = self._get_class_name(2)
        self._log_if_possible(
            log_type=self.success,
            message=message,
            function_name=function_name,
            class_name=class_name,
            stream=stream
        )

    def log_debug(self, message: str, *, function_name: Optional[str] = None, class_name: Optional[str] = None, stream: Union[TextIO, "TeeStream"] = sys.stdout) -> None:
        """Log a debug message to the stream (if logging conditions are met)

        Args:
            message (str): The message to display
            function_name (Optional[str], optional): The name of the function calling it. Defaults to None.
            class_name (Optional[str], optional): The name of the class calling it. Defaults to None.
            stream (Union[TextIO, TeeStream], optional): The stream to write to. Defaults to sys.stdout.
        """
        if self.toggles.debug is False:
            return
        if function_name is None:
            function_name = self._get_function_name(2)
        if class_name is None:
            class_name = self._get_class_name(2)
        self._log_if_possible(
            log_type=self.success,
            message=message,
            function_name=function_name,
            class_name=class_name,
            stream=stream
        )


# Module-level shared Rogger instance for convenience (used by TeeStream and others)
RI: Rogger = Rogger()
