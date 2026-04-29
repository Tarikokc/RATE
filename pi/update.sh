#!/bin/bash
# =============================================================
# update.sh — Mise a jour de RATE sur Raspberry Pi
# Usage : bash pi/update.sh
# A lancer apres chaque git pull ou push sur la branche
# =============================================================

set -e

PROJECT_DIR="/home/pi/RATE"
BRANCH="main"
SERVICE="rate"

echo ""
echo "============================================="
echo "  RATE — Mise a jour"
echo "============================================="
echo ""

# 1. Pull du repo
echo "[1/4] Pull origin $BRANCH..."
cd "$PROJECT_DIR"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"

# 2. Mise a jour des dependances
echo "[2/4] Mise a jour des dependances Python..."
source "$PROJECT_DIR/venv/bin/activate"
pip install -r requirements.txt --quiet

# 3. Redemarrage du service
echo "[3/4] Redemarrage du service..."
sudo systemctl restart "$SERVICE"
sleep 2

# 4. Verification
echo "[4/4] Verification..."
if systemctl is-active --quiet "$SERVICE"; then
  PI_IP=$(hostname -I | awk '{print $1}')
  echo ""
  echo "  Service actif."
  echo "  App : http://$PI_IP"
  echo "  API : http://$PI_IP/api/rooms"
else
  echo ""
  echo "  ERREUR : le service n'a pas redemarre."
  echo "  Logs : sudo journalctl -u $SERVICE -n 30"
  exit 1
fi

echo ""
echo "  Mise a jour terminee."
echo ""
