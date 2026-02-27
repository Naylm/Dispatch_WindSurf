"""
Helpers for realtime notifications.
Notifications are emitted only to authorized Socket.IO rooms.
"""

from datetime import datetime
import logging
from app.utils.references import get_reference_data

logger = logging.getLogger(__name__)

ADMIN_SOCKET_ROOM = "role:admin"


def _tech_room(technicien):
    return f"tech:{(technicien or '').strip().lower()}"


def _user_room(username):
    return f"user:{(username or '').strip().lower()}"


def _emit_notification(socketio, payload, technicien=None, target_user=None, include_admin=True):
    """
    Emit a notification to policy-managed rooms only.

    - Admin room receives everything unless include_admin=False
    - Technician room receives technician-targeted events
    - target_user allows targeting username-based rooms (wiki)
    """
    rooms = set()
    if include_admin:
        rooms.add(ADMIN_SOCKET_ROOM)
    if technicien:
        rooms.add(_tech_room(technicien))
    if target_user:
        # Compatibility: target can be username or display name.
        rooms.add(_user_room(target_user))
        rooms.add(_tech_room(target_user))

    for room in rooms:
        socketio.emit("notification", payload, room=room)


def emit_new_assignment_notification(socketio, incident_data, technicien):
    """Emit a notification for a new assignment."""
    notification = {
        "type": "new_assignment",
        "incident_id": incident_data.get("id"),
        "numero": incident_data.get("numero"),
        "site": incident_data.get("site"),
        "sujet": incident_data.get("sujet"),
        "urgence": incident_data.get("urgence"),
        "is_urgent": is_urgent(incident_data.get("urgence")),
        "technicien": technicien,
        "note_dispatch": incident_data.get("note_dispatch", ""),
        "timestamp": datetime.now().isoformat(),
    }

    logger.info("Emit notification new_assignment: %s", notification)
    _emit_notification(socketio, notification, technicien=technicien)


def emit_status_change_notification(socketio, incident_id, numero, old_status, new_status, technicien, changed_by=None):
    """Emit a notification for a status change."""
    notification = {
        "type": "status_change",
        "incident_id": incident_id,
        "numero": numero,
        "old_status": old_status,
        "new_status": new_status,
        "technicien": technicien,
        "changed_by": changed_by or technicien,
        "timestamp": datetime.now().isoformat(),
    }

    logger.info("Emit notification status_change: %s", notification)
    _emit_notification(socketio, notification, technicien=technicien)


def emit_urgent_update_notification(socketio, incident_id, numero, message, technicien):
    """Emit a high-priority notification for an urgent ticket."""
    notification = {
        "type": "urgent_update",
        "incident_id": incident_id,
        "numero": numero,
        "message": message,
        "technicien": technicien,
        "timestamp": datetime.now().isoformat(),
    }

    _emit_notification(socketio, notification, technicien=technicien)


def emit_relance_due_notification(socketio, incident_id, numero, technicien, urgence, planned_at):
    """Emit a notification when a scheduled follow-up is due."""
    planned_str = planned_at.isoformat() if planned_at else None
    notification = {
        "type": "relance_due",
        "incident_id": incident_id,
        "numero": numero,
        "technicien": technicien,
        "urgence": urgence,
        "planned_at": planned_str,
        "timestamp": datetime.now().isoformat(),
    }

    _emit_notification(socketio, notification, technicien=technicien)


def emit_reassignment_notification(socketio, incident_data, old_technicien, new_technicien):
    """Emit notifications for ticket reassignment."""
    notification_new = {
        "type": "reassignment_new",
        "incident_id": incident_data.get("id"),
        "numero": incident_data.get("numero"),
        "site": incident_data.get("site"),
        "sujet": incident_data.get("sujet"),
        "urgence": incident_data.get("urgence"),
        "is_urgent": is_urgent(incident_data.get("urgence")),
        "technicien": new_technicien,
        "from_technicien": old_technicien,
        "note_dispatch": incident_data.get("note_dispatch", ""),
        "timestamp": datetime.now().isoformat(),
    }

    notification_old = {
        "type": "reassignment_removed",
        "incident_id": incident_data.get("id"),
        "numero": incident_data.get("numero"),
        "technicien": old_technicien,
        "to_technicien": new_technicien,
        "timestamp": datetime.now().isoformat(),
    }

    _emit_notification(socketio, notification_new, technicien=new_technicien)
    _emit_notification(socketio, notification_old, technicien=old_technicien)


def emit_wiki_update_requested_notification(socketio, article_id, title, requested_by, target_user, request_type):
    """Emit a wiki update request to the targeted user only."""
    notification = {
        "type": "wiki_update_requested",
        "article_id": article_id,
        "title": title,
        "requested_by": requested_by,
        "target_user": target_user,
        "request_type": request_type,
        "timestamp": datetime.now().isoformat(),
    }

    logger.info("Emit notification wiki_update_requested: %s", notification)
    _emit_notification(socketio, notification, target_user=target_user, include_admin=False)


def is_urgent(urgence):
    """Return True if urgency level is configured as high priority."""
    refs = get_reference_data()
    priorites = refs.get('priorites', [])
    for p in priorites:
        if p.get('nom') == urgence:
            return bool(p.get('is_urgent', False))
    return False


def format_notification_message(incident_data):
    """Format a display message from incident data."""
    parts = [
        f"#{incident_data.get('numero')}",
        f"{incident_data.get('site')}",
        f"{incident_data.get('sujet')}",
    ]

    if incident_data.get("localisation"):
        parts.append(f"{incident_data.get('localisation')}")

    urgence = incident_data.get("urgence")
    if is_urgent(urgence):
        parts.insert(0, f"URGENT ({urgence})")

    return " | ".join(parts)
    

def emit_config_updated(socketio, config_type, item_data=None):
    """
    Emit a notification that configuration has changed.
    All connected clients (admin and techs) should probably know about this
    to update their UI styles/colors.
    """
    notification = {
        "type": "config_updated",
        "config_type": config_type, # 'site', 'priorite', 'statut'
        "item": item_data,
        "timestamp": datetime.now().isoformat(),
    }
    
    logger.info("Emit notification config_updated: %s", notification)
    # Broadcast to everyone
    socketio.emit("notification", notification)

