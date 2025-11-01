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
# FILE: test_integration_writes.py
# CREATION DATE: 01-11-2025
# LAST Modified: 13:47:22 01-11-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: File in charge of testing the dual channel logging where each stream is logged to it's own file.
# // AR
# +==== END rotary_logger =================+
"""
import sys
from pathlib import Path
from typing import Optional
from rotary_logger import constants as CONST
from rotary_logger.rotary_logger_cls import RotaryLogger


def _find_log_by_folder(root: Path, folder_name: Optional[str]) -> Path:
    """Return the first .log file under root matching the folder_name.

    If folder_name is None, look for log files directly under the day
    directory (i.e. not in stdout/stderr subfolders).
    """
    logs_root = root / CONST.LOG_FOLDER_BASE_NAME
    if not logs_root.exists():
        # older code may place directly under root
        logs_root = root
    # perform a shallow recursive search for .log files
    for p in logs_root.rglob("*.log"):
        parent = p.parent
# LAST Modified: 13:38:57 01-11-2025
        # prefer files whose parent is not one of the STD subfolders
        if parent.name not in (CONST.FOLDER_STDOUT, CONST.FOLDER_STDERR, CONST.FOLDER_STDIN, CONST.FOLDER_STDUNKNOWN):
            return p
        else:
            if parent.name == folder_name:
                return p
    raise AssertionError(
        f"No log file found for folder {folder_name!r} under {root}")


def test_start_logging_split_writes(tmp_path: Path) -> None:
    rl = RotaryLogger()
    orig_out = sys.stdout
    orig_err = sys.stderr
    try:
        rl.start_logging(log_folder=tmp_path, merged=False, log_to_file=True)
        # write one line to each stream
        sys.stdout.write("OUT: hello split\n")
        sys.stderr.write("ERR: goodbye split\n")
        # flush both
        try:
            sys.stdout.flush()
        except Exception:
            pass
        try:
            sys.stderr.flush()
        except Exception:
            pass
    finally:
        # restore
        sys.stdout = orig_out
        sys.stderr = orig_err

    # locate the files
    out_file = _find_log_by_folder(tmp_path, CONST.FOLDER_STDOUT)
    err_file = _find_log_by_folder(tmp_path, CONST.FOLDER_STDERR)

    assert out_file.exists()
    assert err_file.exists()

    out_text = out_file.read_text(encoding="utf-8")
    err_text = err_file.read_text(encoding="utf-8")

    assert "OUT: hello split" in out_text
    assert "ERR: goodbye split" in err_text


def test_start_logging_merged_writes(tmp_path: Path) -> None:
    rl = RotaryLogger()
    orig_out = sys.stdout
    orig_err = sys.stderr
    try:
        rl.start_logging(log_folder=tmp_path, merged=True, log_to_file=True)
        sys.stdout.write("OUT: hello merged\n")
        sys.stderr.write("ERR: goodbye merged\n")
        try:
            sys.stdout.flush()
        except Exception:
            pass
        try:
            sys.stderr.flush()
        except Exception:
            pass
    finally:
        sys.stdout = orig_out
        sys.stderr = orig_err

    # merged logs are placed in the day directory (no stdout/stderr subfolder)
    merged_file = _find_log_by_folder(tmp_path, None)
    assert merged_file.exists()
    contents = merged_file.read_text(encoding="utf-8")
    assert "OUT: hello merged" in contents
    assert "ERR: goodbye merged" in contents
