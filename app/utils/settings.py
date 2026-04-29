import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'settings.json')

def get_setting(key, default=None):
    try:
        if not os.path.exists(SETTINGS_FILE):
            return default
        with open(SETTINGS_FILE, 'r') as f:
            data = json.load(f)
            return data.get(key, default)
    except Exception:
        return default

def set_setting(key, value):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        data = {}
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
        data[key] = value
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving setting {key}: {e}")
