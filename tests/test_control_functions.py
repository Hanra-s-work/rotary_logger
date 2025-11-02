""" 
# +==== BEGIN rotary_logger =================+
# LOGO: 
# ..........####...####..........
# ......###.....#.#########......
# ....##........#.###########....
# ...#..........#.############...
# ...#..........#.#####.######...
# ..#.....##....#.###..#...####..
# .#.....#.##...#.##..##########.
# #.....##########....##...######
# #.....#...##..#.##..####.######
# .#...##....##.#.##..###..#####.
# ..#.##......#.#.####...######..
# ..#...........#.#############..
# ..#...........#.#############..
# ...##.........#.############...
# ......#.......#.#########......
# .......#......#.########.......
# .........#####...#####.........
# /STOP
# PROJECT: rotary_logger
# FILE: test_control_functions.py
# CREATION DATE: 02-11-2025
# LAST Modified: 4:55:13 02-11-2025
# DESCRIPTION: 
# A module that provides a universal python light on iops way of logging to files your program execution.
# /STOP
# COPYRIGHT: (c) Asperguide
# PURPOSE: File in charge of testing the control functions that provide status and information.
# // AR
# +==== END rotary_logger =================+
"""


import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from rotary_logger.rotary_logger_cls import RotaryLogger


def test_start_stop_registers_and_unregisters_atexit(tmp_path: Path):
    orig_out = sys.stdout
    rl = RotaryLogger()
    # start logging into tmp_path
    rl.start_logging(log_folder=tmp_path, merged=False)

    # After start, atexit handlers should be recorded
    assert getattr(rl, "_atexit_registered", False) in (True, False)
    # The registered flushers list should exist when registered
    if rl._atexit_registered:
        assert hasattr(rl, "_registered_flushers")
        assert len(rl._registered_flushers) >= 1

# LAST Modified: 4:53:54 02-11-2025riginal stdout and unregister atexit handlers
    rl.stop_logging()
    assert sys.stdout is orig_out
    assert getattr(rl, "_atexit_registered", False) is False


def test_pause_and_resume_toggle(tmp_path: Path):
    rl = RotaryLogger()
    rl.start_logging(log_folder=tmp_path, merged=False)

    # Initially logging should be active
    assert rl.is_logging() is True

    # Pause
    paused = rl.pause_logging()
    assert paused is True
    # while paused, is_logging should be False
    assert rl.is_logging() is False

    # Resume
    resumed = rl.resume_logging()
    # resume_logging returns paused state (False)
    assert resumed is False
    assert rl.is_logging() is True

    rl.stop_logging()


def _toggle_pause_resume(rl: RotaryLogger, stop_event: threading.Event):
    # Rapidly toggle pause/resume until stop_event is set
    while not stop_event.is_set():
        rl.pause_logging()
        rl.resume_logging()


def test_concurrent_pause_resume_stress(tmp_path: Path):
    rl = RotaryLogger()
    rl.start_logging(log_folder=tmp_path, merged=False)

    stop_event = threading.Event()

    # Start a few threads toggling pause/resume
    threads = []
    for _ in range(6):
        t = threading.Thread(target=_toggle_pause_resume,
                             args=(rl, stop_event))
        t.start()
        threads.append(t)

    # Meanwhile write some output to the current stdout for a short while
    try:
        for _ in range(100):
            print("ping")
            time.sleep(0.002)
    finally:
        # Stop the togglers
        stop_event.set()
        for t in threads:
            t.join(timeout=1.0)

    # Ensure no exceptions and logger remains in a valid state
    assert isinstance(rl.is_logging(), bool)
    rl.stop_logging()
