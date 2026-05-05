"""
Utilitaires pour améliorer la stabilité et les performances de l'application.
Fournit des wrappers pour la gestion des erreurs, conflits et cache.
"""

import threading
import traceback
from functools import wraps
from datetime import datetime
from flask import jsonify, flash, redirect, url_for, request, current_app


# ==================== GESTION DES ERREURS ====================

def handle_errors(return_json=None):
    """
    Décorateur pour gérer les erreurs de manière cohérente.

    Args:
        return_json: Si True, retourne toujours JSON. Si False, redirige. Si None, détecte automatiquement.

    Usage:
        @app.route("/api/something")
        @handle_errors(return_json=True)
        def my_api_route():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except ValueError as e:
                # Erreurs de validation (400 Bad Request)
                current_app.logger.warning(f"Validation error in {f.__name__}: {e}")
                if return_json or (return_json is None and request.is_json):
                    return jsonify({"error": "Données invalides", "details": str(e)}), 400
                else:
                    flash(f"Erreur de validation: {e}", "warning")
                    return redirect(request.referrer or url_for("main.home"))

            except PermissionError as e:
                # Erreurs de permission (403 Forbidden)
                current_app.logger.warning(f"Permission denied in {f.__name__}: {e}")
                if return_json or (return_json is None and request.is_json):
                    return jsonify({"error": "Permission refusée", "details": str(e)}), 403
                else:
                    flash("Vous n'avez pas la permission d'effectuer cette action.", "danger")
                    return redirect(url_for("main.home"))

            except LookupError as e:
                # Ressource introuvable (404 Not Found)
                current_app.logger.warning(f"Resource not found in {f.__name__}: {e}")
                if return_json or (return_json is None and request.is_json):
                    return jsonify({"error": "Ressource introuvable", "details": str(e)}), 404
                else:
                    flash(f"Ressource introuvable: {e}", "warning")
                    return redirect(url_for("main.home"))

            except ConflictError as e:
                # Conflit de modification concurrente (409 Conflict)
                current_app.logger.warning(f"Conflict detected in {f.__name__}: {e}")
                if return_json or (return_json is None and request.is_json):
                    return jsonify({
                        "error": "conflit_modification",
                        "message": str(e)
                    }), 409
                else:
                    flash(str(e), "warning")
                    return redirect(request.referrer or url_for("main.home"))

            except Exception as e:
                # Erreur serveur générique (500 Internal Server Error)
                current_app.logger.error(f"Unexpected error in {f.__name__}: {e}")
                current_app.logger.error(traceback.format_exc())
                if return_json or (return_json is None and request.is_json):
                    return jsonify({"error": "Erreur serveur", "details": str(e)}), 500
                else:
                    flash("Une erreur est survenue. Veuillez réessayer.", "danger")
                    return redirect(url_for("main.home"))

        return decorated_function
    return decorator


# ==================== EXCEPTIONS PERSONNALISÉES ====================

class ConflictError(Exception):
    """Exception levée lors d'un conflit de modification concurrente."""
    pass


# ==================== GESTION DES ACTIONS CONCURRENTES ====================

_ALLOWED_TABLES = {"incidents", "techniciens", "users", "historique"}


def check_version_conflict(db, table, record_id, expected_version):
    """
    Vérifie si la version d'un enregistrement correspond à la version attendue.
    Lève une ConflictError si conflit détecté.

    Args:
        db: Connexion DB
        table: Nom de la table (doit être dans _ALLOWED_TABLES)
        record_id: ID de l'enregistrement
        expected_version: Version attendue (ou None pour ignorer)

    Returns:
        dict: L'enregistrement actuel

    Raises:
        ValueError: Si la table n'est pas dans le whitelist
        ConflictError: Si la version ne correspond pas
        LookupError: Si l'enregistrement n'existe pas
    """
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"Table non autorisée: {table!r}")

    if expected_version is None:
        record = db.execute(f"SELECT * FROM {table} WHERE id=%s", (record_id,)).fetchone()
        if not record:
            raise LookupError(f"{table.capitalize()} avec id={record_id} introuvable")
        return record

    record = db.execute(
        f"SELECT * FROM {table} WHERE id=%s",
        (record_id,)
    ).fetchone()

    if not record:
        raise LookupError(f"{table.capitalize()} avec id={record_id} introuvable")

    if 'version' in record.keys() and int(expected_version) != record['version']:
        raise ConflictError(
            f"Ce {table} a été modifié par quelqu'un d'autre. "
            "Veuillez recharger la page et réessayer."
        )

    return record


# ==================== CACHE SIMPLE POUR LES DONNÉES DE RÉFÉRENCE ====================

class SimpleCache:
    """Cache simple en mémoire pour les données de référence — thread-safe via threading.Lock."""
    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key):
        """Récupère une valeur du cache si elle n'a pas expiré."""
        with self._lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                if (datetime.now() - timestamp).total_seconds() < self._ttl:
                    return data
                del self._cache[key]
        return None

    def set(self, key, value):
        """Stocke une valeur dans le cache."""
        with self._lock:
            self._cache[key] = (value, datetime.now())

    def clear(self, key=None):
        """Vide le cache (entièrement ou pour une clé spécifique)."""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()


# Instance globale du cache
app_cache = SimpleCache(ttl_seconds=300)  # 5 minutes TTL
