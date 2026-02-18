from app import create_app, socketio
import os

app = create_app()

if __name__ == "__main__":
    # Mode production : debug désactivé pour la stabilité
    is_development = os.environ.get("FLASK_ENV") == "development"
    socketio.run(
        app, 
        host="0.0.0.0", 
        port=5000, 
        debug=is_development,
        log_output=not is_development,
        allow_unsafe_werkzeug=True
    )
