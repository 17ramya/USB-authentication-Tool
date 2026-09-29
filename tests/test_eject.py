"""Eject tests.

The Win32 layer is replaced by a recording stub: sending the real
IOCTL_STORAGE_EJECT_MEDIA would physically eject a drive from the machine that
runs the tests.
"""

from __future__ import annotations

import sys
import types

import pytest

import eject


class FakeWin32File(types.ModuleType):
    """Records the calls eject.py makes and can fail like an access denial."""

    def __init__(self, fail=False):
        super().__init__("win32file")
        self.calls = []
        self.fail = fail

    def CreateFile(self, path, access, share, attrs, disposition, flags, template):
        self.calls.append(("CreateFile", path, access, share))
        if self.fail:
            raise OSError("access is denied")
        return "HANDLE"

    def DeviceIoControl(self, handle, code, in_buffer, out_size):
        self.calls.append(("DeviceIoControl", handle, code))

    def CloseHandle(self, handle):
        self.calls.append(("CloseHandle", handle))


@pytest.fixture
def fake_win32file(monkeypatch):
    """Install a fake win32file module and return the factory used to build it."""

    def _install(fail=False):
        module = FakeWin32File(fail=fail)
        monkeypatch.setitem(sys.modules, "win32file", module)
        return module

    return _install


def test_device_path_uses_the_volume_namespace():
    assert eject.device_path("e") == "\\\\.\\E:"
    assert eject.device_path("E:\\") == "\\\\.\\E:"


def test_device_path_rejects_junk():
    with pytest.raises(ValueError):
        eject.device_path("not-a-drive")


def test_eject_sends_the_ioctl_and_closes_the_handle(fake_win32file, make_settings):
    module = fake_win32file()

    assert eject.eject_usb("E:", make_settings()) is True
    assert module.calls == [
        (
            "CreateFile",
            "\\\\.\\E:",
            eject.GENERIC_READ | eject.GENERIC_WRITE,
            eject.FILE_SHARE_READ | eject.FILE_SHARE_WRITE,
        ),
        ("DeviceIoControl", "HANDLE", eject.IOCTL_STORAGE_EJECT_MEDIA),
        ("CloseHandle", "HANDLE"),
    ]


def test_eject_reports_failure_without_sending_the_ioctl(fake_win32file, make_settings):
    module = fake_win32file(fail=True)

    assert eject.eject_usb("E:", make_settings()) is False
    assert [call[0] for call in module.calls] == ["CreateFile"]


def test_eject_without_a_drive_letter_uses_discovery(fake_win32file, make_settings, monkeypatch):
    module = fake_win32file()
    monkeypatch.setattr(eject.driveletter, "removable_drive_letters", lambda: ["F:"])

    assert eject.eject_usb(settings=make_settings()) is True
    assert module.calls[0][1] == "\\\\.\\F:"


def test_eject_without_any_removable_drive_fails(make_settings, monkeypatch):
    monkeypatch.setattr(eject.driveletter, "removable_drive_letters", lambda: [])
    assert eject.eject_usb(settings=make_settings()) is False


def test_dry_run_never_touches_the_drive(fake_win32file, make_settings):
    """USBAUTH_DRY_RUN lets a deployment be rehearsed without removing hardware."""
    module = fake_win32file()

    assert eject.eject_usb("E:", make_settings(dry_run=True)) is True
    assert module.calls == []
