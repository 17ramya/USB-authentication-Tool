"""Configuration tests: defaults, environment overrides and fail-fast validation."""

from __future__ import annotations

import hashlib
import sys

import pytest

import config

PASSWORD = "correct horse battery staple"
PASSWORD_HASH = hashlib.sha256(PASSWORD.encode("utf-8")).hexdigest()


def test_defaults_without_environment():
    settings = config.load_settings()

    assert settings.authfile.name == config.DEFAULT_AUTHFILE_NAME
    assert settings.poll_seconds == config.DEFAULT_POLL_SECONDS
    assert settings.max_attempts == config.DEFAULT_MAX_ATTEMPTS
    assert settings.dry_run is False
    assert settings.hash_mode == config.HASH_MODE_LEGACY
    assert settings.log_level == config.DEFAULT_LOG_LEVEL
    assert settings.has_password is False


def test_environment_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv(config.ENV_AUTHFILE, str(tmp_path / "custom.txt"))
    monkeypatch.setenv(config.ENV_POLL_SECONDS, "0.5")
    monkeypatch.setenv(config.ENV_MAX_ATTEMPTS, "5")
    monkeypatch.setenv(config.ENV_DRY_RUN, "yes")
    monkeypatch.setenv(config.ENV_PASSWORD_SHA256, PASSWORD_HASH.upper())
    monkeypatch.setenv(config.ENV_LOG_LEVEL, "debug")
    monkeypatch.setenv(config.ENV_LOG_FILE, str(tmp_path / "usb-auth.log"))
    monkeypatch.setenv(config.ENV_HASH_MODE, "sha256")
    monkeypatch.setenv(config.ENV_SALT, "pepper")

    settings = config.load_settings()

    assert settings.authfile == tmp_path / "custom.txt"
    assert settings.poll_seconds == 0.5
    assert settings.max_attempts == 5
    assert settings.dry_run is True
    assert settings.password_hash == PASSWORD_HASH
    assert settings.log_level == "DEBUG"
    assert settings.log_file == tmp_path / "usb-auth.log"
    assert settings.hash_mode == config.HASH_MODE_SHA256
    assert settings.salt == "pepper"


@pytest.mark.parametrize(
    "name, value",
    [
        (config.ENV_DRY_RUN, "maybe"),
        (config.ENV_POLL_SECONDS, "soon"),
        (config.ENV_POLL_SECONDS, "0"),
        (config.ENV_MAX_ATTEMPTS, "zero"),
        (config.ENV_MAX_ATTEMPTS, "0"),
        (config.ENV_HASH_MODE, "md5"),
    ],
)
def test_invalid_values_fail_fast(monkeypatch, name, value):
    """Bad configuration is reported at start-up, not when a device is plugged in."""
    monkeypatch.setenv(name, value)
    with pytest.raises(config.ConfigurationError):
        config.load_settings()


def test_sha256_mode_requires_a_salt(monkeypatch):
    monkeypatch.setenv(config.ENV_HASH_MODE, "sha256")
    with pytest.raises(config.ConfigurationError, match=config.ENV_SALT):
        config.load_settings()


@pytest.mark.parametrize("prefix", ["", "sha256:", "sha256$", " SHA256:"])
def test_password_hash_accepts_common_prefixes(monkeypatch, prefix):
    monkeypatch.setenv(config.ENV_PASSWORD_SHA256, prefix + PASSWORD_HASH)
    assert config.load_settings().password_hash == PASSWORD_HASH


def test_password_hash_rejects_a_bad_digest(monkeypatch):
    monkeypatch.setenv(config.ENV_PASSWORD_SHA256, "abc123")
    with pytest.raises(config.ConfigurationError):
        config.load_settings()


def test_verify_password_with_sha256_hash(make_settings):
    settings = make_settings(password=None, password_hash=PASSWORD_HASH)
    assert settings.has_password is True
    assert settings.verify_password(PASSWORD) is True
    assert settings.verify_password(PASSWORD + "x") is False


def test_verify_password_with_plaintext(make_settings):
    settings = make_settings(password="hunter2", password_hash=None)
    assert settings.verify_password("hunter2") is True
    assert settings.verify_password("Hunter2") is False


@pytest.mark.parametrize("candidate", [None, ""])
def test_verify_password_fails_closed_when_not_configured(make_settings, candidate):
    """No configured password means nobody can authorize a device."""
    settings = make_settings(password=None, password_hash=None)
    assert settings.has_password is False
    assert settings.verify_password(candidate) is False
    assert settings.verify_password("123") is False


def test_with_overrides_ignores_none(make_settings, tmp_path):
    settings = make_settings(poll_seconds=2.0, max_attempts=3)
    updated = settings.with_overrides(poll_seconds=10.0, max_attempts=None)
    assert updated.poll_seconds == 10.0
    assert updated.max_attempts == 3
    assert settings.poll_seconds == 2.0  # original untouched (frozen dataclass)


def test_app_dir_uses_the_executable_folder_when_frozen(monkeypatch, tmp_path):
    executable = tmp_path / "USB-Authentication-Tool.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert config.app_dir() == tmp_path


def test_app_dir_is_the_source_folder_when_not_frozen():
    assert (config.app_dir() / "config.py").exists()
