"""
TEMPORARY BRIDGE - the worker moved to ingest/worker.py.

This file only exists so the old Railway start command
(python3 scripts/run_forever.py) keeps working during the switch.
Delete this file once Railway uses:  python3 -m ingest.worker
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from ingest.worker import main  # noqa: E402

if __name__ == "__main__":
    main()
