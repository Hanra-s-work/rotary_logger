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
# LAST Modified: 8:55:33 01-11-2025
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
    from .rotary_logger_cls import RotaryLogger
except ImportError:
    import constants as CONST
    from rotary_logger_cls import RotaryLogger


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
        output_error: CONST.ErrorMode = CONST.ErrorMode.WARN_NO_PIPE
    ) -> None:
        """Create the entrypoint helper and initialise the logger.

        Args:
            override: When True, log files are opened in overwrite mode.
            ignore_interrupts: When True, SIGINT (Ctrl-C) is ignored.
            output_error: Policy for handling broken-pipe / stdout errors.
        """
        self.output_error: CONST.ErrorMode = output_error
        self.args = self._parse_args()
        self._handle_interrupts_if_required()

        # Create and configure the logger
        # Create and configure the high-level RotaryLogger instance
        self.rotary_logger: RotaryLogger = RotaryLogger(
            log_to_file=True,
            override=not self.args.append,
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
            "-a", "--append", action="store_true",
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
        """Handle broken-pipe policy."""
        if self.output_error == CONST.ErrorMode.WARN:
            sys.stderr.write(CONST.BROKEN_PIPE_ERROR)
        elif self.output_error == CONST.ErrorMode.EXIT:
            sys.exit(CONST.ERROR)
        elif self.output_error in (CONST.ErrorMode.WARN_NO_PIPE, CONST.ErrorMode.EXIT_NO_PIPE):
            if not CONST.IS_PIPE:
                if "WARN" in self.output_error.value:
                    sys.stderr.write(CONST.BROKEN_PIPE_ERROR)
                else:
                    sys.exit(CONST.ERROR)

    def run(self):
        """Main execution loop (like UNIX `tee`)."""
        _log_to_file = True
        if self.args.files is None:
            _log_to_file = False
        self.rotary_logger.start_logging(
            log_folder=self.args.files or None,
            max_filesize=self.args.max_size,
            merged=self.args.merge,
            log_to_file=_log_to_file
        )

        try:
            for line in sys.stdin:
                try:
                    print(line, end="")
                except BrokenPipeError:
                    self._pipe_check()
                    break
        except KeyboardInterrupt:
            if not self.args.ignore_interrupts:
                raise
        finally:
            sys.stdout.flush()
            sys.stderr.flush()


def main():
    Tee().run()


if __name__ == "__main__":
    main()
