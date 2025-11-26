#!/usr/bin/env python3
"""
Script de réinitialisation du mot de passe admin
Réinitialise à admin/admin
"""

import sys
from werkzeug.security import generate_password_hash
from db_config import get_db

def reset_admin():
    """Réinitialise le mot de passe admin"""
    
    print("\n" + "="*70)
    print("RÉINITIALISATION DU MOT DE PASSE ADMIN")
    print("="*70 + "\n")
    
    db = get_db()
    
    # Vérifier si admin existe
    user = db.execute("SELECT * FROM users WHERE username = %s", ('admin',)).fetchone()
    
    if not user:
        print("❌ Utilisateur 'admin' non trouvé. Création...")
        admin_hash = generate_password_hash('admin')
        db.execute(
            "INSERT INTO users (username, password, role, force_password_reset) VALUES (%s, %s, %s, %s)",
            ('admin', admin_hash, 'admin', 0)
        )
        db.commit()
        print("✅ Utilisateur 'admin' créé avec le mot de passe 'admin'")
    else:
        print(f"👤 Utilisateur trouvé: {user['username']}")
        print(f"   Rôle actuel: {user['role']}")
        
        # Générer nouveau hash
        new_hash = generate_password_hash('admin')
        
        # Mettre à jour
        db.execute(
            "UPDATE users SET password = %s, force_password_reset = 0 WHERE username = %s",
            (new_hash, 'admin')
        )
        db.commit()
        
        print("\n✅ Mot de passe réinitialisé avec succès !")
        print("\nIdentifiants:")
        print("   Username: admin")
        print("   Password: admin")
    
    db.close()
    
    print("\n" + "="*70)
    print("⚠️  IMPORTANT: Changez ce mot de passe après la connexion !")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        reset_admin()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
