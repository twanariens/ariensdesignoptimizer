from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/optimize', methods=['POST'])
def optimize():
    data = request.get_json()
    file_path = data.get('file')
    print(f"Ontvangen bestand: {file_path}")
    
    # Hier komt straks je optimalisatiecode
    return jsonify({"status": "ok", "message": f"Ontvangen bestand: {file_path}"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)