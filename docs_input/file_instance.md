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
-- FILE: file_instance.md
-- CREATION DATE: 01-11-2025
-- LAST Modified: 4:4:12 04-03-2026
-- DESCRIPTION: 
-- A module that provides a universal python light on iops way of logging to files your program execution.
-- /STOP
-- COPYRIGHT: (c) Asperguide
-- PURPOSE: The documentation for the file instance, this an overview of the details of the documentation.
-- // AR
-- +==== END rotary_logger =================+
-->
# FileInstance — module documentation

## Purpose

- `FileInstance` manages the full lifecycle of a log file: path resolution, descriptor opening/closing, in-memory buffering, and size-triggered rotation. It is the file I/O layer that `TeeStream` and `RotaryLogger` delegate to.

## Constructor

```py
FileInstance(
    file_path,          # Optional[Union[str, Path, FileInfo]]
    override=None,      # Optional[bool]
    merged=None,        # Optional[bool]
    encoding=None,      # Optional[str]
    prefix=None,        # Optional[Prefix]
    *,
    max_size_mb=None,   # Optional[int]
    flush_size_kb=None, # Optional[int]
    folder_prefix=None, # Optional[StdMode]
    log_to_file=True,   # bool
    merge_stdin=None,   # Optional[bool]
)
```

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `file_path` | `Optional[Union[str, Path, FileInfo]]` | Log-file path, or `None` to defer opening | — |
| `override` | `Optional[bool]` | Use write mode (`w`) instead of append (`a`) | `None` |
| `merged` | `Optional[bool]` | Whether multiple streams share this file | `None` |
| `encoding` | `Optional[str]` | Text encoding override | `None` |
| `prefix` | `Optional[Prefix]` | Stream-prefix configuration | `None` |
| `max_size_mb` | `Optional[int]` | Rotation threshold in MB | `None` |
| `flush_size_kb` | `Optional[int]` | Buffer flush threshold in KB | `None` |
| `folder_prefix` | `Optional[StdMode]` | StdMode used to create per-stream sub-folders | `None` |
| `log_to_file` | `bool` | Whether disk writes are enabled | `True` |
| `merge_stdin` | `Optional[bool]` | Whether stdin is merged into the shared file | `None` |

## Public API

### Setters (all keyword-safe via `lock=True`)

| Method | Description |
|--------|-------------|
| `set_log_to_file(bool)` | Enable or disable file logging for this instance |
| `set_max_size(int)` | Rotation threshold in MB |
| `set_flush_size(int)` | Buffer flush threshold in bytes |
| `set_filepath(path)` | Assign (and open) a new file path, or supply a `FileInfo` |
| `set_folder_prefix(StdMode)` | Override the per-stream sub-folder |
| `set_merged(bool)` | Toggle merged-stream mode |
| `set_merge_stdin(bool)` | Toggle whether stdin is part of the merged file |
| `set_encoding(str)` | Change the text encoding |
| `set_prefix(Prefix)` | Set the stream-prefix configuration |
| `set_override(bool)` | Toggle write-mode vs append-mode |

### Getters

| Method | Returns | Description |
|--------|---------|-------------|
| `get_log_to_file()` | `bool` | Whether file logging is enabled |
| `get_mode()` | `str` | Current open mode (`"a"` or `"w"`) |
| `get_merged()` | `bool` | Whether merged-stream mode is on |
| `get_merge_stdin()` | `bool` | Whether stdin is merged |
| `get_encoding()` | `str` | Current encoding |
| `get_prefix()` | `Optional[Prefix]` | Current prefix config |
| `get_override()` | `bool` | Whether override mode is on |
| `get_filepath()` | `Optional[FileInfo]` | Current `FileInfo` or `None` |
| `get_flush_size()` | `int` | Current flush threshold in bytes |
| `get_max_size()` | `int` | Current rotation threshold in bytes |

### I/O

| Method | Description |
|--------|-------------|
| `write(message: str)` | Append to the in-memory buffer (thread-safe); may trigger a flush |
| `flush()` | Force the buffer to disk |

### Lifecycle helpers

| Method | Description |
|--------|-------------|
| `copy()` | Return a deep copy of this `FileInstance` |
| `update(other: FileInstance)` | Merge configuration from `other` into `self` |

## Buffering and rotation

- Writes append to an in-memory `list[str]` protected by an `RLock`. When the byte-count of the buffer (measured with the configured encoding) exceeds `flush_size`, `_flush_buffer()` is triggered automatically.
- `_flush_buffer()` uses a swap-buffer pattern: it detaches the pending buffer under the lock and performs disk I/O outside the lock to avoid blocking other writers. It then updates `written_bytes` and triggers rotation under the lock if the file exceeds `max_size`.

## Thread-safety and locking

- Every public setter and getter accepts a `*, lock: bool = True` keyword argument. When `True` (the default) the method acquires `_file_lock` before reading or writing instance state.
- **Important invariant**: do not acquire another object's lock while already holding a `FileInstance` lock — in particular, never call `TeeStream` methods that acquire their own lock while holding the `FileInstance` lock.

## Resource and failure handling

- Files are opened lazily: the first time a valid `file_path` is set, `_open_file()` creates any missing parent directories and opens the descriptor.
- Specific OS-level errors (`OSError`, `ValueError`) are caught during I/O; broad `except Exception` is avoided.
- Because buffering is in memory, high-throughput writes with slow disk can cause memory growth. Callers that require bounded memory should flush explicitly at regular intervals.
- `__del__` attempts a best-effort close, but callers should call `flush()` explicitly at shutdown for deterministic cleanup.

## Usage example

```py
from rotary_logger.file_instance import FileInstance
from rotary_logger import constants as CONST

fi = FileInstance(
    "/var/log/myapp",
    merged=True,
    encoding="utf-8",
    max_size_mb=512,
)
fi.write("hello\n")
fi.flush()
```
