from flask import session, request
from flask_socketio import join_room
import logging

logger = logging.getLogger(__name__)

def register_socket_handlers(socketio):
    """
    Enregistre les gestionnaires d'événements Socket.IO sur l'instance socketio fournie.
    """
    
    @socketio.on('connect')
    def handle_connect():
        """
        Gère la connexion d'un client Socket.IO.
        Inscrit automatiquement le client dans les salles appropriées (admin, tech).
        """
        user = session.get('user')
        role = session.get('role')

        logger.info(f"🔌 Nouveau client Socket.IO: {request.sid} (User: {user}, Role: {role})")

        # Rejoindre la salle Admin si nécessaire
        if role in ('admin', 'superadmin'):
            join_room('role:admin')
            logger.info(f"👤 Socket {request.sid} a rejoint la salle : role:admin")

        # Rejoindre la salle spécifique au technicien (pour les notifications ciblées)
        if user:
            # Salle par username
            user_room = f"tech:{user.strip().lower()}"
            join_room(user_room)
            logger.info(f"🛠️ Socket {request.sid} a rejoint la salle : {user_room}")
            
            # Salle par prénom (si disponible)
            prenom = session.get('prenom')
            if prenom:
                prenom_room = f"tech:{prenom.strip().lower()}"
                join_room(prenom_room)
                logger.info(f"🤝 Socket {request.sid} a rejoint automatiquement la salle : {prenom_room}")

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"❌ Client Socket.IO déconnecté: {request.sid}")

    @socketio.on('join_tech_room')
    def handle_join_tech_room(data):
        """
        Permet à un client de rejoindre explicitement une salle technicien par son prénom.
        Utile car le backend émet souvent vers tech:prenom.
        """
        prenom = data.get('prenom')
        if prenom:
            room = f"tech:{prenom.strip().lower()}"
            join_room(room)
            logger.info(f"🤝 Socket {request.sid} a rejoint manuellement la salle : {room}")
