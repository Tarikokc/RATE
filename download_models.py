"""
Télécharge les artefacts ML (rate_model.tflite, scaler_X.pkl, scaler_y.pkl)
depuis la dernière GitHub Release si les fichiers sont absents localement.

Usage :
    python download_models.py

Variables d'environnement optionnelles :
    GITHUB_TOKEN  — token pour augmenter la limite de l'API GitHub
    RATE_RELEASE  — tag de release cible (défaut : latest)
"""
import os
import sys
import json
import urllib.request

OWNER    = "Tarikokc"
REPO     = "RATE"
ARTIFACTS = ["rate_model.tflite", "scaler_X.pkl", "scaler_y.pkl"]

def github_headers():
    h = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def get_release_assets():
    tag = os.environ.get("RATE_RELEASE", "latest")
    if tag == "latest":
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{tag}"

    req = urllib.request.Request(url, headers=github_headers())
    with urllib.request.urlopen(req) as r:
        release = json.loads(r.read())

    return {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}

def download_file(url: str, dest: str):
    print(f"  ↓ {os.path.basename(dest)} ...", end=" ", flush=True)
    req = urllib.request.Request(url, headers=github_headers())
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        f.write(r.read())
    print("OK")

def main():
    missing = [a for a in ARTIFACTS if not os.path.exists(a)]
    if not missing:
        print("[models] Tous les artefacts sont déjà présents.")
        return

    print(f"[models] Artefacts manquants : {missing}")
    try:
        assets = get_release_assets()
    except Exception as e:
        print(f"[models] Échec récupération release GitHub : {e}", file=sys.stderr)
        sys.exit(1)

    for name in missing:
        if name not in assets:
            print(f"[models] ⚠️  {name} introuvable dans la release.", file=sys.stderr)
            continue
        download_file(assets[name], name)

    print("[models] Terminé.")

if __name__ == "__main__":
    main()
