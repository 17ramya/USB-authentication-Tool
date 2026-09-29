"""
Configuration for the USB authentication tool.

Every runtime value is resolved here from the environment, so a deployed copy -
either a source checkout or a packaged ``.exe`` - can be reconfigured without
editing or rebuilding the code.  See the "Configuration" table in README.md.

Environment variables
---------------------
USBAUTH_AUTHFILE         Path to the authorized-device file (default: authfile.txt
                         stored next to the program).
USBAUTH_PASSWORD         Plaintext authorization password (development only).
USBAUTH_PASSWORD_SHA256  SHA-256 hex digest of the authorization password. Use this
                         instead of USBAUTH_PASSWORD on real deployments - the
                         plaintext then never exists on disk or in the environment.
USBAUTH_MAX_ATTEMPTS     Password attempts before the device is ejected (default 3).
USBAUTH_POLL_SECONDS     Monitor polling interval in seconds (default 2).
USBAUTH_DRY_RUN          When true, log what would happen instead of ejecting drives.
USBAUTH_HASH             Fingerprint scheme: ``legacy`` (default) or ``sha256``.
USBAUTH_SALT             Secret salt, required when USBAUTH_HASH=sha256.
USBAUTH_LOG_LEVEL        DEBUG/INFO/WARNING/ERROR (default INFO).
USBAUTH_LOGFILE          Optional log file path for unattended deployments.
"""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
import os
import string
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

APP_NAME = "USB Authentication Tool"
APP_VERSION = "2.0.0"

#: Environment variable names - kept as constants so docs and tests cannot drift.
ENV_AUTHFILE = "USBAUTH_AUTHFILE"
ENV_PASSWORD = "USBAUTH_PASSWORD"
ENV_PASSWORD_SHA256 = "USBAUTH_PASSWORD_SHA256"
ENV_MAX_ATTEMPTS = "USBAUTH_MAX_ATTEMPTS"
ENV_POLL_SECONDS = "USBAUTH_POLL_SECONDS"
ENV_DRY_RUN = "USBAUTH_DRY_RUN"
ENV_HASH_MODE = "USBAUTH_HASH"
ENV_SALT = "USBAUTH_SALT"
ENV_LOG_LEVEL = "USBAUTH_LOG_LEVEL"
ENV_LOG_FILE = "USBAUTH_LOGFILE"

#: Fingerprint schemes understood by encrypt.py.
HASH_MODE_LEGACY = "legacy"
HASH_MODE_SHA256 = "sha256"
HASH_MODES = (HASH_MODE_LEGACY, HASH_MODE_SHA256)

DEFAULT_AUTHFILE_NAME = "authfile.txt"
DEFAULT_POLL_SECONDS = 2.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_LOG_LEVEL = "INFO"

_TRUTHY = {"1", "true", "yes", "on", "y"}
_FALSY = {"0", "false", "no", "off", "n", ""}

_SHA256_HEX_LENGTH = 64
_HEX_DIGITS = set(string.hexdigits)


class ConfigurationError(ValueError):
    """Raised when the environment holds a value the tool cannot use.

    Configuration problems are reported at start-up instead of at the moment a
    USB device is plugged in, so a bad deployment fails loudly and immediately.
    """


def app_dir() -> Path:
    """Directory that holds user data (authfile.txt, logs).

    * Source checkout - the repository folder (next to this module).
    * PyInstaller onefile build - the folder containing the ``.exe``, which is a
      writable location the operator controls.  The temporary extraction folder
      (``sys._MEIPASS``) is deliberately never used: it is deleted when the
      program exits, so a whitelist written there would be lost.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _env_text(name: str) -> Optional[str]:
    """Return a stripped environment value, or ``None`` when unset/blank."""
    raw = os.environ.get(name)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUTHY:
        return True
    if value in _FALSY:
        return False
    raise ConfigurationError(
        f"{name} must be a boolean (1/0, true/false, yes/no), got {raw!r}"
    )


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = _env_text(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a whole number, got {raw!r}") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}, got {value}")
    return value


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = _env_text(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number, got {raw!r}") from exc
    if value <= minimum:
        raise ConfigurationError(f"{name} must be > {minimum}, got {value}")
    return value


def normalize_password_hash(raw: str) -> str:
    """Accept a SHA-256 digest written as hex, ``sha256:<hex>`` or ``sha256$<hex>``."""
    value = raw.strip().lower()
    for prefix in ("sha256:", "sha256$"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    if len(value) != _SHA256_HEX_LENGTH or any(char not in _HEX_DIGITS for char in value):
        raise ConfigurationError(
            f"{ENV_PASSWORD_SHA256} must be a 64 character SHA-256 hex digest, got {raw!r}"
        )
    return value


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the tool configuration."""

    authfile: Path
    poll_seconds: float = DEFAULT_POLL_SECONDS
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    dry_run: bool = False
    hash_mode: str = HASH_MODE_LEGACY
    salt: str = ""
    password_hash: Optional[str] = None
    password: Optional[str] = None
    log_level: str = DEFAULT_LOG_LEVEL
    log_file: Optional[Path] = None

    @property
    def has_password(self) -> bool:
        """True when an authorization password was configured."""
        return bool(self.password_hash or self.password)

    def verify_password(self, candidate: Optional[str]) -> bool:
        """Constant-time password check that fails closed.

        When no password is configured *nobody* can authorize a device.  The v1
        popup compared against the literal ``'123'`` baked into the source, so
        every copy of this tool shipped with the same known password.
        """
        if not candidate:
            return False
        if self.password_hash:
            digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
            return hmac.compare_digest(
                digest.encode("ascii"), self.password_hash.encode("ascii")
            )
        if self.password:
            return hmac.compare_digest(
                candidate.encode("utf-8"), self.password.encode("utf-8")
            )
        return False

    def with_overrides(self, **overrides) -> "Settings":
        """Return a copy with the given fields replaced (``None`` values ignored)."""
        clean = {key: value for key, value in overrides.items() if value is not None}
        return dataclasses.replace(self, **clean)


def load_settings() -> Settings:
    """Build a :class:`Settings` from the current environment.

    Read on every call rather than cached, so tests and CLI overrides can change
    the environment without restarting the process.
    """
    hash_mode = (_env_text(ENV_HASH_MODE) or HASH_MODE_LEGACY).lower()
    if hash_mode not in HASH_MODES:
        raise ConfigurationError(
            f"{ENV_HASH_MODE} must be one of {', '.join(HASH_MODES)}, got {hash_mode!r}"
        )

    salt = _env_text(ENV_SALT) or ""
    if hash_mode == HASH_MODE_SHA256 and not salt:
        raise ConfigurationError(
            f"{ENV_SALT} must be set when {ENV_HASH_MODE}={HASH_MODE_SHA256}"
        )

    password_hash_raw = _env_text(ENV_PASSWORD_SHA256)
    password_hash = normalize_password_hash(password_hash_raw) if password_hash_raw else None

    authfile_raw = _env_text(ENV_AUTHFILE)
    authfile = (
        Path(authfile_raw).expanduser()
        if authfile_raw
        else app_dir() / DEFAULT_AUTHFILE_NAME
    )

    log_file_raw = _env_text(ENV_LOG_FILE)
    log_file = Path(log_file_raw).expanduser() if log_file_raw else None

    return Settings(
        authfile=authfile,
        poll_seconds=_env_float(ENV_POLL_SECONDS, DEFAULT_POLL_SECONDS),
        max_attempts=_env_int(ENV_MAX_ATTEMPTS, DEFAULT_MAX_ATTEMPTS),
        dry_run=_env_bool(ENV_DRY_RUN, False),
        hash_mode=hash_mode,
        salt=salt,
        password_hash=password_hash,
        password=_env_text(ENV_PASSWORD),
        log_level=(_env_text(ENV_LOG_LEVEL) or DEFAULT_LOG_LEVEL).upper(),
        log_file=log_file,
    )


def missing_password_warning() -> str:
    """Operator-facing guidance shown when no authorization password is set."""
    return (
        "No authorization password is configured, so a new device can never be "
        "authorized. Set one before deploying:\n"
        "  Generate a digest:\n"
        '    python -c "import hashlib,getpass;'
        'print(hashlib.sha256(getpass.getpass().encode()).hexdigest())"\n'
        "  PowerShell (current session):\n"
        '    $env:USBAUTH_PASSWORD_SHA256 = "<digest>"\n'
        "  PowerShell (persistent, per user):\n"
        '    [Environment]::SetEnvironmentVariable("USBAUTH_PASSWORD_SHA256", '
        '"<digest>", "User")'
    )
