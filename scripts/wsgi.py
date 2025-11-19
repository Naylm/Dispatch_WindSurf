"""
WSGI entry point pour les serveurs de production (Gunicorn, uWSGI, etc.)
Pour utiliser avec eventlet (recommandé pour SocketIO):
    gunicorn --worker-class eventlet -w 1 wsgi:app
"""
import eventlet
eventlet.monkey_patch()

from app import app, socketio

# Pour les serveurs WSGI traditionnels
application = app

if __name__ == "__main__":
    # Pour le développement local
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
