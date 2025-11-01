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
# LAST Modified: 4:31:57 01-11-2025
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
