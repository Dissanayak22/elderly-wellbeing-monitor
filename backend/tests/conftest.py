"""Keep backend tests isolated from the application's persistent demo data."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="ewm-backend-tests-")
TEST_DATABASE_PATH = Path(_TEST_DIRECTORY.name) / "test.db"

# These values must be set before importing backend.app, where settings and the
# SQLAlchemy engine are constructed once for the process.
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "backend-test-secret-key-with-at-least-32-characters"
os.environ["AI_DEMO_MODE"] = "true"
os.environ["SEED_DEMO_DATA"] = "true"


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Close SQLite handles before deleting the temporary test directory."""
    from backend.app.core.database import engine

    engine.dispose()
    _TEST_DIRECTORY.cleanup()
