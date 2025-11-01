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
-- LAST Modified: 2:36:8 01-11-2025
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

- `RotaryLogger` is the high-level coordinator that configures `FileInstance` and replaces `sys.stdout` / `sys.stderr` with `TeeStream` wrappers to mirror program output into the logging folder.

## Public API

- RotaryLogger(...): constructor accepts default folder, max filesize, merge_streams flag and prefix toggles.
- start_logging(log_folder=None, max_filesize=None, merged=None): installs `TeeStream` instances on `sys.stdout` and `sys.stderr` and registers `atexit` flush handlers.

## Behavior and safety

- The class is thread-safe via an internal `RLock` used around startup and configuration operations.
- `start_logging()` verifies the provided folder (creates it if needed) and attempts a safe write test to ensure it's writable; on failure it falls back to the default log folder or raises a `RuntimeError` when neither is writable.
- `RotaryLogger` registers `sys.stdout.flush` and `sys.stderr.flush` with `atexit` to attempt a last flush at process exit; note that `atexit` callbacks run as part of Python shutdown and should not be relied on for cross-process durability guarantees.

## Usage example

```py
from rotary_logger.rotary_logger import RotaryLogger
# Basic usage; this replaces sys.stdout/stderr for the process
RotaryLogger().start_logging()
print("Hello world")  # will be mirrored to logs/ and to the terminal
# LAST Modified: 2:32:40 01-11-2025

## Operator notes

- Environment variables supported: `LOG_TO_FILE` and `LOG_FOLDER_NAME` control whether and where logs are stored.
- For deterministic shutdown and maximum safety, call `flush()` (or a future `close()` API) explicitly from application shutdown code rather than relying solely on `atexit` handlers.
- The logger performs validation on folder paths (path length, write test). If the path is invalid, it warns and falls back to the default folder.
