
                    #### TO DETECT USBs THAT ARE CONNECTED ####

import win32api
import time

def detect_devices():
    original = set(win32api.GetLogicalDriveStrings().split('\x00')[:-1])
    print('Detecting...')
    time.sleep(2)
    current = set(win32api.GetLogicalDriveStrings().split('\x00')[:-1])

    added = current - original
    if added:
        #### USBs connected ###
        print(f'{len(added)} drives added:')
        for drive in added:
            import auth1
            auth1.authentication()
            print(drive)

    removed = original - current
    if removed:
        #### USBs disconnected ###
        print(f'{len(removed)} drives removed:')
        for drive in removed:
            print(drive)

if __name__ == '__main__':
    while True:
        detect_devices()

