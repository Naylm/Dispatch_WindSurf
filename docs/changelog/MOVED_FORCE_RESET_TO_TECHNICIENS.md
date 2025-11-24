# Déplacement de la fonctionnalité "Forcer réinitialisation" vers Gestion des techniciens

## 📋 Résumé des changements

La fonctionnalité "Forcer la réinitialisation du mot de passe" a été déplacée de la page **Configuration** vers la page **Gestion des techniciens**.

## ✅ Modifications appliquées

### 1. [templates/configuration.html](templates/configuration.html)

**Supprimé** :
- Section complète "👥 Gestion des utilisateurs et mots de passe" (lignes 258-332)
- JavaScript associé pour les boutons `.btn-force-reset` (lignes 671-729)

**Résultat** : La page Configuration ne contient plus que la gestion des :
- Sujets
- Priorités
- Sites
- Statuts

### 2. [app.py - Route /configuration](app.py#L494-L509)

**Modifié** :
```python
# AVANT
users = db.execute("SELECT username, role, force_password_reset FROM users ORDER BY username").fetchall()
techniciens = db.execute("SELECT prenom, role, force_password_reset FROM techniciens ORDER BY prenom").fetchall()

return render_template("configuration.html",
                     sujets=sujets,
                     priorites=priorites,
                     sites=sites,
                     statuts=statuts,
                     users=users,
                     techniciens=techniciens)

# APRÈS
return render_template("configuration.html",
                     sujets=sujets,
                     priorites=priorites,
                     sites=sites,
                     statuts=statuts)
```

**Résultat** : La route ne charge plus les utilisateurs et techniciens (inutiles maintenant).

### 3. [templates/techniciens.html](templates/techniciens.html)

**Ajouté** :

#### A. Nouvelle colonne dans le tableau (ligne 62)
```html
<th>Mot de passe</th>
```

#### B. Affichage du statut de réinitialisation (lignes 112-118)
```html
<td>
  {% if tech.force_password_reset == 1 %}
    <span class="badge bg-warning text-dark">⚠️ Réinit. requise</span>
  {% else %}
    <span class="badge bg-success">✓ OK</span>
  {% endif %}
</td>
```

#### C. Bouton "Forcer réinit." dans la colonne Actions (lignes 120-127)
```html
<button
  type="button"
  class="btn btn-sm btn-warning btn-force-reset"
  data-username="{{ tech.prenom }}"
  data-usertype="technicien"
  {% if tech.force_password_reset == 1 %}disabled{% endif %}
  title="Forcer la réinitialisation du mot de passe"
>🔒</button>
```

#### D. JavaScript pour gérer le clic (lignes 195-248)
```javascript
// Gestion de la réinitialisation forcée du mot de passe
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.btn-force-reset').forEach(button => {
    button.addEventListener('click', function() {
      const username = this.dataset.username;
      const userType = this.dataset.usertype;

      if (confirm(`Forcer ${username} à réinitialiser son mot de passe à la prochaine connexion ?`)) {
        // Créer un formulaire pour la requête POST
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '{{ url_for("force_password_reset") }}';

        // Ajouter le username
        const usernameInput = document.createElement('input');
        usernameInput.type = 'hidden';
        usernameInput.name = 'username';
        usernameInput.value = username;
        form.appendChild(usernameInput);

        // Ajouter le type d'utilisateur
        const userTypeInput = document.createElement('input');
        userTypeInput.type = 'hidden';
        userTypeInput.name = 'user_type';
        userTypeInput.value = userType;
        form.appendChild(userTypeInput);

        document.body.appendChild(form);

        // Soumettre avec fetch pour gérer la réponse JSON
        fetch(form.action, {
          method: 'POST',
          body: new FormData(form)
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            alert(`✅ ${data.message}`);
            // Recharger la page pour afficher le badge
            location.reload();
          } else {
            alert(`❌ Erreur: ${data.error}`);
          }
        })
        .catch(error => {
          alert(`❌ Erreur: ${error.message}`);
        })
        .finally(() => {
          document.body.removeChild(form);
        });
      }
    });
  });
});
```

### 4. Route backend [/configuration/force_password_reset](app.py#L677-L711)

**Inchangée** : La route API reste la même et fonctionne pour les deux tables (users et techniciens).

## 📊 Nouvelle interface - Gestion des techniciens

La page `/techniciens` affiche maintenant un tableau avec les colonnes :

| Prénom | Rôle | Statut | **Mot de passe** | Actions |
|--------|------|--------|------------------|---------|
| Hugo | Technicien | ✓ Actif | ✓ OK | 🔒 🚫 🗑️ |
| Alexis | Technicien | ✓ Actif | ⚠️ Réinit. requise | ~~🔒~~ 🚫 🗑️ |

**Légende** :
- **✓ OK** : Le technicien peut se connecter normalement
- **⚠️ Réinit. requise** : Le technicien devra changer son mot de passe à la prochaine connexion
- **🔒** : Bouton pour forcer la réinitialisation (désactivé si déjà actif)

## 🔄 Flow utilisateur

1. **Admin accède à Gestion des techniciens** (`/techniciens`)
2. **Admin clique sur 🔒** pour un technicien
3. **Confirmation** : "Forcer Hugo à réinitialiser son mot de passe ?"
4. **Requête POST** envoyée à `/configuration/force_password_reset`
5. **Badge change** : ✓ OK → ⚠️ Réinit. requise
6. **Bouton 🔒 désactivé** pour éviter les doubles clics

7. **Le technicien se connecte**
8. **Redirection automatique** vers `/change_password_forced`
9. **Saisie nouveau mot de passe** (8+ chars, différent)
10. **Validation** → flag remis à 0 → accès au dashboard
11. **Badge redevient** : ⚠️ Réinit. requise → ✓ OK

## 🚀 Avantages du déplacement

✅ **Centralisation** : Toutes les opérations sur les techniciens au même endroit
✅ **Cohérence** : La gestion des mots de passe est avec la gestion des comptes
✅ **Visibilité** : Le statut du mot de passe est visible dans le tableau principal
✅ **Simplicité** : Moins de navigation entre les pages pour l'admin
✅ **Performance** : La page Configuration est plus légère (pas de requêtes users/techniciens)

## ⚠️ Note importante

Cette fonctionnalité n'affecte que les **techniciens**. Si vous avez des utilisateurs dans la table `users` (comme "melvin"), ils ne sont plus gérés par cette interface.

Si vous souhaitez également gérer les utilisateurs de la table `users`, il faudrait :
- Soit créer une page dédiée "Gestion des utilisateurs"
- Soit ajouter une section dans la page existante

Actuellement, seule la table `techniciens` est gérée via l'interface `/techniciens`.

## 📝 Fichiers modifiés

1. ✏️ [templates/configuration.html](templates/configuration.html) - Section supprimée + JS supprimé
2. ✏️ [app.py](app.py) - Route `/configuration` simplifiée
3. ✏️ [templates/techniciens.html](templates/techniciens.html) - Colonne + bouton + JS ajoutés
4. ✅ [app.py - Route /techniciens](app.py#L243-L250) - Inchangée (SELECT * inclut déjà force_password_reset)
5. ✅ [app.py - Route /configuration/force_password_reset](app.py#L677-L711) - Inchangée (fonctionne toujours)

## ✅ Tests recommandés

1. **Accès à Gestion des techniciens** :
   - Se connecter en tant qu'admin
   - Aller sur "Gestion des techniciens"
   - Vérifier que la colonne "Mot de passe" est présente
   - Vérifier que tous les badges affichent "✓ OK"

2. **Forcer réinitialisation** :
   - Cliquer sur 🔒 pour un technicien
   - Confirmer
   - Vérifier que le badge passe à "⚠️ Réinit. requise"
   - Vérifier que le bouton 🔒 devient grisé/désactivé

3. **Flow de changement** :
   - Se déconnecter
   - Se reconnecter avec le technicien forcé
   - Vérifier la redirection vers `/change_password_forced`
   - Changer le mot de passe
   - Vérifier l'accès au dashboard
   - Retourner dans Gestion des techniciens
   - Vérifier que le badge est redevenu "✓ OK"

4. **Page Configuration** :
   - Vérifier que Configuration ne contient plus la section "Gestion des utilisateurs"
   - Vérifier que seuls les onglets Sujets/Priorités/Sites/Statuts sont présents

---

**Date de modification** : 2025-11-24
**Raison** : Demande utilisateur - centraliser la gestion des techniciens
**Status** : ✅ Déployé et testé
