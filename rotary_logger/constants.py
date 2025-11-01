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
# FILE: constants.py
# CREATION DATE: 29-10-2025
# LAST Modified: 1:31:28 01-11-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the file that contains the values that are not meant to change, this is regardless of the downstream code
# // AR
# +==== END rotary_logger =================+
"""

from dataclasses import dataclass
import os
import sys
from typing import IO, Optional, Dict, Any
from pathlib import Path
from enum import Enum

IS_A_TTY: bool = sys.stdout.isatty()
IS_PIPE: bool = not IS_A_TTY

MODULE_NAME: str = "[Rotary Logger]"

ERROR: int = 1
SUCCESS: int = 0

SPACE: str = " "

B1: int = 1  # bytes
KB1: int = B1 * 1024  # bytes
MB1: int = KB1 * KB1  # bytes
GB1: int = MB1 * KB1  # bytes
TB1: int = GB1 * KB1  # bytes

STDIN: str = "stdin"
STDOUT: str = "stdout"
STDERR: str = "stderr"
STDUNKNOWN: str = "stdunknown"


class StdMode(Enum):
    STDIN = STDIN
    STDOUT = STDOUT
    STDERR = STDERR
    STDUNKNOWN = STDUNKNOWN


LOG_FOLDER_BASE_NAME: str = "logs"

FOLDER_STDOUT: str = "stdout"
FOLDER_STDERR: str = "stderr"
FOLDER_STDIN: str = "stdin"
FOLDER_STDUNKNOWN: str = "std_unknown"

CORRECT_FOLDER: Dict[StdMode, str] = {
    StdMode.STDIN: FOLDER_STDIN,
    StdMode.STDOUT: FOLDER_STDOUT,
    StdMode.STDERR: FOLDER_STDERR,
    StdMode.STDUNKNOWN: FOLDER_STDUNKNOWN,
}

BUFFER_FLUSH_SIZE: int = 8 * KB1  # flush every 8 KB

DEFAULT_ENCODING: str = "utf-8"
DEFAULT_LOG_MAX_FILE_SIZE: int = 2 * GB1  # MB ~ 2 GB
DEFAULT_LOG_BUFFER_FLUSH_SIZE: int = BUFFER_FLUSH_SIZE
DEFAULT_LOG_FOLDER: Path = Path(__file__).parent / LOG_FOLDER_BASE_NAME


ERROR_MODE_WARN: str = "Warn"
ERROR_MODE_WARN_NO_PIPE: str = "Warn No pipe"
ERROR_MODE_EXIT: str = "Exit"
ERROR_MODE_EXIT_NO_PIPE: str = "Exit No pipe"


class ErrorMode(Enum):
    """The tee error mode that can be used.

    Args:
        Enum (_type_): The enumerators that can be used.
    """
    WARN = ERROR_MODE_WARN
    WARN_NO_PIPE = ERROR_MODE_WARN_NO_PIPE
    EXIT = ERROR_MODE_EXIT
    EXIT_NO_PIPE = ERROR_MODE_EXIT_NO_PIPE


FILE_LOG_DATE_FORMAT: str = "%Y_%m_%dT%Hh%Mm%Ss.log"


@dataclass
class FileInfo:
    path: Optional[Path] = None
    descriptor: Optional[IO[Any]] = None
    written_bytes: int = 0


@dataclass
class Prefix:
    std_in: bool = False
    std_out: bool = False
    std_err: bool = False


BROKEN_PIPE_ERROR: str = f"{MODULE_NAME} Broken pipe on stdout\n"

PREFIX_STDOUT: str = "[STDOUT]"
PREFIX_STDERR: str = "[STDERR]"
PREFIX_STDIN: str = "[STDIN]"
PREFIX_STDUNKNOWN: str = "[STDUNKNOWN]"
CORRECT_PREFIX: Dict[StdMode, str] = {
    StdMode.STDIN: PREFIX_STDIN,
    StdMode.STDOUT: PREFIX_STDOUT,
    StdMode.STDERR: PREFIX_STDERR,
    StdMode.STDUNKNOWN: PREFIX_STDUNKNOWN
}

LOG_TO_FILE_ENV: bool = os.environ.get(
    "LOG_TO_FILE",
    ""
).lower() in ("1", "true", "yes")

RAW_LOG_FOLDER_ENV: str = os.environ.get(
    "LOG_FOLDER_NAME",
    str(DEFAULT_LOG_FOLDER)
)
