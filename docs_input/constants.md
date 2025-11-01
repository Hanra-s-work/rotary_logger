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
-- LAST Modified: 2:35:28 01-11-2025
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

- `constants.py` centralizes configuration values, sizes, enums, and small dataclasses used by other modules. Keep the file as the single source of truth for defaults and literal values.

## Key values and enums

- SIZE constants: `B1`, `KB1`, `MB1`, `GB1`, `TB1` (use for conversions)
- Default sizes: `BUFFER_FLUSH_SIZE`, `DEFAULT_LOG_MAX_FILE_SIZE`, `DEFAULT_LOG_BUFFER_FLUSH_SIZE`.
- `StdMode` and `ErrorMode` enums: represent stream identity (`STDOUT`, `STDERR`, `STDIN`) and error handling modes for `TeeStream`.
- `FileInfo` dataclass: holds `path`, `descriptor`, and `written_bytes` for a `FileInstance`.
- `Prefix` dataclass: three booleans used for prefixing messages when mirroring.

## Operator notes

- Prefer using the enum types (`StdMode`, `ErrorMode`) over raw strings for clarity and safety.
- If you change default sizes here, ensure unit semantics in `FileInstance` and `TeeStream` are still consistent (MB vs bytes, KB vs bytes).

## Examples

```py
from rotary_logger import constants as CONST
print(CONST.DEFAULT_LOG_MAX_FILE_SIZE)
```
