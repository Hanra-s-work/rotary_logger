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
# LAST Modified: 18:12:28 03-03-2026
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
from pathlib import Path

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
        """Initialise the entrypoint helper and configure the logger.

        Parses CLI arguments, installs the SIGINT handler when requested,
        and creates the underlying RotaryLogger instance.

        Keyword Arguments:
            output_error (CONST.ErrorMode): Policy for handling broken-pipe or stdout errors. Default: CONST.ErrorMode.WARN_NO_PIPE
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
        """Parse command-line arguments for the tee entrypoint.

        Returns:
            The populated argparse.Namespace with the parsed arguments.
        """
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
        """Ignore SIGINT (KeyboardInterrupt) when configured to do so.

        Installs a SIG_IGN handler for SIGINT when the --ignore-interrupts
        flag was passed on the command line. This is a no-op when interrupts
        should be processed normally.
        """
        if self.args.ignore_interrupts:
            signal.signal(signal.SIGINT, signal.SIG_IGN)

    def _pipe_check(self) -> None:
        """Apply the configured broken-pipe error policy.

        Writes a warning to stderr or exits the process depending on the
        value of self.output_error and whether stdout is currently a pipe.
        """
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
        """Start logging and run the main stdin-to-stdout forwarding loop.

        Behaves like UNIX tee: reads lines from stdin, prints them to
        stdout (which is wrapped by RotaryLogger), and mirrors everything
        to the configured log folder. Handles BrokenPipeError per the
        configured error policy and KeyboardInterrupt when interrupts are
        not suppressed.
        """
        # Determine whether file logging is requested and normalise the
        # provided files argument into a single Path (or None). The
        # argparse `files` is a list (nargs='*'), so map it to a Path if
        # present; if multiple paths are provided, use the first and warn.
        if not self.args.files:
            _log_to_file = False
            _log_folder = None
        else:
            _log_to_file = True
            if len(self.args.files) > 1:
                # Prefer the first provided argument but notify the user.
                try:
                    sys.stderr.write(
                        f"{CONST.MODULE_NAME} Multiple destination files provided; using first: {self.args.files[0]}\n"
                    )
                except OSError:
                    pass
            _log_folder = Path(self.args.files[0])

        self.rotary_logger.start_logging(
            log_folder=_log_folder,
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
    """CLI entrypoint: create a Tee instance and run the forwarding loop."""
    Tee().run()


if __name__ == "__main__":
    main()
