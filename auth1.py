
             ##### READING THE deviceID FROM authfile.txt #####

import subprocess
import tkinter as tk
from tkinter import simpledialog

def authentication():
    print("write")
    ## getting deviceID of connected USB ##
    import win32com.client
    wmi = win32com.client.GetObject('winmgmts:')
    devices = wmi.InstancesOf('Win32_PnPEntity')
    serial_number = ""
    for device in devices:
        if device.ClassGuid == '{36fc9e60-c465-11cf-8056-444553540000}' and device.Name == 'USB Mass Storage Device':
            serial_number = device.DeviceID

            import encrypt
            serial_number=encrypt.encrypt_device_id(serial_number)
            print("encrypted:",serial_number)
            break


    # Read the deviceID from a file ###
    with open('authfile.txt', 'r') as f:
        auth_devices = f.readlines()

        device_found = False  # Flag to track if the device ID is found in the file
        for line in auth_devices:

            auth_device = line.strip()
            print("Line:",auth_device)
            if serial_number in auth_device:
                ## if deviceID present in authfile.txt, then it is considered authenticated ###
                device_found = True
                break

        if device_found:
            import pythonpopup
            pythonpopup.authenticated()
        else:
            import pythonpopup
            pythonpopup.popup()

    root = tk.Tk()
    root.withdraw()
