# Dispatch Manager V1.3

## 📋 Description

Dispatch Manager V1.3 est une application web de gestion de tickets informatiques développée avec Flask et SocketIO. Elle permet aux administrateurs et techniciens de gérer efficacement les incidents, de suivre leur progression et de collaborer via une base de connaissances intégrée.

## 🚀 Fonctionnalités principales

### Gestion des tickets

- Création, modification et suppression d'incidents
- Assignation des tickets aux techniciens
- Suivi des statuts et priorités
- Historique complet des modifications
- Export Excel et PDF

### Interface utilisateur

- Vue admin avec colonnes de techniciens
- Vue technicien avec cartes d'incidents
- Sidebar permanente avec liens rapides
- Mode sombre/clair
- Design responsive mobile

### Wiki collaboratif

- Base de connaissances avec catégories et sous-catégories
- Éditeur Markdown avec preview
- Système de likes/dislikes
- Historique des modifications
- Upload d'images

### Temps réel

- Mises à jour en direct via SocketIO
- Notifications instantanées
- Synchronisation automatique

## 🛠️ Installation

### Prérequis

- Python 3.8+
- pip
- Git

### Étapes d'installation

1. Cloner le dépôt :

```bash
git clone https://github.com/Naylm/DispatchManagerV1.3.git
cd DispatchManagerV1.3
```

2. Installer les dépendances :

```bash
pip install -r requirements.txt
```

3. Lancer l'application :

```bash
python scripts/DEMARRER.bat
```

4. Accéder à l'application :

```text
http://localhost:5000
```

## 📁 Structure du projet

```text
DispatchManagerV1.2/
├── app.py                 # Application principale Flask
├── wsgi.py               # Configuration serveur Gunicorn
├── dispatch.db           # Base de données SQLite
├── static/               # Fichiers statiques
│   ├── css/             # Styles CSS
│   ├── js/              # Fichiers JavaScript
│   └── img/             # Images et favicon
├── templates/           # Templates HTML
├── scripts/             # Scripts de démarrage
└── docs/                # Documentation
```

## 👥 Utilisateurs

### Rôles

- **Admin** : Gestion complète des tickets, techniciens et configuration
- **Technicien** : Gestion des incidents qui lui sont assignés

### Comptes par défaut

- Admin : `admin` / `admin`
- Technicien : `tech` / `tech`

## 🔧 Configuration

### Variables d'environnement

Créer un fichier `.env` avec :

```text
SECRET_KEY=votre_clé_secrète
```

### Base de données

La base de données SQLite est automatiquement initialisée au premier démarrage.

## 📞 Support

Pour toute question ou problème, veuillez créer une issue dans le dépôt GitHub.

## 📄 Licence

Ce projet est sous licence privée.
