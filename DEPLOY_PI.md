# Déploiement RATE sur Raspberry Pi

Guide complet pour déployer RATE (Flask + Angular) avec Gunicorn + Nginx.

---

## Prérequis

- Raspberry Pi OS (Bullseye ou Bookworm)
- Python 3.9+, Git installés
- Accès SSH ou terminal direct

---

## 1. Cloner le repo

```bash
git clone https://github.com/Tarikokc/RATE.git /home/pi/RATE
cd /home/pi/RATE
git checkout clean-repo
```

---

## 2. Virtualenv + dépendances

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Si `tflite-runtime` échoue sur ARM :
> ```bash
> pip install tflite-runtime --extra-index-url https://google-coral.github.io/py-repo/
> ```

---

## 3. Dossiers nécessaires

```bash
mkdir -p /home/pi/RATE/data
mkdir -p /home/pi/RATE/logs
```

---

## 4. Configurer le .env

```bash
cp .env.example .env
nano .env
```

```env
FLASK_ENV=prod
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

API_URL=http://TON_IP_PI:80

DB_PATH=/home/pi/RATE/data/rate.db

TARGET_TEMP=20.0
HEAT_ADVANCE_MIN=60
DEG_PER_HOUR=2.5
TEMP_TOLERANCE=0.5

WEATHER_LATITUDE=48.8566
WEATHER_LONGITUDE=2.3522
```

> Trouver l'IP de la Pi : `hostname -I`

---

## 5. Tester Gunicorn manuellement

```bash
cd /home/pi/RATE
source venv/bin/activate
gunicorn --bind 0.0.0.0:5000 --workers 2 server:app
```

```bash
curl http://localhost:5000/api/rooms
```

Si tu as un JSON → OK. `Ctrl+C` puis passer à la suite.

---

## 6. Service systemd

```bash
sudo nano /etc/systemd/system/rate.service
```

```ini
[Unit]
Description=RATE Flask API
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/RATE
EnvironmentFile=/home/pi/RATE/.env
ExecStart=/home/pi/RATE/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 2 \
    --timeout 60 \
    --access-logfile /home/pi/RATE/logs/access.log \
    --error-logfile /home/pi/RATE/logs/error.log \
    server:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable rate
sudo systemctl start rate
sudo systemctl status rate   # → active (running)
```

---

## 7. Nginx en reverse proxy

```bash
sudo apt update && sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/rate
```

```nginx
server {
    listen 80;
    server_name _;

    location /api/ {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60;
    }

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/rate /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t                    # → syntax is ok
sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

## 8. Build Angular

### Option A — Sur ton PC, puis SCP

```bash
# Sur ton PC
cd clientApp
ng build --configuration production

scp -r dist/ pi@TON_IP_PI:/home/pi/RATE/clientApp/
```

### Option B — Directement sur la Pi

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

cd /home/pi/RATE/clientApp
npm install
npx ng build --configuration production
```

> Le `dist/` doit être dans `clientApp/dist/client-app/browser/`

---

## 9. Vérification finale

```bash
sudo systemctl status rate
sudo systemctl status nginx

curl http://localhost/api/rooms
curl http://localhost/api/heating/decision

tail -f /home/pi/RATE/logs/error.log
sudo journalctl -u rate -f
```

Ouvrir `http://TON_IP_PI` dans un navigateur → l'app Angular doit s'afficher.

---

## Commandes utiles au quotidien

```bash
# Redémarrer après un git pull
cd /home/pi/RATE && git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart rate

# Logs live
sudo journalctl -u rate -n 50 -f

# Statut rapide
sudo systemctl status rate nginx
```

---

## Architecture finale

```
Réseau local
     ↓
 Nginx :80
 ↙        ↘
/api/*      /*
  ↓           ↓
Gunicorn:5000 (Flask)
  ↓               ↓
API Routes     Angular dist/
  ↓
SQLite (/home/pi/RATE/data/rate.db)
```

Gunicorn écoute **uniquement sur `127.0.0.1:5000`** (non exposé directement).
Nginx fait le pont depuis le port 80 et gère les headers.
