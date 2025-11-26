#!/usr/bin/env python3
"""
Script de diagnostic pour les problèmes de connexion
Vérifie les utilisateurs, mots de passe hashés et permet de réinitialiser
"""

import sys
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import get_db

def diagnose_login():
    """Diagnostique les problèmes de connexion"""
    
    print("\n" + "="*70)
    print("DIAGNOSTIC DES COMPTES - DISPATCH MANAGER")
    print("="*70 + "\n")
    
    db = get_db()
    
    # Vérifier les utilisateurs admin
    print("📊 UTILISATEURS ADMIN (table users)")
    print("-" * 70)
    
    users = db.execute("SELECT id, username, password, role, force_password_reset FROM users").fetchall()
    
    if not users:
        print("❌ AUCUN UTILISATEUR TROUVÉ !")
        print("\nCréation d'un compte admin par défaut...")
        admin_hash = generate_password_hash('admin')
        db.execute(
            "INSERT INTO users (username, password, role, force_password_reset) VALUES (%s, %s, %s, %s)",
            ('admin', admin_hash, 'admin', 0)
        )
        db.commit()
        print("✅ Compte créé: username='admin', password='admin'")
    else:
        for user in users:
            print(f"\n👤 Utilisateur: {user['username']}")
            print(f"   ID: {user['id']}")
            print(f"   Rôle: {user['role']}")
            print(f"   Force reset: {user['force_password_reset']}")
            
            pwd = user['password']
            if pwd:
                if pwd.startswith('pbkdf2:') or pwd.startswith('scrypt:'):
                    print(f"   Mot de passe: ✅ Hashé correctement")
                    print(f"   Hash (début): {pwd[:30]}...")
                    
                    # Tester le hash avec "admin"
                    if check_password_hash(pwd, 'admin'):
                        print(f"   ✅ Le mot de passe est 'admin'")
                    else:
                        print(f"   ⚠️  Le mot de passe N'EST PAS 'admin'")
                else:
                    print(f"   ❌ Mot de passe NON HASHÉ: {pwd}")
                    print(f"   ⚠️  CONNEXION IMPOSSIBLE - Hash requis")
            else:
                print(f"   ❌ Mot de passe VIDE")
    
    # Vérifier les techniciens
    print("\n" + "="*70)
    print("📊 TECHNICIENS (table techniciens)")
    print("-" * 70)
    
    techs = db.execute("SELECT id, prenom, password, role, actif, force_password_reset FROM techniciens").fetchall()
    
    if not techs:
        print("ℹ️  Aucun technicien configuré")
    else:
        for tech in techs:
            print(f"\n👨‍🔧 Technicien: {tech['prenom']}")
            print(f"   ID: {tech['id']}")
            print(f"   Rôle: {tech['role']}")
            print(f"   Actif: {'✅ Oui' if tech['actif'] == 1 else '❌ Non'}")
            print(f"   Force reset: {tech['force_password_reset']}")
            
            pwd = tech['password']
            if pwd:
                if pwd.startswith('pbkdf2:') or pwd.startswith('scrypt:'):
                    print(f"   Mot de passe: ✅ Hashé correctement")
                    print(f"   Hash (début): {pwd[:30]}...")
                    
                    # Tester avec le prénom en minuscules
                    if check_password_hash(pwd, tech['prenom'].lower()):
                        print(f"   ✅ Le mot de passe est '{tech['prenom'].lower()}'")
                    elif check_password_hash(pwd, tech['prenom']):
                        print(f"   ✅ Le mot de passe est '{tech['prenom']}'")
                    else:
                        print(f"   ⚠️  Le mot de passe n'est ni '{tech['prenom']}' ni '{tech['prenom'].lower()}'")
                else:
                    print(f"   ❌ Mot de passe NON HASHÉ: {pwd}")
            else:
                print(f"   ⚠️  Mot de passe NON DÉFINI (connexion impossible)")
    
    db.close()
    
    # Propositions
    print("\n" + "="*70)
    print("💡 SOLUTIONS")
    print("="*70)
    print("\n1. Pour réinitialiser le mot de passe admin:")
    print("   python reset_admin_password.py")
    print("\n2. Pour créer/réinitialiser les techniciens:")
    print("   python maintenance/admin/reset_technicien_passwords.py")
    print("\n3. Pour tester la connexion:")
    print("   - Username: admin")
    print("   - Password: admin")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        diagnose_login()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
