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
# LAST Modified: 9:14:12 01-11-20255
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the file that python reads when you do import rotary_logger or from rotary_logger import <component from the module>
# // AR
# +==== END rotary_logger =================+
"""

try:
    from rotary_logger.entrypoint import Tee
    from rotary_logger.rotary_logger_cls import RotaryLogger
    from rotary_logger.tee_stream import TeeStream
    from rotary_logger.file_instance import FileInstance
    from rotary_logger import constants as CONST
except ImportError:
    try:
        from .entrypoint import Tee
        from .rotary_logger_cls import RotaryLogger
        from .tee_stream import TeeStream
        from .file_instance import FileInstance
        from . import constants as CONST
    except ImportError:
        try:
            from entrypoint import Tee
            from rotary_logger_cls import RotaryLogger
            from tee_stream import TeeStream
            from file_instance import FileInstance
            import constants as CONST
        except ImportError as e:
            raise RuntimeError("Failed to import required dependencies") from e

__all__ = [
    "Tee",
    "RotaryLogger",
    "TeeStream",
    "FileInstance",
    "CONST"
]
