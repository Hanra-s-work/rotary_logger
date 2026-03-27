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
# LAST Modified: 1:31:47 27-03-2026
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

        log_function_calls_stdin = False
        log_function_calls_stdout = False
        log_function_calls_stderr = False
        program_log = False
        program_debug_log = False
        if self.args.verbose is True:
            log_function_calls_stdin = True
            log_function_calls_stdout = True
            log_function_calls_stderr = True
            program_log = True
            program_debug_log = True

        # Create and configure the logger. We do not start file logging here;
        # the `run()` method will only call `start_logging()` when a folder
        # or positional file argument was provided (matching traditional `tee`
        # behaviour where no files => no file output).
        self.rotary_logger: RotaryLogger = RotaryLogger(
            log_to_file=False,
            override=not self.args.append,
            merge_streams=self.args.merge,
            merge_stdin=self.args.merge_stdin,
            capture_stdin=self.args.capture_stdin,
            capture_stdout=self.args.capture_stdout,
            capture_stderr=self.args.capture_stderr,
            prefix_in_stream=self.args.prefix_in,
            prefix_out_stream=self.args.prefix_out,
            prefix_err_stream=self.args.prefix_err,
            log_function_calls_stdin=log_function_calls_stdin,
            log_function_calls_stdout=log_function_calls_stdout,
            log_function_calls_stderr=log_function_calls_stderr,
            program_log=program_log,
            program_debug_log=program_debug_log,
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
            "-mi", "--merge-stdin", action="store_true",
            help="Merge stdin into the same file as stdout and stderr"
        )
        parser.add_argument(
            "-i", "--ignore-interrupts", action="store_true",
            help="Ignore Ctrl+C (SIGINT)"
        )
        parser.add_argument(
            "-s", "--max-size", type=int, default=None,
            help="Maximum log file size in MB before rotation"
        )
        parser.add_argument(
            "-V", "--verbose", action="store_true",
            help="Activate all debug logging options of the program"
        )
        # Additional options to control folder behaviour and prefixes
        parser.add_argument(
            "--log-folder", "-F", dest="log_folder", default=None,
            help="Destination log folder (when omitted no file logging will occur)"
        )
        parser.add_argument(
            "--create-folder", action="store_true", dest="create_folder", default=False,
            help="Create the log folder if it does not exist (use with --log-folder or positional file)",
        )

        # Prefix toggles: disabled by default; use `--prefix-*` to enable
        parser.set_defaults(
            prefix_in=False, prefix_out=False, prefix_err=False)
        parser.add_argument(
            "--prefix-stdin", dest="prefix_in", action="store_true",
            help="Prepend STDIN label to logged stdin entries"
        )
        parser.add_argument(
            "--prefix-stdout", dest="prefix_out", action="store_true",
            help="Prepend STDOUT label to logged stdout entries"
        )
        parser.add_argument(
            "--prefix-stderr", dest="prefix_err", action="store_true",
            help="Prepend STDERR label to logged stderr entries"
        )

        # Capture toggles: stdin capture is opt-in; stdout/stderr captured by default
        parser.set_defaults(capture_stdout=True,
                            capture_stderr=True, capture_stdin=False)
        parser.add_argument(
            "--capture-stdin", dest="capture_stdin", action="store_true",
            help="Capture stdin (wrap sys.stdin)"
        )
        parser.add_argument(
            "--no-capture-stdout", dest="capture_stdout", action="store_false",
            help="Do not capture stdout"
        )
        parser.add_argument(
            "--no-capture-stderr", dest="capture_stderr", action="store_false",
            help="Do not capture stderr"
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
        # Determine whether file logging is requested. Behavior:
        # - If `--log-folder` was provided, use it.
        # - Else if a positional file was provided, use the first one.
        # - Otherwise, do not enable file logging (matches `tee`).
        if self.args.log_folder:
            _log_to_file = True
            _log_folder = Path(self.args.log_folder)
        elif self.args.files:
            _log_to_file = True
            if len(self.args.files) > 1:
                try:
                    sys.stderr.write(
                        f"{CONST.MODULE_NAME} Multiple destination files provided; using first: {self.args.files[0]}\n"
                    )
                except OSError:
                    pass
            _log_folder = Path(self.args.files[0])
        else:
            _log_to_file = False
            _log_folder = None

        # If a folder was requested but does not exist, either create it
        # (when --create-folder) or warn and disable file logging.
        if _log_to_file and _log_folder is not None and not _log_folder.exists():
            if self.args.create_folder:
                try:
                    _log_folder.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    try:
                        sys.stderr.write(
                            f"{CONST.MODULE_NAME} Could not create log folder: {_log_folder} -> {e}\n")
                    except OSError:
                        pass
                    _log_to_file = False
                    _log_folder = None
            else:
                try:
                    sys.stderr.write(
                        f"{CONST.MODULE_NAME} Log folder does not exist: {_log_folder}. Use --create-folder to create it. File logging disabled.\n"
                    )
                except OSError:
                    pass
                _log_to_file = False
                _log_folder = None

        # Only start file logging when explicitly requested.
        if _log_to_file:
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
