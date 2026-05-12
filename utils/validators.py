# ------------------------------------------------------------------ VALIDATE
import re


def validate_filename(name):
    if not name or not name.strip():
        return False, "Name cannot be empty."
    if name != name.strip():
        return False, "Name cannot have leading or trailing whitespace."
    if name in ['.', '..']:
        return False, "Name cannot be '.' or '..'."
    if re.search(r'[<>:"/\\|?*]', name):
        return False, "Name contains at least one forbidden character:\n\n<  >  :  \"  /  \\  |  ?  *"
    if name.lower().endswith(('.json', '.txt', '.csv')):
        return False, "Name should not end with file extensions (.json, .txt, .csv).\nThey are added automatically."
    return True, None

