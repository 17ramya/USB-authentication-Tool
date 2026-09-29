"""
Eject (power off) a USB mass-storage device.

The v1 implementation called ``ctypes.windll.kernel32.CreateFileW`` without
declaring a return type.  ctypes defaults to ``c_int``, so on 64-bit Python the
file HANDLE was truncated to 32 bits and ``DeviceIoControl`` was then invoked
with a damaged handle.  This version uses the pywin32 bindings - already a
dependency of the project - which marshal pointers and handles correctly.
"""

from __future__ import annotations

import logging
from typing import Optional

import config
import driveletter

log = logging.getLogger(__name__)

#: IOCTL_STORAGE_EJECT_MEDIA (0x2D4808).  pywin32 does not expose this constant,
#: so it is defined here; the value is fixed by the Windows SDK.
IOCTL_STORAGE_EJECT_MEDIA = 0x2D4808

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3


def device_path(drive_letter: str) -> str:
    """Volume device path: ``E:`` becomes ``\\\\.\\E:``."""
    letter = driveletter.normalize_letter(drive_letter)
    if not letter:
        raise ValueError("no drive letter supplied")
    return "\\\\.\\" + letter


def eject_usb(
    drive_letter: Optional[str] = None, settings: Optional[config.Settings] = None
) -> bool:
    """Eject ``drive_letter`` (default: the first removable drive).

    Returns ``True`` when the eject request reached the driver.  Honours
    ``USBAUTH_DRY_RUN`` so a new deployment can be rehearsed without removing
    hardware from the operator's machine.
    """
    settings = settings or config.load_settings()
    letter = drive_letter or driveletter.find_usb_drive_letter()
    if not letter:
        log.error("cannot eject: no removable drive is mounted")
        return False

    if settings.dry_run:
        log.warning("dry run: would eject %s", letter)
        return True

    import win32file

    handle = None
    try:
        handle = win32file.CreateFile(
            device_path(letter),
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        win32file.DeviceIoControl(handle, IOCTL_STORAGE_EJECT_MEDIA, None, 0)
        log.info("ejected %s", letter)
        return True
    except Exception as exc:  # pywintypes.error for every driver-level failure
        log.error("failed to eject %s: %s", letter, exc)
        return False
    finally:
        if handle is not None:
            try:
                win32file.CloseHandle(handle)
            except Exception:  # pragma: no cover - best effort cleanup
                log.debug("closing the volume handle failed", exc_info=True)
