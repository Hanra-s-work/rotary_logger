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
# FILE: test_constants.py
# CREATION DATE: 01-11-2025
# LAST Modified: 3:42:4 04-03-2026
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the file in charge of testing the critical variables of the constants file to make sure that they are still accurate.
# // AR
# +==== END rotary_logger =================+
"""
from rotary_logger import constants as CONST


def test_size_constants() -> None:
    # basic sanity of size constants
    assert CONST.KB1 == 1024
    assert CONST.MB1 == 1024 * 1024
    assert CONST.GB1 == CONST.MB1 * CONST.KB1


def test_default_values() -> None:
    assert isinstance(CONST.DEFAULT_ENCODING, str)
    assert CONST.DEFAULT_ENCODING.lower() == 'utf-8'
    assert CONST.LOG_FOLDER_BASE_NAME == 'logs'


def test_prefix_and_enum_mappings() -> None:
    # prefix mappings should contain entries for each StdMode
    for mode in CONST.StdMode:
        assert mode in CONST.CORRECT_PREFIX
    # check correct string for a known entry
    assert CONST.CORRECT_PREFIX[CONST.StdMode.STDOUT] == CONST.PREFIX_STDOUT


def test_correct_folder_all_modes() -> None:
    """CORRECT_FOLDER should have an entry for every StdMode value."""
    for mode in CONST.StdMode:
        assert mode in CONST.CORRECT_FOLDER, f"Missing CORRECT_FOLDER entry for {mode!r}"
    assert CONST.CORRECT_FOLDER[CONST.StdMode.STDOUT] == CONST.FOLDER_STDOUT
    assert CONST.CORRECT_FOLDER[CONST.StdMode.STDERR] == CONST.FOLDER_STDERR
    assert CONST.CORRECT_FOLDER[CONST.StdMode.STDIN] == CONST.FOLDER_STDIN


def test_error_mode_members() -> None:
    """ErrorMode should expose all four policy variants."""
    members = {m.name for m in CONST.ErrorMode}
    assert 'WARN' in members
    assert 'WARN_NO_PIPE' in members
    assert 'EXIT' in members
    assert 'EXIT_NO_PIPE' in members


def test_prefix_function_call_members() -> None:
    """PrefixFunctionCall should include EMPTY and all I/O method tags."""
    names = {m.name for m in CONST.PrefixFunctionCall}
    for expected in ('EMPTY', 'WRITE', 'WRITELINES', 'FLUSH', 'READ', 'READLINE', 'READLINES'):
        assert expected in names, f"Missing PrefixFunctionCall member: {expected}"


def test_file_stream_instances_default_all_false() -> None:
    """A freshly created FileStreamInstances should report all streams unmerged."""
    fsi = CONST.FileStreamInstances()
    for mode in CONST.StdMode:
        assert fsi.merged_streams.get(mode, None) is False, (
            f"Expected merged_streams[{mode!r}] to be False by default"
        )


def test_file_stream_instances_dict_isolation() -> None:
    """Two FileStreamInstances must not share the same merged_streams dict."""
    fsi_a = CONST.FileStreamInstances()
    fsi_b = CONST.FileStreamInstances()
    fsi_a.merged_streams[CONST.StdMode.STDOUT] = True
    assert fsi_b.merged_streams[CONST.StdMode.STDOUT] is False, (
        "Mutating fsi_a.merged_streams should not affect fsi_b (shared mutable default)"
    )
