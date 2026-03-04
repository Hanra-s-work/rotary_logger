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
-- FILE: tee_stream.md
-- CREATION DATE: 01-11-2025
-- LAST Modified: 4:5:44 04-03-2026
-- DESCRIPTION: 
-- A module that provides a universal python light on iops way of logging to files your program execution.
-- /STOP
-- COPYRIGHT: (c) Asperguide
-- PURPOSE: The documentation for the tee stream, this an overview of the details of the documentation.
-- // AR
-- +==== END rotary_logger =================+
-->
# TeeStream — module documentation

## Purpose

`TeeStream` mirrors a `TextIO` stream (`sys.stdout`, `sys.stderr`, or `sys.stdin`) to disk via a `FileInstance` while preserving normal terminal output. It is a drop-in replacement for the standard streams: the rest of application code simply calls `print()`, `sys.stdout.write()`, etc. without knowing the stream was replaced.

## Constructor

```py
TeeStream(
    root,                                   # Union[str, Path, FileInstance]
    original_stream,                        # TextIO
    *,
    max_size_mb=None,                       # Optional[int]
    flush_size=None,                        # Optional[int]
    mode=CONST.StdMode.STDUNKNOWN,          # CONST.StdMode
    error_mode=CONST.ErrorMode.WARN_NO_PIPE, # CONST.ErrorMode
    encoding=None,                          # Optional[str]
    log_to_file=True,                       # bool
    log_function_calls=False,               # bool
)
```

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `root` | `Union[str, Path, FileInstance]` | Log destination: path string, `Path`, or a pre-built `FileInstance` | — |
| `original_stream` | `TextIO` | The stream to mirror (e.g. `sys.stdout`) | — |
| `max_size_mb` | `Optional[int]` | Max log-file size in MB; forwarded to `FileInstance` | `None` |
| `flush_size` | `Optional[int]` | Buffer-flush threshold in bytes; forwarded to `FileInstance` | `None` |
| `mode` | `CONST.StdMode` | Which standard stream this instance wraps | `STDUNKNOWN` |
| `error_mode` | `CONST.ErrorMode` | Broken-pipe handling policy | `WARN_NO_PIPE` |
| `encoding` | `Optional[str]` | Encoding override; forwarded to `FileInstance` | `None` |
| `log_to_file` | `bool` | Whether disk logging is enabled on construction | `True` |
| `log_function_calls` | `bool` | Prefix each log entry with the method name (`[WRITE]`, `[READLINE]`, …) | `False` |

Raises `ValueError` if `root` is not a `str`, `Path`, or `FileInstance`.

## Public methods

### Write path

| Method | Signature | Description |
|--------|-----------|-------------|
| `write` | `write(message: str)` | Write `message` to the terminal and buffer it for disk |
| `writelines` | `writelines(lines: List[str])` | Call `write()` for each line |
| `flush` | `flush()` | Flush the terminal stream and trigger a `FileInstance` flush |

### Read path (stdin wrapping)

| Method | Signature | Description |
|--------|-----------|-------------|
| `read` | `read(size=-1) → str` | Read from the original stream; optionally log the result |
| `readline` | `readline(size=-1) → str` | Read one line from the original stream |
| `readlines` | `readlines(hint=-1) → list[str]` | Read all lines from the original stream |

### Capability probes (TextIO compatibility)

| Method | Returns | Description |
|--------|---------|-------------|
| `readable()` | `bool` | `True` when `mode` is `STDIN` |
| `writable()` | `bool` | `True` when `mode` is not `STDIN` |
| `seekable()` | `bool` | Always `False` |

## Behavior and guarantees

- **No background threads**: all I/O runs on the caller's thread. Terminal writes are wrapped in specific exception handlers (`BrokenPipeError`, `OSError`) and will never raise unexpected exceptions back into the application.
- **Disk writes are cheap**: buffering is delegated to `FileInstance`. Each `write()` call appends to an in-memory list; actual disk I/O and rotation happen in `FileInstance._flush_buffer()`.
- **Broken-pipe semantics** are controlled by `error_mode`:
  - `WARN` / `WARN_NO_PIPE`: print a warning to the real `sys.stderr`.
  - `EXIT` / `EXIT_NO_PIPE`: call `sys.exit()` on the caller thread.

## Threading and resource notes

- A tiny `RLock` guards reference reads; disk I/O is performed outside the lock.
- Because terminal writes block the caller, a slow or blocked `original_stream` can delay the calling thread — an unavoidable trade-off without a dedicated I/O worker.
- For high-throughput services, consider tuning `flush_size` in `FileInstance` to amortise syscall overhead.

## Usage example

```py
import sys
import pathlib
from rotary_logger.tee_stream import TeeStream
from rotary_logger.file_instance import FileInstance
from rotary_logger import constants as CONST

fi = FileInstance(pathlib.Path("/var/log/myapp"))
tee = TeeStream(
    fi,
    sys.stdout,
    mode=CONST.StdMode.STDOUT,
    log_function_calls=True,
)
sys.stdout = tee
print("hello")  # → terminal + /var/log/myapp/…/stdout/….log
```

## Operator notes

- `flush()` is best-effort; for deterministic shutdown call `FileInstance.flush()` directly.
- The `log_function_calls` flag adds a `PrefixFunctionCall` tag (`[WRITE]`, `[READLINE]`, …) to each log entry, making it easy to distinguish write origins in mixed-stream log files.
- `TeeStream` does not close or restore the `original_stream`; that is the responsibility of `RotaryLogger.stop_logging()`.
