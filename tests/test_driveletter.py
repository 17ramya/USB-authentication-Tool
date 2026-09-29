"""Drive letter tests - win32api is replaced with a stub, so they run anywhere."""

from __future__ import annotations

import sys
import types

import pytest

import driveletter

DRIVE_FIXED = 3


def stub_win32(monkeypatch, drives, types_by_path, drive_type_location="win32file"):
    """Install fake win32api/win32file modules covering everything driveletter uses.

    ``drive_type_location`` selects which module exposes ``GetDriveType`` so both
    the preferred path and the fallback can be exercised.
    """
    api = types.ModuleType("win32api")
    api.GetLogicalDriveStrings = lambda: "".join(f"{drive}\x00" for drive in drives)

    def get_drive_type(path):
        return types_by_path.get(path, DRIVE_FIXED)

    if drive_type_location == "win32api":
        api.GetDriveType = get_drive_type
        winfile = types.ModuleType("win32file")  # deliberately without GetDriveType
    else:
        winfile = types.ModuleType("win32file")
        winfile.GetDriveType = get_drive_type
        winfile.DRIVE_REMOVABLE = 2

    monkeypatch.setitem(sys.modules, "win32api", api)
    monkeypatch.setitem(sys.modules, "win32file", winfile)
    return api, winfile


@pytest.mark.parametrize(
    "raw, expected",
    [("e", "E:"), ("E", "E:"), ("E:", "E:"), ("E:\\", "E:"), (" e:\\ ", "E:")],
)
def test_normalize_letter(raw, expected):
    assert driveletter.normalize_letter(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", None, "EF:", "1:", r"\\server\share"])
def test_normalize_letter_rejects_junk(raw):
    if not raw or not raw.strip():
        assert driveletter.normalize_letter(raw) == ""
    else:
        with pytest.raises(ValueError):
            driveletter.normalize_letter(raw)


def test_removable_drive_letters_filters_by_type(monkeypatch):
    stub_win32(monkeypatch, ["C:\\", "E:\\", "F:\\"], {"C:\\": 3, "E:\\": 2, "F:\\": 2})
    assert driveletter.removable_drive_letters() == ["E:", "F:"]


def test_removable_drive_letters_without_removable_drives(monkeypatch):
    stub_win32(monkeypatch, ["C:\\"], {"C:\\": 3})
    assert driveletter.removable_drive_letters() == []


def test_removable_drive_letters_ignores_unexpected_paths(monkeypatch):
    stub_win32(monkeypatch, ["C:\\", "not-a-drive", "E:\\"], {"E:\\": 2})
    assert driveletter.removable_drive_letters() == ["E:"]


def test_removable_drive_letters_falls_back_to_win32api(monkeypatch):
    """Builds of pywin32 that expose GetDriveType through win32api still work."""
    stub_win32(monkeypatch, ["C:\\", "E:\\"], {"E:\\": 2}, drive_type_location="win32api")
    assert driveletter.removable_drive_letters() == ["E:"]


def test_find_usb_drive_letter_uses_injected_letters():
    assert driveletter.find_usb_drive_letter(["E:", "F:"]) == "E:"


def test_find_usb_drive_letter_returns_none_without_drives(monkeypatch):
    """Regression: v1 returned None, which the eject call formatted into 'None'."""
    assert driveletter.find_usb_drive_letter([]) is None

    stub_win32(monkeypatch, ["C:\\"], {"C:\\": 3})
    assert driveletter.find_usb_drive_letter() is None


@pytest.mark.skipif(sys.platform != "win32", reason="needs the real pywin32 modules")
def test_get_drive_type_comes_from_win32file():
    """Integration guard: GetDriveType is in win32file, not win32api.

    ``win32api`` does not export ``GetDriveType`` at all, so reading the drive type
    from there made every drive look non-removable and the monitor saw nothing.
    """
    import win32file

    assert driveletter._drive_type_getter() is win32file.GetDriveType


@pytest.mark.skipif(sys.platform != "win32", reason="needs the real pywin32 modules")
def test_removable_drive_letters_runs_against_the_real_api():
    assert isinstance(driveletter.removable_drive_letters(), list)
