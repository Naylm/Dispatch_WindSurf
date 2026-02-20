from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.db_config import get_db
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"].strip()
        p = request.form["password"].strip()
        db = get_db()

        # 1) Try users (admin/user)
        user = db.execute("""
            SELECT * FROM users
            WHERE LOWER(username)=LOWER(%s)
            LIMIT 1
        """, (u,)).fetchone()
        
        if user:
            current_app.logger.debug(f"Login attempt for user: {u}")
            password_valid = False
            is_password_hashed = user["password"] and (user["password"].startswith("pbkdf2:") or user["password"].startswith("scrypt:"))
            
            if is_password_hashed:
                password_valid = check_password_hash(user["password"], p)
            elif user["password"]:
                password_valid = (user["password"] == p)
            
            if password_valid:
                session["user"] = user["username"]
                session["role"] = user["role"]
                session["user_type"] = "user"
                session.permanent = True
                current_app.logger.info(f"Login success: {user['username']} (role: {user['role']})")

                force_reset = user.get("force_password_reset", 0)
                if not is_password_hashed:
                    force_reset = 1
                    db.execute("UPDATE users SET force_password_reset=1 WHERE username=%s", (user["username"],))
                    db.commit()

                db.close()
                if force_reset == 1:
                    session["force_password_reset"] = True
                    return redirect(url_for("auth.change_password_forced"))

                return redirect(url_for("main.home"))
            else:
                db.close()
                flash("Mauvais identifiants", "danger")
                return render_template("login.html")

        # 2) Try techniciens
        tech = db.execute("""
            SELECT * FROM techniciens
            WHERE actif=1
              AND LOWER(username)=LOWER(%s)
            LIMIT 1
        """, (u,)).fetchone()

        if tech and tech["password"]:
            current_app.logger.debug(f"Login attempt for technician: {u}")
            password_valid = False
            is_password_hashed = tech["password"].startswith("pbkdf2:") or tech["password"].startswith("scrypt:")
            
            if is_password_hashed:
                password_valid = check_password_hash(tech["password"], p)
            else:
                password_valid = (tech["password"] == p)
            
            if password_valid:
                session["user"] = tech["username"]
                session["role"] = tech["role"] or "technicien"
                session["user_type"] = "technicien"
                session["prenom"] = tech["prenom"]
                session["user_display_name"] = f"{tech['prenom']} {tech['nom']}".strip()
                session.permanent = True
                current_app.logger.info(f"Technician login success: {tech['username']}")

                force_reset = tech.get("force_password_reset", 0)
                if not is_password_hashed:
                    force_reset = 1
                    db.execute("UPDATE techniciens SET force_password_reset=1 WHERE id=%s", (tech["id"],))
                    db.commit()

                db.close()
                if force_reset == 1:
                    session["force_password_reset"] = True
                    return redirect(url_for("auth.change_password_forced"))

                return redirect(url_for("main.home"))
            else:
                db.close()
                flash("Mauvais identifiants", "danger")
                return render_template("login.html")
        elif tech and not tech["password"]:
            db.close()
            flash("Aucun mot de passe défini. Contactez l'administrateur.", "danger")
            return render_template("login.html")

        db.close()
        flash("Mauvais identifiants", "danger")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

@auth_bp.route("/change_password_forced", methods=["GET", "POST"])
def change_password_forced():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    if not session.get("force_password_reset", False):
        return redirect(url_for("main.home"))

    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not current_password or not new_password or not confirm_password:
            flash("Tous les champs sont obligatoires", "danger")
            return render_template("change_password_forced.html")

        if new_password != confirm_password:
            flash("Les mots de passe ne correspondent pas", "danger")
            return render_template("change_password_forced.html")

        if len(new_password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères", "danger")
            return render_template("change_password_forced.html")

        db = get_db()
        user_type = session.get("user_type", "user")
        username = session["user"]

        if user_type == "user":
            user = db.execute("SELECT * FROM users WHERE username=%s", (username,)).fetchone()
        else:
            user = db.execute("SELECT * FROM techniciens WHERE username=%s AND actif=1", (username,)).fetchone()

        if not user:
            db.close()
            flash("Utilisateur introuvable", "danger")
            return redirect(url_for("auth.logout"))

        password_valid = False
        is_password_hashed = user["password"] and (user["password"].startswith("pbkdf2:") or user["password"].startswith("scrypt:"))
        
        if is_password_hashed:
            password_valid = check_password_hash(user["password"], current_password)
        else:
            password_valid = (user["password"] == current_password)
        
        if not password_valid:
            db.close()
            flash("Mot de passe actuel incorrect", "danger")
            return render_template("change_password_forced.html")

        hashed_password = generate_password_hash(new_password)

        if user_type == "user":
            db.execute("UPDATE users SET password=%s, force_password_reset=0 WHERE username=%s", (hashed_password, username))
        else:
            db.execute("UPDATE techniciens SET password=%s, force_password_reset=0 WHERE username=%s", (hashed_password, username))

        db.commit()
        db.close()

        session.pop("force_password_reset", None)
        flash("Mot de passe réinitialisé avec succès!", "success")
        return redirect(url_for("main.home"))

    return render_template("change_password_forced.html")

@auth_bp.route("/profil")
def profil():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    db = get_db()
    username = session["user"]
    user_type = session.get("user_type", "user")
    
    if user_type == "technicien":
        user_data = db.execute("""
            SELECT id, nom, prenom, username, email, dect_number, role, photo_profil, created_at,
                   question1, question2
            FROM techniciens 
            WHERE username=%s AND actif=1
        """, (username,)).fetchone()
    else:
        user_data = db.execute("""
            SELECT id, 
                   COALESCE(nom, NULL) as nom, 
                   COALESCE(prenom, username) as prenom, 
                   username, 
                   COALESCE(email, NULL) as email, 
                   COALESCE(dect_number, NULL) as dect_number, 
                   role, 
                   COALESCE(photo_profil, NULL) as photo_profil, 
                   NULL as created_at,
                   question1, question2
            FROM users 
            WHERE username=%s
        """, (username,)).fetchone()
    
    db.close()
    
    if not user_data:
        flash("Utilisateur introuvable", "danger")
        return redirect(url_for("main.home"))
    
    return render_template("profil.html", user_data=dict(user_data), role=session.get("role"))

@auth_bp.route("/profil/update_info", methods=["POST"])
def update_profile_info():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    nom = request.form.get("nom", "").strip()
    prenom = request.form.get("prenom", "").strip()
    dect_number = request.form.get("dect_number", "").strip()
    email = request.form.get("email", "").strip()
    
    db = get_db()
    username = session["user"]
    user_type = session.get("user_type", "user")
    
    try:
        if user_type == "technicien":
            db.execute("""
                UPDATE techniciens 
                SET dect_number=%s, email=%s
                WHERE username=%s
            """, (dect_number, email, username))
        else:
            if not prenom:
                flash("Le prénom est obligatoire", "danger")
                return redirect(url_for("auth.profil"))
            
            db.execute("""
                UPDATE users 
                SET nom=%s, prenom=%s, dect_number=%s, email=%s
                WHERE username=%s
            """, (nom if nom else None, prenom, dect_number if dect_number else None, email if email else None, username))
        
        db.commit()
        flash("Informations mises à jour avec succès!", "success")
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Erreur mise à jour profil: {e}")
        flash("Erreur lors de la mise à jour", "danger")
    finally:
        db.close()
    
    return redirect(url_for("auth.profil"))

@auth_bp.route("/profil/update_password", methods=["POST"])
def update_profile_password():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()
    
    if not current_password or not new_password or not confirm_password:
        flash("Tous les champs sont obligatoires", "danger")
        return redirect(url_for("auth.profil"))
    
    if new_password != confirm_password:
        flash("Les mots de passe ne correspondent pas", "danger")
        return redirect(url_for("auth.profil"))
    
    if len(new_password) < 8:
        flash("Le mot de passe doit contenir au moins 8 caractères", "danger")
        return redirect(url_for("auth.profil"))
    
    db = get_db()
    username = session["user"]
    user_type = session.get("user_type", "user")
    
    try:
        if user_type == "technicien":
            user = db.execute("SELECT id, password FROM techniciens WHERE username=%s AND actif=1", (username,)).fetchone()
        else:
            user = db.execute("SELECT id, password FROM users WHERE username=%s", (username,)).fetchone()
        
        if not user:
            flash("Utilisateur introuvable", "danger")
            return redirect(url_for("auth.profil"))
        
        is_password_hashed = user["password"] and (user["password"].startswith("pbkdf2:") or user["password"].startswith("scrypt:"))
        
        if is_password_hashed:
            password_valid = check_password_hash(user["password"], current_password)
        else:
            password_valid = (user["password"] == current_password)
        
        if not password_valid:
            flash("Mot de passe actuel incorrect", "danger")
            return redirect(url_for("auth.profil"))
        
        hashed_password = generate_password_hash(new_password)
        
        if user_type == "technicien":
            db.execute("UPDATE techniciens SET password=%s WHERE id=%s", (hashed_password, user["id"]))
        else:
            db.execute("UPDATE users SET password=%s WHERE id=%s", (hashed_password, user["id"]))
        
        db.commit()
        flash("Mot de passe modifié avec succès!", "success")
        
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Erreur changement mot de passe: {e}")
        flash("Erreur lors du changement de mot de passe", "danger")
    finally:
        db.close()
    
    return redirect(url_for("auth.profil"))

@auth_bp.route("/profil/update_photo", methods=["POST"])
def update_profile_photo():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    if 'photo' not in request.files:
        flash("Aucun fichier sélectionné", "danger")
        return redirect(url_for("auth.profil"))
    
    file = request.files['photo']
    if file.filename == '':
        flash("Aucun fichier sélectionné", "danger")
        return redirect(url_for("auth.profil"))
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
        flash("Type de fichier non autorisé (PNG, JPG, GIF, WEBP uniquement)", "danger")
        return redirect(url_for("auth.profil"))
    
    import uuid
    UPLOAD_FOLDER = os.path.join(current_app.static_folder, 'uploads', 'avatars')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    from werkzeug.utils import secure_filename
    file_extension = secure_filename(file.filename).rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    db = get_db()
    try:
        file.save(filepath)
        username = session["user"]
        user_type = session.get("user_type", "user")
        
        # Determine table logic
        if user_type == "technicien":
            table = "techniciens"
        else:
            table = "users"
            
        old_photo = db.execute(f"SELECT photo_profil FROM {table} WHERE username=%s", (username,)).fetchone()
        
        if old_photo and old_photo.get("photo_profil"):
            old_path = os.path.join(UPLOAD_FOLDER, old_photo["photo_profil"])
            if os.path.exists(old_path):
                os.remove(old_path)
        
        db.execute(f"UPDATE {table} SET photo_profil=%s WHERE username=%s", (unique_filename, username))
        db.commit()
        flash("Photo de profil mise à jour!", "success")
        
    except Exception as e:
        current_app.logger.error(f"Erreur upload photo: {e}")
        flash("Erreur lors de l'upload de la photo", "danger")
        if os.path.exists(filepath):
            os.remove(filepath)
    finally:
        db.close()
    
    return redirect(url_for("auth.profil"))

@auth_bp.route("/profil/delete_photo", methods=["POST"])
def delete_profile_photo():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    
    db = get_db()
    username = session["user"]
    user_type = session.get("user_type", "user")
    
    try:
        table = "techniciens" if user_type == "technicien" else "users"
        user = db.execute(f"SELECT photo_profil FROM {table} WHERE username=%s", (username,)).fetchone()
        
        if not user:
            flash("Utilisateur introuvable", "danger")
            return redirect(url_for("auth.profil"))
        
        if user.get("photo_profil"):
            UPLOAD_FOLDER = os.path.join(current_app.static_folder, 'uploads', 'avatars')
            photo_path = os.path.join(UPLOAD_FOLDER, user["photo_profil"])
            if os.path.exists(photo_path):
                try:
                    os.remove(photo_path)
                except Exception:
                    pass
        
        db.execute(f"UPDATE {table} SET photo_profil=NULL WHERE username=%s", (username,))
        db.commit()
        flash("Photo de profil supprimée avec succès!", "success")
        
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Erreur suppression photo: {e}")
        flash("Erreur lors de la suppression de la photo", "danger")
    finally:
        db.close()
    
    return redirect(url_for("auth.profil"))

# ==========================================
# Password Recovery System
# ==========================================

@auth_bp.route("/profil/setup_recovery", methods=["GET", "POST"])
def setup_recovery():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        q1 = request.form.get("question1", "").strip()
        a1 = request.form.get("answer1", "").strip().lower()
        q2 = request.form.get("question2", "").strip()
        a2 = request.form.get("answer2", "").strip().lower()
        password = request.form.get("current_password", "").strip()

        if not all([q1, a1, q2, a2, password]):
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("auth.profil"))

        db = get_db()
        username = session["user"]
        user_type = session.get("user_type", "user")

        try:
            table = "techniciens" if user_type == "technicien" else "users"
            user = db.execute(f"SELECT * FROM {table} WHERE username=%s", (username,)).fetchone()

            if not user:
                flash("Utilisateur introuvable.", "danger")
                return redirect(url_for("auth.profil"))

            # Verify password
            is_password_hashed = user["password"] and (user["password"].startswith("pbkdf2:") or user["password"].startswith("scrypt:"))
            if is_password_hashed:
                password_valid = check_password_hash(user["password"], password)
            else:
                password_valid = (user["password"] == password)

            if not password_valid:
                flash("Mot de passe incorrect.", "danger")
                return redirect(url_for("auth.profil"))

            # Hash answers
            hashed_a1 = generate_password_hash(a1)
            hashed_a2 = generate_password_hash(a2)

            db.execute(f"""
                UPDATE {table}
                SET question1=%s, answer1=%s, question2=%s, answer2=%s
                WHERE id=%s
            """, (q1, hashed_a1, q2, hashed_a2, user["id"]))
            
            db.commit()
            flash("Questions de sécurité mises à jour avec succès!", "success")

        except Exception as e:
            db.rollback()
            current_app.logger.error(f"Error setup recovery: {e}")
            flash("Erreur lors de la configuration.", "danger")
        finally:
            db.close()
        
        return redirect(url_for("auth.profil"))

    return redirect(url_for("auth.profil")) # GET is handled in profil modal

@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        
        if not identity:
            flash("Veuillez entrer votre nom d'utilisateur ou email.", "danger")
            return render_template("forgot_password.html")

        db = get_db()
        # Try finding user in both tables
        user = db.execute("""
            SELECT id, username, 'user' as type, question1, question2 
            FROM users 
            WHERE LOWER(username)=LOWER(%s) OR LOWER(email)=LOWER(%s)
        """, (identity, identity)).fetchone()

        if not user:
             user = db.execute("""
                SELECT id, username, 'technicien' as type, question1, question2
                FROM techniciens
                WHERE (LOWER(username)=LOWER(%s) OR LOWER(email)=LOWER(%s)) AND actif=1
            """, (identity, identity)).fetchone()
        
        db.close()

        if user:
            if not user["question1"] or not user["question2"]:
                flash("Ce compte n'a pas configuré de questions de sécurité. Veuillez contacter un administrateur.", "warning")
                return render_template("forgot_password.html")
            
            # Store in temp session for verification step
            session["recovery_user_id"] = user["id"]
            session["recovery_user_type"] = user["type"]
            session["recovery_username"] = user["username"]
            session["recovery_q1"] = user["question1"]
            session["recovery_q2"] = user["question2"]
            
            return redirect(url_for("auth.verify_questions"))
        else:
            # Fake success to prevent enumeration
            flash("Si ce compte existe, vous serez redirigé vers les questions.", "info")
            return render_template("forgot_password.html")

    return render_template("forgot_password.html")

@auth_bp.route("/verify_questions", methods=["GET", "POST"])
def verify_questions():
    if "recovery_user_id" not in session:
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        a1 = request.form.get("answer1", "").strip().lower()
        a2 = request.form.get("answer2", "").strip().lower()

        db = get_db()
        table = "techniciens" if session["recovery_user_type"] == "technicien" else "users"
        user = db.execute(f"SELECT answer1, answer2 FROM {table} WHERE id=%s", (session["recovery_user_id"],)).fetchone()
        db.close()

        if user and check_password_hash(user["answer1"], a1) and check_password_hash(user["answer2"], a2):
            session["recovery_verified"] = True
            return redirect(url_for("auth.reset_password_recovery"))
        else:
            flash("Réponses incorrectes.", "danger")
            return render_template("answer_questions.html", q1=session["recovery_q1"], q2=session["recovery_q2"])

    return render_template("answer_questions.html", q1=session["recovery_q1"], q2=session["recovery_q2"])

@auth_bp.route("/reset_password_recovery", methods=["GET", "POST"])
def reset_password_recovery():
    if "recovery_verified" not in session or not session["recovery_verified"]:
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        new_pass = request.form.get("new_password", "").strip()
        confirm_pass = request.form.get("confirm_password", "").strip()

        if len(new_pass) < 8:
            flash("Le mot de passe doit faire 8 caractères minimum.", "danger")
            return render_template("reset_password_recovery.html")
        
        if new_pass != confirm_pass:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return render_template("reset_password_recovery.html")

        hashed = generate_password_hash(new_pass)
        db = get_db()
        table = "techniciens" if session["recovery_user_type"] == "technicien" else "users"
        
        try:
            db.execute(f"UPDATE {table} SET password=%s, force_password_reset=0 WHERE id=%s", (hashed, session["recovery_user_id"]))
            db.commit()
            flash("Mot de passe réinitialisé avec succès ! Connectez-vous.", "success")
            
            # Application cleanup
            session.pop("recovery_user_id", None)
            session.pop("recovery_user_type", None)
            session.pop("recovery_username", None)
            session.pop("recovery_q1", None)
            session.pop("recovery_q2", None)
            session.pop("recovery_verified", None)
            
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.rollback()
            current_app.logger.error(f"Reset pwd error: {e}")
            flash("Erreur lors de la réinitialisation.", "danger")
        finally:
            db.close()

    return render_template("reset_password_recovery.html")
