import os
from pathlib import Path
import sys

# Must be set before any app module is imported
os.environ.setdefault("SESSION_SECRET", "test-secret-for-unit-tests")

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def _clear_startup_db_error(monkeypatch):
    """Stub out initialize_database so the lifespan doesn't set startup_db_error."""
    import app.main as main_module
    monkeypatch.setattr(main_module, "initialize_database", lambda: None)
    monkeypatch.setattr(main_module, "startup_db_error", None)
    # Clear rate limiter state between tests
    main_module._login_attempts.clear()
