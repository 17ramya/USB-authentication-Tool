#!/usr/bin/env python3
"""
Entry point for the USB authentication tool.

Examples
--------
    python main.py                  # monitor and authenticate devices as they arrive
    python main.py --list           # show connected devices, fingerprints and state
    python main.py --once           # authenticate what is connected right now, then exit
    python main.py --help           # all options

The packaged equivalent is ``USB-Authentication-Tool.exe`` (see build.ps1).
"""

from __future__ import annotations

from auto import main as run_cli


def main(argv=None) -> int:
    """Run the command line interface and return the process exit code."""
    return run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
