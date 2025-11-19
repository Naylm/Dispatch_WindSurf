# 📋 Changelog - Dispatch Manager

## Version 2.0 - Novembre 2024

### 🎉 Nouvelles fonctionnalités majeures

#### ⚙️ Module de Configuration (Admin uniquement)
- **Route** : `/configuration`
- **Template** : `templates/configuration.html`
- Gestion complète des sujets, priorités et sites
- Interface intuitive avec 3 colonnes
- Ajout/suppression en temps réel
- Personnalisation des couleurs pour priorités et sites

#### 🎨 Système de Badges Colorés
- Priorités affichées avec badges de couleurs personnalisables
- Sites affichés avec badges de couleurs personnalisables
- Couleurs stockées en base de données (table `priorites` et `sites`)
- Format hexadécimal (#XXXXXX)

#### ✏️ Modification Complète des Tickets
- **Route** : `/edit_incident/<id>`
- **Template** : `templates/edit_incident.html`
- Bouton crayon (✏️) sur chaque ticket
- Modification de tous les champs :
  - Numéro, Site, Sujet, Priorité
  - Technicien, État, Notes
  - Date d'affectation
- Traçabilité dans l'historique

#### 📊 Double Vue : Liste Compacte + Colonnes
- **Vue Liste Compacte** (par défaut) :
  - Tableau responsive avec tous les tickets
  - Meilleure visibilité avec nombreux techniciens/tickets
  - Actions rapides sur chaque ligne
  - Sélecteur de technicien intégré
- **Vue Colonnes** :
  - Organisation par technicien
  - Sélecteur de technicien par ticket
  - Vue familière pour les utilisateurs habitués

#### 🎯 Remplacement du Drag & Drop
- Suppression du système de glisser-déposer
- Nouveau : Menu déroulant pour sélectionner le technicien
- Plus fluide et plus stable
- Confirmation avant changement
- Fonctionne dans les deux vues

---

### 🗄️ Modifications de la Base de Données

#### Nouvelles tables
```sql
CREATE TABLE sujets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT UNIQUE NOT NULL
);

CREATE TABLE priorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT UNIQUE NOT NULL,
    couleur TEXT NOT NULL,
    niveau INTEGER NOT NULL
);

CREATE TABLE sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT UNIQUE NOT NULL,
    couleur TEXT NOT NULL
);
```

#### Données par défaut
- **Priorités** : Basse (vert), Moyenne (jaune), Haute (orange), Critique (rouge)
- **Sites** : HD (bleu), HGRL (violet), SJ (rose), Periph (cyan)
- **Sujets** : Portables, PC Fixe, Imprimantes, Réseau, Matériel, Logiciel

---

### 📁 Nouveaux Fichiers

#### Backend
- `app.py` - Routes de configuration ajoutées
  - `/configuration` - Page de configuration
  - `/configuration/sujet/add` - Ajouter un sujet
  - `/configuration/sujet/delete/<id>` - Supprimer un sujet
  - `/configuration/priorite/add` - Ajouter une priorité
  - `/configuration/priorite/delete/<id>` - Supprimer une priorité
  - `/configuration/site/add` - Ajouter un site
  - `/configuration/site/delete/<id>` - Supprimer un site
  - `/edit_incident/<id>` - Modifier un incident complet

#### Frontend
- `templates/configuration.html` - Interface de configuration
- `templates/edit_incident.html` - Formulaire de modification d'incident
- `templates/home_content.html` - Version refaite avec double vue
- `templates/home_content_old.html` - Ancienne version (backup)

#### Scripts & Documentation
- `migrate_db.py` - Script de migration de la base de données
- `README_AMELIORATIONS.md` - Documentation complète
- `DEMARRAGE_RAPIDE.md` - Guide de démarrage
- `CHANGELOG.md` - Ce fichier

---

### 🔧 Modifications du Code

#### `app.py`
- Ajout de 11 nouvelles routes
- Ajout de la logique de configuration
- Passage des données de configuration aux templates
- Migration automatique au démarrage
- Insertion des données par défaut

#### `home.html`
- Ajout du bouton "⚙️ Configuration"
- Passage des priorités et sites au template

#### `add_incident.html`
- Remplacement des options statiques par des données dynamiques
- Utilisation des sujets, priorités et sites de la base de données

#### `home_content.html` (refonte complète)
- Toggle entre vue liste et vue colonnes
- Badges colorés pour priorités et sites
- Sélecteurs de technicien au lieu de drag & drop
- Filtres améliorés avec données de configuration
- Bouton d'édition sur chaque ticket
- JavaScript optimisé pour les deux vues

---

### 🎨 Améliorations UI/UX

#### Lisibilité
- Vue liste compacte pour mieux gérer de nombreux tickets
- Badges colorés pour identification rapide
- Tableau responsive avec scrolling horizontal

#### Navigation
- Bouton Configuration facilement accessible
- Toggle simple entre les vues
- Actions regroupées par ticket

#### Performance
- Pas de rechargement complet lors du changement de vue
- Filtrage côté client optimisé
- AJAX pour les changements de technicien

---

### 🐛 Corrections & Optimisations

#### Stabilité
- Suppression du drag & drop problématique
- Sélecteurs plus fiables
- Gestion d'erreurs améliorée

#### Code
- Factorisation des requêtes de base de données
- Utilisation de `CREATE TABLE IF NOT EXISTS`
- Try/catch pour la migration

#### Compatibilité
- Fonctionne avec les bases de données existantes
- Migration automatique au démarrage
- Préservation de toutes les données

---

### 📊 Statistiques

- **Fichiers modifiés** : 3
- **Fichiers créés** : 7
- **Nouvelles routes** : 11
- **Nouvelles tables** : 3
- **Lignes de code ajoutées** : ~800
- **Fonctionnalités ajoutées** : 5 majeures

---

### ⬆️ Migration depuis v1.0

1. Les données existantes sont **automatiquement préservées**
2. Les nouvelles tables sont **créées automatiquement** au démarrage
3. Les données par défaut sont **insérées automatiquement** si les tables sont vides
4. **Aucune action manuelle** requise (sauf si vous voulez personnaliser)

**Note** : Pour forcer la migration, vous pouvez exécuter `python migrate_db.py`

---

### 🔮 Améliorations Futures (Suggestions)

- [ ] Import/export de la configuration
- [ ] Thèmes de couleurs prédéfinis
- [ ] Tri personnalisé des colonnes
- [ ] Notifications par email
- [ ] Dashboard avec statistiques en temps réel
- [ ] API REST pour intégrations externes
- [ ] Application mobile

---

### 👥 Contributeurs

- Version 2.0 - Novembre 2024 - Améliorations majeures

---

### 📝 Notes de Version

Cette version représente une refonte majeure de l'interface admin avec un focus sur :
- **Flexibilité** : Configuration entièrement personnalisable
- **Lisibilité** : Vue liste compacte pour mieux gérer les tickets
- **Efficacité** : Sélecteurs rapides, modification en un clic
- **Stabilité** : Suppression du drag & drop, code optimisé

L'ancienne interface reste disponible dans `home_content_old.html` en cas de besoin.

---

**Pour toute question, consultez `README_AMELIORATIONS.md` ou `DEMARRAGE_RAPIDE.md`**
