#!/bin/bash
echo "Test de connexion Hugo"
echo "======================"

# Test avec Hugo (majuscule)
curl -s -c cookies.txt http://localhost/login > /dev/null
CSRF=$(curl -s http://localhost/login | grep 'csrf_token' | grep -oP 'value="\K[^"]+')

curl -s -b cookies.txt -c cookies.txt \
  -X POST \
  -d "username=Hugo&password=hugo&csrf_token=$CSRF" \
  http://localhost/login -L | grep -o "Dispatch Manager" && echo "✅ Connexion Hugo réussie" || echo "❌ Échec connexion Hugo"

# Test avec melvin
curl -s -c cookies2.txt http://localhost/login > /dev/null
CSRF2=$(curl -s http://localhost/login | grep 'csrf_token' | grep -oP 'value="\K[^"]+')

curl -s -b cookies2.txt -c cookies2.txt \
  -X POST \
  -d "username=melvin&password=admin&csrf_token=$CSRF2" \
  http://localhost/login -L | grep -o "Dispatch Manager" && echo "✅ Connexion melvin réussie" || echo "❌ Échec connexion melvin"

rm -f cookies.txt cookies2.txt
