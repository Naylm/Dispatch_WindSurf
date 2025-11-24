#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier l'état des techniciens
"""
import psycopg2
import os

def diagnostic():
    """Diagnostic complet des techniciens"""
    db_host = os.environ.get('POSTGRES_HOST', 'postgres')
    db_port = os.environ.get('POSTGRES_PORT', '5432')
    db_name = os.environ.get('POSTGRES_DB', 'dispatch')
    db_user = os.environ.get('POSTGRES_USER', 'dispatch_user')
    db_pass = os.environ.get('POSTGRES_PASSWORD', 'dispatch_pass')

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass
        )
        cursor = conn.cursor()

        print("=" * 70)
        print(" DIAGNOSTIC COMPLET DES TECHNICIENS ".center(70))
        print("=" * 70)

        # Nombre total de techniciens
        cursor.execute("SELECT COUNT(*) FROM techniciens")
        total = cursor.fetchone()[0]
        print(f"\n📊 TOTAL: {total} technicien(s) dans la base")

        # Techniciens actifs
        cursor.execute("SELECT COUNT(*) FROM techniciens WHERE actif = 1")
        actifs = cursor.fetchone()[0]
        print(f"✓ ACTIFS: {actifs} technicien(s)")

        # Techniciens inactifs
        cursor.execute("SELECT COUNT(*) FROM techniciens WHERE actif = 0")
        inactifs = cursor.fetchone()[0]
        print(f"✗ INACTIFS: {inactifs} technicien(s)")

        # Techniciens avec reset requis
        cursor.execute("SELECT COUNT(*) FROM techniciens WHERE force_password_reset = 1")
        reset_requis = cursor.fetchone()[0]
        print(f"⚠️  RESET REQUIS: {reset_requis} technicien(s)")

        print("\n" + "=" * 70)
        print(" LISTE DÉTAILLÉE ".center(70))
        print("=" * 70)
        print(f"{'Prénom':<12} {'Rôle':<12} {'Actif':<8} {'Reset':<8} {'Password'}")
        print("-" * 70)

        cursor.execute("""
            SELECT prenom, role, actif, force_password_reset,
                   LEFT(password, 25) as pass_preview
            FROM techniciens
            ORDER BY prenom
        """)

        for prenom, role, actif, reset, pass_prev in cursor.fetchall():
            actif_str = "✓ Oui" if actif == 1 else "✗ Non"
            reset_str = "⚠️  Oui" if reset == 1 else "✓ Non"
            print(f"{prenom:<12} {role:<12} {actif_str:<8} {reset_str:<8} {pass_prev}")

        print("\n" + "=" * 70)
        print(" IDENTIFIANTS DE CONNEXION ".center(70))
        print("=" * 70)

        cursor.execute("SELECT prenom FROM techniciens WHERE actif = 1 ORDER BY prenom")
        print("\nPour se connecter, utilisez:")
        for (prenom,) in cursor.fetchall():
            print(f"  • Username: {prenom:<12} Password: {prenom.lower()}")

        print("\n" + "=" * 70)
        print("✅ Diagnostic terminé!")
        print("=" * 70)

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False

    return True

if __name__ == "__main__":
    diagnostic()
