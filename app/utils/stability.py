"""
Utilitaires pour améliorer la stabilité et les performances de l'application.
Fournit des wrappers pour la gestion des transactions, des erreurs et des conflits.
"""

from contextlib import contextmanager
from functools import wraps
from flask import jsonify, flash, redirect, url_for, request, current_app
from datetime import datetime
import traceback


# ==================== GESTION DES TRANSACTIONS ====================

@contextmanager
def db_transaction(conn=None):
    """
    Context manager pour des transactions atomiques PostgreSQL.

    Usage:
        with db_transaction() as db:
            db.execute("UPDATE ...")
            db.execute("INSERT ...")
        # Auto-commit si succès, auto-rollback si erreur

    Args:
        conn: Connexion DB existante (optionnel). Si None, crée une nouvelle connexion.

    Yields:
        Connection DB

    Raises:
        Exception: Propage toute exception après rollback
    """
    from db_config import get_db

    db = conn if conn else get_db()
    created_connection = conn is None

    try:
        db.execute("BEGIN")
        yield db
        db.commit()
        current_app.logger.debug("Transaction committed successfully")
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Transaction rollback due to error: {e}")
        current_app.logger.error(traceback.format_exc())
        raise
    finally:
        if created_connection:
            db.close()


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

def check_version_conflict(db, table, record_id, expected_version):
    """
    Vérifie si la version d'un enregistrement correspond à la version attendue.
    Lève une ConflictError si conflit détecté.

    Args:
        db: Connexion DB
        table: Nom de la table
        record_id: ID de l'enregistrement
        expected_version: Version attendue (ou None pour ignorer)

    Returns:
        dict: L'enregistrement actuel

    Raises:
        ConflictError: Si la version ne correspond pas
        LookupError: Si l'enregistrement n'existe pas
    """
    if expected_version is None:
        # Pas de vérification de version
        record = db.execute(f"SELECT * FROM {table} WHERE id=?", (record_id,)).fetchone()
        if not record:
            raise LookupError(f"{table.capitalize()} avec id={record_id} introuvable")
        return record

    record = db.execute(
        f"SELECT * FROM {table} WHERE id=?",
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


def add_historique_entry(db, incident_id, champ, ancienne_valeur, nouvelle_valeur, modifie_par):
    """
    Ajoute une entrée dans la table historique.

    Args:
        db: Connexion DB
        incident_id: ID de l'incident
        champ: Nom du champ modifié
        ancienne_valeur: Ancienne valeur
        nouvelle_valeur: Nouvelle valeur
        modifie_par: Utilisateur ayant effectué la modification
    """
    db.execute("""
        INSERT INTO historique (
            incident_id, champ, ancienne_valeur,
            nouvelle_valeur, modifie_par, date_modification
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        incident_id,
        champ,
        str(ancienne_valeur) if ancienne_valeur is not None else "",
        str(nouvelle_valeur) if nouvelle_valeur is not None else "",
        modifie_par,
        datetime.now().strftime("%d-%m-%Y %H:%M")
    ))
    current_app.logger.info(
        f"Historique: {modifie_par} a modifié {champ} de l'incident {incident_id}: "
        f"{ancienne_valeur} → {nouvelle_valeur}"
    )


# ==================== VALIDATION DES PERMISSIONS ====================

def require_role(*allowed_roles):
    """
    Décorateur pour restreindre l'accès à certains rôles.

    Usage:
        @app.route("/admin/something")
        @require_role("admin")
        def admin_only():
            ...

    Args:
        *allowed_roles: Liste des rôles autorisés ("admin", "technicien", etc.)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import session

            if "user" not in session:
                if request.is_json:
                    return jsonify({"error": "Non authentifié"}), 401
                else:
                    return redirect(url_for("auth.login"))

            if session.get("role") not in allowed_roles:
                raise PermissionError(
                    f"Rôle requis: {', '.join(allowed_roles)}. "
                    f"Votre rôle actuel: {session.get('role')}"
                )

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# ==================== VALIDATION DES DONNÉES ====================

def validate_required_fields(data, required_fields):
    """
    Valide que tous les champs requis sont présents et non vides.

    Args:
        data: dict ou request.form/request.json
        required_fields: liste des champs requis

    Raises:
        ValueError: Si un champ requis est manquant ou vide
    """
    missing = []
    for field in required_fields:
        value = data.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(field)

    if missing:
        raise ValueError(f"Champs requis manquants: {', '.join(missing)}")


# ==================== HELPERS POUR LES NOTIFICATIONS TEMPS RÉEL ====================

def emit_incident_update(socketio, action, incident_id=None, **extra_data):
    """
    Émet une notification Socket.IO avec des données structurées.

    Args:
        socketio: Instance SocketIO
        action: Type d'action ("add", "edit", "delete", "reassign", "etat", "note", etc.)
        incident_id: ID de l'incident (optionnel)
        **extra_data: Données supplémentaires à inclure
    """
    payload = {
        "action": action,
        "timestamp": datetime.now().isoformat()
    }

    if incident_id is not None:
        payload["incident_id"] = incident_id

    payload.update(extra_data)

    socketio.emit("incident_update", payload, broadcast=True)
    current_app.logger.debug(f"Socket.IO emit: {payload}")


# ==================== CACHE SIMPLE POUR LES DONNÉES DE RÉFÉRENCE ====================

class SimpleCache:
    """Cache simple en mémoire pour les données de référence (statuts, priorités, etc.)"""

    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self._ttl = ttl_seconds

    def get(self, key):
        """Récupère une valeur du cache si elle n'a pas expiré."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self._ttl:
                return data
            else:
                del self._cache[key]
        return None

    def set(self, key, value):
        """Stocke une valeur dans le cache."""
        self._cache[key] = (value, datetime.now())

    def clear(self, key=None):
        """Vide le cache (entièrement ou pour une clé spécifique)."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()


# Instance globale du cache
app_cache = SimpleCache(ttl_seconds=300)  # 5 minutes TTL
