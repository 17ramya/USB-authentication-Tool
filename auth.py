
                        ##### WRITING THE deviceID to authfile.txt #####

import subprocess

def connected():
    import win32com.client
    wmi = win32com.client.GetObject('winmgmts:')
    devices = wmi.InstancesOf('Win32_PnPEntity')
    serial_number = ""

    for device in devices:
        if device.ClassGuid == '{36fc9e60-c465-11cf-8056-444553540000}' and device.Name == 'USB Mass Storage Device':
            serial_number = device.DeviceID
            
            # Encrypt device id
            import encrypt
            serial_number=encrypt.encrypt_device_id(serial_number)
            break

              # Exit the loop after finding the first serial number

    # Read the existing serial numbers from the file
    existing_serial_numbers = []
    with open('authfile.txt', 'r') as f:

        existing_serial_numbers = f.readlines()


    # Check if the serial number is already present in the file
    if serial_number + '\n' not in existing_serial_numbers:
        # Append the new serial number to the existing numbers

        existing_serial_numbers.append(serial_number + '\n')

        # Write the serial numbers back to the file
        with open('authfile.txt', 'w') as f:

            f.writelines(existing_serial_numbers)
connected()
