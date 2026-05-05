import json
import os
import logging

logger = logging.getLogger(__name__)

_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'settings.json')


def _use_db():
    """Retourne True si on peut utiliser la base de données."""
    try:
        from flask import has_app_context
        return has_app_context()
    except Exception:
        return False


def get_setting(key, default=None):
    if _use_db():
        try:
            from app.utils.db_config import get_db
            row = get_db().execute(
                "SELECT value FROM app_settings WHERE key=%s", (key,)
            ).fetchone()
            if row is None:
                return default
            raw = row["value"]
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        except Exception as e:
            logger.warning(f"get_setting DB error for '{key}': {e}")
            return default

    try:
        if not os.path.exists(_SETTINGS_FILE):
            return default
        with open(_SETTINGS_FILE, 'r') as f:
            return json.load(f).get(key, default)
    except Exception:
        return default


def set_setting(key, value):
    serialized = json.dumps(value)
    if _use_db():
        try:
            from app.utils.db_config import get_db
            db = get_db()
            db.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=CURRENT_TIMESTAMP
                """,
                (key, serialized),
            )
            db.commit()
            return
        except Exception as e:
            logger.error(f"set_setting DB error for '{key}': {e}")
            return

    try:
        os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
        data = {}
        if os.path.exists(_SETTINGS_FILE):
            with open(_SETTINGS_FILE, 'r') as f:
                data = json.load(f)
        data[key] = value
        with open(_SETTINGS_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"set_setting file error for '{key}': {e}")
