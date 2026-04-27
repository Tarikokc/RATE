import os, json
from flask import Blueprint, jsonify, current_app

bp = Blueprint('config', __name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'client.config.json')

@bp.route('/api/client-config', methods=['GET'])
def get_client_config():
    """Expose la configuration client (organisation, seuils, salles prédéfinies)."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return jsonify(config)
    except FileNotFoundError:
        return jsonify({'error': 'client.config.json introuvable'}), 404
    except json.JSONDecodeError as e:
        return jsonify({'error': f'JSON invalide : {str(e)}'}), 500
