import os
import time
from flask import Flask, request, jsonify
from celery import Celery

API_TOKEN = os.getenv("API_TOKEN", "mijn_geheime_token")

app = Flask(__name__)

# Configure Celery
CELERY_BROKER = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

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
        return { "file": file_path, "result": result }

    except subprocess.CalledProcessError as e:
        app.logger.error(f"❌ Fout bij optimalisatie: {e}")
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
