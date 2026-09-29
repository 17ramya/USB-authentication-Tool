"""
Watch USB drives and authenticate them as they are connected.

    python main.py                # run the monitor (Ctrl+C to stop)
    python main.py --once         # authenticate what is connected now, then exit
    python main.py --list         # report devices, fingerprints and state
    python main.py --eject E:     # eject a drive (used when testing a deployment)

The v1 module only printed what it saw, had no way to stop other than killing the
process, and any exception raised inside the loop ended the monitor silently.  The
loop below isolates per-device failures, logs connect/disconnect events, and shuts
down cleanly on Ctrl+C.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Tuple

import auth
import auth1
import config
import driveletter
import eject
import encrypt

log = logging.getLogger(__name__)


def removable_drives(drive_provider=None) -> Set[str]:
    """Set of currently mounted removable drive letters.

    ``drive_provider`` is injectable for tests; the default reads the live system
    through :mod:`driveletter`.
    """
    provider = drive_provider or driveletter.removable_drive_letters
    try:
        return set(provider())
    except Exception as exc:
        log.error("could not enumerate drives: %s", exc)
        return set()


def detect_devices(
    previous: Optional[Iterable[str]] = None, drive_provider=None
) -> Tuple[Set[str], Set[str]]:
    """Return ``(added, removed)`` drive letters relative to ``previous``.

    Same contract as the v1 helper, but the previous snapshot is passed in rather
    than sampled inside the function.  That makes it testable and removes the
    fixed "sleep two seconds and hope nothing was plugged in meanwhile" blind spot.
    """
    before = set(previous or ())
    after = removable_drives(drive_provider)
    return after - before, before - after


def process_added(added: Iterable[str], settings: config.Settings) -> List[str]:
    """Authenticate each newly connected drive and return the outcomes."""
    outcomes: List[str] = []
    for drive in sorted(added):
        log.info("drive %s connected - authenticating", drive)
        try:
            outcomes.append(auth1.authentication(drive, settings))
        except Exception:
            # One failing device must never take the monitor down; fail closed by
            # ejecting the drive that caused the problem.
            log.exception("authentication of %s failed", drive)
            eject.eject_usb(drive, settings)
            outcomes.append(auth1.RESULT_DENIED)
    return outcomes


def report(settings: config.Settings) -> int:
    """Print connected devices, their fingerprints and their authorization state."""
    device_ids = auth.current_device_ids()
    drives = sorted(removable_drives())
    stored = auth.read_authorized(auth.authfile_path(settings))
    password_state = "yes" if settings.has_password else "NO - new devices cannot be allowed"

    print(f"{config.APP_NAME} {config.APP_VERSION}")
    print(f"authfile          : {settings.authfile} ({len(stored)} entries)")
    print(f"fingerprint mode  : {settings.hash_mode}")
    print(f"password set      : {password_state}")
    print(f"dry run           : {'yes' if settings.dry_run else 'no'}")
    print(f"removable drives  : {', '.join(drives) if drives else 'none'}")
    print(f"usb storage       : {len(device_ids)} device(s)")
    for device_id in device_ids:
        fingerprint = encrypt.device_fingerprint(device_id, settings)
        state = "authorized" if encrypt.is_match(stored, fingerprint) else "NOT authorized"
        print(f"  - {device_id}")
        print(f"      fingerprint : {fingerprint}")
        print(f"      state       : {state}")
    if not device_ids:
        print("  (no USB mass-storage device detected - plug one in and run again)")
    return 0


def configure_logging(settings: config.Settings) -> None:
    """Log to stderr, and additionally to a file when one is configured."""
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if settings.log_file:
        settings.log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(settings.log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, str(settings.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
        force=True,  # 3.8+: replace any handler a host application installed
    )


def run_monitor(
    settings: config.Settings, once: bool = False, drive_provider=None
) -> int:
    """Monitor removable drives until interrupted.

    ``once`` authenticates the drives that are already connected and returns
    instead of waiting for new ones - the fastest way to check a deployment.
    """
    current = removable_drives(drive_provider)

    if once:
        if not current:
            log.warning("no removable drive is connected")
            return 0
        process_added(current, settings)
        return 0

    log.info(
        "%s %s monitoring (poll %.1fs) - press Ctrl+C to stop",
        config.APP_NAME,
        config.APP_VERSION,
        settings.poll_seconds,
    )
    log.info("drives connected at start-up: %s", ", ".join(sorted(current)) or "none")

    while True:
        try:
            time.sleep(settings.poll_seconds)
            added, removed = detect_devices(current, drive_provider)
            for drive in sorted(removed):
                log.info("drive %s disconnected", drive)
            if added:
                process_added(added, settings)
            current = removable_drives(drive_provider)
        except KeyboardInterrupt:
            log.info("stopped")
            return 0
        except Exception:
            # A transient WMI or permission error must not end the session.
            log.exception("monitor cycle failed - continuing")
            time.sleep(min(settings.poll_seconds, 5.0))


def build_parser() -> argparse.ArgumentParser:
    """Command line interface definition."""
    parser = argparse.ArgumentParser(
        prog="usb-auth",
        description=(
            f"{config.APP_NAME} {config.APP_VERSION} - authorize USB drives and "
            "eject the ones that are not allowed."
        ),
        epilog=(
            "Configuration comes from the environment: "
            f"{config.ENV_AUTHFILE}, {config.ENV_PASSWORD_SHA256}, {config.ENV_PASSWORD}, "
            f"{config.ENV_MAX_ATTEMPTS}, {config.ENV_POLL_SECONDS}, {config.ENV_DRY_RUN}, "
            f"{config.ENV_HASH_MODE}, {config.ENV_SALT}, {config.ENV_LOG_LEVEL}, "
            f"{config.ENV_LOG_FILE}."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="authenticate the drives connected right now, then exit",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="report connected devices, their fingerprints and their state, then exit",
    )
    parser.add_argument("--eject", metavar="DRIVE", help="eject a drive letter, e.g. --eject E:")
    parser.add_argument("--authfile", metavar="PATH", help="override the authorized-device file")
    parser.add_argument("--poll", type=float, metavar="SECONDS", help="polling interval (default 2)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="log what would happen instead of ejecting drives",
    )
    parser.add_argument("--log-level", metavar="LEVEL", help="DEBUG, INFO, WARNING or ERROR")
    parser.add_argument("--log-file", metavar="PATH", help="also append logs to this file")
    parser.add_argument(
        "--version",
        action="version",
        version=f"{config.APP_NAME} {config.APP_VERSION}",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point used by main.py and by the packaged executable."""
    args = build_parser().parse_args(argv)

    try:
        settings = config.load_settings().with_overrides(
            authfile=Path(args.authfile) if args.authfile else None,
            poll_seconds=args.poll,
            dry_run=True if args.dry_run else None,
            log_level=args.log_level,
            log_file=Path(args.log_file) if args.log_file else None,
        )
    except config.ConfigurationError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    configure_logging(settings)

    if sys.platform != "win32":
        print(
            f"{config.APP_NAME} drives Windows devices (WMI, logical drives and the "
            "Win32 storage IOCTLs) and cannot run on this platform.",
            file=sys.stderr,
        )
        return 2

    if not settings.has_password:
        log.warning(config.missing_password_warning())

    if args.list:
        return report(settings)

    if args.eject:
        return 0 if eject.eject_usb(args.eject, settings) else 1

    return run_monitor(settings, once=args.once)


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    raise SystemExit(main())
