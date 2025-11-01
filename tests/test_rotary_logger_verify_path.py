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
# FILE: test_rotary_logger_verify_path.py
# CREATION DATE: 29-10-2025
# LAST Modified: 23:33:44 29-10-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the test file in charge of checking if the error handling for paths work for writable and unwritable paths.
# // AR
# +==== END rotary_logger =================+
"""

import sys
from pathlib import Path

try:
    sys.path.insert(0, '.')
    from rotary_logger import constants as CONST
    from rotary_logger.rotary_logger_cls import RotaryLogger
except ImportError as e:
    raise RuntimeError(f"Failed to import the library, error: {e}") from e


def test_unwritable_root_fallback() -> None:
    """If the provided path is not writable (e.g. /root), the function should
    fall back to the package default log folder.
    """
    rl = RotaryLogger()
    result = rl._verify_user_log_path(Path('/root'))
    assert result == CONST.DEFAULT_LOG_FOLDER


def test_tmpdir_accepted(tmp_path: Path) -> None:
    """A writable absolute tmp path should be accepted and the configured
    base folder ('logs') appended if missing.
    """
    rl = RotaryLogger()
    # tmp_path is absolute; _verify_user_log_path should append 'logs'
    result = rl._verify_user_log_path(tmp_path)
    assert result == tmp_path / CONST.LOG_FOLDER_BASE_NAME
    # Directory should have been created
    assert (tmp_path / CONST.LOG_FOLDER_BASE_NAME).exists()
