#!/bin/bash
# =============================================================
# deploy.sh — Script de déploiement RATE sur Raspberry Pi
# Usage : bash deploy.sh
# =============================================================

set -e

PROJECT_DIR="/home/pi/RATE"
BRANCH="clean-repo"
SERVICE="rate"

echo "======================================"
echo " RATE — Déploiement Raspberry Pi"
echo "======================================"

# 1. Mise à jour du code
echo "[1/6] Pull du repo..."
cd "$PROJECT_DIR"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

# 2. Mise à jour des dépendances Python
echo "[2/6] Installation des dépendances Python..."
source "$PROJECT_DIR/venv/bin/activate"
pip install -r requirements.txt --quiet

# 3. Création des dossiers si absents
echo "[3/6] Vérification des dossiers..."
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"

# 4. Vérifier la présence du .env
echo "[4/6] Vérification du .env..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
  echo "  ⚠️  .env introuvable. Copie de .env.example..."
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  echo "  ❗  Pense à configurer /home/pi/RATE/.env avant de relancer."
  exit 1
fi

# 5. Redémarrage du service
echo "[5/6] Redémarrage du service $SERVICE..."
sudo systemctl daemon-reload
sudo systemctl restart "$SERVICE"
sleep 2

# 6. Vérification du statut
echo "[6/6] Vérification..."
if systemctl is-active --quiet "$SERVICE"; then
  echo ""
  echo "  ✅  $SERVICE est actif et tourne correctement."
  echo "  API disponible sur : http://$(hostname -I | awk '{print $1}')/api/rooms"
else
  echo ""
  echo "  ❌  $SERVICE a échoué au démarrage."
  echo "  Consulte les logs : sudo journalctl -u $SERVICE -n 30"
  exit 1
fi

echo ""
echo "======================================"
echo " Déploiement terminé avec succès ✅"
echo "======================================"
