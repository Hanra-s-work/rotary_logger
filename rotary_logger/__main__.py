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
# FILE: __main__.py
# CREATION DATE: 29-10-2025
# LAST Modified: 7:51:1 01-11-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This file is the one called by python when you run the library as an executable (via python -m rotary_logger)
# // AR
# +==== END rotary_logger =================+
"""
try:
    from rotary_logger.entrypoint import main
except ImportError:
    try:
        from .entrypoint import main
    except ImportError:
        try:
            from entrypoint import main
        except ImportError as e:
            raise RuntimeError(
                "Failed to import 'main' from the entrypoint file.") from e

if __name__ == "__main__":
    main()
