# DispatchDockerWorking

Plateforme de gestion d'incidents et de techniciens avec base de connaissances, prete pour un deploiement Docker.

## Sommaire
- Presentation
- Stack technique
- Demarrage rapide
- Configuration
- Fonctionnalites
- Maintenance

## Presentation
DispatchDockerWorking fournit :
- gestion des incidents (statuts, priorites, relances, historique)
- gestion des techniciens (activation, reset mdp, ordre)
- wiki interne (articles, categories, tags)
- temps reel via Socket.IO (notifications, refresh)

## Stack technique
- Backend: Flask + Socket.IO
- DB: PostgreSQL 15
- Reverse proxy: Nginx
- Conteneurs: Docker Compose

## Demarrage rapide
```bash
git clone https://github.com/Naylm/DispatchDockerWorking.git
cd DispatchDockerWorking

docker compose up -d --build
```

Acces: http://localhost

Compte par defaut:
- login: admin
- mot de passe: admin

## Configuration
Variables utiles dans `.env`:
```
SECRET_KEY=change_me
GUNICORN_WORKERS=1
DB_POOL_MIN=5
DB_POOL_MAX=20
```

## Fonctionnalites
### Admin
- creation et edition des incidents
- assignation technicien
- gestion statuts, priorites, sites
- export CSV/PDF/Excel
- relances planifiees avec badge et notification in-app
- gestion techniciens (actif/inactif, reset mdp)
- wiki complet

### Technicien
- vue des tickets assignes
- changement de statut
- notes technicien
- relances et rdv selon statut
- notifications temps reel
- consultation du wiki

## Maintenance
Logs:
```bash
docker compose logs -f app
docker compose logs -f postgres
docker compose logs -f nginx
```

Backup PostgreSQL:
```bash
docker exec dispatch_postgres pg_dump -U dispatch_user dispatch > backup.sql
```

## Licence
MIT
