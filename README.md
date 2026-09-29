# USB Authentication Tool

A Python-based utility to authenticate USB drives automatically upon connection. 

## Features
- **Auto-Detection**: Continuously monitors for connected USB devices.
- **Hardware ID Validation**: Validates the unique Device ID of the inserted USB mass storage against a predefined list of authorized devices (`authfile.txt`).
- **Encryption**: Encrypts the device ID for secure storage and comparison.
- **Interactive Prompts**: Prompts the user with an interactive GUI (built with `tkinter`) if an unauthorized USB drive is connected.
- **Password Protection**: Allows emergency access to unauthorized devices via a password prompt.
- **Auto-Eject**: Automatically ejects the USB drive if the user denies access or fails the password check.

## Architecture & Modules
- `auto.py`: The main entry point. Runs continuously in the background to detect when a USB drive is added or removed.
- `auth1.py`: Extracts the hardware Device ID of the connected USB drive and checks it against `authfile.txt`.
- `encrypt.py`: Handles the encryption of the USB Device ID.
- `pythonpopup.py`: Displays graphical Tkinter popups asking for permission and/or a password if the device is not pre-authorized.
- `eject.py`: Handles the automatic ejection of unauthorized USB drives.

## Requirements
- Windows OS (uses `win32api` and `wmic` for drive detection)
- Python 3.x
- `pywin32` library (for `win32api`)

## Usage
1. Add authorized encrypted Device IDs to `authfile.txt`.
2. Run `auto.py` in the background.

```bash
python auto.py
```
