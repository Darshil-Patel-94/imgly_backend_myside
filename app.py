from flask import Flask, request, jsonify, send_from_directory
import os
import sqlite3
from pathlib import Path
from convert_scene_json import convert_to_scene_json
from download_extract import bulk_download_from_metadata
import glob

app = Flask(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / 'downloads'
EXTRACT_DIR = BASE_DIR / 'assets'
CONVERTED_DIR = BASE_DIR / 'converted'
RAW_JSON_DIR = BASE_DIR / 'raw_json'
DB_PATH = BASE_DIR / 'db' / 'templates.db'

# Ensure folders exist
for folder in [DOWNLOAD_DIR, EXTRACT_DIR, CONVERTED_DIR, DB_PATH.parent]:
    folder.mkdir(parents=True, exist_ok=True)

# Initialize SQLite DB
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT
            );
        ''')
init_db()

# Utility: Check if template is already stored in DB
def template_exists(template_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM templates WHERE name = ?", (template_id,))
        return cur.fetchone() is not None

# Utility: Add new template to DB
def save_template(template_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO templates (name) VALUES (?)", (template_id,))

# Route 1: List all stored templates (also triggers bulk download from all JSON files)
@app.route('/templates', methods=['GET'])
def list_templates():
    json_files = glob.glob(str(RAW_JSON_DIR / '*.json'))
    for file_path in json_files:
        bulk_download_from_metadata(file_path, DOWNLOAD_DIR, EXTRACT_DIR, DB_PATH)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM templates")
        templates = [row[0] for row in cur.fetchall()]
    return jsonify(templates)

# Route 2: Convert to scene.json
@app.route('/convert', methods=['POST'])
def convert_template():
    data = request.get_json()
    template_id = data.get('template_id')

    if not template_id:
        return jsonify({'error': 'template_id is required'}), 400

    extract_path = EXTRACT_DIR / template_id
    input_json = extract_path / 'template.json'
    output_path = CONVERTED_DIR / f'{template_id}.scene.json'

    if not input_json.exists():
        return jsonify({'error': 'template.json not found for given template_id'}), 404

    try:
        convert_to_scene_json(input_json, output_path)
        return jsonify({
            'message': 'Converted successfully',
            'download_url': f'/converted/{template_id}.scene.json'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route 3: Serve converted .scene.json file (for frontend/editor)
@app.route('/converted/<filename>', methods=['GET'])
def serve_converted_file(filename):
    return send_from_directory(CONVERTED_DIR, filename ,  as_attachment=True)

@app.route('/index.html')
def index():
    return send_from_directory('static', 'index.html')

if __name__ == '__main__':
    app.run(debug=True)
