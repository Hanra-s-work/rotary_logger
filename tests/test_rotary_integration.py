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
# FILE: test_rotary_integration.py
# CREATION DATE: 01-11-2025
# LAST Modified: 3:44:19 04-03-2026
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the file in charge of making sure that the Rotary logger class works and does what is expected of it.
# // AR
# +==== END rotary_logger =================+
"""
import sys
import shutil
from pathlib import Path

from rotary_logger.rotary_logger_cls import RotaryLogger


def test_start_logging_wires_and_writes(tmp_path: Path) -> None:
    parent = tmp_path
    # Construct a FileInstance-backed TeeStream and write to it to verify
    # that the wiring results in log files being created.
    from rotary_logger.file_instance import FileInstance
    from rotary_logger.tee_stream import TeeStream

    orig = sys.stdout
    try:
        fi = FileInstance(parent / 'logs.log', max_size_mb=1)
        ts = TeeStream(fi, orig)
        ts.write('integration test line\n')
        ts.flush()
        logs = list(parent.rglob('*.log'))
        assert logs, 'No logs created by TeeStream/FileInstance'
        content = logs[0].read_text(
            encoding=fi.get_encoding(), errors='ignore')
        assert 'integration test line' in content
    finally:
        try:
            shutil.rmtree(parent)
        except Exception:
            pass


def test_destructor_safe_on_closed_files(tmp_path: Path) -> None:
    root = tmp_path / 'logs'
    # Create and immediately close underlying streams to simulate shutdown
    import io
    import gc
    orig = io.StringIO()
    # create a TeeStream directly to test destructor
    from rotary_logger.tee_stream import TeeStream
    ts = TeeStream(root, orig, max_size_mb=1)
    # close underlying file descriptor (best-effort) and original stream
    try:
        fi = getattr(ts, "file_instance", None)
        if fi and fi.file and getattr(fi.file, "descriptor", None):
            try:
                fi.file.descriptor.close()
            except Exception:
                pass
    except Exception:
        pass
    orig.close()
    # deleting ts should not raise; collect to trigger __del__
    del ts
    gc.collect()


def test_log_to_file_false_writes_no_content(tmp_path: Path) -> None:
    """With log_to_file=False, no content should be written to any log file."""
    SENTINEL = "SENTINEL_MUST_NOT_APPEAR_IN_LOG_XYZ"
    rl = RotaryLogger()
    orig_out = sys.stdout
    orig_err = sys.stderr
    try:
        rl.start_logging(log_folder=tmp_path, merged=True, log_to_file=False)
        sys.stdout.write(f"{SENTINEL}\n")
        try:
            sys.stdout.flush()
        except Exception:
            pass
    finally:
        sys.stdout = orig_out
        sys.stderr = orig_err

    for log_file in tmp_path.rglob("*.log"):
        content = log_file.read_text(encoding="utf-8", errors="ignore")
        assert SENTINEL not in content, (
            f"Sentinel unexpectedly logged to {log_file} when log_to_file=False"
        )


def test_stdout_prefix_appears_in_log(tmp_path: Path) -> None:
    """When prefix_out_stream=True the [STDOUT] prefix should appear in the log."""
    from rotary_logger import constants as CONST

    rl = RotaryLogger(prefix_out_stream=True)
    orig_out = sys.stdout
    orig_err = sys.stderr
    try:
        rl.start_logging(log_folder=tmp_path, merged=True, log_to_file=True)
        sys.stdout.write("prefixed line\n")
        try:
            sys.stdout.flush()
        except Exception:
            pass
    finally:
        sys.stdout = orig_out
        sys.stderr = orig_err

    log_files = list(tmp_path.rglob("*.log"))
    assert log_files, "No log file was created"
    content = log_files[0].read_text(encoding="utf-8")
    assert CONST.PREFIX_STDOUT in content, (
        f"Expected {CONST.PREFIX_STDOUT!r} in log, got: {content!r}"
    )
