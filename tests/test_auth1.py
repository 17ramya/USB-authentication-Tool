"""Policy tests for ``auth1.authentication`` - the one place access is decided."""

from __future__ import annotations

import pytest

import auth
import auth1
import eject
import pythonpopup

DEVICE_ID = r"USB\VID_0781&PID_5567\4C530001231031117553"
LEGACY_FINGERPRINT = r"OMV\PCX_xefy&JCX_ccde\bWcaxxxyzayxayyyecca"


class Recorder:
    """Replaces the UI and the eject call so the decision itself can be asserted."""

    def __init__(self, monkeypatch):
        self.device_ids = [DEVICE_ID]
        self.popup_result = pythonpopup.RESULT_DENIED
        self.calls = []
        self._monkeypatch = monkeypatch

    def install(self):
        monkeypatch = self._monkeypatch
        monkeypatch.setattr(auth, "current_device_ids", lambda: list(self.device_ids))
        monkeypatch.setattr(
            eject,
            "eject_usb",
            lambda letter, settings: self.calls.append(("eject", letter)) or True,
        )
        monkeypatch.setattr(
            pythonpopup,
            "popup",
            lambda ids, settings: self.calls.append(("popup", list(ids))) or self.popup_result,
        )
        monkeypatch.setattr(
            pythonpopup,
            "authenticated",
            lambda: self.calls.append(("authenticated", None)),
        )
        monkeypatch.setattr(
            pythonpopup,
            "show_ejected",
            lambda incorrect=False: self.calls.append(("ejected", incorrect)),
        )
        monkeypatch.setattr(
            pythonpopup,
            "show_error",
            lambda title, message: self.calls.append(("error", title)),
        )
        return self

    def events(self):
        return [name for name, _ in self.calls]


@pytest.fixture
def recorder(monkeypatch):
    return Recorder(monkeypatch).install()


def test_whitelisted_device_is_allowed_without_a_prompt(recorder, settings):
    auth.authorize_devices([DEVICE_ID], settings)

    assert auth1.authentication("E:", settings) == auth1.RESULT_AUTHORIZED
    assert recorder.events() == ["authenticated"]
    assert ("popup", [DEVICE_ID]) not in recorder.calls


def test_device_declined_by_the_operator_is_ejected(recorder, settings):
    recorder.popup_result = pythonpopup.RESULT_DENIED

    assert auth1.authentication("E:", settings) == auth1.RESULT_DENIED
    assert recorder.calls == [("popup", [DEVICE_ID]), ("eject", "E:"), ("ejected", False)]
    assert auth.read_authorized(settings.authfile) == []


def test_correct_password_authorizes_and_stores_the_device(recorder, settings):
    recorder.popup_result = pythonpopup.RESULT_AUTHORIZED

    assert auth1.authentication("E:", settings) == auth1.RESULT_AUTHORIZED
    assert recorder.events() == ["popup", "authenticated"]
    assert "eject" not in recorder.events()
    assert auth.read_authorized(settings.authfile) == [LEGACY_FINGERPRINT]


def test_wrong_password_is_reported_and_ejects(recorder, settings):
    recorder.popup_result = pythonpopup.RESULT_INCORRECT

    assert auth1.authentication("E:", settings) == auth1.RESULT_INCORRECT
    assert recorder.calls == [("popup", [DEVICE_ID]), ("eject", "E:"), ("ejected", True)]


def test_unidentifiable_device_is_denied_and_ejected(recorder, settings):
    """Regression: v1 compared an empty device id against the whitelist with
    ``in``, which matched every entry and reported the device as authenticated."""
    recorder.device_ids = []

    assert auth1.authentication("E:", settings) == auth1.RESULT_DENIED
    assert recorder.events() == ["error", "eject", "ejected"]
    assert ("popup", []) not in recorder.calls


def test_eject_targets_the_drive_that_was_plugged_in(recorder, settings):
    """v1 always ejected "the first USB drive", which is wrong with two inserted."""
    recorder.popup_result = pythonpopup.RESULT_DENIED

    auth1.authentication("G:", settings)

    assert ("eject", "G:") in recorder.calls


def test_result_constants_match_the_ui_module():
    assert auth1.RESULT_AUTHORIZED == pythonpopup.RESULT_AUTHORIZED
    assert auth1.RESULT_DENIED == pythonpopup.RESULT_DENIED
    assert auth1.RESULT_INCORRECT == pythonpopup.RESULT_INCORRECT
