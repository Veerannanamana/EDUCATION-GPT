import os
import requests
from flask import Flask, jsonify, request, session, render_template, redirect, url_for
from flask_cors import CORS
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo.errors import ServerSelectionTimeoutError

load_dotenv()

# ----------------- Flask App Setup -----------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback_secret")
app.config["MONGO_URI"] = os.getenv("MONGO_URI")

# Enable CORS for frontend
CORS(app, supports_credentials=True, origins=["http://localhost:3000"])

# Session configuration
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False
)

# Initialize PyMongo
mongo = PyMongo(app)
app.db = mongo.cx[os.getenv("DB_NAME", "CHAT")]
app.users_collection = app.db["users"]
app.history_collection = app.db["history"]

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ----------------- Helper Functions -----------------
def safe_str(val):
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        return " ".join(safe_str(item) for item in val)
    if val is None:
        return ""
    if isinstance(val, dict):
        return str(val)
    try:
        return str(val)
    except Exception:
        return repr(val)

# ----------------- Gemini Chat -----------------
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
        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return safe_str(text)
    except Exception as e:
        return safe_str(f"Error: {e}")

# ----------------- Routes -----------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("chat_page"))
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if "user_id" in session:
        return redirect(url_for("chat_page"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "Username and password required", 400
        if app.users_collection.find_one({"username": username}):
            return "Username already exists", 400

        hashed_pw = generate_password_hash(password)
        app.users_collection.insert_one({
            "username": username,
            "password": hashed_pw,
            "created_at": datetime.now(timezone.utc)
        })
        return redirect(url_for("home"))

    return render_template("signup.html")

@app.route("/login", methods=["POST"])
def login_page():
    username = request.form.get("username")
    password = request.form.get("password")

    user = app.users_collection.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        session["user_id"] = str(user["_id"])
        session.permanent = True
        return redirect(url_for("chat_page"))

    return "Invalid credentials", 401

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("home"))

@app.route("/chat", methods=["GET", "POST"])
def chat_page():
    if "user_id" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        user_input = request.form.get("message", "").strip()
        if not user_input:
            return jsonify({"reply": "Error: Empty message"}), 400

        reply = get_gemini_reply(user_input)
        reply_str = safe_str(reply)

        # Save to history
        try:
            app.history_collection.insert_one({
                "user_id": session["user_id"],
                "question": safe_str(user_input),
                "answer": reply_str,
                "timestamp": datetime.now(timezone.utc)
            })
        except ServerSelectionTimeoutError:
            return jsonify({"reply": "Error: Cannot connect to MongoDB"}), 500

        return jsonify({"reply": reply_str})

    return render_template("chat.html")

@app.route("/chat/history")
def chat_history():
    if "user_id" not in session:
        return jsonify([])

    try:
        history = list(app.history_collection.find({"user_id": session["user_id"]}).sort("timestamp", 1))
        formatted = [{"question": h["question"], "answer": h["answer"]} for h in history]
        return jsonify(formatted)
    except ServerSelectionTimeoutError:
        return jsonify({"error": "Cannot connect to MongoDB"}), 500

# ----------------- Run Server -----------------
if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=debug)
