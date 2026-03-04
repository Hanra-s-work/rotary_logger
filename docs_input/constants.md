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
-- FILE: constants.md
-- CREATION DATE: 01-11-2025
-- LAST Modified: 4:3:55 04-03-2026
-- DESCRIPTION: 
-- A module that provides a universal python light on iops way of logging to files your program execution.
-- /STOP
-- COPYRIGHT: (c) Asperguide
-- PURPOSE: The documentation for the constants, this an overview of the details of the documentation.
-- // AR
-- +==== END rotary_logger =================+
-->
# constants — module documentation

## Purpose

- `constants.py` centralizes configuration values, sizes, enums, and small dataclasses used by other modules. It is the single source of truth for defaults, literal values, and shared type definitions.

## Size constants

| Name | Value | Description |
|------|-------|-------------|
| `B1` | 1 | 1 byte |
| `KB1` | 1 024 | 1 kibibyte |
| `MB1` | 1 048 576 | 1 mebibyte |
| `GB1` | 1 073 741 824 | 1 gibibyte |
| `TB1` | 1 099 511 627 776 | 1 tebibyte |
| `BUFFER_FLUSH_SIZE` | `8 * KB1` | Default in-memory flush threshold |
| `DEFAULT_LOG_MAX_FILE_SIZE` | `2 * GB1` | Default rotation size |
| `DEFAULT_LOG_BUFFER_FLUSH_SIZE` | `BUFFER_FLUSH_SIZE` | Alias used by `FileInstance` |

## Enumerations

### `StdMode`

Identifies which standard stream a `TeeStream` instance is wrapping.

| Member | Value |
|--------|-------|
| `STDIN` | `"stdin"` |
| `STDOUT` | `"stdout"` |
| `STDERR` | `"stderr"` |
| `STDUNKNOWN` | `"stdunknown"` |

### `ErrorMode`

Controls what `TeeStream` does when a broken-pipe condition is detected.

| Member | Value | Behaviour |
|--------|-------|-----------|
| `WARN` | `"Warn"` | Print warning |
| `WARN_NO_PIPE` | `"Warn No pipe"` | Print warning only when stdout is not a pipe (default) |
| `EXIT` | `"Exit"` | Call `sys.exit()` |
| `EXIT_NO_PIPE` | `"Exit No pipe"` | Call `sys.exit()` only when stdout is not a pipe |

### `PrefixFunctionCall`

Optional per-call tag prepended to log entries to identify which stream method produced the write.

| Member | Value |
|--------|-------|
| `EMPTY` | `""` (no tag) |
| `WRITE` | `"[WRITE]"` |
| `WRITELINES` | `"[WRITELINES]"` |
| `FLUSH` | `"[FLUSH]"` |
| `READ` | `"[READ]"` |
| `READLINE` | `"[READLINE]"` |
| `READLINES` | `"[READLINES]"` |

Only relevant when `log_function_calls` is enabled on a `TeeStream`.

## Dataclasses

### `FileInfo`

Container for an open log file held by a `FileInstance`.

| Field | Type | Description |
|-------|------|-------------|
| `path` | `Optional[Path]` | Path to the log file on disk |
| `descriptor` | `Optional[IO[Any]]` | Open file object or `None` |
| `written_bytes` | `int` | Number of bytes written so far |

### `Prefix`

Flags controlling whether a textual stream prefix (`[STDOUT]`, `[STDERR]`, `[STDIN]`) is prepended to each log entry.

| Field | Type | Default |
|-------|------|---------|
| `std_in` | `bool` | `False` |
| `std_out` | `bool` | `False` |
| `std_err` | `bool` | `False` |

### `FileStreamInstances`

Container for the `FileInstance` objects created by `RotaryLogger.start_logging()`, one per captured stream.

| Field | Type | Description |
|-------|------|-------------|
| `stdout` | `Optional[FileInstance]` | Instance for stdout, or `None` |
| `stderr` | `Optional[FileInstance]` | Instance for stderr, or `None` |
| `stdin` | `Optional[FileInstance]` | Instance for stdin, or `None` |
| `stdunknown` | `Optional[FileInstance]` | Instance for unknown stream, or `None` |
| `merged_streams` | `Dict[StdMode, bool]` | Tracks which streams share the merged log file |

## Lookup maps

- `CORRECT_FOLDER: Dict[StdMode, str]` — maps each `StdMode` to its sub-folder name (e.g. `StdMode.STDOUT → "stdout"`).
- `CORRECT_PREFIX: Dict[StdMode, str]` — maps each `StdMode` to its text prefix (e.g. `StdMode.STDOUT → "[STDOUT]"`).

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_TO_FILE` | `"true"` | Set to `"0"`, `"false"`, or `"no"` to disable file logging at startup |
| `LOG_FOLDER_NAME` | `DEFAULT_LOG_FOLDER` | Override the default log folder path |

These are evaluated once at import time and stored in `LOG_TO_FILE_ENV` (`bool`) and `RAW_LOG_FOLDER_ENV` (`str`).

## Operator notes

- Prefer using the enum types (`StdMode`, `ErrorMode`, `PrefixFunctionCall`) over raw strings for clarity and safety.
- If you change default sizes here, ensure unit semantics in `FileInstance` and `TeeStream` are still consistent (MB vs bytes, KB vs bytes).
- `FileStreamInstances.merged_streams` is a `dict` backed by a `field(default_factory=…)`, so each instance gets its own independent copy.

## Examples

```py
from rotary_logger import constants as CONST

# Size arithmetic
print(CONST.DEFAULT_LOG_MAX_FILE_SIZE)   # 2147483648 (2 GB in bytes)

# Enum lookup
folder = CONST.CORRECT_FOLDER[CONST.StdMode.STDOUT]  # "stdout"
prefix = CONST.CORRECT_PREFIX[CONST.StdMode.STDERR]  # "[STDERR]"
```
