
                                    ##### Ejecting USB using dive letter #####

import ctypes

def eject_usb():
    import driveletter
    driveletter = driveletter.find_usb_drive_letter()
    print(driveletter)


    # Define constants
    # CMF_DEVICE_NAME = "\\\\.\\G:"
    CMF_DEVICE_NAME = r"\\.\{}".format(driveletter)
    CMF_IOCTL_STORAGE_EJECT_MEDIA = 2967560

    # Open handle to drive
    handle = ctypes.windll.kernel32.CreateFileW(
        ctypes.c_wchar_p(CMF_DEVICE_NAME),
        ctypes.c_uint32(0x80000000),
        ctypes.c_uint32(0x00000003),
        None,
        ctypes.c_uint32(0x00000003),
        ctypes.c_uint32(0),
        None
    )

    # Send eject command to drive
    ctypes.windll.kernel32.DeviceIoControl(
        handle,
        CMF_IOCTL_STORAGE_EJECT_MEDIA,
        None,
        0,
        None,
        0,
        ctypes.pointer(ctypes.c_ulong()),
        None
    )

    # Close handle to drive
    ctypes.windll.kernel32.CloseHandle(handle)
