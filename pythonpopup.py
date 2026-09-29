"""
Tkinter dialogs used by the authentication flow.

UI only: this module never decides whether a device is allowed and never ejects
anything.  The v1 popup compared the typed password against the literal ``'123'``
in the source and called the eject routine itself, which made the security policy
impossible to test or to reuse.  The password now comes from configuration and the
caller (:func:`auth1.authentication`) applies the decision.

Every dialog owns exactly one ``tk.Tk`` root and destroys it in a ``finally``
block.  v1 created a root per message box and leaked an extra hidden root each
time a device was checked, which kept the process alive after an exit request.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

import config

log = logging.getLogger(__name__)

RESULT_AUTHORIZED = "authorized"
RESULT_DENIED = "denied"
RESULT_INCORRECT = "incorrect"

OVERLAY_ALPHA = 0.7
DIALOG_WIDTH = 300
DIALOG_HEIGHT = 200


def _new_overlay():
    """Create the dimmed full-screen backdrop and return ``(root, overlay)``."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()

    overlay = tk.Toplevel(root)
    overlay.overrideredirect(True)  # no window decorations
    overlay.attributes("-alpha", OVERLAY_ALPHA)  # dim the desktop behind the dialog
    overlay.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}")
    overlay.configure(background="black")
    return root, overlay


def _center(root) -> None:
    """Place the dialog in the middle of the screen."""
    width, height = root.winfo_screenwidth(), root.winfo_screenheight()
    x_position = int((width / 2) - (DIALOG_WIDTH / 2))
    y_position = int((height / 2) - (DIALOG_HEIGHT / 2))
    root.geometry(f"{DIALOG_WIDTH}x{DIALOG_HEIGHT}+{x_position}+{y_position}")


def _close(root, overlay) -> None:
    for window in (overlay, root):
        try:
            window.destroy()
        except Exception:  # pragma: no cover - window already gone
            log.debug("window was already destroyed", exc_info=True)


def show_error(title: str, message: str) -> None:
    """Standalone error dialog (used when no device could be identified)."""
    from tkinter import messagebox

    root, overlay = _new_overlay()
    try:
        messagebox.showerror(title, message, parent=overlay)
    finally:
        _close(root, overlay)


def show_ejected(incorrect: bool = False) -> None:
    """Report that the drive was ejected because it is not authorized."""
    from tkinter import messagebox

    root, overlay = _new_overlay()
    try:
        if incorrect:
            messagebox.showerror("File access not allowed", "Incorrect password", parent=overlay)
        messagebox.showinfo("Not authenticated", "Device ejected", parent=overlay)
    finally:
        _close(root, overlay)


def authenticated() -> None:
    """Confirm that the connected device is authorized."""
    from tkinter import messagebox

    root, overlay = _new_overlay()
    try:
        messagebox.showinfo("Authentication status", "Device Authenticated", parent=overlay)
    finally:
        _close(root, overlay)


def popup(device_ids: Iterable[str] = (), settings: Optional[config.Settings] = None) -> str:
    """Ask the operator to authorize the connected device(s).

    Returns ``RESULT_AUTHORIZED`` when the correct password was entered,
    ``RESULT_DENIED`` when the operator declined or cancelled, and
    ``RESULT_INCORRECT`` after ``USBAUTH_MAX_ATTEMPTS`` wrong passwords.  The
    caller is responsible for ejecting the drive.

    Without a configured password the prompt cannot succeed, so the request is
    refused immediately and the operator is told how to configure one.
    """
    settings = settings or config.load_settings()

    if not settings.has_password:
        log.error("no authorization password is configured")
        show_error("USB not authenticated", config.missing_password_warning())
        return RESULT_DENIED

    from tkinter import messagebox, simpledialog

    root, overlay = _new_overlay()
    try:
        _center(root)
        devices = "\n".join(dict.fromkeys(str(item) for item in device_ids if item))
        detail = f"\n\n{devices}" if devices else ""
        answer = messagebox.askquestion(
            "USB not authenticated",
            "Do you want to allow the device to access your computer?" + detail,
            icon="warning",
            parent=overlay,
        )
        if answer != "yes":
            log.info("operator declined the device")
            return RESULT_DENIED

        for attempt in range(1, settings.max_attempts + 1):
            password = simpledialog.askstring(
                "Password",
                f"Enter password ({attempt} of {settings.max_attempts}):",
                show="*",
                parent=root,
            )
            if password is None:
                log.info("password prompt cancelled")
                return RESULT_DENIED
            if settings.verify_password(password):
                return RESULT_AUTHORIZED
            log.warning(
                "incorrect password (attempt %d of %d)", attempt, settings.max_attempts
            )

        return RESULT_INCORRECT
    finally:
        _close(root, overlay)


#: v1 name for :func:`popup`, kept so existing scripts keep importing cleanly.
prompt_authorization = popup
