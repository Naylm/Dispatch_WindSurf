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

Premier compte admin:
- definir `BOOTSTRAP_ADMIN_USERNAME` et `BOOTSTRAP_ADMIN_PASSWORD` dans `.env`
- le compte est cree au demarrage avec `force_password_reset=1`

## Configuration
Variables utiles dans `.env`:
```
SECRET_KEY=change_me
POSTGRES_USER=dispatch_user
POSTGRES_PASSWORD=change_me
GUNICORN_WORKERS=2
REDIS_URL=redis://redis:6379/0
SOCKETIO_ALLOWED_ORIGINS=http://localhost,http://127.0.0.1
SOCKETIO_DEBUG=false
BOOTSTRAP_ADMIN_USERNAME=
BOOTSTRAP_ADMIN_PASSWORD=
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
