import sys
import time
from pathlib import Path
from rotary_logger.tee_stream import TeeStream

root = Path('tmp_pipe.log')
orig = sys.stdout
# Wrap stdout with TeeStream but avoid writing to file for this test
ts = TeeStream(root, orig, log_to_file=False)
sys.stdout = ts

print('hello from tee')
# intentional short sleep to simulate streaming
time.sleep(0.1)
# do another print
print('second line')
# do not explicitly flush here; rely on process exit
