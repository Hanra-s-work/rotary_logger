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
-- LAST Modified: 2:34:56 01-11-2025
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

- `FileInstance` manages file descriptor lifecycle, buffering, rotation and flush semantics for log output. It centralizes path/resolution, opening/closing descriptors, and deciding when to rotate based on written bytes.

## Primary responsibilities / public API

- FileInstance(file_path, override=None, merged=None, encoding=None, prefix=None, *, max_size_mb=None, flush_size_kb=None, folder_prefix=None)
- set_max_size(int), set_flush_size(int), set_filepath(...), set_override(...)
- write(message: str): append to an internal buffer (thread-safe)
- flush(): force buffer flush to disk
- get_prefix(), get_* accessors for configuration

## Buffering and rotation

- Writes append to an in-memory buffer protected by an `RLock`. When the buffer exceeds `flush_size` (byte-count measured using the configured encoding), `_flush_buffer()` is triggered.
- `_flush_buffer()` follows a swap-buffer pattern: it detaches the pending buffer under the lock and performs disk I/O outside the lock to avoid stalling other writers. It then updates `written_bytes` and triggers rotation under lock if the file exceeds `max_size`.

## Thread-safety and locking

- `FileInstance` uses an `RLock` for internal synchronization; callers should prefer the public `set_*`, `get_*`, `write`, and `flush` methods which accept a `lock` parameter (default true) for safety.
- Important invariant: avoid acquiring another object lock while holding a `FileInstance` lock to prevent deadlocks (for example, never acquire `FileInstance` lock and then call into `TeeStream` methods that acquire their own lock).

## Resource and failure handling

- Files are opened lazily when needed (first flush or when filepath is set).
- Disk I/O errors during write/flush are retried once where reasonable; expected OS-level errors are caught specifically (OSError, ValueError). The code avoids catching broad `Exception` where the specific error types are known.
- Because buffering is in memory, high-throughput writes with slow disk can cause memory growth. To bound memory, a bounded-buffer policy (not currently enabled) can be added; implementors should expose a dropped-message counter and configurable policy (drop-new, drop-old, or block briefly).

## Usage example

```py
from rotary_logger.file_instance import FileInstance
fi = FileInstance("/var/log/myapp")
fi.write("hello\n")
fi.flush()
```

## Operator notes

- `max_size_mb` is interpreted as megabytes and converted to bytes internally; `flush_size_kb` is interpreted as kilobytes. Provide reasonably-sized flush thresholds for production (e.g., 8 KB or higher) to reduce syscall overhead.
- Avoid relying on `__del__` for deterministic cleanup; call `flush()` or a `close()` API (if added) at shutdown to ensure all buffered messages are persisted.
