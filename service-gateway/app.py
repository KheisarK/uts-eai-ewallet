# gateway.py
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

from jwt_utils import require_jwt  # JWT middleware

load_dotenv()

app = Flask(__name__)

# Allow ALL origins (untuk frontend http://localhost:8000)
CORS(app, resources={r"/*": {"origins": "*"}})

# =============================
# SERVICE ENDPOINTS
# =============================
SERVICES = {
    "user": os.getenv("USER_SERVICE_URL", "http://localhost:3001"),
    "wallet": os.getenv("WALLET_SERVICE_URL", "http://localhost:3002"),
    "transaction": os.getenv("TRANSACTION_SERVICE_URL", "http://localhost:3003")
}

# =============================
# FORWARD FUNCTION
# =============================
def forward(service_name, path, method, data=None):
    base = SERVICES.get(service_name)
    if not base:
        return jsonify({"error": f"Service '{service_name}' not found"}), 404

    # PERBAIKAN: jangan pakai replace("//","/") karena merusak http://
    if base.endswith("/"):
        base = base[:-1]
    if path.startswith("/"):
        path = path[1:]

    url = f"{base}/{path}"

    headers = {}

    # forward JWT token
    incoming_auth = request.headers.get("Authorization")
    if incoming_auth:
        headers["Authorization"] = incoming_auth

    print(f"[Gateway] → {method} {url} data={data}")

    try:
        if method == "GET":
            res = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            res = requests.post(url, json=data, headers=headers, timeout=10)
        elif method == "PUT":
            res = requests.put(url, json=data, headers=headers, timeout=10)
        elif method == "DELETE":
            res = requests.delete(url, headers=headers, timeout=10)
        else:
            return jsonify({"error": "Method Not Allowed"}), 405

        # Jika backend kirim JSON → forward JSON
        try:
            return jsonify(res.json()), res.status_code
        except ValueError:
            return res.text, res.status_code, {"Content-Type": res.headers.get("Content-Type")}

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": f"{service_name} service unreachable",
            "url": url
        }), 503


# =============================
# ROUTES
# =============================

# PUBLIC USER ROUTES
@app.route("/api/users/login", methods=["POST"])
@app.route("/api/users/register", methods=["POST"])
def users_public():
    body = request.get_json()
    path = request.path.replace("/api/", "")  # contoh: users/login
    return forward("user", path, request.method, body)


# PROTECTED USER ROUTES
@app.route("/api/users/me", methods=["GET", "PUT", "DELETE"])
@require_jwt(optional=False)
def users_me():
    body = request.get_json() if request.method == "PUT" else None
    return forward("user", "users/me", request.method, body)


# INTERNAL USER LOOKUP
@app.route("/api/users/internal/by-phone/<phone>", methods=["GET"])
@require_jwt(optional=False)
def users_internal_by_phone(phone):
    return forward("user", f"users/internal/by-phone/{phone}", "GET")


# WALLET ROUTES
@app.route("/api/wallets/me", methods=["GET"])
@require_jwt(optional=False)
def wallets_me():
    return forward("wallet", "wallets/me", "GET")


@app.route("/api/internal/wallets", methods=["POST"])
@require_jwt(optional=True)
def internal_wallets_create():
    body = request.get_json()
    return forward("wallet", "internal/wallets", "POST", body)


@app.route("/api/internal/wallets/by-user/<user_id>", methods=["GET", "DELETE"])
@require_jwt(optional=True)
def internal_wallets_by_user(user_id):
    return forward("wallet", f"internal/wallets/by-user/{user_id}", request.method)


@app.route("/api/internal/wallets/<wallet_id>/balance", methods=["PUT"])
@require_jwt(optional=True)
def internal_wallet_balance(wallet_id):
    body = request.get_json()
    return forward("wallet", f"internal/wallets/{wallet_id}/balance", "PUT", body)


# TRANSACTIONS
@app.route("/api/transactions", methods=["GET", "POST"])
@require_jwt(optional=False)
def transactions_collection():
    body = request.get_json() if request.method == "POST" else None
    return forward("transaction", "transactions", request.method, body)


@app.route("/api/transactions/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@require_jwt(optional=False)
def transactions_item(path):
    body = request.get_json() if request.method in ["POST", "PUT"] else None
    return forward("transaction", f"transactions/{path}", request.method, body)


# HEALTH CHECK
@app.route("/health")
def health():
    statuses = {}
    for name, srv in SERVICES.items():
        try:
            r = requests.get(f"{srv}/health", timeout=2)
            statuses[name] = "healthy" if r.status_code == 200 else "error"
        except:
            statuses[name] = "offline"
    return jsonify({"gateway": "healthy", "services": statuses})


@app.route("/")
def index():
    return jsonify({"message": "E-Wallet API Gateway with JWT", "services": SERVICES})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=True)
