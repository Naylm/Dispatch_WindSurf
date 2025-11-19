import sqlite3
import os

# Chemin vers la base de données (un niveau au-dessus)
DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dispatch.db')

def ensure_techniciens_table():
    # Ouvre la BDD (ou la crée si elle n'existe pas)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # 1. Vérifier si la table 'techniciens' existe
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='techniciens';")
    if not cur.fetchone():
        # La table n'existe pas : on la crée avec la colonne password
        cur.execute("""
            CREATE TABLE techniciens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prenom TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'technicien',
                password TEXT
            );
        """)
        print("Table 'techniciens' créée avec la colonne 'password'.")
    else:
        # La table existe : on vérifie la colonne password
        cur.execute("PRAGMA table_info(techniciens);")
        cols = [row[1] for row in cur.fetchall()]  # nom des colonnes
        if 'password' not in cols:
            # Ajout de la colonne password
            cur.execute("ALTER TABLE techniciens ADD COLUMN password TEXT;")
            print("Colonne 'password' ajoutée à la table 'techniciens'.")
        else:
            print("La table 'techniciens' et la colonne 'password' existent déjà.")

    conn.commit()
    conn.close()

def insert_example_technicien():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Exemple d'ajout d'un technicien avec mot de passe (si le prénom n'existe pas déjà)
    prenom_ex = "Alice"
    role_ex = "technicien"
    pass_ex = "monMDP123"

    cur.execute("""
        INSERT OR IGNORE INTO techniciens (prenom, role, password)
        VALUES (?, ?, ?);
    """, (prenom_ex, role_ex, pass_ex))

    if cur.rowcount:
        print(f"• Technicien '{prenom_ex}' inséré avec mot de passe.")
    else:
        print(f"• Le technicien '{prenom_ex}' existe déjà (aucune insertion).")

    conn.commit()
    conn.close()

def show_all_techniciens():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print("\nListe actuelle des techniciens :")
    cur.execute("SELECT id, prenom, role, password FROM techniciens;")
    for row in cur.fetchall():
        tid, prenom, role, pwd = row
        print(f"  • [id={tid}] {prenom} ({role}) — password='{pwd}'")

    conn.close()

if __name__ == "__main__":
    ensure_techniciens_table()
    insert_example_technicien()
    show_all_techniciens()
