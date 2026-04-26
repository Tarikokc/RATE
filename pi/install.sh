#!/bin/bash
# =============================================================
# install.sh — Installation initiale de RATE sur Raspberry Pi
# Usage : bash pi/install.sh
# A lancer UNE SEULE FOIS sur la Pi depuis /home/pi/RATE
# =============================================================

set -e

PROJECT_DIR="/home/pi/RATE"
SERVICE="rate"

echo ""
echo "============================================="
echo "  RATE — Installation Raspberry Pi"
echo "============================================="
echo ""

# --- 1. Mise a jour systeme ---
echo "[1/9] Mise a jour du systeme..."
sudo apt update -y && sudo apt upgrade -y

# --- 2. Installer Nginx ---
echo "[2/9] Installation de Nginx..."
sudo apt install -y nginx

# --- 3. Creer le virtualenv ---
echo "[3/9] Creation du virtualenv Python..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate

# --- 4. Installer les dependances Python ---
echo "[4/9] Installation des dependances Python..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# --- 5. Creer les dossiers necessaires ---
echo "[5/9] Creation des dossiers..."
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"

# --- 6. Configurer le .env ---
echo "[6/9] Configuration du .env..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  PI_IP=$(hostname -I | awk '{print $1}')
  sed -i "s|API_URL=.*|API_URL=http://$PI_IP:80|" "$PROJECT_DIR/.env"
  sed -i "s|DB_PATH=.*|DB_PATH=/home/pi/RATE/data/rate.db|" "$PROJECT_DIR/.env"
  sed -i "s|FLASK_ENV=.*|FLASK_ENV=prod|" "$PROJECT_DIR/.env"
  echo "  .env cree automatiquement avec IP=$PI_IP"
  echo "  Verifie /home/pi/RATE/.env si besoin."
else
  echo "  .env deja present, on le conserve."
fi

# --- 7. Installer le service systemd ---
echo "[7/9] Installation du service systemd..."
sudo cp "$PROJECT_DIR/pi/rate.service" /etc/systemd/system/rate.service
sudo systemctl daemon-reload
sudo systemctl enable rate
sudo systemctl start rate
sleep 2

if systemctl is-active --quiet rate; then
  echo "  Service rate : actif"
else
  echo "  ERREUR : le service rate n'a pas demarre."
  echo "  Logs : sudo journalctl -u rate -n 30"
  exit 1
fi

# --- 8. Configurer Nginx ---
echo "[8/9] Configuration de Nginx..."
sudo cp "$PROJECT_DIR/pi/rate.nginx" /etc/nginx/sites-available/rate
sudo ln -sf /etc/nginx/sites-available/rate /etc/nginx/sites-enabled/rate
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# --- 9. Verification finale ---
echo "[9/9] Verification finale..."
sleep 2
PI_IP=$(hostname -I | awk '{print $1}')

if curl -s "http://localhost/api/rooms" > /dev/null; then
  echo ""
  echo "  API repond correctement."
else
  echo ""
  echo "  ATTENTION : l'API ne repond pas encore."
  echo "  Verifie les logs : tail -f /home/pi/RATE/logs/error.log"
fi

echo ""
echo "============================================="
echo "  Installation terminee !"
echo "  App disponible sur : http://$PI_IP"
echo "  API disponible sur : http://$PI_IP/api/rooms"
echo "============================================="
echo ""
