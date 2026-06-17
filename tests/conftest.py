"""pytest configuration — sets up the test environment."""

import os
import sys

# Add tests/ directory to path so helpers.py is importable from test modules.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Ensure a token is set before any module-level imports fire so the startup
# warning in server.py does not appear during normal test runs.
os.environ.setdefault("SAFETYCULTURE_API_TOKEN", "test_token_for_testing")
