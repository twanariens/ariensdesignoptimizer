import os
import time
import logging
import datetime
import subprocess
import redis

from flask import Flask, request, jsonify
from celery import Celery
from logging.handlers import RotatingFileHandler

API_TOKEN = os.getenv("API_TOKEN", "mijn_geheime_token")

app = Flask(__name__)

# Zorg dat de map bestaat
os.makedirs("logs", exist_ok=True)

# Logging naar bestand
handler = RotatingFileHandler("logs/worker.log", maxBytes=1000000, backupCount=5)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Redis connectie via variabele
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Celery configuratie
CELERY_BROKER = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

celery = Celery(app.name, broker=CELERY_BROKER, backend=CELERY_BACKEND)

@celery.task(bind=True, max_retries=3)
def optimize_image(self, file_path):
    try:
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

        redis_client.hincrby(key, "total", 1)
        redis_client.hincrby(key, "success", 1)
        redis_client.lpush(f"{key}:types", list(result.keys())[0])
        redis_client.lpush(f"{key}:timestamps", now)
        redis_client.ltrim(f"{key}:types", 0, 9)
        redis_client.ltrim(f"{key}:timestamps", 0, 9)

        return { "file": file_path, "result": result }

    except subprocess.CalledProcessError as e:
        app.logger.error(f"❌ Fout bij optimalisatie: {e}")

        site_id = self.request.headers.get('X-Site-ID', 'unknown')
        key = f"site:{site_id}:stats"
        now = datetime.datetime.utcnow().isoformat()

        redis_client.hincrby(key, "total", 1)
        redis_client.hincrby(key, "failed", 1)
        redis_client.lpush(f"{key}:types", "failed")
        redis_client.lpush(f"{key}:timestamps", now)
        redis_client.ltrim(f"{key}:types", 0, 9)
        redis_client.ltrim(f"{key}:timestamps", 0, 9)

        raise self.retry(exc=e, countdown=5)

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
