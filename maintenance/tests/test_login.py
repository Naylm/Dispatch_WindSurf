#!/usr/bin/env python3
"""
Script de test pour vérifier que tous les utilisateurs peuvent se connecter
"""
import requests
from bs4 import BeautifulSoup

BASE_URL = "http://localhost"

def get_csrf_token(session):
    """Récupère le token CSRF de la page de login"""
    response = session.get(f"{BASE_URL}/login")
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    if csrf_input:
        return csrf_input.get('value')
    return None

def test_login(username, password):
    """Teste la connexion pour un utilisateur"""
    session = requests.Session()

    # Récupérer le token CSRF
    csrf_token = get_csrf_token(session)
    if not csrf_token:
        return False, "Pas de token CSRF"

    # Tenter la connexion
    response = session.post(
        f"{BASE_URL}/login",
        data={
            'username': username,
            'password': password,
            'csrf_token': csrf_token
        },
        allow_redirects=False
    )

    # Si on est redirigé, c'est que la connexion a réussi
    if response.status_code in [302, 303]:
        location = response.headers.get('Location', '')
        if 'login' in location:
            return False, "Redirection vers login (échec)"
        return True, f"Redirection vers {location}"

    # Vérifier s'il y a un message d'erreur
    soup = BeautifulSoup(response.text, 'html.parser')
    alert = soup.find('div', {'class': 'alert'})
    if alert:
        return False, alert.text.strip()

    return False, f"Status {response.status_code}"

# Liste des utilisateurs à tester (username, password)
# NOTE: Remplacer par les vrais mots de passe
test_users = [
    ("melvin", "admin123"),  # Admin
    ("Hugo", "tech123"),     # Technicien
    ("Alexis", "tech123"),   # Technicien
]

print("=" * 60)
print("TEST DE CONNEXION POUR TOUS LES UTILISATEURS")
print("=" * 60)
print()

success_count = 0
fail_count = 0

for username, password in test_users:
    success, message = test_login(username, password)
    status = "✅ OK" if success else "❌ ÉCHEC"
    print(f"{status} | {username:15s} | {message}")

    if success:
        success_count += 1
    else:
        fail_count += 1

print()
print("=" * 60)
print(f"Résultat: {success_count} réussis, {fail_count} échoués")
print("=" * 60)
