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
-- FILE: rotary_logger.md
-- CREATION DATE: 01-11-2025
-- LAST Modified: 4:5:27 04-03-2026
-- DESCRIPTION: 
-- A module that provides a universal python light on iops way of logging to files your program execution.
-- /STOP
-- COPYRIGHT: (c) Asperguide
-- PURPOSE: The documentation for the rotary logger, this an overview of the details of the documentation.
-- // AR
-- +==== END rotary_logger =================+
-->
# RotaryLogger — module documentation

## Purpose

`RotaryLogger` is the high-level coordinator: it configures `FileInstance` objects for each stream and replaces `sys.stdout`, `sys.stderr`, and optionally `sys.stdin` with `TeeStream` wrappers that mirror program output to rotating log files on disk.

## Constructor

```py
RotaryLogger(
    log_to_file=CONST.LOG_TO_FILE_ENV,       # bool
    override=False,                           # bool
    raw_log_folder=CONST.RAW_LOG_FOLDER_ENV, # str
    default_log_folder=CONST.DEFAULT_LOG_FOLDER, # Path
    default_max_filesize=CONST.DEFAULT_LOG_MAX_FILE_SIZE, # int
    merge_streams=True,                       # bool
    *,
    encoding=CONST.DEFAULT_ENCODING,          # str
    merge_stdin=False,                        # bool
    capture_stdin=False,                      # bool
    capture_stdout=True,                      # bool
    capture_stderr=True,                      # bool
    prefix_in_stream=True,                    # bool
    prefix_out_stream=True,                   # bool
    prefix_err_stream=True,                   # bool
    log_function_calls_stdin=False,           # bool
    log_function_calls_stdout=False,          # bool
    log_function_calls_stderr=False,          # bool
)
```

### Positional parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `log_to_file` | `bool` | Whether file logging is enabled at all | `LOG_TO_FILE_ENV` |
| `override` | `bool` | Open log files in write mode instead of append | `False` |
| `raw_log_folder` | `str` | Preferred log folder path (raw string) | `RAW_LOG_FOLDER_ENV` |
| `default_log_folder` | `Path` | Fallback log folder if `raw_log_folder` is invalid | `DEFAULT_LOG_FOLDER` |
| `default_max_filesize` | `int` | Rotation size in bytes | `DEFAULT_LOG_MAX_FILE_SIZE` |
| `merge_streams` | `bool` | Whether stdout and stderr share one log file | `True` |

### Keyword-only parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `encoding` | `str` | File encoding for all log files | `DEFAULT_ENCODING` |
| `merge_stdin` | `bool` | Whether stdin is merged into the shared log file | `False` |
| `capture_stdin` | `bool` | Wrap `sys.stdin` with a `TeeStream` | `False` |
| `capture_stdout` | `bool` | Wrap `sys.stdout` with a `TeeStream` | `True` |
| `capture_stderr` | `bool` | Wrap `sys.stderr` with a `TeeStream` | `True` |
| `prefix_in_stream` | `bool` | Prepend `[STDIN]` to stdin log entries | `True` |
| `prefix_out_stream` | `bool` | Prepend `[STDOUT]` to stdout log entries | `True` |
| `prefix_err_stream` | `bool` | Prepend `[STDERR]` to stderr log entries | `True` |
| `log_function_calls_stdin` | `bool` | Tag stdin entries with the calling method name | `False` |
| `log_function_calls_stdout` | `bool` | Tag stdout entries with the calling method name | `False` |
| `log_function_calls_stderr` | `bool` | Tag stderr entries with the calling method name | `False` |

## Public methods

### `start_logging(*, log_folder=None, max_filesize=None, merged=None, log_to_file=True, merge_stdin=None)`

Install `TeeStream` wrappers and begin mirroring output to disk.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `log_folder` | `Optional[Path]` | Log folder override; falls back to configured defaults | `None` |
| `max_filesize` | `Optional[int]` | Rotation size override in MB | `None` |
| `merged` | `Optional[bool]` | Override merge-streams toggle | `None` |
| `log_to_file` | `bool` | Whether file writes are enabled | `True` |
| `merge_stdin` | `Optional[bool]` | Override merge-stdin toggle | `None` |

- The folder is created if it does not exist. If the path is unwritable, the logger falls back to `default_log_folder`; if that also fails, a `RuntimeError` is raised.
- `atexit` flush handlers are registered once (idempotent on repeated calls).

### `stop_logging()`

Restore original `sys.stdout`, `sys.stderr`, and `sys.stdin`, and de-register the `atexit` handlers.

### `pause_logging(*, toggle: bool = True) → bool`

Pause file logging without restoring the original streams. The `toggle` parameter controls the new state:

- `toggle=True` (default): pause (suspend file writes).
- `toggle=False`: no-op; returns `False` immediately.

Returns the new `paused` state.

### `resume_logging(*, toggle: bool = False) → bool`

Resume file logging after a pause. The `toggle` parameter controls the new state:

- `toggle=False` (default): resume (re-enable file writes).
- `toggle=True`: no-op; returns `True` immediately.

Returns the new `paused` state.

### `is_redirected() → bool`

Return `True` when `sys.stdout` is currently a `TeeStream` managed by this instance.

### `__call__(*args, **kwargs)`

Calling the instance directly is equivalent to calling `start_logging(*args, **kwargs)`.

## Behavior and safety

- All startup and configuration operations are protected by an internal `RLock`. Stream replacement (`sys.stdout = …`) is performed under the lock to keep the switch atomic.
- `_handle_stream_assignments(log_folder)` creates the `FileInstance` objects stored in `_file_stream_instances`. When `merge_streams=True`, stdout and stderr share the same `FileInstance`; when `merge_stdin=True`, stdin also shares it.
- `atexit` flush handlers are registered only once even if `start_logging()` is called multiple times.

## Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `LOG_TO_FILE` | `"true"` | Set to `"false"` / `"0"` / `"no"` to disable file logging |
| `LOG_FOLDER_NAME` | module `logs/` sub-folder | Override the default log folder path |

## Usage example

```py
from rotary_logger import RotaryLogger

# Minimal: capture stdout and stderr with defaults
rl = RotaryLogger()
rl.start_logging()
print("Hello world")  # mirrored to logs/stdout/ and terminal

# Custom folder + stdin capture
rl2 = RotaryLogger(
    raw_log_folder="/var/log/myapp",
    capture_stdin=True,
    merge_stdin=True,
    log_function_calls_stdout=True,
)
rl2.start_logging()
```

## Operator notes

- After calling `stop_logging()` (or when `RotaryLogger.__del__` runs), the original streams are restored automatically.
- Do not hold a reference to the replaced `sys.stdout`/`sys.stderr` and call methods on it after `stop_logging()` — use the instance's `stdout_stream` / `stderr_stream` attributes instead.
- For deterministic shutdown, call `stop_logging()` explicitly rather than relying solely on `atexit` handlers or `__del__`.
