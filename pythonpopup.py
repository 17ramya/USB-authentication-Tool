
                 ##### UI DESIGN (POPUP) FOR AUTHENTICATION ######

# tkinter library of python to design popup
import tkinter as tk
from tkinter import messagebox, simpledialog

def popup():
    # Create the main application window
    root = tk.Tk()
    # root.option_add('*Dialog.msg.font', 'Arial')
    root.withdraw()

    # Create the overlay window
    overlay = tk.Toplevel(root)
    overlay.overrideredirect(True)  # Remove window decorations
    overlay.attributes('-alpha', 0.7)  # Set transparency level (0.0 - fully transparent, 1.0 - fully opaque)
    overlay.geometry(str(root.winfo_screenwidth()) + 'x' + str(root.winfo_screenheight()))  # Set window size to cover the entire screen
    overlay.configure(background='black')  # Set the background color to black

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    dialog_width = 300
    dialog_height = 200
    x_position = int((screen_width / 2) - (dialog_width / 2))
    y_position = int((screen_height / 2) - (dialog_height / 2))

    root.geometry(f"{dialog_width}x{dialog_height}+{x_position}+{y_position}")

    # Create the popup content
    answer = messagebox.askquestion(
        "USB not authenticated",
        "Do you want to allow the device to access your computer?",
        icon='warning',
        type='yesno',
        parent=overlay

    )

    if answer == 'yes':
        password = simpledialog.askstring("Password", "Enter password:", show = "*", parent=root)
        if password == '123':
            import auth
            auth.connected()
            messagebox.showinfo("Authentication status", "Device Authenticated", parent=overlay)
            # Correct password -> considered authenticated
        else:
            messagebox.showerror("File access not allowed", "Incorrect  password", parent=overlay)
            # Incorrect password -> not authenticated
            import eject
            eject.eject_usb()
            messagebox.showinfo("Not authenticated", "Device ejected", parent=overlay)
    else:
        import eject
        eject.eject_usb()
        messagebox.showinfo("Not authenticated", "Device ejected", parent=overlay)

    # Destroy the overlay and main windows
    overlay.destroy()
    root.destroy()


    #Popup to display device authenticated message
def authenticated():
    root = tk.Tk()
    # root.option_add('*Dialog.msg.font', 'Arial')
    root.withdraw()

    # Create the overlay window
    overlay = tk.Toplevel(root)
    overlay.overrideredirect(True)  # Remove window decorations
    overlay.attributes('-alpha', 0.7)  # Set transparency level (0.0 - fully transparent, 1.0 - fully opaque)
    overlay.geometry(str(root.winfo_screenwidth()) + 'x' + str(root.winfo_screenheight()))  # Set window size to cover the entire screen
    overlay.configure(background='black')  # Set the background color to black

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    dialog_width = 300
    dialog_height = 200
    x_position = int((screen_width / 2) - (dialog_width / 2))
    y_position = int((screen_height / 2) - (dialog_height / 2))

    root.geometry(f"{dialog_width}x{dialog_height}+{x_position}+{y_position}")
    messagebox.showinfo("Authentication status", "Device Authenticated", parent=overlay)
    overlay.destroy()
    root.destroy()
