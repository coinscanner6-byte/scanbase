"""
TEMPORARY BRIDGE - the API moved to serve/main.py.

This file only exists so the old Railway start command
(uvicorn api.main:app ...) keeps working during the switch.
Delete this folder once Railway uses:  uvicorn serve.main:app ...
"""

from serve.main import app  # noqa: F401
