import os
import requests
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback_secret")
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
CORS(app, supports_credentials=True)

mongo = PyMongo(app)
app.db = mongo.cx[os.getenv("DB_NAME", "CHAT")]
app.users_collection = app.db["users"]
app.history_collection = app.db["history"]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_gemini_reply(user_input: str) -> str:
    if not GEMINI_API_KEY:
        return "Error: Missing GEMINI_API_KEY"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    prompt = f"{user_input}\n\nPlease format your answer in Markdown."
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        result = response.json()
        candidates = result.get("candidates", [])
        if not candidates:
            return "Error: No response from Gemini."
        return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    except Exception as e:
        return f"Error: {e}"

# ---------------- AUTH ROUTES ----------------
@app.route("/auth/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if app.users_collection.find_one({"username": username}):
        return jsonify({"error": "Username already exists"}), 400

    hashed_pw = generate_password_hash(password)
    user_id = app.users_collection.insert_one({
        "username": username,
        "password": hashed_pw,
        "created_at": datetime.utcnow()
    }).inserted_id

    return jsonify({"message": "Signup successful", "user_id": str(user_id)})

@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = app.users_collection.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        session["user_id"] = str(user["_id"])
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/auth/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out"})

# ---------------- CHAT ----------------
@app.route("/chat", methods=["POST"])
def chat():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    reply = get_gemini_reply(user_input)
    if reply.startswith("Error:"):
        return jsonify({"error": reply}), 500

    app.history_collection.insert_one({
        "user_id": session["user_id"],
        "question": user_input,
        "answer": reply,
        "timestamp": datetime.utcnow()
    })

    return jsonify({"reply": reply})

# ---------------- HEALTH ----------------
@app.route("/")
def home():
    return {"message": "✅ Flask server is running"}

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "time": datetime.utcnow().isoformat()
    })

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)
