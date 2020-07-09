import winreg
from app.exception_definitions import reg_key_cannot_be_read_error

""" Registry Path """
REG_PATH = r"SOFTWARE\PR Watcher\Token"

""" Registry Key Names """
REG_API_VERSION_NAME = "API Version"
REG_ACCESS_TOKE_NAME = "Access Token"
REG_SERVER_ADDRESS_NAME = "Server Address"
REG_PROJECT_NAME = "Project"
REG_REPO_NAME = "Repository"

VALID_KEY_NAMES = [REG_API_VERSION_NAME, REG_ACCESS_TOKE_NAME, REG_SERVER_ADDRESS_NAME, REG_PROJECT_NAME, REG_REPO_NAME]


def write_reg_key(key_name, token):
    if key_name not in VALID_KEY_NAMES:
        return False
    try:
        print("Write registry key called, token: " + str(token))
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                                      winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, key_name, 0, winreg.REG_SZ, token)
        winreg.CloseKey(registry_key)
        return True
    except WindowsError:
        return False


def read_reg_key(key_name):
    if key_name not in VALID_KEY_NAMES:
        raise reg_key_cannot_be_read_error.RegKeyCannotBeReadError(str(key_name) + " is not a valid name!", key_name)
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                                      winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(registry_key, key_name)
        winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        raise reg_key_cannot_be_read_error.RegKeyCannotBeReadError("Windows error occurred!", key_name)
