"""
Authenticate a newly connected device and act on the outcome.

The flow lives in one place, which makes the policy easy to audit:

1. Read the PnP DeviceIDs of the connected USB mass-storage devices.
2. Nothing identifiable -> deny and eject (v1 reported success in this case).
3. Any fingerprint whitelisted -> allow.
4. Otherwise ask the operator for the password; on success the device is added to
   the whitelist, on refusal/cancel/failure the drive is ejected.

v1 spread these decisions across the popup, the reader and the writer, and the
module-level ``connected()`` call in auth.py meant that merely importing the file
changed the whitelist.
"""

from __future__ import annotations

import logging
from typing import Optional

import auth
import config
import eject
import encrypt
import pythonpopup

log = logging.getLogger(__name__)

RESULT_AUTHORIZED = pythonpopup.RESULT_AUTHORIZED
RESULT_DENIED = pythonpopup.RESULT_DENIED
RESULT_INCORRECT = pythonpopup.RESULT_INCORRECT


def authentication(
    drive_letter: Optional[str] = None, settings: Optional[config.Settings] = None
) -> str:
    """Authenticate the connected device, ejecting it when it is not allowed."""
    settings = settings or config.load_settings()

    device_ids = auth.current_device_ids()
    fingerprints = [
        value
        for value in (encrypt.device_fingerprint(item, settings) for item in device_ids)
        if value
    ]

    if not fingerprints:
        log.warning(
            "no identifiable USB mass-storage device (drive %s) - denying", drive_letter or "?"
        )
        pythonpopup.show_error(
            "Device not recognised",
            "The connected drive could not be identified, so it has not been authorized.",
        )
        return _deny(drive_letter, settings)

    label = drive_letter or fingerprints[0]
    if auth.authorized(fingerprints, settings):
        log.info("device %s is authorized", label)
        pythonpopup.authenticated()
        return RESULT_AUTHORIZED

    log.info("device %s is unknown - requesting authorization", label)
    result = pythonpopup.popup(device_ids, settings)

    if result == RESULT_AUTHORIZED:
        auth.authorize_devices(device_ids, settings)
        pythonpopup.authenticated()
        return RESULT_AUTHORIZED

    return _deny(drive_letter, settings, incorrect=result == RESULT_INCORRECT)


def _deny(
    drive_letter: Optional[str], settings: config.Settings, incorrect: bool = False
) -> str:
    """Eject the drive and tell the operator - the fail-closed path."""
    eject.eject_usb(drive_letter, settings)
    pythonpopup.show_ejected(incorrect=incorrect)
    return RESULT_INCORRECT if incorrect else RESULT_DENIED
