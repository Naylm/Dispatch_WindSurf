#!/usr/bin/env python3
"""
Script de création de l'utilisateur Melvin avec le rôle Admin
"""

import sys
from werkzeug.security import generate_password_hash
from db_config import get_db

def create_melvin():
    """Crée l'utilisateur Melvin avec le rôle admin"""
    
    print("\n" + "="*70)
    print("CRÉATION DE L'UTILISATEUR MELVIN")
    print("="*70 + "\n")
    
    db = get_db()
    
    # Vérifier si Melvin existe déjà
    user = db.execute("SELECT * FROM users WHERE username = %s", ('Melvin',)).fetchone()
    
    if user:
        print("⚠️  Utilisateur 'Melvin' existe déjà.")
        print(f"   ID: {user['id']}")
        print(f"   Rôle actuel: {user['role']}")
        
        # Mettre à jour le mot de passe et le rôle
        melvin_hash = generate_password_hash('Admin')
        db.execute(
            "UPDATE users SET password = %s, role = %s WHERE username = %s",
            (melvin_hash, 'admin', 'Melvin')
        )
        db.commit()
        print("\n✅ Utilisateur 'Melvin' mis à jour avec succès !")
    else:
        print("📝 Création de l'utilisateur 'Melvin'...")
        melvin_hash = generate_password_hash('Admin')
        db.execute(
            "INSERT INTO users (username, password, role, force_password_reset) VALUES (%s, %s, %s, %s)",
            ('Melvin', melvin_hash, 'admin', 0)
        )
        db.commit()
        print("✅ Utilisateur 'Melvin' créé avec succès !")
    
    db.close()
    
    print("\nIdentifiants:")
    print("   Username: Melvin")
    print("   Password: Admin")
    print("   Rôle: admin")
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    try:
        create_melvin()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

