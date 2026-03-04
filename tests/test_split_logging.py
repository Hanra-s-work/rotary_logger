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
# LAST Modified: 3:42:31 04-03-2026
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


def test_merge_stdin_true_shares_instance_with_stdout_stderr(tmp_path: Path) -> None:
    """When merged=True and merge_stdin=True, stdin FileInstance must be the same object as stdout."""
    from rotary_logger.rotary_logger_cls import RotaryLogger
    rl = RotaryLogger(merge_stdin=True)
    rl.start_logging(log_folder=tmp_path, merged=True,
                     merge_stdin=True, log_to_file=False)
    try:
        assert rl.stdin_stream is not None
        assert rl.stdout_stream is not None
        assert rl.stdin_stream.file_instance is rl.stdout_stream.file_instance
    finally:
        rl.stop_logging()


def test_log_function_calls_prefix_appears_in_log(tmp_path: Path) -> None:
    """With log_function_calls=True the [WRITE] prefix should appear in the log file."""
    import io
    log_file = tmp_path / 'prefixed.log'
    orig = io.StringIO()
    ts = TeeStream(
        FileInstance(log_file, max_size_mb=1),
        orig,
        mode=CONST.StdMode.STDOUT,
        log_function_calls=True
    )
    ts.write('tagged line\n')
    ts.flush()
    logfile = next(tmp_path.rglob('*.log'), None)
    assert logfile is not None, 'No log file created'
    content = logfile.read_text(encoding='utf-8')
    assert CONST.PREFIX_FUNCTION_CALL_WRITE in content, (
        f'Expected {CONST.PREFIX_FUNCTION_CALL_WRITE!r} prefix in log, got: {content!r}'
    )
