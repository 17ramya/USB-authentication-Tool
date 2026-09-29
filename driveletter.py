
                  ###### Finding drive letter of connected USB to eject ######

import win32com.client

def find_usb_drive_letter():
    wmi = win32com.client.GetObject("winmgmts:")
    drives = wmi.ExecQuery("SELECT * FROM Win32_DiskDrive WHERE InterfaceType='USB'")

    for drive in drives:
        partitions = drive.Associators_("Win32_DiskDriveToDiskPartition")
        for partition in partitions:
            logical_disks = partition.Associators_("Win32_LogicalDiskToPartition")
            for disk in logical_disks:
                drive_letter = disk.DeviceID
                print(f"Drive Letter: {drive_letter}")
                return drive_letter

    return None
