from datetime import datetime, timedelta
from flask import request, session
from app.utils.db_config import get_db
from app import socketio
from flask_socketio import emit

def _can_access_incident(db, incident):
    """Vérifie si l'utilisateur connecté peut accéder à l'incident.
    Utilise le tech_id mis en cache dans la session pour éviter une requête DB à chaque appel."""
    if session.get("role") in ["admin", "superadmin"]:
        return True

    tech_id = incident.get("technicien_id")
    current_user = session.get("user")
    if not current_user:
        return False

    cached_tech_id = session.get("tech_id")
    if cached_tech_id is None:
        tech = db.execute("SELECT id FROM techniciens WHERE username=%s", (current_user,)).fetchone()
        if not tech:
            return False
        cached_tech_id = tech["id"]
        session["tech_id"] = cached_tech_id

    return cached_tech_id == tech_id

def _is_api_or_ajax_request():
    """Détecte si la requête est une API ou AJAX"""
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or (request.path and request.path.startswith('/api/'))

def _get_current_tech_info(db):
    """Récupère les infos du technicien connecté"""
    if "user" not in session: return None
    return db.execute("SELECT * FROM techniciens WHERE username=%s", (session["user"],)).fetchone()


ADMIN_SOCKET_ROOM = "role:admin"
RELANCE_DELAYS_HOURS = {
    "Critique": 2,
    "Haute": 4,
    "Moyenne": 8,
    "Basse": 24
}
RELANCE_DEFAULT_DELAY_HOURS = 24

def _socket_tech_room(technician_name):
    return f"tech:{(technician_name or '').strip().lower()}"

def _event_rooms_for_technicians(technician_names=None):
    rooms = {ADMIN_SOCKET_ROOM}
    for name in technician_names or []:
        if name:
            rooms.add(_socket_tech_room(name))
    return rooms

def _emit_event_to_rooms(event_name, payload, rooms):
    for room in rooms:
        socketio.emit(event_name, payload, room=room)

def _emit_incident_event(event_name, incident_id, db=None, technician_names=None, **extra_payload):
    incident_id = int(incident_id)
    version = extra_payload.pop("version", None)
    inferred_tech = None

    if db is not None and (version is None or not technician_names):
        inc_meta = db.execute(
            "SELECT collaborateur, version FROM incidents WHERE id=%s",
            (incident_id,),
        ).fetchone()
        if inc_meta:
            if version is None:
                version = inc_meta.get("version")
            inferred_tech = inc_meta.get("collaborateur")

    tech_names = list(technician_names or [])
    if inferred_tech and inferred_tech not in tech_names:
        tech_names.append(inferred_tech)

    payload = {"id": incident_id, "incident_id": incident_id}
    if version is not None:
        payload["version"] = version
    payload.update(extra_payload)

    _emit_event_to_rooms(event_name, payload, _event_rooms_for_technicians(tech_names))
    return payload

def _emit_bulk_refresh(reason, technician_names=None, incident_id=None):
    payload = {"reason": reason}
    if incident_id is not None:
        payload["incident_id"] = int(incident_id)
    _emit_event_to_rooms(
        "bulk_refresh_required",
        payload,
        _event_rooms_for_technicians(technician_names),
    )

def _log_historique(db, incident_id, champ, ancienne_valeur, nouvelle_valeur, modifie_par):
    db.execute(
        """
        INSERT INTO historique (
            incident_id, champ, ancienne_valeur,
            nouvelle_valeur, modifie_par, date_modification
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            incident_id,
            champ,
            ancienne_valeur,
            nouvelle_valeur,
            modifie_par,
            datetime.now().strftime("%d-%m-%Y %H:%M"),
        ),
    )

def _format_relance_dt(dt_value):
    return dt_value.strftime("%d-%m-%Y %H:%M") if dt_value else ""

def update_relance_schedule(db, incident_id, new_etat=None, new_urgence=None, changed_by="system"):
    inc = db.execute(
        "SELECT id, numero, etat, urgence, relance_planifiee_at, relance_done_at, collaborateur "
        "FROM incidents WHERE id=%s",
        (incident_id,),
    ).fetchone()
    if not inc:
        return

    etat = new_etat if new_etat is not None else inc["etat"]
    urgence = new_urgence if new_urgence is not None else inc["urgence"]

    statut_info = db.execute(
        "SELECT has_relances FROM statuts WHERE nom=%s",
        (etat,),
    ).fetchone()

    if not statut_info or not statut_info.get("has_relances"):
        if inc.get("relance_planifiee_at"):
            old_value = _format_relance_dt(inc.get("relance_planifiee_at"))
            db.execute(
                "UPDATE incidents SET relance_planifiee_at=NULL, relance_done_at=NULL WHERE id=%s",
                (incident_id,),
            )
            _log_historique(db, incident_id, "relance_planifiee", old_value, "Annulée", changed_by)
        return

    delay_hours = RELANCE_DELAYS_HOURS.get(urgence, RELANCE_DEFAULT_DELAY_HOURS)
    planned_at = datetime.now() + timedelta(hours=delay_hours)
    old_value = _format_relance_dt(inc.get("relance_planifiee_at"))
    new_value = _format_relance_dt(planned_at)

    db.execute(
        "UPDATE incidents SET relance_planifiee_at=%s, relance_done_at=NULL WHERE id=%s",
        (planned_at, incident_id),
    )

    if old_value != new_value:
        _log_historique(db, incident_id, "relance_planifiee", old_value, new_value, changed_by)
