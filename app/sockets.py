from flask import session, request
from flask_socketio import join_room
import logging

logger = logging.getLogger(__name__)

active_sids = {}

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

        # Track active connections and broadcast count
        active_sids[request.sid] = user or "anonymous"
        
        # Build list of connected users (unique, remove 'anonymous')
        connected_users = list(set([u for u in active_sids.values() if u and u != "anonymous"]))
        
        # Emit to all connected clients (not just admin room) so everyone gets updates
        socketio.emit('active_connections_count', {
            'count': len(active_sids),
            'users': connected_users
        })
        
        # Also send directly to the connecting client
        socketio.emit('active_connections_count', {
            'count': len(active_sids),
            'users': connected_users
        }, to=request.sid)

    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"❌ Client Socket.IO déconnecté: {request.sid}")
        if request.sid in active_sids:
            del active_sids[request.sid]
        # Build list of connected users (unique, remove 'anonymous')
        connected_users = list(set([u for u in active_sids.values() if u and u != "anonymous"]))
        # Broadcast to all clients
        socketio.emit('active_connections_count', {
            'count': len(active_sids),
            'users': connected_users
        })

    @socketio.on('request_connection_count')
    def handle_request_connection_count():
        """Permet à un client de demander le nombre d'utilisateurs connectés"""
        connected_users = list(set([u for u in active_sids.values() if u and u != "anonymous"]))
        socketio.emit('active_connections_count', {
            'count': len(active_sids),
            'users': connected_users
        }, to=request.sid)
        logger.info(f"📊 Client {request.sid} a demandé le nombre de connexions: {len(active_sids)}")


    @socketio.on('join_tech_room')
    def handle_join_tech_room(data):
        """
        Permet à un client de rejoindre explicitement une salle technicien par son prénom.
        SECURITY: Vérifie que l'utilisateur ne rejoint que sa propre salle.
        """
        prenom = data.get('prenom')
        if prenom:
            user = session.get('user', '').strip().lower()
            session_prenom = session.get('prenom', '').strip().lower()
            requested = prenom.strip().lower()
            
            # Allow join only if it matches the user's own username or prenom
            if requested == user or requested == session_prenom:
                room = f"tech:{requested}"
                join_room(room)
                logger.info(f"🤝 Socket {request.sid} a rejoint sa salle : {room}")
            else:
                logger.warning(f"⚠️ Socket {request.sid} a tenté de rejoindre une salle non autorisée : tech:{requested} (user={user})")
