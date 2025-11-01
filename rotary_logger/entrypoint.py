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
# LAST Modified: 7:29:41 01-11-2025
# DESCRIPTION:
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: This is the code that will be called when the module is called as a program more than a library.
# // AR
# +==== END rotary_logger =================+
"""
import sys
import signal
import argparse

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
        self.args = self._parse_args()
        self._handle_interrupts_if_required()

        # Create and configure the logger
        # Create and configure the high-level RotaryLogger instance
        self.rotary_logger: RotaryLogger = RotaryLogger(
            log_to_file=True,
            override=self.args.overwrite,
            merge_streams=self.args.merge,
        )

    def _parse_args(self):
        parser = argparse.ArgumentParser(
            description="Python-powered tee replacement with rotation"
        )
        parser.add_argument(
            "files", nargs="*", help="Destination log files (defaults to rotary_logger folder)"
        )
        parser.add_argument(
            "-a", "--append", dest="overwrite", action="store_false",
            help="Append to the output files instead of overwriting"
        )
        parser.add_argument(
            "-m", "--merge", action="store_true",
            help="Merge stdout and stderr into a single log file"
        )
        parser.add_argument(
            "-i", "--ignore-interrupts", action="store_true",
            help="Ignore Ctrl+C (SIGINT)"
        )
        parser.add_argument(
            "-s", "--max-size", type=int, default=None,
            help="Maximum log file size in MB before rotation"
        )
        return parser.parse_args()

    def _handle_interrupts_if_required(self) -> None:
        """Ignore SIGINT (KeyboardInterrupt) when configured.

        When `self.ignore_interrupts` is truthy this method installs a
        signal handler that ignores SIGINT. This is called during
        initialization and is a no-op when interrupts should be
        processed normally.
        """
        if self.args.ignore_interrupts:
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

    def run(self):
        """Main execution loop (like the UNIX tee)."""
        self.rotary_logger.start_logging(
            log_folder=None,
            max_filesize=self.args.max_size,
            merged=self.args.merge
        )

        try:
            for line in sys.stdin:
                # This goes to both terminal and log file
                print(line, end="")
        except KeyboardInterrupt:
            if not self.args.ignore_interrupts:
                raise


def main():
    Tee().run()


if __name__ == "__main__":
    main()
