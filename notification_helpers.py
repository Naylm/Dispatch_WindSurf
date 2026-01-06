"""
Helpers pour le système de notifications en temps réel.
Gère l'émission des notifications WebSocket vers les techniciens.
"""

from datetime import datetime
import logging
import sys

logger = logging.getLogger(__name__)


def emit_new_assignment_notification(socketio, incident_data, technicien):
    """
    Émet une notification pour un nouveau ticket assigné à un technicien.

    Args:
        socketio: Instance SocketIO
        incident_data: Dict contenant les données de l'incident
        technicien: Nom du technicien assigné
    """
    notification = {
        "type": "new_assignment",
        "incident_id": incident_data.get("id"),
        "numero": incident_data.get("numero"),
        "site": incident_data.get("site"),
        "sujet": incident_data.get("sujet"),
        "urgence": incident_data.get("urgence"),
        "technicien": technicien,
        "note_dispatch": incident_data.get("note_dispatch", ""),
        "timestamp": datetime.now().isoformat()
    }

    # Émettre vers tout le monde (le JS filtrera côté client selon le rôle)
    logger.info(f"🔔 Émission notification new_assignment: {notification}")
    print(f"🔔 NOTIFICATION new_assignment pour {technicien}: {notification['numero']}", flush=True)
    socketio.emit("notification", notification)


def emit_status_change_notification(socketio, incident_id, numero, old_status, new_status, technicien, changed_by=None):
    """
    Émet une notification pour un changement de statut.

    Args:
        socketio: Instance SocketIO
        incident_id: ID de l'incident
        numero: Numéro du ticket
        old_status: Ancien statut
        new_status: Nouveau statut
        technicien: Nom du technicien concerné
        changed_by: Qui a fait le changement (pour filtrage côté client)
    """
    notification = {
        "type": "status_change",
        "incident_id": incident_id,
        "numero": numero,
        "old_status": old_status,
        "new_status": new_status,
        "technicien": technicien,
        "changed_by": changed_by or technicien,  # Qui a fait le changement
        "timestamp": datetime.now().isoformat()
    }

    logger.info(f"🔔 Émission notification status_change: {notification}")
    print(f"🔔 NOTIFICATION status_change pour {technicien} (par {changed_by}): {numero} ({old_status} -> {new_status})", flush=True)
    socketio.emit("notification", notification)


def emit_urgent_update_notification(socketio, incident_id, numero, message, technicien):
    """
    Émet une notification prioritaire pour un ticket urgent.

    Args:
        socketio: Instance SocketIO
        incident_id: ID de l'incident
        numero: Numéro du ticket
        message: Message de la notification
        technicien: Nom du technicien concerné
    """
    notification = {
        "type": "urgent_update",
        "incident_id": incident_id,
        "numero": numero,
        "message": message,
        "technicien": technicien,
        "timestamp": datetime.now().isoformat()
    }

    socketio.emit("notification", notification)


def emit_relance_due_notification(socketio, incident_id, numero, technicien, urgence, planned_at):
    """
    Émet une notification pour une relance arrivée à échéance.

    Args:
        socketio: Instance SocketIO
        incident_id: ID de l'incident
        numero: Numéro du ticket
        technicien: Nom du technicien concerné
        urgence: Niveau d'urgence
        planned_at: Datetime prévue pour la relance
    """
    planned_str = planned_at.isoformat() if planned_at else None
    notification = {
        "type": "relance_due",
        "incident_id": incident_id,
        "numero": numero,
        "technicien": technicien,
        "urgence": urgence,
        "planned_at": planned_str,
        "timestamp": datetime.now().isoformat()
    }

    socketio.emit("notification", notification)


def emit_reassignment_notification(socketio, incident_data, old_technicien, new_technicien):
    """
    Émet une notification pour une réaffectation de ticket.

    Args:
        socketio: Instance SocketIO
        incident_data: Dict contenant les données de l'incident
        old_technicien: Ancien technicien
        new_technicien: Nouveau technicien
    """
    # Notification pour le nouveau technicien
    notification_new = {
        "type": "reassignment_new",
        "incident_id": incident_data.get("id"),
        "numero": incident_data.get("numero"),
        "site": incident_data.get("site"),
        "sujet": incident_data.get("sujet"),
        "urgence": incident_data.get("urgence"),
        "technicien": new_technicien,
        "from_technicien": old_technicien,
        "note_dispatch": incident_data.get("note_dispatch", ""),
        "timestamp": datetime.now().isoformat()
    }

    # Notification pour l'ancien technicien
    notification_old = {
        "type": "reassignment_removed",
        "incident_id": incident_data.get("id"),
        "numero": incident_data.get("numero"),
        "technicien": old_technicien,
        "to_technicien": new_technicien,
        "timestamp": datetime.now().isoformat()
    }

    # Émettre les deux notifications vers tout le monde (le JS filtrera)
    socketio.emit("notification", notification_new)
    socketio.emit("notification", notification_old)


def is_urgent(urgence):
    """
    Vérifie si une urgence est considérée comme prioritaire.

    Args:
        urgence: Niveau d'urgence (Basse, Moyenne, Haute, Critique, Immédiate)

    Returns:
        bool: True si urgent
    """
    return urgence in ['Critique', 'Immédiate', 'Haute']


def format_notification_message(incident_data):
    """
    Formate un message de notification à partir des données d'incident.

    Args:
        incident_data: Dict contenant les données de l'incident

    Returns:
        str: Message formaté
    """
    parts = [
        f"📋 {incident_data.get('numero')}",
        f"🏢 {incident_data.get('site')}",
        f"💼 {incident_data.get('sujet')}"
    ]

    if incident_data.get('localisation'):
        parts.append(f"📍 {incident_data.get('localisation')}")

    urgence = incident_data.get('urgence')
    if is_urgent(urgence):
        parts.insert(0, f"🚨 URGENT ({urgence})")

    return " • ".join(parts)
