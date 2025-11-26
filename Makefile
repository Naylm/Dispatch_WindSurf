# ============================================
# Makefile - Dispatch Manager Docker
# ============================================
# Commandes simplifiées pour Docker Compose

.PHONY: help build up down restart logs shell db-backup db-restore clean test

# Couleurs pour l'affichage
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Afficher cette aide
	@echo "$(CYAN)╔════════════════════════════════════════╗$(NC)"
	@echo "$(CYAN)║   Dispatch Manager - Docker Helper    ║$(NC)"
	@echo "$(CYAN)╚════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Commandes disponibles :$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-15s$(NC) %s\n", $$1, $$2}'

build: ## Construire les images Docker
	@echo "$(GREEN)🔨 Construction des images Docker...$(NC)"
	docker-compose build

up: ## Démarrer tous les services
	@echo "$(GREEN)🚀 Démarrage de l'application...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Application disponible sur http://localhost$(NC)"

down: ## Arrêter tous les services
	@echo "$(YELLOW)⏸️  Arrêt de l'application...$(NC)"
	docker-compose down

restart: ## Redémarrer tous les services
	@echo "$(YELLOW)🔄 Redémarrage de l'application...$(NC)"
	docker-compose restart

logs: ## Afficher les logs (CTRL+C pour quitter)
	@echo "$(CYAN)📋 Logs en temps réel...$(NC)"
	docker-compose logs -f

logs-app: ## Afficher les logs de l'application uniquement
	@echo "$(CYAN)📋 Logs Flask/Gunicorn...$(NC)"
	docker-compose logs -f app

logs-nginx: ## Afficher les logs Nginx
	@echo "$(CYAN)📋 Logs Nginx...$(NC)"
	docker-compose logs -f nginx

logs-db: ## Afficher les logs PostgreSQL
	@echo "$(CYAN)📋 Logs PostgreSQL...$(NC)"
	docker-compose logs -f postgres

ps: ## Afficher l'état des conteneurs
	@echo "$(CYAN)📊 État des conteneurs :$(NC)"
	docker-compose ps

shell: ## Accéder au shell du conteneur app
	@echo "$(CYAN)🐚 Shell interactif (app)...$(NC)"
	docker-compose exec app /bin/bash

shell-db: ## Accéder au shell PostgreSQL
	@echo "$(CYAN)🐚 Shell PostgreSQL (psql)...$(NC)"
	docker-compose exec postgres psql -U dispatch_user -d dispatch

db-backup: ## Sauvegarder la base de données
	@echo "$(GREEN)💾 Sauvegarde de la base de données...$(NC)"
	@mkdir -p backups
	docker exec dispatch_postgres pg_dump -U dispatch_user dispatch > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup créé dans backups/$(NC)"

db-restore: ## Restaurer la base (Usage: make db-restore FILE=backup.sql)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)❌ Erreur : Spécifiez FILE=backup.sql$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)⚠️  Restauration de $(FILE)...$(NC)"
	docker exec -i dispatch_postgres psql -U dispatch_user dispatch < $(FILE)
	@echo "$(GREEN)✅ Restauration terminée$(NC)"

clean: ## Nettoyer les conteneurs, images et volumes non utilisés
	@echo "$(YELLOW)🧹 Nettoyage Docker...$(NC)"
	docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

rebuild: down build up ## Reconstruire et redémarrer (down + build + up)

test: ## Tester que l'application répond
	@echo "$(CYAN)🧪 Test de l'application...$(NC)"
	@curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q 200 && \
		echo "$(GREEN)✅ Application opérationnelle (HTTP 200)$(NC)" || \
		echo "$(RED)❌ Application ne répond pas$(NC)"

dev: ## Mode développement (montage du code source)
	@echo "$(CYAN)🔧 Mode développement activé$(NC)"
	@echo "$(YELLOW)⚠️  Décommentez la ligne '- .:/app' dans docker-compose.yml$(NC)"

prod: up ## Démarrer en mode production
	@echo "$(GREEN)🚀 Mode production$(NC)"

init: ## Initialisation complète (première installation)
	@echo "$(CYAN)🎯 Initialisation de Dispatch Manager...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)📝 Création du fichier .env...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)⚠️  N'oubliez pas de modifier .env avec vos valeurs !$(NC)"; \
	fi
	@echo "$(GREEN)🔨 Construction des images...$(NC)"
	docker-compose build
	@echo "$(GREEN)🚀 Démarrage des services...$(NC)"
	docker-compose up -d
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║  ✅ Installation terminée !            ║$(NC)"
	@echo "$(GREEN)╠════════════════════════════════════════╣$(NC)"
	@echo "$(GREEN)║  🌐 Application : http://localhost     ║$(NC)"
	@echo "$(GREEN)║  📋 Voir les logs : make logs          ║$(NC)"
	@echo "$(GREEN)║  ⏸️  Arrêter : make down               ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════╝$(NC)"

status: ## Afficher un résumé complet de l'état
	@echo "$(CYAN)╔════════════════════════════════════════╗$(NC)"
	@echo "$(CYAN)║     État de Dispatch Manager           ║$(NC)"
	@echo "$(CYAN)╚════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)Conteneurs :$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(GREEN)Volumes :$(NC)"
	@docker volume ls | grep dispatch
	@echo ""
	@echo "$(GREEN)Réseau :$(NC)"
	@docker network ls | grep dispatch
