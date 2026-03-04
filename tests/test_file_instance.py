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
# LAST Modified: 3:42:18 04-03-2026
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


def test_file_instance_log_to_file_false_suppresses_write(tmp_path: Path) -> None:
    """When log_to_file=False, no file should be created even after writing."""
    log_path = tmp_path / 'should_not_exist.log'
    fi = FileInstance(log_path, log_to_file=False)
    fi.write('this should not be written to disk\n')
    fi.flush()
    assert not log_path.exists(), "File must not be created when log_to_file=False"


def test_file_instance_copy_is_independent(tmp_path: Path) -> None:
    """copy() should return a new instance with identical configuration but no shared state."""
    fi = FileInstance(None, encoding='utf-16', merged=False)
    fi.set_merge_stdin(True)
    copy = fi.copy()
    assert copy is not fi
    assert copy.get_encoding() == 'utf-16'
    assert copy.get_merged() is False
    assert copy.get_merge_stdin() is True
    # Mutating the copy must not affect the original
    copy.set_encoding('utf-8')
    assert fi.get_encoding() == 'utf-16'


def test_file_instance_update_copies_config(tmp_path: Path) -> None:
    """update() should copy all configuration fields from the source instance."""
    src = FileInstance(None, encoding='latin-1', merged=False)
    src.set_merge_stdin(True)
    dst = FileInstance(None)
    dst.update(src)
    assert dst.get_encoding() == 'latin-1'
    assert dst.get_merged() is False
    assert dst.get_merge_stdin() is True


def test_file_instance_set_get_merge_stdin() -> None:
    """set_merge_stdin / get_merge_stdin round-trip should be consistent."""
    fi = FileInstance(None)
    assert fi.get_merge_stdin() is False  # default
    fi.set_merge_stdin(True)
    assert fi.get_merge_stdin() is True
    fi.set_merge_stdin(False)
    assert fi.get_merge_stdin() is False
