from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app
from app.utils.db_config import get_db
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename

broadcast_bp = Blueprint('broadcast', __name__)

# Extensions autorisées pour les images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@broadcast_bp.route("/")
def list_broadcasts():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    db = get_db()
    # On trie par permanence puis par date de création
    broadcasts = db.execute("""
        SELECT * FROM broadcasts 
        WHERE is_active=TRUE 
        ORDER BY is_permanent DESC, created_at DESC
    """).fetchall()
    
    role = session.get("role", "").lower()
    return render_template("broadcasts.html", broadcasts=broadcasts, role=role)

@broadcast_bp.route("/add", methods=["POST"])
def add_broadcast():
    if "user" not in session or session.get("role") not in ("admin", "superadmin"):
        return jsonify({"success": False, "error": "Non autorisé"}), 403
    
    title = request.form.get("title")
    content = request.form.get("content")
    is_permanent = request.form.get("is_permanent") == "on"
    
    if not title or not content:
        return jsonify({"success": False, "error": "Titre et contenu requis"}), 400
    
    db = get_db()
    db.execute("""
        INSERT INTO broadcasts (title, content, is_permanent, created_by)
        VALUES (%s, %s, %s, %s)
    """, (title, content, is_permanent, session["user"]))
    db.commit()
    
    return jsonify({"success": True})

@broadcast_bp.route("/delete/<int:id>", methods=["DELETE"])
def delete_broadcast(id):
    if "user" not in session or session.get("role") not in ("admin", "superadmin"):
        return jsonify({"success": False, "error": "Non autorisé"}), 403
    
    db = get_db()
    db.execute("UPDATE broadcasts SET is_active=FALSE WHERE id=%s", (id,))
    db.commit()
    
    return jsonify({"success": True})

@broadcast_bp.route("/update/<int:id>", methods=["POST"])
def update_broadcast(id):
    if "user" not in session or session.get("role") not in ("admin", "superadmin"):
        return jsonify({"success": False, "error": "Non autorisé"}), 403
    
    title = request.form.get("title")
    content = request.form.get("content")
    is_permanent = request.form.get("is_permanent") == "on"
    
    if not title or not content:
        return jsonify({"success": False, "error": "Titre et contenu requis"}), 400
    
    db = get_db()
    db.execute("""
        UPDATE broadcasts 
        SET title=%s, content=%s, is_permanent=%s, updated_at=CURRENT_TIMESTAMP
        WHERE id=%s
    """, (title, content, is_permanent, id))
    db.commit()
    
    return jsonify({"success": True})

@broadcast_bp.route("/upload", methods=["POST"])
def upload_broadcast_image():
    try:
        if "user" not in session or session.get("role") not in ("admin", "superadmin"):
            return jsonify({"error": "Non autorisé"}), 403
        
        if 'file' not in request.files:
            return jsonify({"error": "Aucun fichier"}), 400
        
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({"error": "Fichier invalide"}), 400

        # Vérification de la taille
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": "Fichier trop volumineux (max 5MB)"}), 400

        UPLOAD_FOLDER = os.path.join(current_app.static_folder, 'uploads', 'broadcasts')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        db = get_db()
        db.execute("""
            INSERT INTO broadcast_images (filename, original_filename, filepath, uploaded_by, file_size)
            VALUES (%s, %s, %s, %s, %s)
        """, (unique_filename, original_filename, filepath, session["user"], file_size))
        db.commit()
        
        image_url = url_for('static', filename=f'uploads/broadcasts/{unique_filename}')
        
        return jsonify({
            "success": True,
            "url": image_url,
            "filename": unique_filename
        }), 200
    
    except Exception as e:
        current_app.logger.exception(f"broadcast_upload_image: exception: {e}")
        return jsonify({"success": False, "error": f"Erreur serveur: {str(e)}"}), 500
