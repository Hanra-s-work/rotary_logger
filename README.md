# rotary_logger
<!-- 
-- +==== BEGIN rotary_logger =================+
-- LOGO: 
-- ..........####...####..........
-- ......###.....#.#########......
-- ....##........#.###########....
-- ...#..........#.############...
-- ...#..........#.#####.######...
-- ..#.....##....#.###..#...####..
-- .#.....#.##...#.##..##########.
-- #.....##########....##...######
-- #.....#...##..#.##..####.######
-- .#...##....##.#.##..###..#####.
-- ..#.##......#.#.####...######..
-- ..#...........#.#############..
-- ..#...........#.#############..
-- ...##.........#.############...
-- ......#.......#.#########......
-- .......#......#.########.......
-- .........#####...#####.........
-- /STOP
-- PROJECT: rotary_logger
-- FILE: README.md
-- LAST Modified: 3:29:36 04-03-2026
-- LAST Modified: 5:3:14 02-11-2025
-- DESCRIPTION: 
-- A module that provides a universal python light on iops way of logging to files your program execution.
-- /STOP
-- COPYRIGHT: (c) Asperguide
-- PURPOSE: This is the readme of the project, an explanation of the aim of the project as well as how to set it up or contribute.
-- // AR
-- +==== END rotary_logger =================+
-->
![Rotary Logger logo](doxygen_generation/html/files/icon/favicon.svg)

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rotary_logger)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/rotary_logger)
![PyPI - Wheel](https://img.shields.io/pypi/wheel/rotary_logger)
![PyPI - Version](https://img.shields.io/pypi/v/rotary_logger?label=pypi%20package:%20rotary_logger)
![PyPI - Downloads](https://img.shields.io/pypi/dm/rotary_logger)
![PyPI - License](https://img.shields.io/pypi/l/rotary_logger)
![Execution status](https://github.com/Hanra-s-work/rotary_logger/actions/workflows/run_unit_tests.yaml/badge.svg)
![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/Hanra-s-work/rotary_logger/run_unit_tests.yaml)
![GitHub repo size](https://img.shields.io/github/repo-size/Hanra-s-work/rotary_logger)
![GitHub Repo stars](https://img.shields.io/github/stars/Hanra-s-work/rotary_logger)
![GitHub commit activity (branch)](https://img.shields.io/github/commit-activity/m/Hanra-s-work/rotary_logger)
![GitHub last commit (branch)](https://img.shields.io/github/last-commit/Hanra-s-work/rotary_logger/main)

[![Static Badge](https://img.shields.io/badge/Buy_me_a_tea-Hanra-%235F7FFF?style=flat-square&logo=buymeacoffee&label=Buy%20me%20a%20coffee&labelColor=%235F7FFF&color=%23FFDD00&link=https%3A%2F%2Fwww.buymeacoffee.com%2Fhanra)](https://www.buymeacoffee.com/hanra)

## Table of contents

- [Features](#features)
- [Installation](#installation)
- [Quickstart](#quickstart)
  - [CLI](#cli)
  - [Library usage](#library-usage)
- [Configuration & options](#configuration--options)
- [Running tests](#running-tests)
- [Development notes](#development-notes)
- [Documentation (Doxygen)](#documentation-doxygen)
- [Contributing](#contributing)
- [License](#license)

## Features

- Mirror stdout, stderr, and optionally stdin into rotating log files
- Optionally merge all streams into a single file or keep them split into separate per-stream subfolders (`stdout/`, `stderr/`, `stdin/`)
- Configurable log-line prefixes per stream (e.g. `[STDOUT]`, `[STDERR]`, `[STDIN]`) and optional per-call function tracing (e.g. `[WRITE]`, `[READLINE]`)
- Low-IO buffered writes using a swap-buffer flush strategy (configurable flush threshold, default 8 KB)
- Automatic log file rotation when a file exceeds a configurable size (default 2 GB)
- Log folder organised by date: `<root>/logs/<year>/<month>/<day>/[<stream>/]<timestamp>.log`
- Runtime configurable text encoding (default `utf-8`)
- Safe concurrent use (per-object `RLock`; see developer notes on lock ordering)
- Runtime environment variable overrides for log folder, file toggle, and max size (see [Environment variables](#environment-variables))

## Installation

From PyPI (when published):

```bash
pip install rotary_logger
```

From source (recommended for development):

```bash
git clone https://github.com/Hanra-s-work/rotary_logger.git
cd rotary_logger
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

If you only need the package without dev dependencies:

```bash
pip install -e .
```

## Quickstart

### CLI

You can use the package as a CLI similar to `tee`:

```bash
echo "hello" | python -m rotary_logger my_log_folder
```

You can also use the shortcut: `pytee`.

It works similarly to `python -m rotary_logger`.

The positional argument is the **base folder** where logs will be stored. The package always builds the rest of the path automatically in the following way: `path/to/folder/year/month/day/`. If you pass `-m` (`--merge`), all streams are written to timestamped files directly under the day folder; otherwise two subfolders `stdout/` and `stderr/` are created, each containing their own timestamped files.

If multiple destination folders are passed, only the first is used and a warning is printed to stderr.

### Library usage

Embed RotaryLogger in your application:

```python
from pathlib import Path
from rotary_logger import RotaryLogger, RL_CONST

_path_to_store_the_log: Path = Path('/var/log/myapp')

RL = RotaryLogger(
 log_to_file=True,
 override=False,
 default_max_filesize=(2*RL_CONST.GB1),
 merge_streams=False # Set to True if you want your stdout and stderr to be put into the same file instead of seperate.
)
RL.start_logging(log_folder=_path_to_store_the_log, merged=False)
```

This replaces `sys.stdout` and `sys.stderr` with `TeeStream` wrappers. To stop logging in-process call `RL.stop_logging()` — this restores the original streams, flushes any buffered data, and unregisters the atexit flush handlers.

## Public API exports

The following symbols are exported from the top-level `rotary_logger` package:

```python
from rotary_logger import RotaryLogger  # main high-level class
from rotary_logger import Tee           # CLI entrypoint wrapper
from rotary_logger import TeeStream     # low-level stream mirror
from rotary_logger import FileInstance  # buffered file writer / rotator
from rotary_logger import RL_CONST      # package constants (GB1, MB1, StdMode, …)
```

## Documentation

You can find documentation here: [docs](./docs_input/) as well as here: [https://hanra-s-work.github.io/rotary_logger/](https://hanra-s-work.github.io/rotary_logger/)

## Logo source

The source of the logo used in the documentation: [https://deepai.org](https://deepai.org), then edited in gimp.

## Configuration & options

### Common CLI options

| Flag | Long form | Description |
|---|---|---|
| (positional) | `files` | Base folder for log output (optional; disables file logging when omitted) |
| `-a` | `--append` | Append to existing log files instead of overwriting |
| `-m` | `--merge` | Merge stdout and stderr into a single log file |
| `-i` | `--ignore-interrupts` | Ignore Ctrl+C (SIGINT) |
| `-s N` | `--max-size N` | Maximum log file size in MB before rotation |

### Library API (short)

- `RotaryLogger(log_to_file, override, raw_log_folder, default_log_folder, default_max_filesize, merge_streams, *, encoding, merge_stdin, capture_stdin, capture_stdout, capture_stderr, prefix_in_stream, prefix_out_stream, prefix_err_stream, log_function_calls_stdin, log_function_calls_stdout, log_function_calls_stderr)` — constructor; does not start logging
- `RotaryLogger.start_logging(*, log_folder=None, max_filesize=None, merged=None, log_to_file=True, merge_stdin=None)` — begin capturing and rotating logs

Refer to the module docs (or docstrings) for full API details.

## Running tests

The project uses pytest. From the repository root (inside your `virtualenv`):

```bash
pip install -r requirements.txt
pytest -q
```

To run the CI-like test harness used during development, use `action_test.sh` (requires Docker):

```bash
./action_test.sh
```

## Development notes

- Locking: the code uses per-object `threading.RLock` instances. The recommended pattern is to snapshot minimal state while holding the lock, release the lock to perform blocking I/O, then re-acquire to commit state. This avoids holding locks during filesystem operations.
- By default, logs are written under the `logs/` folder inside the package directory unless a `log_folder` is supplied.

## Control functions (library API)

RotaryLogger exposes a small set of control functions to manage in-process log capturing. These are safe to call from multiple threads, but there are a few rules and guarantees to understand:

- `start_logging(*, log_folder=None, max_filesize=None, merged=None, log_to_file=True, merge_stdin=None) -> None`
  - Start redirecting `sys.stdout` and `sys.stderr` to `TeeStream` wrappers and begin writing to rotating files.
  - Parameters: `log_folder` — optional base folder to write logs; `max_filesize` — override rotation size in MB; `merged` — whether to merge stdout/stderr into a single file; `log_to_file` — whether to enable file writes; `merge_stdin` — whether stdin is merged into the shared file.
  - Thread-safety: the function snapshots configuration under an internal lock and performs filesystem checks outside the lock; assignment of `sys.stdout`/`sys.stderr` is performed atomically while holding the lock.

- `stop_logging() -> None`
  - Stop capturing and restore the original `sys.stdout`/`sys.stderr`/`sys.stdin` objects.
  - This function flushes buffers and also attempts to unregister any atexit flush handlers that were registered by `start_logging`.
  - Thread-safety: restores streams while holding the internal lock and flushes outside the lock to avoid blocking critical sections.

- `pause_logging(*, toggle: bool = True) -> bool`
  - Toggle the pause state. When `toggle=True` and logging is active, pause it (uninstall TeeStreams, restore originals); when `toggle=True` and already paused, resume it. When `toggle=False`, always pause regardless of current state.
  - Returns the new paused state (True when paused).
  - Thread-safety: updates and stream replacements are done while holding the internal lock; expensive flushes are executed outside the lock.

- `resume_logging(*, toggle: bool = False) -> bool`
  - Explicitly resume logging. When `toggle=False` (default), always resume. When `toggle=True` and logging is already active, pauses instead.
  - Returns the paused state after the call (False when logging was resumed).
  - Thread-safety: same guarantees as `pause_logging`.

- `is_logging() -> bool`
  - Returns True when logging is active (a TeeStream is installed and the logger is not paused).
  - Safe to call concurrently.

- `is_redirected(stream: StdMode) -> bool`
  - Query whether the given stream (`StdMode.STDOUT`, `STDIN`, `STDERR`) is currently redirected to a TeeStream.

### Notes

- **atexit handlers**: RotaryLogger registers flush handlers via `atexit.register` to attempt a final flush at process exit; those handlers are unregistered when `stop_logging()` is called. The implementation stores the exact bound-methods used to guarantee `atexit.unregister` works reliably.
- **Concurrency testing**: basic concurrent toggling of pause/resume is covered by the project's tests. Calling `start_logging`/`stop_logging` concurrently from multiple threads is heavier and may involve filesystem operations — avoid such patterns in production unless you synchronize externally.
- **stdin capture**: stdin is not captured by default. Pass `capture_stdin=True` to the `RotaryLogger` constructor to wrap `sys.stdin`.

## Environment variables

The following environment variables are read at import time and can override default configuration:

| Variable | Type | Default | Description |
|---|---|---|---|
| `LOG_TO_FILE` | bool (`1`/`true`/`yes`) | `true` | Whether file logging is enabled |
| `LOG_FOLDER_NAME` | str (path) | `<package_dir>/logs` | Base folder for log output |
| `LOG_MAX_SIZE` | int (bytes) | `2 GB` | Maximum log file size before rotation |

## Documentation (Doxygen)

The project uses generated Doxygen in different formats:

- [`HTML`](https://hanra-s-work.github.io/rotary_logger/)
- `LaTeX` (every time a version is released)
- `RTF` (every time a version is released)

You can view the documentation online, by going here: [https://hanra-s-work.github.io/rotary_logger/](https://hanra-s-work.github.io/rotary_logger/)

## Contributing

Please read [`CONTRIBUTING.md`](./CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) before opening issues or PRs.

## License

See the [`LICENSE`](./LICENSE) file in the repository.
