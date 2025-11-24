#!/usr/bin/env python3
"""
Script pour réinitialiser les mots de passe des techniciens
Utilise le prénom en minuscule comme mot de passe (ex: Hugo -> hugo)
"""
import psycopg2
import os
from werkzeug.security import generate_password_hash

def reset_passwords():
    """Réinitialise les mots de passe des techniciens"""
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
        print("Réinitialisation des mots de passe des techniciens...\n")

        # Récupérer tous les techniciens
        cursor.execute("SELECT id, prenom FROM techniciens ORDER BY prenom")
        techniciens = cursor.fetchall()

        print(f"Trouvé {len(techniciens)} technicien(s)\n")
        print("=" * 60)

        for tech_id, prenom in techniciens:
            # Mot de passe = prénom en minuscule
            password = prenom.lower()
            hashed = generate_password_hash(password)

            # Mettre à jour le mot de passe ET remettre force_password_reset à 0
            cursor.execute(
                "UPDATE techniciens SET password = %s, force_password_reset = 0 WHERE id = %s",
                (hashed, tech_id)
            )

            print(f"✓ {prenom:15s} → mot de passe: {password}")

        print("=" * 60)
        print("\n✅ Tous les mots de passe ont été réinitialisés avec succès!")
        print("\nVous pouvez maintenant vous connecter avec:")
        print("  - Username: [prénom du technicien]")
        print("  - Password: [prénom en minuscule]")
        print("\nExemples:")
        for tech_id, prenom in techniciens[:3]:
            print(f"  - {prenom} / {prenom.lower()}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

    return True

if __name__ == "__main__":
    reset_passwords()
