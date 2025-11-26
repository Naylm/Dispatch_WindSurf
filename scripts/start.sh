#!/bin/bash
# ============================================
# Script de démarrage rapide - Linux/Mac
# Dispatch Manager Docker
# ============================================

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Dispatch Manager - Démarrage${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Vérifier si Docker est installé
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERREUR]${NC} Docker n'est pas installé"
    echo "Installez Docker depuis https://www.docker.com/get-started"
    exit 1
fi

# Vérifier si docker-compose est installé
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}[ERREUR]${NC} Docker Compose n'est pas installé"
    echo "Installez Docker Compose depuis https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Docker est installé"
echo ""

# Vérifier si .env existe, sinon le créer
if [ ! -f .env ]; then
    echo -e "${YELLOW}[INFO]${NC} Création du fichier .env..."
    cp .env.example .env
    echo -e "${YELLOW}[ATTENTION]${NC} N'oubliez pas de modifier .env avec vos valeurs !"
    echo ""
fi

echo -e "${CYAN}[INFO]${NC} Démarrage des conteneurs Docker..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[ERREUR]${NC} Échec du démarrage"
    echo "Vérifiez les logs avec : docker-compose logs"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ Installation terminée !${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  🌐 Application disponible sur : ${CYAN}http://localhost${NC}"
echo ""
echo -e "  ${YELLOW}Commandes utiles :${NC}"
echo -e "    - Voir les logs     : ${CYAN}docker-compose logs -f${NC}"
echo -e "    - Arrêter           : ${CYAN}docker-compose down${NC}"
echo -e "    - Redémarrer        : ${CYAN}docker-compose restart${NC}"
echo -e "    - Aide complète     : ${CYAN}make help${NC}"
echo ""
echo -e "${GREEN}========================================${NC}"
echo ""
