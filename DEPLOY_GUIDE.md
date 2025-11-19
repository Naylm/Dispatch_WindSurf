# Guide de Déploiement - Dispatch Manager

Ce guide explique comment déployer l'application Dispatch Manager facilement sur n'importe quel serveur équipé de Docker.

## Prérequis

- **Docker** et **Docker Compose** doivent être installés sur votre serveur.

## Installation Rapide

1.  **Téléchargez les fichiers** sur votre serveur.
2.  **Ouvrez un terminal** dans le dossier.
3.  **Lancez l'application** :

    ```bash
    docker compose up -d
    ```

    L'application sera accessible directement sur :
    > **http://agartha.cc** (ou http://88.214.57.137)

## Configuration Domaine

Le fichier `nginx.conf` est déjà pré-configuré pour votre domaine :
- `agartha.cc`
- `88.214.57.137`

Si vous ajoutez le SSL plus tard, modifiez simplement ce fichier.

## Gestion des Données

Les données sont persistantes et stockées dans des volumes Docker locaux gérés automatiquement :

- **Base de données** : Volume `dispatch_data` (monté dans `/app/data`)
- **Uploads Wiki** : Volume `dispatch_uploads` (monté dans `/app/static/uploads`)

## Commandes Utiles

- **Voir les logs** :
  ```bash
  docker compose logs -f
  ```

- **Arrêter l'application** :
  ```bash
  docker compose down
  ```

- **Mettre à jour l'application** (après avoir téléchargé le nouveau code) :
  ```bash
  docker compose build --no-cache
  docker compose up -d
  ```

## Configuration Avancée (Optionnel)

Si vous souhaitez changer la clé secrète (recommandé en production), vous pouvez créer un fichier `.env` à la racine :

```env
SECRET_KEY=votre_cle_secrete_tres_longue_et_aleatoire
FLASK_ENV=production
```

## Architecture

- **Image** : Python 3.11 Slim
- **Serveur WSGI** : Gunicorn avec Eventlet (pour le support WebSocket)
- **Base de données** : SQLite (embarquée, mode WAL activé pour la performance)

## Note pour Nginx (Production Avancée)

Un fichier `nginx.conf.example` est fourni si vous souhaitez placer l'application derrière un reverse proxy Nginx (pour gérer le SSL/HTTPS par exemple). Ce n'est pas nécessaire pour un usage simple en intranet.
