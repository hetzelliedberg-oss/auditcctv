import os
import win32file
import win32con

def copy_locked_file(src, dst):
    h_file = win32file.CreateFile(
        src,
        win32con.GENERIC_READ,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None,
        win32con.OPEN_EXISTING,
        win32con.FILE_ATTRIBUTE_NORMAL,
        None
    )
    with open(dst, "wb") as f_out:
        while True:
            err, data = win32file.ReadFile(h_file, 64 * 1024)
            if not data:
                break
            f_out.write(data)
    win32file.CloseHandle(h_file)
