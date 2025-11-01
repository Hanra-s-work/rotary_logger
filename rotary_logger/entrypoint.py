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
# FILE: entrypoint.py
# CREATION DATE: 29-10-2025
# LAST Modified: 0:55:31 30-10-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the code that will be called when the module is called as a program more than a library.
# // AR
# +==== END rotary_logger =================+
"""
import signal

try:
    from . import constants as CONST
    from .rotary_logger import RotaryLogger
except ImportError:
    import constants as CONST
    from rotary_logger import RotaryLogger


class Tee:
    def __init__(
        self,
        override: bool = True,
        ignore_interrupts: bool = False,
        output_error: CONST.ErrorMode = CONST.ErrorMode.WARN_NO_PIPE
    ) -> None:
        self.override: bool = override
        self.ignore_interrupts: bool = ignore_interrupts
        self.output_error: CONST.ErrorMode = output_error
        self._handle_interrupts_if_required()
        self.rotary_logger: RotaryLogger = RotaryLogger(
            log_to_file=True,
            override=self.override,
        )

    def _handle_interrupts_if_required(self) -> None:
        if self.ignore_interrupts:
            signal.signal(signal.SIGINT, signal.SIG_IGN)

    def _pipe_check(self) -> None:
        if self.output_error == CONST.ErrorMode.WARN_NO_PIPE and CONST.IS_PIPE:
            return
