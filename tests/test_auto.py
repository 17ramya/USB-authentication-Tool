"""Monitor and CLI tests - drive enumeration is injected, no hardware is touched."""

from __future__ import annotations

import pytest

import auth
import auth1
import auto
import config
import eject

DEVICE_ID = r"USB\VID_0781&PID_5567\4C530001231031117553"


def provider(*snapshots):
    """A drive provider returning the given snapshots, then repeating the last."""
    remaining = list(snapshots)

    def _provider():
        return list(remaining.pop(0) if remaining else snapshots[-1])

    return _provider


def test_detect_devices_reports_additions_and_removals():
    added, removed = auto.detect_devices(["C:", "E:"], provider(["C:", "F:"]))
    assert added == {"F:"}
    assert removed == {"E:"}


def test_detect_devices_without_changes():
    added, removed = auto.detect_devices(["E:"], provider(["E:"]))
    assert added == set()
    assert removed == set()


def test_removable_drives_survives_a_failing_provider():
    def broken():
        raise OSError("win32api is unavailable")

    assert auto.removable_drives(broken) == set()


def test_process_added_authenticates_each_drive_in_order(monkeypatch, settings):
    seen = []
    monkeypatch.setattr(
        auth1,
        "authentication",
        lambda letter, settings=None: seen.append(letter) or auth1.RESULT_AUTHORIZED,
    )

    outcomes = auto.process_added(["F:", "E:"], settings)

    assert seen == ["E:", "F:"]
    assert outcomes == [auth1.RESULT_AUTHORIZED, auth1.RESULT_AUTHORIZED]


def test_process_added_fails_closed_when_authentication_raises(monkeypatch, settings):
    def boom(letter, settings=None):
        raise RuntimeError("wmi exploded")

    ejected = []
    monkeypatch.setattr(auth1, "authentication", boom)
    monkeypatch.setattr(eject, "eject_usb", lambda letter, settings: ejected.append(letter) or True)

    assert auto.process_added(["E:"], settings) == [auth1.RESULT_DENIED]
    assert ejected == ["E:"]


def test_run_monitor_once_authenticates_connected_drives(monkeypatch, settings):
    seen = []
    monkeypatch.setattr(
        auth1,
        "authentication",
        lambda letter, settings=None: seen.append(letter) or auth1.RESULT_AUTHORIZED,
    )

    assert auto.run_monitor(settings, once=True, drive_provider=provider(["E:", "F:"])) == 0
    assert seen == ["E:", "F:"]


def test_run_monitor_once_without_drives_exits_cleanly(settings):
    assert auto.run_monitor(settings, once=True, drive_provider=provider([])) == 0


def test_run_monitor_stops_on_keyboard_interrupt(monkeypatch, settings):
    def interrupt(seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(auto.time, "sleep", interrupt)

    assert auto.run_monitor(settings, drive_provider=provider(["E:"])) == 0


def test_run_monitor_keeps_going_after_a_failed_cycle(monkeypatch, settings):
    """A transient failure must not end the monitoring session."""
    cycles = {"count": 0}

    def flaky(previous, drive_provider=None):
        cycles["count"] += 1
        if cycles["count"] == 1:
            raise RuntimeError("wmi glitch")
        raise KeyboardInterrupt

    monkeypatch.setattr(auto, "detect_devices", flaky)
    monkeypatch.setattr(auto.time, "sleep", lambda seconds: None)

    assert auto.run_monitor(settings, drive_provider=provider(["E:"])) == 0
    assert cycles["count"] == 2


def test_report_lists_devices_and_their_state(monkeypatch, settings, capsys):
    monkeypatch.setattr(auth, "current_device_ids", lambda: [DEVICE_ID])
    monkeypatch.setattr(auto, "removable_drives", lambda drive_provider=None: {"E:"})

    assert auto.report(settings) == 0

    output = capsys.readouterr().out
    assert DEVICE_ID in output
    assert "NOT authorized" in output
    assert "E:" in output
    assert str(settings.authfile) in output


def test_main_reports_configuration_errors(monkeypatch, capsys):
    monkeypatch.setenv(config.ENV_POLL_SECONDS, "soon")

    assert auto.main(["--list"]) == 2
    assert "configuration error" in capsys.readouterr().err


def test_main_refuses_non_windows_platforms(monkeypatch, settings, capsys):
    monkeypatch.setattr(auto.sys, "platform", "linux")

    assert auto.main(["--list"]) == 2
    assert "Windows" in capsys.readouterr().err


def test_main_version_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exit_info:
        auto.main(["--version"])

    assert exit_info.value.code == 0
    assert config.APP_VERSION in capsys.readouterr().out


def test_main_eject_returns_one_when_no_drive_is_found(monkeypatch, settings):
    # Pin the platform so the test asserts the eject path on every CI runner.
    monkeypatch.setattr(auto.sys, "platform", "win32")
    monkeypatch.setattr(auto.eject, "eject_usb", lambda letter, settings: False)

    assert auto.main(["--eject", "E:"]) == 1
