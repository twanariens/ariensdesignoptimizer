import os
import subprocess
from flask import Flask, request, jsonify

app = Flask(__name__)
API_TOKEN = os.getenv("API_TOKEN", "fallback_token")

@app.route('/optimize', methods=['POST'])
def optimize():
    auth_header = request.headers.get('Authorization')
    if auth_header != API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    file_path = data.get('file')

    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 400

    ext = os.path.splitext(file_path)[1].lower()
    result = {}

    try:
        if ext == '.jpg' or ext == '.jpeg':
            subprocess.run(['jpegoptim', '--strip-all', file_path], check=True)
            result['jpeg'] = 'optimized'
        elif ext == '.png':
            subprocess.run(['pngquant', '--force', '--ext', '.png', file_path], check=True)
            result['png'] = 'optimized'
        elif ext == '.webp':
            result['webp'] = 'already webp'
        else:
            # Convert anything else to webp
            webp_path = file_path + '.webp'
            subprocess.run(['cwebp', '-q', '75', file_path, '-o', webp_path], check=True)
            result['converted_to_webp'] = webp_path
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Optimization failed: {str(e)}"}), 500

    return jsonify({"status": "ok", "file": file_path, "actions": result})
