#!/usr/bin/env python3
"""
Script pour appliquer les indexes de performance à la base de données PostgreSQL
Usage: python apply_indexes.py
"""

import psycopg2
import os
import sys

def apply_indexes():
    """Applique les indexes de performance à la base de données"""

    # Lire les variables d'environnement
    db_host = os.environ.get('POSTGRES_HOST', 'localhost')
    db_port = os.environ.get('POSTGRES_PORT', '5432')
    db_name = os.environ.get('POSTGRES_DB', 'dispatch')
    db_user = os.environ.get('POSTGRES_USER', 'dispatch_user')
    db_pass = os.environ.get('POSTGRES_PASSWORD', 'dispatch_pass')

    print(f"Connexion à la base de données: {db_host}:{db_port}/{db_name}")

    try:
        # Connexion à PostgreSQL
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass
        )
        conn.autocommit = True
        cursor = conn.cursor()

        print("Connexion établie avec succès!")
        print("\nCréation des indexes de performance...")

        # Lire le fichier SQL
        with open('add_indexes.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # Exécuter chaque commande SQL
        for statement in sql_script.split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    print(f"✓ Exécuté: {statement[:60]}...")
                except Exception as e:
                    print(f"⚠ Avertissement: {statement[:60]}... - {str(e)}")

        # Vérifier les indexes créés
        cursor.execute("""
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)

        print("\n" + "="*60)
        print("Indexes créés:")
        print("="*60)
        for table, index in cursor.fetchall():
            print(f"  • {table:30s} → {index}")

        cursor.close()
        conn.close()

        print("\n✓ Indexes appliqués avec succès!")
        return 0

    except psycopg2.Error as e:
        print(f"\n✗ Erreur PostgreSQL: {e}")
        return 1
    except FileNotFoundError:
        print(f"\n✗ Erreur: fichier add_indexes.sql introuvable")
        return 1
    except Exception as e:
        print(f"\n✗ Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(apply_indexes())
