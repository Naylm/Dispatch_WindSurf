import os
import sys
from werkzeug.security import generate_password_hash

# Add app directory to path to import app modules
# Assuming script is run from project root inside container
sys.path.append(os.getcwd())

from app.utils.db_config import get_db

def create_technician(username, password):
    print(f"Connecting to database to create technician '{username}'...")
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check if technician already exists (check both username and prenom)
        cursor.execute("SELECT id FROM techniciens WHERE LOWER(username) = LOWER(%s) OR LOWER(prenom) = LOWER(%s)", (username, username))
        if cursor.fetchone():
            print(f"Technician '{username}' already exists.")
            return

        # Insert technician
        cursor.execute(
            "INSERT INTO techniciens (prenom, username, password, role, actif) VALUES (%s, %s, %s, %s, %s)",
            (username, username, generate_password_hash(password), 'technicien', 1)
        )
        db.commit()
        print(f"Technician '{username}' created successfully.")
    except Exception as e:
        print(f"Error creating technician: {e}")

if __name__ == "__main__":
    create_technician("Technicien", "Technicien")
