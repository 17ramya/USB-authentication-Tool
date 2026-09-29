
                        ##### WRITING THE deviceID to authfile.txt #####

import subprocess

def connected():
    import subprocess

    cmd = 'wmic path Win32_PnPEntity where "ClassGuid=\'{36fc9e60-c465-11cf-8056-444553540000}\'" get DeviceId,Name'
    output = subprocess.check_output(cmd, shell=True)
    serial_number = ""

    # Decode the output into a string
    output_str = output.decode('utf-8')

    # Split the string into lines
    output_lines = output_str.split('\r\r\n')

    # Look for the line containing the USB drive's serial number
    for line in output_lines:
        if 'USB Mass Storage Device' in line:
            serial_number = line.split()[0]
            # Encrypt device id
            import encrypt
            serial_number=encrypt.encrypt_device_id(serial_number)

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
