#!/bin/bash
# Lance le worker localement pour tester une analyse
# Usage: ./scripts/run_worker.sh [fichier_tc.txt] [source_name]
#
# Exemple:
#   ./scripts/run_worker.sh raw_data/spotify_tc.txt spotify

set -e

FILE="${1:-raw_data/spotify_tc.txt}"
SOURCE="${2:-spotify}"
TASK_ID="${SOURCE}-$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$FILE" ]; then
  echo "Erreur: fichier '$FILE' introuvable"
  exit 1
fi

echo "Démarrage du worker..."
echo "  Fichier  : $FILE"
echo "  Source   : $SOURCE"
echo "  Task ID  : $TASK_ID"
echo ""

MONGO_HOSTNAME=localhost MONGO_PORT=27017 python worker.py \
  --task-id "$TASK_ID" \
  --source-name "$SOURCE" \
  --use-stdin < "$FILE"
