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
# FILE: test_split_logging.py
# CREATION DATE: 01-11-2025
# LAST Modified: 4:32:48 01-11-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the file in charge of testing the split logging functionality of the Rotary logger class.
# // AR
# +==== END rotary_logger =================+
"""
import sys
from pathlib import Path

from rotary_logger.rotary_logger_cls import RotaryLogger
from rotary_logger.tee_stream import TeeStream
from rotary_logger.file_instance import FileInstance
from rotary_logger import constants as CONST


def test_merged_uses_same_instance(tmp_path: Path) -> None:
    parent = tmp_path
    # Instead of invoking RotaryLogger.start_logging (which opens a
    # directory path), construct a shared FileInstance pointing to a file
    # path and create two TeeStream wrappers that share it.
    shared_file = parent / 'merged.log'
    mixed_inst = FileInstance(shared_file, merged=True)
    ts_out = TeeStream(mixed_inst, sys.stdout, mode=CONST.StdMode.STDOUT)
    ts_err = TeeStream(mixed_inst, sys.stderr, mode=CONST.StdMode.STDERR)
    # distinct stream objects but same underlying FileInstance
    assert id(ts_out) != id(ts_err)
    assert getattr(ts_out, "file_instance", None) is getattr(
        ts_err, "file_instance", None)


def test_split_uses_different_instances(tmp_path: Path) -> None:
    parent = tmp_path
    # Construct two separate FileInstance objects that point to different
    # file paths and wrap them in TeeStream instances.
    out_file = parent / 'out.log'
    err_file = parent / 'err.log'
    out_inst = FileInstance(out_file, merged=False)
    err_inst = FileInstance(err_file, merged=False)
    ts_out = TeeStream(out_inst, sys.stdout, mode=CONST.StdMode.STDOUT)
    ts_err = TeeStream(err_inst, sys.stderr, mode=CONST.StdMode.STDERR)
    assert id(ts_out) != id(ts_err)
    assert getattr(ts_out, "file_instance", None) is not getattr(
        ts_err, "file_instance", None)
