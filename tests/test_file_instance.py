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
# FILE: test_file_instance.py
# CREATION DATE: 01-11-2025
# LAST Modified: 4:29:56 01-11-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the set of tests in charge of making sure the file_instance class works as expected.
# // AR
# +==== END rotary_logger =================+
"""
from pathlib import Path

from rotary_logger.file_instance import FileInstance


def _find_log_file(root: Path):
    logs = list(root.rglob('*.log'))
    if not logs:
        return None
    return logs[0]


def test_file_instance_write_and_flush(tmp_path: Path) -> None:
    # Use a file path (with .log suffix) to avoid the library opening a
    # directory path which can result in inconsistent behaviour.
    root = tmp_path / 'logs.log'
    fi = FileInstance(root, max_size_mb=1)
    try:
        fi.write('hello file_instance\n')
        fi.flush()
        logfile = _find_log_file(tmp_path)
        assert logfile is not None, 'No .log file created by FileInstance'
        content = logfile.read_text(encoding=fi.get_encoding())
        assert 'hello file_instance' in content
    finally:
        # best-effort cleanup
        try:
            if fi and fi.get_filepath():
                fp = fi.get_filepath()
                if fp and getattr(fp, 'descriptor', None):
                    try:
                        fp.descriptor.close()
                    except Exception:
                        pass
        except Exception:
            pass


def test_file_instance_defaults(tmp_path: Path) -> None:
    fi = FileInstance(None)
    # ensure getters return sane defaults
    assert fi.get_encoding() is not None
    assert fi.get_flush_size() > 0
    assert fi.get_max_size() > 0
