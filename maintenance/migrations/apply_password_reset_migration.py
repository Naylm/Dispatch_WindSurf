#!/usr/bin/env python3
"""
Script pour appliquer la migration de la colonne force_password_reset
"""
import psycopg2
import os

def apply_migration():
    """Applique la migration de la colonne force_password_reset"""
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
        print("Application de la migration force_password_reset...\n")

        # Lire le fichier SQL
        with open('add_password_reset_column.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # Découper par blocs DO $$ ... END $$; et par UPDATE ... ;
        import re
        # Trouver les blocs DO $$ ... END $$;
        do_blocks = re.findall(r'DO \$\$.*?END \$\$;', sql_script, re.DOTALL)
        # Trouver les UPDATE statements
        update_statements = re.findall(r'UPDATE\s+\w+.*?;', sql_script, re.DOTALL)

        # Exécuter les blocs DO
        for statement in do_blocks:
            statement = statement.strip()
            if statement:
                print(f"Exécution: DO block for column addition...")
                cursor.execute(statement)
                print("✓ OK\n")

        # Exécuter les UPDATE statements
        for statement in update_statements:
            statement = statement.strip()
            if statement:
                print(f"Exécution: {statement[:80]}...")
                cursor.execute(statement)
                print("✓ OK\n")

        print("=" * 60)
        print("Migration appliquée avec succès!")
        print("=" * 60)

        # Vérifier les utilisateurs qui nécessitent une réinitialisation
        cursor.execute("SELECT username FROM users WHERE force_password_reset = 1")
        users_to_reset = cursor.fetchall()

        cursor.execute("SELECT prenom FROM techniciens WHERE force_password_reset = 1")
        techs_to_reset = cursor.fetchall()

        if users_to_reset or techs_to_reset:
            print("\nUtilisateurs nécessitant une réinitialisation:")
            print("-" * 60)
            if users_to_reset:
                print("Users:", ", ".join([u[0] for u in users_to_reset]))
            if techs_to_reset:
                print("Techniciens:", ", ".join([t[0] for t in techs_to_reset]))
        else:
            print("\nTous les utilisateurs ont des mots de passe valides!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

    return True

if __name__ == "__main__":
    apply_migration()
