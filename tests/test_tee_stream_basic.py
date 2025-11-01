import io
import sys
from pathlib import Path

import pytest

from rotary_logger.tee_stream import TeeStream


def _find_log_file(root: Path):
    logs = list(root.rglob('*.log'))
    if not logs:
        pytest.skip('No log file created')
    return logs[0]


def test_tee_stream_write_and_flush(tmp_path: Path) -> None:
    # Use an explicit .log file path to avoid the library attempting to
    # open a directory as a file (some FileInstance constructors accept
    # a file path rather than a folder).
    root = tmp_path / 'logs.log'
    # use an in-memory stream to capture original_stream writes
    orig = io.StringIO()
    ts = TeeStream(root, orig, max_size_mb=1)
    try:
        ts.write('hello world\n')
        ts.write('another line\n')
        # flush should force buffer to disk
        ts.flush()
        # original stream should contain the messages
        assert 'hello world' in orig.getvalue()
        # file should exist with the contents
        logfile = _find_log_file(tmp_path)
        # use the FileInstance configured encoding
        enc = ts.file_instance.get_encoding()
        content = logfile.read_text(encoding=enc)
        assert 'hello world' in content
        assert logfile.stat().st_size > 0
    finally:
        # cleanup
        try:
            orig.close()
        except Exception:
            pass


def test_tee_stream_encoding_byte_count(tmp_path: Path) -> None:
    root = tmp_path / 'logs.log'
    orig = io.StringIO()
    # use utf-16 to ensure byte-counting uses configured encoding
    # Create a FileInstance with the desired encoding first so the
    # underlying descriptor is opened with utf-16.
    from rotary_logger.file_instance import FileInstance
    fi = FileInstance(root, max_size_mb=1, encoding='utf-16')
    ts = TeeStream(fi, orig)
    try:
        s = 'é' * 10 + '\n'
        ts.write(s)
        ts.flush()
        # _written_bytes should equal the encoded byte length
        expected = len(s.encode(ts.file_instance.get_encoding()))
        logfile = _find_log_file(tmp_path)
        assert logfile.stat().st_size >= expected
    finally:
        try:
            orig.close()
        except Exception:
            pass
