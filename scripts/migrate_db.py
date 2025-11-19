"""
Script de migration pour ajouter les tables de configuration
à une base de données existante
"""
import sqlite3
import os

# Chemin vers la base de données (un niveau au-dessus)
DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dispatch.db")

def migrate():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    
    print("🔄 Migration de la base de données en cours...")
    
    # Créer la table sujets si elle n'existe pas
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sujets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT UNIQUE NOT NULL
            )
        """)
        print("✅ Table 'sujets' créée ou déjà existante")
    except Exception as e:
        print(f"❌ Erreur lors de la création de la table 'sujets': {e}")
    
    # Créer la table priorites si elle n'existe pas
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS priorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT UNIQUE NOT NULL,
                couleur TEXT NOT NULL,
                niveau INTEGER NOT NULL
            )
        """)
        print("✅ Table 'priorites' créée ou déjà existante")
    except Exception as e:
        print(f"❌ Erreur lors de la création de la table 'priorites': {e}")
    
    # Créer la table sites si elle n'existe pas
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT UNIQUE NOT NULL,
                couleur TEXT NOT NULL
            )
        """)
        print("✅ Table 'sites' créée ou déjà existante")
    except Exception as e:
        print(f"❌ Erreur lors de la création de la table 'sites': {e}")
    
    # Ajouter la colonne localisation à la table incidents si elle n'existe pas
    try:
        cursor.execute("ALTER TABLE incidents ADD COLUMN localisation TEXT DEFAULT ''")
        print("✅ Colonne 'localisation' ajoutée à la table 'incidents'")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️  La colonne 'localisation' existe déjà dans la table 'incidents'")
        else:
            print(f"⚠️  Erreur lors de l'ajout de la colonne 'localisation': {e}")
    
    # Ajouter des données par défaut si les tables sont vides
    try:
        count = cursor.execute("SELECT COUNT(*) FROM priorites").fetchone()[0]
        if count == 0:
            cursor.execute("""
                INSERT INTO priorites (nom, couleur, niveau) VALUES
                ('Basse', '#28a745', 1),
                ('Moyenne', '#ffc107', 2),
                ('Haute', '#fd7e14', 3),
                ('Critique', '#dc3545', 4)
            """)
            print("✅ Priorités par défaut ajoutées")
    except Exception as e:
        print(f"⚠️  Erreur lors de l'ajout des priorités: {e}")
    
    try:
        count = cursor.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        if count == 0:
            cursor.execute("""
                INSERT INTO sites (nom, couleur) VALUES
                ('HD', '#007bff'),
                ('HGRL', '#6f42c1'),
                ('SJ', '#e83e8c'),
                ('Periph', '#17a2b8')
            """)
            print("✅ Sites par défaut ajoutés")
    except Exception as e:
        print(f"⚠️  Erreur lors de l'ajout des sites: {e}")
    
    try:
        count = cursor.execute("SELECT COUNT(*) FROM sujets").fetchone()[0]
        if count == 0:
            cursor.execute("""
                INSERT INTO sujets (nom) VALUES
                ('Portables'),
                ('PC Fixe'),
                ('Imprimantes - impressions'),
                ('Réseau'),
                ('Matériel'),
                ('Logiciel')
            """)
            print("✅ Sujets par défaut ajoutés")
    except Exception as e:
        print(f"⚠️  Erreur lors de l'ajout des sujets: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration terminée avec succès!")
    print("Vous pouvez maintenant démarrer l'application.")

if __name__ == "__main__":
    migrate()
