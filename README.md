# Dispatch Manager V3.0 🚀

Dispatch Manager est une application web moderne pour la gestion d'incidents, la planification de techniciens et le suivi collaboratif, conçue spécialement pour les centres de services et les équipes de support.

![Interface du projet](/c:/Users/nayso/.gemini/antigravity/brain/6981928c-c453-4026-9e26-2c7ba2b3d363/note_edit_mode_view_1772629884093.png)

## 🌟 Fonctionnalités Clés

- **Dashboard Kanban Interactif** : Gérez vos incidents avec une vue en colonnes fluide et intuitive.
- **Calendrier Collaboratif (Style Google/Apple)** : Planifiez les interventions, gérez les rendez-vous et visualisez la charge de travail de l'équipe.
- **Gestion des Techniciens** : Suivi des effectifs, affectations rapides et profils détaillés.
- **Base de Connaissances (Wiki)** : Créez et partagez des articles de support pour une résolution plus rapide.
- **Mode Sombre/Clair Premium** : Interface élégante avec Glassmorphism, transitions fluides et design responsive.
- **Typographie Française** : Conformité totale avec les règles de ponctuation française.

## 🛠️ Stack Technique

- **Backend** : Python (Flask), PostgreSQL, Redis.
- **Frontend** : HTML5, Vanilla CSS3 (Glassmorphism), JavaScript (ES6+).
- **Communication** : WebSockets (Socket.io) pour les mises à jour en temps réel.
- **Déploiement** : Docker & Docker Compose (Nginx, Gunicorn).

## 🚀 Installation & Lancement

Le projet est entièrement conteneurisé pour faciliter le déploiement local et en production.

### Prérequis
- Docker
- Docker Compose

### Lancement
1. Clonez le dépôt :
   ```bash
   git clone https://github.com/Naylm/antigravity_dispatch.git
   cd antigravity_dispatch
   ```

2. Démarrez les services :
   ```bash
   docker-compose up -d --build
   ```

3. Accédez à l'application :
   L'application sera disponible sur `http://localhost`.

## 📈 Améliorations Récentes

- Refonte complète du calendrier collaboratif (empilement des événements, vue journalière/hebdomadaire).
- Optimisation de la visibilité des icônes dans les notes d'incidents.
- Correction de l'ergonomie des boutons d'action (Save/Cancel).

---

Développé avec ❤️ pour l'efficacité opérationnelle.
