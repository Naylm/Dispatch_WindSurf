#!/usr/bin/env python3
"""
Met le compte Melvin en "normal" (role=user) dans la table users.
Ne touche pas au mot de passe (sauf si force_password_reset doit etre remis a 0).
"""

import sys
from db_config import get_db


def make_melvin_normal():
    db = get_db()

    user = db.execute(
        "SELECT id, username, role, force_password_reset FROM users WHERE LOWER(username)=LOWER(%s)",
        ("Melvin",),
    ).fetchone()

    if not user:
        print("❌ Aucun utilisateur 'Melvin' trouvé dans la table users.")
        db.close()
        return 1

    db.execute(
        "UPDATE users SET role=%s, force_password_reset=%s WHERE id=%s",
        ("user", 0, user["id"]),
    )
    db.commit()
    db.close()

    print("✅ Melvin est maintenant un compte normal (role=user).")
    print("   Tu peux mettre email/numero depuis le profil.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(make_melvin_normal())
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        sys.exit(1)
