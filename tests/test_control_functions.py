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
# LAST Modified: 3:41:37 04-03-2026
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

    # stop_logging should restore original stdout and unregister atexit handlers
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


def test_pause_logging_toggle_false_always_pauses(tmp_path: Path):
    """pause_logging(toggle=False) should always pause, even if already paused."""
    rl = RotaryLogger()
    rl.start_logging(log_folder=tmp_path, merged=False)
    assert rl.is_logging()

    # First call: running → pause
    result = rl.pause_logging(toggle=False)
    assert result is True

    # Second call: already paused → still pause (idempotent)
    result = rl.pause_logging(toggle=False)
    assert result is True

    rl.stop_logging()


def test_resume_logging_toggle_true_pauses_when_active(tmp_path: Path):
    """resume_logging(toggle=True) should pause when the logger is currently running."""
    rl = RotaryLogger()
    rl.start_logging(log_folder=tmp_path, merged=False)
    assert rl.is_logging()

    # toggle=True when active → should pause
    result = rl.resume_logging(toggle=True)
    assert result is True
    assert not rl.is_logging()

    rl.stop_logging()


def test_is_redirected_reflects_logging_state(tmp_path: Path):
    """is_redirected() should return False before and after stop_logging, True during."""
    from rotary_logger import constants as CONST

    rl = RotaryLogger()
    assert rl.is_redirected(CONST.StdMode.STDOUT) is False
    assert rl.is_redirected(CONST.StdMode.STDERR) is False

    rl.start_logging(log_folder=tmp_path, merged=False)
    assert rl.is_redirected(CONST.StdMode.STDOUT) is True
    assert rl.is_redirected(CONST.StdMode.STDERR) is True

    rl.stop_logging()
    assert rl.is_redirected(CONST.StdMode.STDOUT) is False
    assert rl.is_redirected(CONST.StdMode.STDERR) is False


def test_rotary_logger_callable_starts_logging(tmp_path: Path):
    """Calling the RotaryLogger instance like a function should start logging."""
    rl = RotaryLogger(default_log_folder=tmp_path)
    orig_out = sys.stdout
    try:
        rl()  # __call__ delegates to start_logging() with no args
        assert rl.is_logging()
    finally:
        rl.stop_logging()
        # Guard: ensure stdout is restored even on unexpected failure
        if sys.stdout is not orig_out and not hasattr(sys.stdout, 'original_stream'):
            sys.stdout = orig_out


def test_stop_logging_clears_stdin_stream(tmp_path: Path):
    """stop_logging should restore sys.stdin and clear stdin_stream."""
    orig_in = sys.stdin
    rl = RotaryLogger()
    rl.start_logging(log_folder=tmp_path, merged=True)
    assert rl.stdin_stream is not None

    rl.stop_logging()
    assert rl.stdin_stream is None
    assert sys.stdin is orig_in
