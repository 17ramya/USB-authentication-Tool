
"""
Device identity fingerprints.

A fingerprint is the value stored in ``authfile.txt`` for an authorized device.
Two schemes exist, selected with ``USBAUTH_HASH``:

``legacy`` (default)
    The Caesar-style obfuscation shipped with v1 of this tool.  The algorithm is
    frozen - :func:`encrypt_device_id` still produces byte-identical output - so
    whitelists written by the original scripts keep working after this upgrade.

``sha256``
    Salted SHA-256 over the PnP DeviceID.  Recommended for new deployments: the
    legacy scheme is reversible (its key is derived from the id itself), so a
    leaked authfile reveals the identifiers it was meant to obscure.

Fingerprints are not used to forge anything: they are compared against ids read
from the hardware, which an attacker cannot influence without physical control
of the drive itself.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Iterable, List, Optional, Set

import config

log = logging.getLogger(__name__)

#: Prefix marking a salted SHA-256 entry in authfile.txt.
SHA256_PREFIX = "sha256$"

def encrypt_device_id(device_id):
    key = sum(ord(char) for char in device_id) % 26 + 1  # Device-specific encryption key
    encrypted_id = ""

    for char in device_id:
        if char.isalnum():
            if char.isupper():
                encrypted_char = chr((ord(char) + key - 65) % 26 + 65)
            else:
                encrypted_char = chr((ord(char) + key - 97) % 26 + 97)
        else:
            encrypted_char = char
        encrypted_id += encrypted_char

    return encrypted_id


def device_fingerprint(device_id: str, settings: Optional[config.Settings] = None) -> str:
    """Return the fingerprint stored in ``authfile.txt`` for ``device_id``.

    Blank input yields ``""``, which every caller treats as "not authorized" -
    never as a match.  (The v1 reader tested an empty id against the whitelist
    with ``in``, so whenever Windows could not name a mass-storage device the
    tool silently reported the device as authenticated.)
    """
    device_id = (device_id or "").strip()
    if not device_id:
        log.debug("empty device id - refusing to build a fingerprint")
        return ""

    settings = settings or config.load_settings()
    if settings.hash_mode == config.HASH_MODE_SHA256:
        digest = hashlib.sha256(f"{settings.salt}:{device_id}".encode("utf-8")).hexdigest()
        return SHA256_PREFIX + digest
    return encrypt_device_id(device_id)


def normalize_entry(entry: str) -> str:
    """Usable content of a stored line (``""`` for blanks and ``#`` comments).

    The entry keeps the spelling it was written with, so the authfile stays
    readable (a ``sha256$`` digest keeps its lower-case hex).  Matching is
    case-insensitive - see :func:`is_match`.
    """
    if not entry:
        return ""
    value = entry.strip()
    if not value or value.startswith("#"):
        return ""
    return value


def is_comment(entry: str) -> bool:
    """True when an authfile line is a comment or blank and can be skipped."""
    return normalize_entry(entry) == ""


def read_entries(lines: Iterable[str]) -> List[str]:
    """Filter raw authfile lines down to the unique fingerprints they contain.

    Duplicates are detected case-insensitively; the first spelling wins, so a file
    cannot grow an entry that only differs from an existing one by its case.
    """
    entries: List[str] = []
    seen: Set[str] = set()
    for line in lines:
        value = normalize_entry(line)
        key = value.upper()
        if value and key not in seen:
            seen.add(key)
            entries.append(value)
    return entries


def is_match(stored_entries: Iterable[str], fingerprint: str) -> bool:
    """Constant-time membership test (case-insensitive, comments/blank lines ignored)."""
    candidate = normalize_entry(fingerprint).upper().encode("utf-8")
    if not candidate:
        return False

    matched = False
    for entry in stored_entries:
        stored = normalize_entry(entry).upper().encode("utf-8")
        if not stored:
            continue
        # compare_digest instead of `in`/`==`: identical result, no timing side
        # channel, and no accidental match of the kind an empty string caused.
        if hmac.compare_digest(stored, candidate):
            matched = True
    return matched
