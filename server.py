# from flask import Flask, request

# app = Flask(__name__)

# @app.route("/measure", methods=["POST"])
# def measure():
#     data = request.get_data(as_text=True)
#     print("relu :", data)
#     return "OK", 200

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)
# from flask import Flask, request, jsonify
# from flask import render_template_string
# from datetime import datetime
# import json
# import os

# app = Flask(__name__)

# DATA_FILE = "measures.ndjson"  # 1 JSON par ligne


# def append_measure(measure: dict):
#     """Ajoute une mesure au fichier NDJSON."""
#     with open(DATA_FILE, "a", encoding="utf-8") as f:
#         f.write(json.dumps(measure) + "\n")


# def read_measures():
#     """Lit toutes les mesures depuis le fichier."""
#     if not os.path.exists(DATA_FILE):
#         return []
#     measures = []
#     with open(DATA_FILE, "r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
#             try:
#                 measures.append(json.loads(line))
#             except json.JSONDecodeError:
#                 continue
#     return measures


# @app.route("/measure", methods=["POST"])
# def measure():
#     # Parse le JSON envoyé par l'ESP
#     data = request.get_json(force=True)  # lit directement le JSON [web:630][web:635]

#     # Ajoute un timestamp serveur
#     data["timestamp"] = datetime.utcnow().isoformat() + "Z"

#     print("Reçu :", data)

#     append_measure(data)

#     return "OK", 200


# @app.route("/api/last", methods=["GET"])
# def api_last():
#     """Retourne la dernière mesure en JSON."""
#     measures = read_measures()
#     if not measures:
#         return jsonify({"error": "no data"}), 404
#     return jsonify(measures[-1])  # Flask sérialise dict -> JSON tout seul [web:623][web:632]


# @app.route("/api/all", methods=["GET"])
# def api_all():
#     """Retourne toutes les mesures (pour debug)."""
#     measures = read_measures()
#     return jsonify(measures)


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000)
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import json
import os

app = Flask(__name__)

DATA_FILE = "measures.ndjson"  # 1 JSON par ligne

# ---------- Fonctions utilitaires ----------

def append_measure(measure: dict):
    """Ajoute une mesure au fichier NDJSON."""
    with open(DATA_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(measure) + "\n")


def read_measures():
    """Lit toutes les mesures depuis le fichier."""
    if not os.path.exists(DATA_FILE):
        return []
    measures = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                measures.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return measures

# ---------- Routes API ----------

@app.route("/measure", methods=["POST"])
def measure():
    # Parse le JSON envoyé par l'ESP8266
    data = request.get_json(force=True)  # lit directement le JSON [web:630][web:635]

    # Ajoute un timestamp serveur
    data["timestamp"] = datetime.utcnow().isoformat() + "Z"

    print("Reçu :", data)

    append_measure(data)

    return "OK", 200


@app.route("/api/last", methods=["GET"])
def api_last():
    """Retourne la dernière mesure en JSON."""
    measures = read_measures()
    if not measures:
        return jsonify({"error": "no data"}), 404
    return jsonify(measures[-1])  # dict -> JSON [web:623][web:632]


@app.route("/api/all", methods=["GET"])
def api_all():
    """Retourne toutes les mesures (pour debug)."""
    measures = read_measures()
    return jsonify(measures)

# ---------- Interface HTML simple ----------

HTML_PAGE = """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Capteur ESP8266</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; background: #111; color: #eee; }
    .card { border: 1px solid #444; border-radius: 8px; padding: 1.5rem; max-width: 420px; }
    h1 { margin-top: 0; }
    .value { font-size: 1.2rem; margin: 0.3rem 0; }
    .label { color: #aaa; }
    .status { font-size: 0.9rem; color: #888; margin-top: 1rem; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Dernière mesure (live)</h1>
    <p class="value"><span class="label">Température :</span> <span id="temp">--</span> °C</p>
    <p class="value"><span class="label">Humidité :</span> <span id="hum">--</span> %</p>
    <p class="value"><span class="label">Pression :</span> <span id="pres">--</span> hPa</p>
    <p class="value"><span class="label">Mouvement :</span> <span id="motion">--</span></p>
    <p class="value"><span class="label">Horodatage :</span> <span id="ts">--</span></p>
    <div class="status" id="status">Chargement...</div>
  </div>

  <script>
    async function refreshData() {
      const statusEl = document.getElementById('status');
      try {
        const resp = await fetch('/api/last', { cache: 'no-store' });
        if (!resp.ok) {
          statusEl.textContent = 'Erreur API: ' + resp.status;
          return;
        }
        const data = await resp.json();

        document.getElementById('temp').textContent   = data.temp?.toFixed ? data.temp.toFixed(2) : data.temp;
        document.getElementById('hum').textContent    = data.hum?.toFixed ? data.hum.toFixed(2) : data.hum;
        document.getElementById('pres').textContent   = data.pres?.toFixed ? data.pres.toFixed(2) : data.pres;
        document.getElementById('motion').textContent = data.motion ? 'Détecté' : 'Aucun';
        document.getElementById('ts').textContent     = data.timestamp || '--';

        const now = new Date();
        statusEl.textContent = 'Dernière mise à jour: ' + now.toLocaleTimeString();
      } catch (e) {
        statusEl.textContent = 'Erreur de connexion au serveur';
      }
    }

    // Premier appel + rafraîchissement toutes les 5 s
    refreshData();
    setInterval(refreshData, 5000);
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    measures = read_measures()
    if not measures:
        m = None
    else:
        m = measures[-1]
    return render_template_string(HTML_PAGE, measure=m)

# ---------- Entrée principale ----------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
