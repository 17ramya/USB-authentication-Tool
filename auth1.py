
             ##### READING THE deviceID FROM authfile.txt #####

import subprocess
import tkinter as tk
from tkinter import simpledialog

def authentication():
    print("write")
    ## getting deviceID of connected USB ##
    cmd = 'wmic path Win32_PnPEntity where "ClassGuid=\'{36fc9e60-c465-11cf-8056-444553540000}\'" get DeviceId,Name'
    print(cmd)
    output = subprocess.check_output(cmd, shell=True)
    serial_number = ""
    output_str = output.decode('utf-8')
    output_lines = output_str.split('\r\r\n')
    print(output_lines)
    for line in output_lines:
        if 'USB Mass Storage Device' in line:
            serial_number = line.split()[0]

            import encrypt
            serial_number=encrypt.encrypt_device_id(serial_number)
            print("encrypted:",serial_number)


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
