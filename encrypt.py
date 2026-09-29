
                                ##### Encrypting USB device id #####

def encrypt_device_id(device_id):
    key = sum(ord(char) for char in device_id) % 26 + 1  # Device-specific encryption key
    encrypted_id = ""

    for char in device_id:
        if char.isalnum():
            if char.isupper():
                encrypted_char = chr((ord(char) + key - 65) % 26 + 65)
            else:
                encrypted_char = chr((ord(char) + key - 97) % 26 + 97)
        else:
            encrypted_char = char
        encrypted_id += encrypted_char

    return encrypted_id
