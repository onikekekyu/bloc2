#!/bin/bash
# Accès à Grafana via port-forward

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}Accès à Grafana${NC}"
echo ""
echo -e "${BLUE}Identifiants :${NC}"
echo "  Username : admin"
echo "  Password : prom-operator"
echo ""
echo -e "${GREEN}Démarrage du port-forward...${NC}"
echo -e "${BLUE}URL : http://localhost:3000${NC}"
echo ""
echo "Ctrl+C pour arrêter"
echo ""

kubectl --namespace monitoring port-forward svc/monitoring-grafana 3000:80
