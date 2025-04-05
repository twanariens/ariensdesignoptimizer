import os
import time
import logging
import datetime
import subprocess
import redis
import sys

from flask import Flask, request, jsonify
from celery import Celery
from logging.handlers import RotatingFileHandler

# Haal de API token op uit de omgevingsvariabele (of gebruik de default waarde als de variabele niet is ingesteld)
API_TOKEN = os.getenv("API_TOKEN", "mijn_geheime_token")

# Maak de app instantie eerst
app = Flask(__name__)

# Zorg dat de map bestaat voor logs
os.makedirs("logs", exist_ok=True)

# Formatter voor logs
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Configureer logging naar stdout
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

# Voeg de stream handler toe
app.logger.addHandler(stream_handler)

# Logging naar bestand (RotatingFileHandler)
handler = RotatingFileHandler("logs/worker.log", maxBytes=1000000, backupCount=5)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Stel het logniveau in op DEBUG
app.logger.setLevel(logging.DEBUG)

# Redis connectie via variabele
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Celery configuratie
CELERY_BROKER = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

celery = Celery(app.name, broker=CELERY_BROKER, backend=CELERY_BACKEND)

# Celery taak om afbeeldingen te optimaliseren
@celery.task(bind=True, max_retries=3)
def optimize_image(self, file_path):
    try:
        app.logger.debug("Test logbericht: Celery taak gestart.")
        ext = os.path.splitext(file_path)[1].lower()
        result = {}

        if ext in ['.jpg', '.jpeg']:
            subprocess.run(['jpegoptim', '--strip-all', file_path], check=True)
            result['jpeg'] = 'optimized'
        elif ext == '.png':
            subprocess.run(['pngquant', '--force', '--ext', '.png', file_path], check=True)
            result['png'] = 'optimized'
        else:
            webp_path = file_path + '.webp'
            subprocess.run(['cwebp', '-q', '75', file_path, '-o', webp_path], check=True)
            result['webp'] = webp_path

        app.logger.info(f"✔️ Optimalisatie gelukt voor: {file_path}")

        site_id = self.request.headers.get('X-Site-ID', 'unknown')
        key = f"site:{site_id}:stats"
        now = datetime.datetime.utcnow().isoformat()

        # Update Redis statistieken
        redis_client.hincrby(key, "total", 1)  # Verhoogt het totaal aantal taken
        redis_client.hincrby(key, "success", 1)  # Verhoogt het aantal succesvolle optimalisaties
        redis_client.lpush(f"{key}:types", list(result.keys())[0])  # Voeg het type toe
        redis_client.lpush(f"{key}:timestamps", now)  # Voeg de timestamp toe
        redis_client.ltrim(f"{key}:types", 0, 9)  # Beperk het aantal types tot de laatste 10
        redis_client.ltrim(f"{key}:timestamps", 0, 9)  # Beperk het aantal timestamps tot de laatste 10

        # **Nieuwe logregel toevoegen voor debugging**
        app.logger.info(f"Gegevens naar Redis gestuurd voor {file_path}: total={redis_client.hget(key, 'total')}, success={redis_client.hget(key, 'success')}")

        return { "file": file_path, "result": result }

    except subprocess.CalledProcessError as e:
        app.logger.error(f"❌ Fout bij optimalisatie: {e}")

        site_id = self.request.headers.get('X-Site-ID', 'unknown')
        key = f"site:{site_id}:stats"
        now = datetime.datetime.utcnow().isoformat()

        # Update Redis statistieken in geval van een fout
        redis_client.hincrby(key, "total", 1)  # Verhoogt het totaal aantal taken
        redis_client.hincrby(key, "failed", 1)  # Verhoogt het aantal mislukte optimalisaties
        redis_client.lpush(f"{key}:types", "failed")  # Voeg "failed" toe aan types
        redis_client.lpush(f"{key}:timestamps", now)  # Voeg de timestamp toe
        redis_client.ltrim(f"{key}:types", 0, 9)  # Beperk het aantal types tot de laatste 10
        redis_client.ltrim(f"{key}:timestamps", 0, 9)  # Beperk het aantal timestamps tot de laatste 10

        raise self.retry(exc=e, countdown=5)

# Route om afbeeldingen te optimaliseren
@app.route('/optimize', methods=['POST'])
def optimize():
    if request.headers.get('Authorization') != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    file_path = data.get("file")

    if not file_path:
        return jsonify({"error": "Geen bestand opgegeven"}), 400

    task = optimize_image.delay(file_path)
    return jsonify({"status": "queued", "task_id": task.id})

# Route om de status van de taak op te vragen
@app.route('/status/<task_id>', methods=['GET'])
def task_status(task_id):
    task = optimize_image.AsyncResult(task_id)
    if task.state == 'PENDING':
        return jsonify({"status": "pending"})
    elif task.state == 'SUCCESS':
        return jsonify({"status": "done", "result": task.result})
    elif task.state == 'FAILURE':
        return jsonify({"status": "failed", "error": str(task.info)})
    else:
        return jsonify({"status": task.state})

# Route om de statistieken op te vragen
@app.route('/stats', methods=['GET'])
def stats():
    if request.headers.get('Authorization') != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    site_id = request.headers.get('X-Site-ID')
    if not site_id:
        return jsonify({"error": "Missing Site ID"}), 400

    key = f"site:{site_id}:stats"
    stats = redis_client.hgetall(key)
    types = redis_client.lrange(f"{key}:types", 0, 9)
    timestamps = redis_client.lrange(f"{key}:timestamps", 0, 9)

    return jsonify({
        "total_tasks": int(stats.get("total", 0)),
        "success": int(stats.get("success", 0)),
        "failed": int(stats.get("failed", 0)),
        "last_10_types": types,
        "last_10_timestamps": timestamps
    })
