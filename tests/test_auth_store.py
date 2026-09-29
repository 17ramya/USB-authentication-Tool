"""Whitelist store tests (auth.py): file handling and fail-closed matching."""

from __future__ import annotations

import auth
import encrypt

DEVICE_ID = r"USB\VID_0781&PID_5567\4C530001231031117553"
SECOND_ID = r"USB\VID_0BC2&PID_2312\00000000ABCD"
LEGACY_FINGERPRINT = r"OMV\PCX_xefy&JCX_ccde\bWcaxxxyzayxayyyecca"


def test_read_authorized_without_a_file_returns_empty(make_settings):
    """Regression: v1 opened authfile.txt for reading, so a first run raised
    FileNotFoundError."""
    settings = make_settings()
    assert not settings.authfile.exists()
    assert auth.read_authorized(settings.authfile) == []


def test_ensure_authfile_creates_a_commented_file(make_settings):
    settings = make_settings()
    assert auth.ensure_authfile(settings.authfile) is True
    assert settings.authfile.exists()
    assert auth.read_authorized(settings.authfile) == []  # header only
    assert auth.ensure_authfile(settings.authfile) is False  # idempotent


def test_authorize_devices_stores_the_fingerprint(make_settings):
    settings = make_settings()
    assert auth.authorize_devices([DEVICE_ID], settings) == [LEGACY_FINGERPRINT]
    assert auth.read_authorized(settings.authfile) == [LEGACY_FINGERPRINT]
    assert auth.authorized([LEGACY_FINGERPRINT], settings) is True


def test_authorize_devices_is_idempotent(make_settings):
    settings = make_settings()
    auth.authorize_devices([DEVICE_ID], settings)
    assert auth.authorize_devices([DEVICE_ID], settings) == []
    assert auth.read_authorized(settings.authfile) == [LEGACY_FINGERPRINT]


def test_authorize_devices_ignores_blank_ids(make_settings):
    settings = make_settings()
    assert auth.authorize_devices(["", "   ", None], settings) == []
    assert not settings.authfile.exists()


def test_authorize_devices_returns_every_new_entry(make_settings):
    settings = make_settings()
    added = auth.authorize_devices([DEVICE_ID, SECOND_ID], settings)
    assert added == [LEGACY_FINGERPRINT, encrypt.encrypt_device_id(SECOND_ID)]


def test_authorized_is_false_for_an_empty_authfile(make_settings):
    settings = make_settings()
    auth.ensure_authfile(settings.authfile)
    assert auth.authorized([LEGACY_FINGERPRINT], settings) is False
    assert auth.authorized([], settings) is False
    assert auth.authorized([""], settings) is False


def test_a_v1_authfile_still_authorizes_its_devices(make_settings):
    """The upgrade must not invalidate devices authorized by the original scripts."""
    settings = make_settings()
    settings.authfile.write_text(f"{LEGACY_FINGERPRINT}\n", encoding="utf-8")

    assert auth.authorized([LEGACY_FINGERPRINT], settings) is True
    assert auth.authorized([encrypt.encrypt_device_id(SECOND_ID)], settings) is False


def test_write_authorized_leaves_no_temporary_file(make_settings):
    settings = make_settings()
    auth.write_authorized([LEGACY_FINGERPRINT], settings.authfile)

    assert not settings.authfile.with_name("authfile.txt.tmp").exists()
    content = settings.authfile.read_text(encoding="utf-8")
    assert content.startswith("#")
    assert LEGACY_FINGERPRINT in content


def test_read_authorized_survives_an_unreadable_file(make_settings):
    settings = make_settings()
    settings.authfile.mkdir()  # a directory where a file is expected
    assert auth.read_authorized(settings.authfile) == []


def test_connected_authorizes_every_connected_device(monkeypatch, make_settings):
    settings = make_settings()
    monkeypatch.setattr(auth, "current_device_ids", lambda: [DEVICE_ID, SECOND_ID])

    added = auth.connected(settings)

    assert added == [LEGACY_FINGERPRINT, encrypt.encrypt_device_id(SECOND_ID)]
    assert auth.authorized([LEGACY_FINGERPRINT], settings) is True
