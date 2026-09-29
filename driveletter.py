"""
Locate removable / USB drives.

``win32api`` is imported inside the functions, so this module can be imported and
unit tested on any platform; the tool itself is Windows-only.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

log = logging.getLogger(__name__)

#: DRIVE_REMOVABLE from the Windows GetDriveType API (win32file.DRIVE_REMOVABLE).
DRIVE_REMOVABLE = 2


def _drive_type_getter():
    """Return the callable that reports a drive's type.

    ``GetDriveType`` lives in ``win32file`` (``win32api`` does **not** expose it -
    verified against pywin32 310 and 312), so win32file is preferred and win32api
    is only used as a fallback for builds that expose it there.
    """
    import win32file

    getter = getattr(win32file, "GetDriveType", None)
    if getter is None:  # pragma: no cover - depends on the pywin32 build
        import win32api

        getter = win32api.GetDriveType
    return getter


def normalize_letter(drive_letter: str) -> str:
    """Return the canonical ``E:`` form of input such as ``e``, ``E:\\`` or ``E:``."""
    value = (drive_letter or "").strip().upper().rstrip("\\/")
    if not value:
        return ""
    if len(value) == 1 and value.isalpha():
        value += ":"
    if len(value) != 2 or value[1] != ":" or not value[0].isalpha():
        raise ValueError(f"not a drive letter: {drive_letter!r}")
    return value


def removable_drive_letters() -> List[str]:
    """Every mounted removable drive, e.g. ``['E:', 'F:']``.

    Uses ``GetDriveType`` from win32file instead of the v1 WMI association walk: it
    needs no privileges, cannot fail half way through a nested association query,
    and returns exactly the letters the eject call expects.
    """
    import win32api

    get_drive_type = _drive_type_getter()
    letters: List[str] = []
    for raw in win32api.GetLogicalDriveStrings().split("\x00"):
        if not raw:
            continue
        try:
            if get_drive_type(raw) == DRIVE_REMOVABLE:
                letters.append(normalize_letter(raw))
        except ValueError:
            log.debug("ignoring unexpected drive path %r", raw)
    return letters


def find_usb_drive_letter(letters: Optional[Iterable[str]] = None) -> Optional[str]:
    """First removable drive letter, or ``None`` when none is mounted.

    ``letters`` can be injected for testing.  The v1 function could return
    ``None``, which callers passed straight into ``CreateFileW`` as the literal
    string ``"None"``; every caller now handles the empty result explicitly.
    """
    candidates = list(letters) if letters is not None else removable_drive_letters()
    if not candidates:
        log.info("no removable drive is mounted")
        return None
    return candidates[0]
