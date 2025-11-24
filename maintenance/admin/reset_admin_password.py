#!/usr/bin/env python3
"""
Script pour réinitialiser le mot de passe admin
Par défaut: melvin / admin
"""
import psycopg2
import os
from werkzeug.security import generate_password_hash

def reset_admin_password():
    """Réinitialise le mot de passe de l'admin"""
    db_host = os.environ.get('POSTGRES_HOST', 'postgres')
    db_port = os.environ.get('POSTGRES_PORT', '5432')
    db_name = os.environ.get('POSTGRES_DB', 'dispatch')
    db_user = os.environ.get('POSTGRES_USER', 'dispatch_user')
    db_pass = os.environ.get('POSTGRES_PASSWORD', 'dispatch_pass')

    print(f"Connexion à la base de données: {db_host}:{db_port}/{db_name}")

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass
        )
        conn.autocommit = True
        cursor = conn.cursor()

        print("Connexion établie avec succès!\n")

        # Mot de passe par défaut pour l'admin
        username = "melvin"
        new_password = "admin"
        hashed = generate_password_hash(new_password)

        # Mettre à jour le mot de passe ET remettre force_password_reset à 0
        cursor.execute(
            "UPDATE users SET password = %s, force_password_reset = 0 WHERE username = %s",
            (hashed, username)
        )

        print("=" * 60)
        print(f"✓ Mot de passe admin réinitialisé")
        print("=" * 60)
        print(f"\nVous pouvez vous connecter avec:")
        print(f"  Username: {username}")
        print(f"  Password: {new_password}")
        print()

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

    return True

if __name__ == "__main__":
    reset_admin_password()
