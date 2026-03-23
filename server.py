from flask import Flask, jsonify
import json

app = Flask(__name__)

def load():
    try:
        return json.load(open("users.json"))
    except:
        return {}

@app.route("/balance/<uid>")
def balance(uid):
    data = load()
    return jsonify({"balance": data.get(uid, {}).get("balance", 0)})

app.run(host="0.0.0.0", port=5000)
