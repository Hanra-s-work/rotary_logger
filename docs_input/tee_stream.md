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
-- LAST Modified: 2:34:12 01-11-2025
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

- TeeStream mirrors a TextIO stream (usually `sys.stdout` or `sys.stderr`) to disk via a `FileInstance` while also preserving normal terminal output.

## Primary class

- TeeStream(root, original_stream, *, max_size_mb=None, flush_size=None, mode=StdMode.STDUNKNOWN, error_mode=ErrorMode.WARN_NO_PIPE, encoding=None)
  - root: a `pathlib.Path` or a `FileInstance` describing the destination.
  - original_stream: the stream to mirror (e.g. `sys.stdout`).
  - mode: which standard stream this instance represents (StdMode).
  - error_mode: controls behavior on broken pipe (warn / exit variants).

## Behavior and guarantees

- The class captures a few references under a tiny `RLock` to avoid races and then performs I/O without holding that lock long-term.
- Writes to the original stream are performed on the caller thread. They are wrapped in specific exception handlers (BrokenPipeError, OSError) and will not raise unexpected exceptions back to caller code.
- File writes are buffered via `FileInstance.write()`; those buffered writes are cheap (append to an in-memory buffer). Rotation and flush I/O is handled inside `FileInstance`.

## Threading and resource constraints

- No background threads are spawned by default; the design intentionally avoids creating threads so the middleware doesn't increase process thread usage.
- Because terminal writes run on the caller thread, a slow or blocked `original_stream` can delay the caller; this is an unavoidable I/O risk unless a dedicated worker thread or external buffering is accepted.

## Error / fatal semantics

- When `error_mode` requests exit, `TeeStream` will call `sys.exit()` on the caller thread for BrokenPipeError (this follows the user's requirement that fatal errors be handled "on our terms").
- Non-fatal I/O errors are reported to `sys.stderr` where possible; `TeeStream` avoids broad `except Exception` catches and only handles known exception types.

## Usage example

```py
from rotary_logger.tee_stream import TeeStream
from rotary_logger.file_instance import FileInstance

fi = FileInstance(pathlib.Path("/var/log/myapp"))
tee = TeeStream(fi, sys.stdout, mode=CONST.StdMode.STDOUT)
tee.write("hello\n")
```

## Operator notes

- The module exposes `flush()` which attempts a best-effort flush; callers that require deterministic shutdown should call `FileInstance.flush()` and an explicit `close()` if/when provided.
- For high-throughput services, consider bounded buffering at `FileInstance` level to avoid unbounded memory growth during slow disk I/O.
