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
# LAST Modified: 5:12:26 01-11-2025
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
    """Small helper used when running the package as a CLI entrypoint.

    This convenience class wraps creation of a `RotaryLogger` when the
    package is executed as a program (it mirrors behaviour of the
    standalone `rotary` command). It also provides small runtime
    configuration points such as whether to override existing logs,
    to ignore keyboard interrupts, and which broken-pipe handling
    policy to use.
    """

    def __init__(
        self,
        override: bool = True,
        ignore_interrupts: bool = False,
        output_error: CONST.ErrorMode = CONST.ErrorMode.WARN_NO_PIPE
    ) -> None:
        """Create the entrypoint helper and initialise the logger.

        Args:
            override: When True, log files are opened in overwrite mode.
            ignore_interrupts: When True, SIGINT (Ctrl-C) is ignored.
            output_error: Policy for handling broken-pipe / stdout errors.
        """
        self.override: bool = override
        self.ignore_interrupts: bool = ignore_interrupts
        self.output_error: CONST.ErrorMode = output_error
        # Apply runtime signal handling if requested
        self._handle_interrupts_if_required()
        # Create and configure the high-level RotaryLogger instance
        self.rotary_logger: RotaryLogger = RotaryLogger(
            log_to_file=True,
            override=self.override,
        )

    def _handle_interrupts_if_required(self) -> None:
        """Ignore SIGINT (KeyboardInterrupt) when configured.

        When `self.ignore_interrupts` is truthy this method installs a
        signal handler that ignores SIGINT. This is called during
        initialization and is a no-op when interrupts should be
        processed normally.
        """
        if self.ignore_interrupts:
            signal.signal(signal.SIGINT, signal.SIG_IGN)

    def _pipe_check(self) -> None:
        """Perform a minimal output-mode check for broken-pipe handling.

        The library supports different error handling policies (see
        `CONST.ErrorMode`). This helper enforces policy variants that
        are no-ops when stdout/stderr are pipes. Currently it simply
        returns when the configured `output_error` indicates a "warn
        but only when not a pipe" policy and the process is running
        with a pipe attached.
        """
        if self.output_error == CONST.ErrorMode.WARN_NO_PIPE and CONST.IS_PIPE:
            return
