import json
import os
import requests
from urllib.parse import urlparse
from zipfile import ZipFile
from pathlib import Path
import sqlite3

def template_exists(template_id, db_path):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM templates WHERE name = ?", (template_id,))
        return cur.fetchone() is not None

def save_template(template_id, db_path):
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT OR IGNORE INTO templates (name) VALUES (?)", (template_id,))

def bulk_download_from_metadata(metadata_path, download_dir, extract_dir, db_path):
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
    except Exception as e:
        return {"error": f"Failed to load metadata JSON: {e}"}

    templates = metadata.get("data", {}).get("templates", [])

    downloaded = []
    skipped = []
    failed = []

    for idx, template in enumerate(templates):
        template_url = template.get("template_url")
        if not template_url:
            failed.append({"index": idx, "reason": "Missing template_url"})
            continue

        filename_from_url = os.path.basename(urlparse(template_url).path)
        if not filename_from_url:
            failed.append({"index": idx, "reason": "Cannot extract filename"})
            continue

        template_id = filename_from_url
        zip_path = Path(download_dir) / f"{template_id}.zip"
        extract_path = Path(extract_dir) / template_id

        if template_exists(template_id, db_path):
            skipped.append(template_id)
            continue

        try:
            response = requests.get(template_url)
            if response.status_code != 200:
                failed.append({"id": template_id, "reason": f"HTTP {response.status_code}"})
                continue

            with open(zip_path, "wb") as f:
                f.write(response.content)

            with ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            save_template(template_id, db_path)
            downloaded.append(template_id)

        except Exception as e:
            failed.append({"id": template_id, "reason": str(e)})

    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "total": len(templates)
    }
