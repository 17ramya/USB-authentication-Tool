"""Fingerprint tests.

The legacy vectors below were produced by the *original* ``encrypt.py`` before the
upgrade, so these tests prove that an existing ``authfile.txt`` keeps working and
that already authorized devices do not have to be re-added after deploying.
"""

from __future__ import annotations

import pytest

import config
import encrypt

LEGACY_VECTORS = [
    (
        r"USB\VID_0781&PID_5567\4C530001231031117553",
        r"OMV\PCX_xefy&JCX_ccde\bWcaxxxyzayxayyyecca",
    ),
    (
        r"USB\VID_0BC2&PID_2312\00000000ABCD",
        r"MKT\NAV_vTUx&HAV_xywx\vvvvvvvvSTUV",
    ),
    (
        r"USB\VID_13FE&PID_4200\070B7A2A0C1E&0",
        r"JHQ\KXS_tvUT&EXS_wuss\szsQzPuPsRtT&s",
    ),
    (
        r"USB\VID_046D&PID_C534\5&2B4A3C1&0&1",
        r"OMV\PCX_xbdX&JCX_Wcab\c&zVbUaWy&x&y",
    ),
]


@pytest.mark.parametrize("device_id, expected", LEGACY_VECTORS)
def test_legacy_algorithm_is_frozen(device_id, expected):
    """The v1 obfuscation must never change - stored fingerprints depend on it."""
    assert encrypt.encrypt_device_id(device_id) == expected


def test_fingerprint_defaults_to_legacy_mode(make_settings):
    settings = make_settings()
    assert settings.hash_mode == config.HASH_MODE_LEGACY
    assert encrypt.device_fingerprint(LEGACY_VECTORS[0][0], settings) == LEGACY_VECTORS[0][1]


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_blank_device_id_produces_no_fingerprint(blank, make_settings):
    """Regression: a blank id must never become a usable fingerprint."""
    assert encrypt.device_fingerprint(blank, make_settings()) == ""


def test_sha256_mode_is_salted_and_stable(make_settings):
    salted = make_settings(hash_mode=config.HASH_MODE_SHA256, salt="pepper")
    other_salt = make_settings(hash_mode=config.HASH_MODE_SHA256, salt="different")

    device_id = LEGACY_VECTORS[0][0]
    digest = encrypt.device_fingerprint(device_id, salted)

    assert digest.startswith(encrypt.SHA256_PREFIX)
    assert len(digest) == len(encrypt.SHA256_PREFIX) + 64
    assert digest == encrypt.device_fingerprint(device_id, salted)
    assert digest != encrypt.device_fingerprint(device_id, other_salt)
    assert digest != encrypt.device_fingerprint(LEGACY_VECTORS[1][0], salted)


def test_is_match_is_case_insensitive_and_ignores_noise(make_settings):
    stored = ["  omv\\pcx_xefy&jcx_ccde\\bwcaxxxyzayxayyyecca  ", "# comment", ""]
    fingerprint = encrypt.device_fingerprint(LEGACY_VECTORS[0][0], make_settings())
    assert encrypt.is_match(stored, fingerprint)


def test_is_match_rejects_blank_candidate():
    """Regression: v1 used ``"" in line``, which matched every entry.

    A device Windows could not identify was therefore reported as authenticated.
    """
    assert encrypt.is_match(["SOME\\ENTRY"], "") is False
    assert encrypt.is_match(["SOME\\ENTRY"], "   ") is False
    assert encrypt.is_match([], "SOME\\ENTRY") is False


def test_is_match_is_not_a_prefix_match():
    assert encrypt.is_match(["ABCDEF"], "ABC") is False
    assert encrypt.is_match(["ABC"], "ABCDEF") is False


def test_read_entries_skips_comments_and_duplicates():
    """Entries keep their spelling, but duplicates are detected case-insensitively."""
    lines = ["# header", "", "  abc  ", "ABC", "def\n"]
    assert encrypt.read_entries(lines) == ["abc", "def"]


def test_is_comment_distinguishes_content_from_noise():
    assert encrypt.is_comment("# note") is True
    assert encrypt.is_comment("   ") is True
    assert encrypt.is_comment("ABC") is False
