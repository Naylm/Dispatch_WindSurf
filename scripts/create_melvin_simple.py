#!/usr/bin/env python3
import sys
from werkzeug.security import generate_password_hash
from db_config import get_db

db = get_db()
melvin_hash = generate_password_hash('Admin')

# Vérifier si existe
user = db.execute("SELECT * FROM users WHERE username = %s", ('Melvin',)).fetchone()

if user:
    db.execute("UPDATE users SET password = %s, role = %s WHERE username = %s", 
               (melvin_hash, 'admin', 'Melvin'))
    print("UPDATE")
else:
    db.execute("INSERT INTO users (username, password, role, force_password_reset) VALUES (%s, %s, %s, %s)",
               ('Melvin', melvin_hash, 'admin', 0))
    print("INSERT")

db.commit()
db.close()
print("SUCCESS")


