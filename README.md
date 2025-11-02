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
-- LAST Modified: 6:10:51 02-11-2025
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

- Mirror stdout and stderr into rotating files
- Optionally merge stdout/stderr into a single file or keep them split into separate per-stream folders
- Low-IO buffered writes using a swap-buffer flush strategy
- Safe concurrent use (per-object RLocks; see developer notes on lock ordering)

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
echo "hello" | python -m rotary_logger -a my_log
```

You can also use the shortcut: `pytee`.

It works similarly to `python -m rotary_logger`.

Because we are similare but not identical, the destination you can specify only corresponds to the base folder that will be used, the rest of the directory will be built in the following way: `path/to/folder/year/month/day/` then in the day, if you pass the `-m` (`--merge`) you will see files that are timestamped, however, if you do not pass the flag, you will see 2 folders, `stdout` and `stderr` which will each contain timestamped files.

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

This replaces `sys.stdout` and `sys.stderr` with `TeeStream` wrappers. If you need to stop logging in-process, restore `sys.stdout` and `sys.stderr` yourself. Or call the `stop_logging` function.

## Documentation

You can find documentation here: [docs](./docs_input/) as well as here: [https://hanra-s-work.github.io/rotary_logger/](https://hanra-s-work.github.io/rotary_logger/)

## Logo source

The source of the logo used in the documentation: [https://deepai.org](https://deepai.org), then edited in gimp.

## Configuration & options

### Common CLI options

- `-a` / `--append`: append to existing logs (do not truncate)
- `-m` / `--merge`: merge stdout and stderr into a single log file
- `-s` / `--max-size`: maximum file size in MB before rotation

### Library API (short)

- `RotaryLogger.start_logging(log_folder: Optional[Path], merged: bool, append: bool, max_size_mb: int)` — begin capturing and rotating logs

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

- start_logging(log_folder: Optional[Path]=None, max_filesize: Optional[int]=None, merged: Optional[bool]=None, log_to_file: bool=True) -> None
  - Start redirecting `sys.stdout` and `sys.stderr` to `TeeStream` wrappers and begin writing to rotating files.
  - Parameters: `log_folder` — optional base folder to write logs; `max_filesize` — override rotation size; `merged` — whether to merge stdout/stderr into a single file; `log_to_file` — whether to enable file writes.
  - Thread-safety: the function snapshots configuration under an internal lock and performs filesystem checks outside the lock; assignment of `sys.stdout`/`sys.stderr` is performed atomically while holding the lock.

- stop_logging() -> None
  - Stop capturing and restore the original `sys.stdout`/`sys.stderr` objects.
  - This function flushes buffers and also attempts to unregister any atexit flush handlers that were registered by `start_logging`.
  - Thread-safety: restores streams while holding the internal lock and flushes outside the lock to avoid blocking critical sections.

- pause_logging() -> bool
  - Toggle the pause state. When pausing, the TeeStreams are uninstalled and the original streams are restored; when resuming, the TeeStreams are reinstalled.
  - Returns the new paused state (True when paused).
  - Thread-safety: updates and stream replacements are done while holding the internal lock; expensive flushes are executed outside the lock.

- resume_logging() -> bool
  - Explicitly resume logging (idempotent). Returns the paused state after resuming (False).
  - Thread-safety: same guarantees as `pause_logging`.

- is_logging() -> bool
  - Returns True when logging is active (a TeeStream is installed and the logger is not paused).
  - Safe to call concurrently.

- is_redirected(stream: StdMode) -> bool
  - Query whether the given stream (StdMode.STDOUT, STDIN, STDERR) is currently redirected to a TeeStream.

### Notes

- **atexit handlers**: RotaryLogger registers flush handlers via `atexit.register` to attempt a final flush at process exit; those handlers are unregistered when `stop_logging()` is called. The implementation stores the exact bound-methods used to guarantee `atexit.unregister` works reliably.
- **Concurrency testing**: basic concurrent toggling of pause/resume is covered by the project's tests. Calling `start_logging`/`stop_logging` concurrently from multiple threads is heavier and may involve filesystem operations — avoid such patterns in production unless you synchronize externally.

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
