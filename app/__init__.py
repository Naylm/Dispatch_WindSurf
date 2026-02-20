import eventlet
eventlet.monkey_patch()

import os
from flask import Flask
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect
from datetime import timedelta
import secrets

# Initialize extensions
socketio = SocketIO()
csrf = CSRFProtect()

def create_app(debug=False):
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # Security: SECRET_KEY is MANDATORY in production
    if not os.environ.get("SECRET_KEY"):
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "CRITICAL ERROR: SECRET_KEY must be defined in production!\n"
                "Generate a key with: python -c \"import secrets; print(secrets.token_hex(32))\"\n"
                "Add it to your .env file: SECRET_KEY=your_key_here"
            )
        else:
            # Development only: generate a temporary key
            app.secret_key = secrets.token_hex(32)
            print("WARNING: SECRET_KEY not defined, using temporary key (dev only)")
    else:
        app.secret_key = os.environ.get("SECRET_KEY")

    # Production Optimized Configuration
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file upload
    
    app.config['WTF_CSRF_ENABLED'] = os.environ.get('WTF_CSRF_ENABLED', 'true').lower() == 'true'
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken', 'X-CSRF-Token']

    is_production = os.environ.get("FLASK_ENV", "production") == "production"
    
    if is_production:
        app.config["TEMPLATES_AUTO_RELOAD"] = False
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000 
        app.jinja_env.auto_reload = False
    else:
        app.config["TEMPLATES_AUTO_RELOAD"] = True
        app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
        app.jinja_env.auto_reload = True
        app.jinja_env.cache = {}

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true" if not is_production else True

    # Register Extensions
    csrf.init_app(app)
    
    # SocketIO Configuration
    redis_url = os.environ.get("REDIS_URL")
    use_redis = False
    gunicorn_workers = max(1, int(os.environ.get("GUNICORN_WORKERS", "1")))
    socketio_debug = os.environ.get("SOCKETIO_DEBUG", "false").lower() == "true"
    
    socketio_allowed_origins = "*"
    if os.environ.get("SOCKETIO_ALLOWED_ORIGINS"):
        socketio_allowed_origins = [o.strip() for o in os.environ.get("SOCKETIO_ALLOWED_ORIGINS", "").split(",") if o.strip()]

    if redis_url:
        use_redis = True
    
    socketio.init_app(app, 
                      async_mode="eventlet", 
                      cors_allowed_origins=socketio_allowed_origins,
                      message_queue=redis_url if use_redis else None,
                      ping_timeout=60,
                      ping_interval=25,
                      logger=socketio_debug,
                      engineio_logger=socketio_debug)

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.wiki import wiki_bp
    from app.routes.stats import stats_bp
    from app.routes.incident import incident_bp
    from app.routes.maintenance import maintenance_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(wiki_bp, url_prefix='/wiki')
    app.register_blueprint(stats_bp)
    app.register_blueprint(incident_bp)
    app.register_blueprint(maintenance_bp)

    # Register template filters
    from app.utils.filters import register_filters
    register_filters(app)

    # Jinja global: is_admin(role) returns True for 'admin' and 'superadmin'
    app.jinja_env.globals['is_admin'] = lambda role: role in ('admin', 'superadmin')
    
    # Ensure integrity
    from app.utils.integrity import ensure_database_integrity
    with app.app_context():
        try:
            ensure_database_integrity()
        except Exception as e:
            print(f"Error ensuring database integrity: {e}")

    # Register Socket.IO event handlers
    from app.sockets import register_socket_handlers
    register_socket_handlers(socketio)

    return app
