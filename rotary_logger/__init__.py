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
# FILE: __init__.py
# CREATION DATE: 29-10-2025
# LAST Modified: 23:31:11 29-10-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the file that python reads when you do import rotary_logger or from rotary_logger import <component from the module>
# // AR
# +==== END rotary_logger =================+
"""


from rotary_logger.rotary_logger import RotaryLogger
from rotary_logger.tee_stream import TeeStream

__all__ = [
    "RotaryLogger",
    "TeeStream"
]
