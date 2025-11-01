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
# LAST Modified: 4:31:14 01-11-2025
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
