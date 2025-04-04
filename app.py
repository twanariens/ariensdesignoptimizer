from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# 💡 Gebruik een veilige token (liefst via ENV VAR in productie)
import os
API_TOKEN = os.getenv("API_TOKEN", "fallback_token")

@app.route('/optimize', methods=['POST'])
def optimize():
    auth_header = request.headers.get('Authorization')
    if auth_header != f"Bearer {API_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    file_path = data.get('file')

    if not file_path:
        return jsonify({"error": "No file path provided"}), 400

    print(f"Ontvangen bestand: {file_path}")

    # Placeholder voor echte optimalisatie (komt later)
    return jsonify({"status": "ok", "message": f"Ontvangen bestand: {file_path}"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)