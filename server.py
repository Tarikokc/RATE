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
    data = request.get_json(force=True)

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
    return jsonify(measures[-1])


@app.route("/api/all", methods=["GET"])
def api_all():
    """Retourne toutes les mesures (pour debug)."""
    measures = read_measures()
    return jsonify(measures)


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Retourne stats min/max/moyenne des dernières mesures."""
    measures = read_measures()
    if not measures:
        return jsonify({"error": "no data"}), 404
    
    # Dernières 100 mesures
    recent = measures[-100:] if len(measures) > 100 else measures
    
    temps = [m.get("temp", 0) for m in recent if "temp" in m]
    hums = [m.get("hum", 0) for m in recent if "hum" in m]
    press = [m.get("pres", 0) for m in recent if "pres" in m]
    motions = [m.get("motion", 0) for m in recent if "motion" in m]
    
    return jsonify({
        "temp": {
            "min": min(temps) if temps else None,
            "max": max(temps) if temps else None,
            "avg": sum(temps) / len(temps) if temps else None
        },
        "humidity": {
            "min": min(hums) if hums else None,
            "max": max(hums) if hums else None,
            "avg": sum(hums) / len(hums) if hums else None
        },
        "pressure": {
            "min": min(press) if press else None,
            "max": max(press) if press else None,
            "avg": sum(press) / len(press) if press else None
        },
        "motion_count": sum(motions),
        "total_records": len(measures)
    })


# ========== DASHBOARD PUBLIC (Visualization) ==========
DASHBOARD_PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RATE Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #0f766e;
            --primary-light: #14b8a6;
            --primary-dark: #0d9488;
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f1f5f9;
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --text-tertiary: #94a3b8;
            --border: #e2e8f0;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --primary: #14b8a6;
                --primary-light: #2dd4bf;
                --primary-dark: #0d9488;
                --bg-primary: #0f172a;
                --bg-secondary: #1e293b;
                --bg-tertiary: #334155;
                --text-primary: #f1f5f9;
                --text-secondary: #cbd5e1;
                --text-tertiary: #94a3b8;
                --border: #334155;
                --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
                --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
                --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
                --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
            }
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            overflow-x: hidden;
            transition: background 0.3s ease, color 0.3s ease;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 3rem;
            animation: slideDown 0.6s ease-out;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .header-info {
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        .header-link {
            padding: 0.5rem 1rem;
            background: var(--primary);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }

        .header-link:hover {
            background: var(--primary-light);
            transform: translateY(-2px);
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 12px rgba(34, 197, 95, 0.6);
            animation: pulse 2s ease-in-out infinite;
        }

        .timestamp {
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
            animation: fadeIn 0.8s ease-out 0.2s both;
        }

        .card {
            background: var(--bg-secondary);
            border-radius: 24px;
            padding: 2rem;
            border: 1px solid var(--border);
            box-shadow: var(--shadow-md);
            transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1);
            cursor: default;
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, rgba(20, 184, 166, 0.1) 0%, transparent 70%);
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .card:hover {
            transform: translateY(-8px);
            box-shadow: var(--shadow-xl);
            border-color: var(--primary-light);
        }

        .card:hover::before {
            opacity: 1;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1.5rem;
        }

        .card-title {
            font-size: 0.95rem;
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .card-icon {
            font-size: 1.5rem;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
        }

        .card-value {
            font-size: 3rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }

        .card-unit {
            font-size: 0.9rem;
            color: var(--text-tertiary);
            font-weight: 500;
        }

        .card-subtitle {
            font-size: 0.8rem;
            color: var(--text-tertiary);
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }

        .card.temp { --accent: #f97316; }
        .card.humidity { --accent: #3b82f6; }
        .card.pressure { --accent: #8b5cf6; }
        .card.motion { --accent: #ec4899; }

        .card-accent {
            display: inline-block;
            width: 4px;
            height: 2rem;
            background: linear-gradient(180deg, var(--accent), transparent);
            border-radius: 2px;
            margin-right: 1rem;
            opacity: 0.7;
        }

        .card.motion .card-value { color: var(--accent); }

        .motion-status {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: linear-gradient(135deg, rgba(236, 72, 153, 0.1), rgba(236, 72, 153, 0.05));
            border-radius: 12px;
            border: 1px solid rgba(236, 72, 153, 0.2);
            font-weight: 600;
            color: #ec4899;
            margin-top: 1rem;
        }

        .motion-status.active {
            background: linear-gradient(135deg, rgba(236, 72, 153, 0.2), rgba(236, 72, 153, 0.1));
            border-color: rgba(236, 72, 153, 0.4);
            box-shadow: 0 0 16px rgba(236, 72, 153, 0.3);
        }

        .motion-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #ec4899;
            animation: pulse-motion 1.5s ease-in-out infinite;
        }

        .motion-status.inactive { opacity: 0.6; }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 0.5rem;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }

        .stat-item { text-align: center; }
        .stat-label {
            font-size: 0.65rem;
            color: var(--text-tertiary);
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.03em;
        }
        .stat-value {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-top: 0.25rem;
        }

        .chart-card { grid-column: 1 / -1; animation: fadeIn 0.8s ease-out 0.4s both; }

        .chart-container {
            background: linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary));
            border-radius: 16px;
            padding: 2rem;
            height: 400px;
            display: flex;
            flex-direction: column;
            border: 1px dashed var(--border);
            position: relative;
            overflow: hidden;
        }

        .chart-placeholder {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-tertiary);
            font-size: 0.95rem;
            position: relative;
        }

        .chart-placeholder::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
            animation: shimmer 2s infinite;
        }

        .sparkline {
            display: flex;
            align-items: flex-end;
            gap: 2px;
            height: 60px;
            margin: 1rem 0;
        }

        .sparkline-bar {
            flex: 1;
            background: var(--accent);
            border-radius: 4px 4px 0 0;
            min-height: 2px;
            opacity: 0.7;
            transition: all 0.3s ease;
        }

        .sparkline-bar:hover { opacity: 1; }

        .footer {
            text-align: center;
            padding: 2rem;
            color: var(--text-tertiary);
            font-size: 0.85rem;
            animation: fadeIn 0.8s ease-out 0.6s both;
        }

        .footer-link {
            color: var(--primary-light);
            text-decoration: none;
            transition: color 0.2s;
        }

        .footer-link:hover {
            color: var(--primary);
            text-decoration: underline;
        }

        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        @keyframes pulse-motion {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.2); opacity: 0.8; }
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .header h1 { font-size: 1.8rem; }
            .card-value { font-size: 2rem; }
            .dashboard-grid { grid-template-columns: 1fr; gap: 1rem; }
            .chart-card { grid-column: 1; }
            .header { flex-direction: column; gap: 1rem; align-items: flex-start; }
            .header-info { width: 100%; justify-content: space-between; }
            .stats-row { grid-template-columns: 1fr 1fr 1fr; }
        }

        @media (prefers-color-scheme: dark) {
            .card { background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02)); backdrop-filter: blur(10px); }
            .card-accent { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RATE Dashboard</h1>
            <div class="header-info">
                <div class="status-indicator"></div>
                <div class="timestamp" id="current-time">--:--:--</div>
                <a href="/control" class="header-link">🎛️ Control Panel</a>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="card temp">
                <div class="card-header">
                    <div class="card-title">Température</div>
                    <div class="card-icon">🌡️</div>
                </div>
                <div>
                    <div class="card-accent"></div>
                    <div class="card-value" id="temp">--</div>
                    <div class="card-unit">°C</div>
                </div>
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-label">Min</div>
                        <div class="stat-value" id="temp-min">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Moy</div>
                        <div class="stat-value" id="temp-avg">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Max</div>
                        <div class="stat-value" id="temp-max">--</div>
                    </div>
                </div>
                <div class="card-subtitle" id="temp-time">-- -- --</div>
            </div>

            <div class="card humidity">
                <div class="card-header">
                    <div class="card-title">Humidité</div>
                    <div class="card-icon">💧</div>
                </div>
                <div>
                    <div class="card-accent"></div>
                    <div class="card-value" id="hum">--</div>
                    <div class="card-unit">%</div>
                </div>
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-label">Min</div>
                        <div class="stat-value" id="hum-min">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Moy</div>
                        <div class="stat-value" id="hum-avg">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Max</div>
                        <div class="stat-value" id="hum-max">--</div>
                    </div>
                </div>
                <div class="card-subtitle" id="hum-time">-- -- --</div>
            </div>

            <div class="card pressure">
                <div class="card-header">
                    <div class="card-title">Pression</div>
                    <div class="card-icon">🧭</div>
                </div>
                <div>
                    <div class="card-accent"></div>
                    <div class="card-value" id="pres">--</div>
                    <div class="card-unit">hPa</div>
                </div>
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-label">Min</div>
                        <div class="stat-value" id="pres-min">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Moy</div>
                        <div class="stat-value" id="pres-avg">--</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Max</div>
                        <div class="stat-value" id="pres-max">--</div>
                    </div>
                </div>
                <div class="card-subtitle" id="pres-time">-- -- --</div>
            </div>

            <div class="card motion">
                <div class="card-header">
                    <div class="card-title">Mouvement</div>
                    <div class="card-icon">👁️</div>
                </div>
                <div>
                    <div class="card-value" id="motion-text">Aucun</div>
                    <div class="motion-status" id="motion-status">
                        <div class="motion-dot"></div>
                        Inactif
                    </div>
                </div>
                <div class="card-subtitle" id="motion-time">-- -- --</div>
            </div>

            <div class="card chart-card">
                <div class="card-header">
                    <div class="card-title">Historique & Analytics</div>
                    <div class="card-icon">📊</div>
                </div>
                <div class="chart-container">
                    <div class="chart-placeholder">
                        <div>
                            <p style="margin-bottom: 1rem;"><strong>Tendances des 50 dernières mesures</strong></p>
                            <p style="font-size: 0.85rem; color: var(--text-tertiary);">Température 🌡️</p>
                            <div class="sparkline" id="sparkline-temp"></div>
                            <p style="font-size: 0.85rem; color: var(--text-tertiary);">Humidité 💧</p>
                            <div class="sparkline" id="sparkline-hum"></div>
                            <p style="font-size: 0.85rem; color: var(--text-tertiary);">Pression 🧭</p>
                            <div class="sparkline" id="sparkline-pres"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>RATE IoT Monitoring System • Dernière sync: <span id="last-sync">--:--:--</span> • <a href="/api/all" class="footer-link">API JSON</a></p>
        </div>
    </div>

    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('current-time').textContent = now.toLocaleTimeString('fr-FR');
            document.getElementById('last-sync').textContent = now.toLocaleTimeString('fr-FR');
        }

        async function refreshData() {
            try {
                const respLast = await fetch('/api/last', { cache: 'no-store' });
                if (!respLast.ok) return;
                const data = await respLast.json();

                const tsDate = new Date(data.timestamp);
                const timeStr = tsDate.toLocaleTimeString('fr-FR');

                document.getElementById('temp').textContent = data.temp ? parseFloat(data.temp).toFixed(2) : '--';
                document.getElementById('temp-time').textContent = timeStr;

                document.getElementById('hum').textContent = data.hum ? parseFloat(data.hum).toFixed(2) : '--';
                document.getElementById('hum-time').textContent = timeStr;

                document.getElementById('pres').textContent = data.pres ? parseFloat(data.pres).toFixed(2) : '--';
                document.getElementById('pres-time').textContent = timeStr;

                const motionText = data.motion === 1 ? 'Détecté' : 'Aucun';
                document.getElementById('motion-text').textContent = motionText;
                const motionStatus = document.getElementById('motion-status');
                if (data.motion === 1) {
                    motionStatus.classList.add('active');
                    motionStatus.classList.remove('inactive');
                    motionStatus.innerHTML = '<div class="motion-dot"></div>Détecté';
                } else {
                    motionStatus.classList.remove('active');
                    motionStatus.classList.add('inactive');
                    motionStatus.innerHTML = '<div class="motion-dot"></div>Inactif';
                }
                document.getElementById('motion-time').textContent = timeStr;

                const respStats = await fetch('/api/stats', { cache: 'no-store' });
                if (respStats.ok) {
                    const stats = await respStats.json();

                    if (stats.temp.min) document.getElementById('temp-min').textContent = stats.temp.min.toFixed(2);
                    if (stats.temp.avg) document.getElementById('temp-avg').textContent = stats.temp.avg.toFixed(2);
                    if (stats.temp.max) document.getElementById('temp-max').textContent = stats.temp.max.toFixed(2);

                    if (stats.humidity.min) document.getElementById('hum-min').textContent = stats.humidity.min.toFixed(2);
                    if (stats.humidity.avg) document.getElementById('hum-avg').textContent = stats.humidity.avg.toFixed(2);
                    if (stats.humidity.max) document.getElementById('hum-max').textContent = stats.humidity.max.toFixed(2);

                    if (stats.pressure.min) document.getElementById('pres-min').textContent = stats.pressure.min.toFixed(2);
                    if (stats.pressure.avg) document.getElementById('pres-avg').textContent = stats.pressure.avg.toFixed(2);
                    if (stats.pressure.max) document.getElementById('pres-max').textContent = stats.pressure.max.toFixed(2);

                    drawSparklines(stats);
                }

            } catch (error) {
                console.error('Erreur:', error);
            }
        }

        function drawSparklines(stats) {
            fetch('/api/all', { cache: 'no-store' })
                .then(r => r.json())
                .then(measures => {
                    if (measures.length === 0) return;

                    const recent = measures.slice(-50);

                    const temps = recent.map(m => parseFloat(m.temp) || 0);
                    const tempMin = Math.min(...temps);
                    const tempMax = Math.max(...temps);
                    const tempRange = tempMax - tempMin || 1;
                    const tempSparkline = document.getElementById('sparkline-temp');
                    tempSparkline.innerHTML = temps.map(t => {
                        const height = ((t - tempMin) / tempRange) * 100;
                        return `<div class="sparkline-bar" style="height: ${Math.max(height, 10)}%;"></div>`;
                    }).join('');

                    const hums = recent.map(m => parseFloat(m.hum) || 0);
                    const humMin = Math.min(...hums);
                    const humMax = Math.max(...hums);
                    const humRange = humMax - humMin || 1;
                    const humSparkline = document.getElementById('sparkline-hum');
                    humSparkline.innerHTML = hums.map(h => {
                        const height = ((h - humMin) / humRange) * 100;
                        return `<div class="sparkline-bar" style="height: ${Math.max(height, 10)}%; --accent: #3b82f6;"></div>`;
                    }).join('');

                    const press = recent.map(m => parseFloat(m.pres) || 0);
                    const presMin = Math.min(...press);
                    const presMax = Math.max(...press);
                    const presRange = presMax - presMin || 1;
                    const presSparkline = document.getElementById('sparkline-pres');
                    presSparkline.innerHTML = press.map(p => {
                        const height = ((p - presMin) / presRange) * 100;
                        return `<div class="sparkline-bar" style="height: ${Math.max(height, 10)}%; --accent: #8b5cf6;"></div>`;
                    }).join('');
                })
                .catch(e => console.error('Sparkline error:', e));
        }

        updateTime();
        refreshData();
        setInterval(updateTime, 1000);
        setInterval(refreshData, 5000);
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(DASHBOARD_PAGE)


# ========== CONTROL PANEL (User Actions) ==========
CONTROL_PAGE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RATE Control Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #0f766e;
            --primary-light: #14b8a6;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --bg-tertiary: #f1f5f9;
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --text-tertiary: #94a3b8;
            --border: #e2e8f0;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --primary: #14b8a6;
                --primary-light: #2dd4bf;
                --bg-primary: #0f172a;
                --bg-secondary: #1e293b;
                --bg-tertiary: #334155;
                --text-primary: #f1f5f9;
                --text-secondary: #cbd5e1;
                --text-tertiary: #94a3b8;
                --border: #334155;
            }
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .nav-tabs {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid var(--border);
            animation: slideDown 0.6s ease-out;
        }

        .nav-tab {
            padding: 1rem 1.5rem;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-secondary);
            position: relative;
            transition: color 0.3s;
        }

        .nav-tab.active {
            color: var(--primary);
        }

        .nav-tab.active::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            right: 0;
            height: 2px;
            background: var(--primary);
        }

        .tab-content {
            display: none;
            animation: fadeIn 0.4s ease-out;
        }

        .tab-content.active {
            display: block;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .card {
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.3s;
        }

        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 15px rgba(0, 0, 0, 0.15);
        }

        .card h3 {
            font-size: 1.1rem;
            margin-bottom: 1rem;
            color: var(--text-primary);
        }

        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 60px;
            height: 32px;
        }

        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #ccc;
            transition: 0.3s;
            border-radius: 32px;
        }

        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 26px;
            width: 26px;
            left: 3px;
            bottom: 3px;
            background: white;
            transition: 0.3s;
            border-radius: 50%;
        }

        input:checked + .toggle-slider {
            background: var(--success);
        }

        input:checked + .toggle-slider:before {
            transform: translateX(28px);
        }

        .switch-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .switch-label span {
            font-weight: 500;
        }

        .threshold-control {
            margin: 1.5rem 0;
        }

        .threshold-control label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            font-size: 0.9rem;
        }

        .threshold-input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 1rem;
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .threshold-value {
            display: inline-block;
            background: var(--primary);
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-left: 0.5rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 0.95rem;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-light);
            transform: translateY(-2px);
        }

        .btn-secondary {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .btn-secondary:hover {
            background: var(--border);
        }

        .btn-danger {
            background: var(--danger);
            color: white;
        }

        .btn-danger:hover {
            background: #dc2626;
        }

        .status-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
        }

        .status-active {
            background: rgba(34, 197, 95, 0.2);
            color: #22c55e;
        }

        .status-inactive {
            background: rgba(148, 163, 184, 0.2);
            color: var(--text-tertiary);
        }

        .event-log {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 1rem;
            max-height: 300px;
            overflow-y: auto;
        }

        .event-item {
            padding: 0.75rem;
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
            display: flex;
            gap: 0.75rem;
        }

        .event-item:last-child {
            border-bottom: none;
        }

        .event-time {
            color: var(--text-tertiary);
            min-width: 80px;
            font-weight: 600;
        }

        .event-message {
            color: var(--text-secondary);
        }

        .alert-config {
            background: linear-gradient(135deg, rgba(34, 197, 95, 0.05), rgba(34, 197, 95, 0.02));
            border-left: 4px solid var(--success);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }

        .alert-config.warning {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.05), rgba(245, 158, 11, 0.02));
            border-left-color: var(--warning);
        }

        .alert-config.danger {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.05), rgba(239, 68, 68, 0.02));
            border-left-color: var(--danger);
        }

        .mode-selector {
            display: flex;
            gap: 1rem;
            margin: 1rem 0;
        }

        .mode-btn {
            flex: 1;
            padding: 0.75rem;
            border: 2px solid var(--border);
            background: transparent;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
        }

        .mode-btn.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            animation: slideDown 0.6s ease-out;
        }

        .header h1 {
            font-size: 2rem;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .system-status {
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--success);
            box-shadow: 0 0 12px rgba(34, 197, 95, 0.6);
            animation: pulse 2s infinite;
        }

        .export-btn {
            display: flex;
            gap: 0.5rem;
        }

        .export-btn button {
            padding: 0.5rem 1rem;
            font-size: 0.85rem;
        }

        .back-link {
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.3s;
        }

        .back-link:hover {
            color: var(--primary-light);
        }

        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .grid { grid-template-columns: 1fr; }
            .header { flex-direction: column; gap: 1rem; }
            .export-btn { flex-direction: column; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🎛️ Control Panel</h1>
                <a href="/" class="back-link">← Retour au Dashboard</a>
            </div>
            <div class="system-status">
                <div class="status-indicator"></div>
                <span>Système actif</span>
                <div class="export-btn">
                    <button class="btn btn-secondary" onclick="exportCSV()">📥 CSV</button>
                    <button class="btn btn-secondary" onclick="exportJSON()">📥 JSON</button>
                </div>
            </div>
        </div>

        <div class="nav-tabs">
            <button class="nav-tab active" onclick="switchTab('system')">⚙️ Système</button>
            <button class="nav-tab" onclick="switchTab('alerts')">🔔 Alertes</button>
            <button class="nav-tab" onclick="switchTab('automation')">🤖 Automation</button>
            <button class="nav-tab" onclick="switchTab('logs')">📋 Historique</button>
        </div>

        <!-- System Tab -->
        <div id="system" class="tab-content active">
            <div class="grid">
                <div class="card">
                    <h3>Mode Opérationnel</h3>
                    <div class="mode-selector">
                        <button class="mode-btn active" onclick="setMode('auto')">AUTO 🤖</button>
                        <button class="mode-btn" onclick="setMode('manual')">MANUEL ⚙️</button>
                    </div>
                    <p style="font-size: 0.85rem; color: var(--text-tertiary); margin-top: 1rem;">
                        <strong>Auto:</strong> Système contrôlé automatiquement<br>
                        <strong>Manuel:</strong> Contrôle entièrement manuel
                    </p>
                </div>

                <div class="card">
                    <h3>Enregistrement des données</h3>
                    <div class="switch-label">
                        <span>Activer l'enregistrement</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="logging-toggle" checked onchange="toggleLogging()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="switch-label">
                        <span>Archivage automatique</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="archive-toggle" onchange="toggleArchive()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>

                <div class="card">
                    <h3>Notifications Système</h3>
                    <div class="switch-label">
                        <span>Notifications desktop</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="notif-toggle" onchange="toggleNotifications()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="switch-label">
                        <span>Sons d'alerte</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="sound-toggle" onchange="toggleSound()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <div class="card" style="margin-top: 1.5rem;">
                <h3>État du capteur</h3>
                <div style="margin-top: 1rem;">
                    <p><strong>ESP8266-1:</strong> <span class="status-badge status-active">✓ Connecté</span></p>
                    <p style="margin-top: 0.5rem; font-size: 0.9rem; color: var(--text-tertiary);">Dernière mesure: <span id="last-measure-time">--:--:--</span></p>
                </div>
            </div>
        </div>

        <!-- Alerts Tab -->
        <div id="alerts" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h3>🌡️ Alertes Température</h3>
                    <div class="switch-label">
                        <span>Activer</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="temp-alert-toggle" checked onchange="toggleAlert('temp')">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="threshold-control">
                        <label>Min <span class="threshold-value" id="temp-min-val">15°C</span></label>
                        <input type="range" min="0" max="50" value="15" class="threshold-input" id="temp-min-slider" oninput="updateThreshold('temp-min', this.value)">
                    </div>
                    <div class="threshold-control">
                        <label>Max <span class="threshold-value" id="temp-max-val">30°C</span></label>
                        <input type="range" min="0" max="50" value="30" class="threshold-input" id="temp-max-slider" oninput="updateThreshold('temp-max', this.value)">
                    </div>
                    <div class="alert-config warning">
                        <strong>⚠️:</strong> Alerte si temp < 15°C ou > 30°C
                    </div>
                </div>

                <div class="card">
                    <h3>💧 Alertes Humidité</h3>
                    <div class="switch-label">
                        <span>Activer</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="hum-alert-toggle" checked onchange="toggleAlert('hum')">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="threshold-control">
                        <label>Min <span class="threshold-value" id="hum-min-val">30%</span></label>
                        <input type="range" min="0" max="100" value="30" class="threshold-input" id="hum-min-slider" oninput="updateThreshold('hum-min', this.value)">
                    </div>
                    <div class="threshold-control">
                        <label>Max <span class="threshold-value" id="hum-max-val">80%</span></label>
                        <input type="range" min="0" max="100" value="80" class="threshold-input" id="hum-max-slider" oninput="updateThreshold('hum-max', this.value)">
                    </div>
                    <div class="alert-config warning">
                        <strong>⚠️:</strong> Alerte si hum < 30% ou > 80%
                    </div>
                </div>

                <div class="card">
                    <h3>👁️ Alertes Mouvement</h3>
                    <div class="switch-label">
                        <span>Activer</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="motion-alert-toggle" onchange="toggleAlert('motion')">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                    <div class="alert-config danger">
                        <strong>🚨:</strong> Notification si mouvement détecté
                    </div>
                    <button class="btn btn-secondary" onclick="testMotionAlert()" style="width: 100%; margin-top: 1rem;">Tester l'alerte</button>
                </div>
            </div>
        </div>

        <!-- Automation Tab -->
        <div id="automation" class="tab-content">
            <div class="grid">
                <div class="card">
                    <h3>Règle 1: Ventilation Auto</h3>
                    <p style="font-size: 0.9rem; color: var(--text-tertiary); margin-bottom: 1rem;">Si temp > 28°C ET hum > 70% → Ventilo</p>
                    <div class="switch-label">
                        <span>Actif</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="rule1-toggle" checked onchange="toggleRule(1)">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>

                <div class="card">
                    <h3>Règle 2: Alerte Sécurité</h3>
                    <p style="font-size: 0.9rem; color: var(--text-tertiary); margin-bottom: 1rem;">Si mouvement (nuit) → Notification</p>
                    <div class="switch-label">
                        <span>Actif</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="rule2-toggle" onchange="toggleRule(2)">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>

                <div class="card">
                    <h3>Règle 3: Chauffage Économe</h3>
                    <p style="font-size: 0.9rem; color: var(--text-tertiary); margin-bottom: 1rem;">Si temp < 18°C → Chauffage</p>
                    <div class="switch-label">
                        <span>Actif</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="rule3-toggle" onchange="toggleRule(3)">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
            </div>
        </div>

        <!-- Logs Tab -->
        <div id="logs" class="tab-content">
            <div class="card">
                <h3>📋 Historique d'événements</h3>
                <div class="event-log" id="event-log">
                    <div class="event-item">
                        <span class="event-time">14:32:15</span>
                        <span class="event-message">✓ Système initialisé</span>
                    </div>
                    <div class="event-item">
                        <span class="event-time">14:33:42</span>
                        <span class="event-message">📨 ESP8266-1 connecté</span>
                    </div>
                </div>
                <button class="btn btn-secondary" onclick="clearLogs()" style="width: 100%; margin-top: 1rem;">🗑️ Effacer</button>
            </div>

            <div class="grid" style="margin-top: 1.5rem;">
                <div class="card">
                    <h3>Statistiques</h3>
                    <p>Mesures: <strong id="total-measures">0</strong></p>
                    <p style="margin-top: 0.5rem;">Alertes: <strong id="total-alerts">0</strong></p>
                    <p style="margin-top: 0.5rem;">Uptime: <strong>24j 12h</strong></p>
                </div>

                <div class="card">
                    <h3>Actions rapides</h3>
                    <button class="btn btn-secondary" onclick="resetSystem()" style="width: 100%; margin-bottom: 0.5rem;">↻ Réinitialiser</button>
                    <button class="btn btn-danger" onclick="emergencyStop()" style="width: 100%;">🛑 Arrêt d'urgence</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const config = { mode: 'auto', logging: true, archive: false, notifications: true, sound: true };

        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        function setMode(mode) { config.mode = mode; document.querySelectorAll('.mode-btn').forEach(el => el.classList.remove('active')); event.target.classList.add('active'); logEvent(`Mode: ${mode.toUpperCase()}`); }
        function toggleLogging() { config.logging = event.target.checked; logEvent(`Enregistrement ${config.logging ? 'ON' : 'OFF'}`); }
        function toggleArchive() { config.archive = event.target.checked; logEvent(`Archivage ${config.archive ? 'ON' : 'OFF'}`); }
        function toggleNotifications() { config.notifications = event.target.checked; }
        function toggleSound() { config.sound = event.target.checked; }
        function toggleAlert(type) { logEvent(`Alertes ${type} ${event.target.checked ? 'ON' : 'OFF'}`); }
        function toggleRule(ruleNum) { logEvent(`Règle ${ruleNum} ${event.target.checked ? 'ON' : 'OFF'}`); }

        function updateThreshold(type, value) {
            const [sensorType, direction] = type.split('-');
            const unit = sensorType === 'temp' ? '°C' : '%';
            document.getElementById(`${type}-val`).textContent = value + unit;
        }

        function testMotionAlert() { logEvent('🚨 Test alerte'); if (config.notifications) alert('Motion Alert!'); }
        function logEvent(msg) {
            const now = new Date().toLocaleTimeString('fr-FR');
            const log = document.getElementById('event-log');
            const item = document.createElement('div');
            item.className = 'event-item';
            item.innerHTML = `<span class="event-time">${now}</span><span class="event-message">${msg}</span>`;
            log.insertBefore(item, log.firstChild);
        }

        function clearLogs() { document.getElementById('event-log').innerHTML = ''; logEvent('Logs cleared'); }
        function resetSystem() { logEvent('🔄 Réinitialisation'); location.reload(); }
        function emergencyStop() { logEvent('🛑 Arrêt d\'urgence'); alert('Emergency stop!'); }

        function exportCSV() {
            fetch('/api/all').then(r => r.json()).then(data => {
                const csv = 'sensor,temp,hum,pres,motion,timestamp\\n' + data.map(m => `${m.sensor},${m.temp},${m.hum},${m.pres},${m.motion},${m.timestamp}`).join('\\n');
                download(csv, 'measures.csv', 'text/csv');
            });
        }

        function exportJSON() {
            fetch('/api/all').then(r => r.json()).then(data => download(JSON.stringify(data, null, 2), 'measures.json', 'application/json'));
        }

        function download(content, filename, type) {
            const el = document.createElement('a');
            el.setAttribute('href', 'data:' + type + ';charset=utf-8,' + encodeURIComponent(content));
            el.setAttribute('download', filename);
            el.click();
        }

        fetch('/api/last').then(r => r.json()).then(data => {
            const ts = new Date(data.timestamp).toLocaleTimeString('fr-FR');
            document.getElementById('last-measure-time').textContent = ts;
        }).catch(e => console.log(e));

        logEvent('✓ Control Panel chargé');
    </script>
</body>
</html>
"""

@app.route("/control", methods=["GET"])
def control():
    return render_template_string(CONTROL_PAGE)


# ---------- Entrée principale ----------


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)