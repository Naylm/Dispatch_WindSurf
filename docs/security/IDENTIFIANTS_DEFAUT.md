# Identifiants par défaut - Dispatch Manager

## 🔐 Tous les mots de passe ont été réinitialisés

Les mots de passe de tous les comptes ont été réinitialisés avec des valeurs simples pour faciliter les tests.

## 👤 Compte Administrateur

| Username | Password | Rôle |
|----------|----------|------|
| melvin   | admin    | Admin |

**Accès** : Peut tout faire (ajout incidents, configuration, gestion techniciens, etc.)

## 👥 Comptes Techniciens

| Username | Password  | Rôle       |
|----------|-----------|------------|
| Hugo     | hugo      | Technicien |
| Alexis   | alexis    | Technicien |
| Aurelien | aurelien  | Technicien |
| Patrice  | patrice   | Technicien |
| Ethan    | ethan     | Technicien |
| Frederic | frederic  | Technicien |
| Tom      | tom       | Technicien |
| Stephane | stephane  | Admin      |

**Accès technicien** : Peut voir et modifier les incidents assignés
**Accès admin** : Stephane a les mêmes droits qu'un admin

## 📝 Notes importantes

### Format des identifiants
- **Username** : Prénom avec majuscule initiale (ex: Hugo)
- **Password** : Prénom en minuscules (ex: hugo)

### Sécurité
⚠️ **ATTENTION** : Ces mots de passe sont volontairement simples pour faciliter les tests.

En production, vous devriez :
1. Changer tous les mots de passe pour des valeurs sécurisées
2. Forcer les utilisateurs à changer leur mot de passe à la première connexion
3. Implémenter une politique de mots de passe forts

### Scripts de réinitialisation

Deux scripts Python sont disponibles pour réinitialiser les mots de passe :

#### 1. [reset_technicien_passwords.py](reset_technicien_passwords.py)
Réinitialise tous les mots de passe des techniciens avec le prénom en minuscule.

```bash
# Exécuter depuis le container
docker exec dispatch_manager python reset_technicien_passwords.py
```

#### 2. [reset_admin_password.py](reset_admin_password.py)
Réinitialise le mot de passe admin (melvin / admin).

```bash
# Exécuter depuis le container
docker exec dispatch_manager python reset_admin_password.py
```

## 🧪 Test de connexion

### 1. Test Admin
1. Aller sur http://localhost/login
2. Username: `melvin`
3. Password: `admin`
4. → Doit accéder au dashboard admin

### 2. Test Technicien
1. Aller sur http://localhost/login
2. Username: `Hugo`
3. Password: `hugo`
4. → Doit accéder au dashboard technicien

### 3. Test Force Reset
1. Se connecter en tant qu'admin (melvin / admin)
2. Aller dans "Gestion des techniciens"
3. Cliquer sur 🔒 pour forcer Hugo à changer son mot de passe
4. Se déconnecter
5. Se reconnecter avec Hugo / hugo
6. → Doit être redirigé vers la page de changement de mot de passe
7. Changer le mot de passe (ex: Hugo / hugo / nouveaumotdepasse123)
8. → Doit accéder au dashboard normalement

## 🔄 Historique des réinitialisations

**Date** : 2025-11-24
**Raison** : Les identifiants actuels ne fonctionnaient pas (mots de passe inconnus)
**Action** : Réinitialisation complète avec des mots de passe simples
**Status** : ✅ Tous les comptes fonctionnels

## 📊 État actuel de la base

```sql
-- Vérifier tous les utilisateurs
SELECT username, role, force_password_reset FROM users;
-- Résultat: melvin | admin | 0

-- Vérifier tous les techniciens
SELECT prenom, role, force_password_reset FROM techniciens ORDER BY prenom;
-- Résultat: 8 techniciens avec force_password_reset = 0
```

Tous les comptes sont maintenant **opérationnels** et peuvent se connecter immédiatement sans restriction.

---

**Accès application** : http://localhost/login
**Documentation complète** : [AUTHENTICATION_FIXES.md](AUTHENTICATION_FIXES.md)
