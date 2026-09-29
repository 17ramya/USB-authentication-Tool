"""Shared test fixtures.

The application is a flat set of modules (``import auth``, ``import config``), so
the repository root is added to ``sys.path`` here, and every test receives a
:class:`config.Settings` whose authfile lives in a temporary directory - tests
never touch the real ``authfile.txt``.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config  # noqa: E402  (must come after sys.path is prepared)

#: Every environment variable the tool reads; tests start from a clean slate.
ENVIRONMENT_VARIABLES = [
    config.ENV_AUTHFILE,
    config.ENV_PASSWORD,
    config.ENV_PASSWORD_SHA256,
    config.ENV_MAX_ATTEMPTS,
    config.ENV_POLL_SECONDS,
    config.ENV_DRY_RUN,
    config.ENV_HASH_MODE,
    config.ENV_SALT,
    config.ENV_LOG_LEVEL,
    config.ENV_LOG_FILE,
]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Remove the tool's environment variables so tests are order independent."""
    for name in ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def make_settings(tmp_path):
    """Factory building Settings that keep every side effect inside tmp_path."""

    def _make(**overrides):
        base = config.Settings(
            authfile=tmp_path / "authfile.txt",
            password="test-password",
        )
        return replace(base, **overrides)

    return _make


@pytest.fixture
def settings(make_settings):
    """Default Settings used by tests that do not care about configuration."""
    return make_settings()
