"""
Pytest configuration and shared fixtures for rotary_logger tests.
"""

import sys

import pytest
from rotary_logger.tee_stream import TeeStream


@pytest.fixture(autouse=True)
def restore_streams():
    """Restore sys.stdout/stderr before and after each test for proper isolation.

    When running with pytest -s (no capture), this fixture ensures that if any
    test leaves sys.stdout or sys.stderr as TeeStream instances (indicating
    cleanup failed), those streams are restored before the next test runs.
    This prevents test isolation failures that are hidden when using pytest -q
    (which has its own capture mechanism that resets streams).
    """
    stdout_before = sys.stdout
    stderr_before = sys.stderr

    # Check if previous test left broken streams and restore if needed
    if isinstance(sys.stdout, TeeStream) or isinstance(sys.stderr, TeeStream):
        # Get a reference to the original streams by checking pytest's internals
        # If stdout/stderr are TeeStream, try to get the wrapped stream
        if isinstance(sys.stdout, TeeStream):
            sys.stdout = getattr(
                sys.stdout, '_get_stream_if_present', lambda: sys.stdout)()
        if isinstance(sys.stderr, TeeStream):
            sys.stderr = getattr(
                sys.stderr, '_get_stream_if_present', lambda: sys.stderr)()

    yield

    # After test, restore if it left broken streams
    if isinstance(sys.stdout, TeeStream) or isinstance(sys.stderr, TeeStream):
        sys.stdout = stdout_before
        sys.stderr = stderr_before
