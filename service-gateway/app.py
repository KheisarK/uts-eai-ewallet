# gateway.py
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv

from jwt_utils import require_jwt  # JWT middleware

load_dotenv()

app = Flask(__name__)

# Izinkan SEMUA origin (untuk frontend http://localhost:8000)
CORS(app, resources={r"/*": {"origins": "*"}})

# =============================
# SERVICE ENDPOINTS
# =============================
SERVICES = {
    "user": os.getenv("USER_SERVICE_URL", "http://localhost:3001"),
    "wallet": os.getenv("WALLET_SERVICE_URL", "http://localhost:3002"),
    "transaction": os.getenv("TRANSACTION_SERVICE_URL", "http://localhost:3003"),
    # --- TAMBAHAN BARU: PAYEE ---
    "payee": os.getenv("PAYEE_SERVICE_URL", "http://localhost:3004")
    # -----------------------------
}

# =============================
# FORWARD FUNCTION
# =============================
def forward(service_name, path, method, data=None):
    base = SERVICES.get(service_name)
    if not base:
        return jsonify({"error": f"Service '{service_name}' not found"}), 404

    # Logika untuk memastikan URL tidak ganda slash
    if base.endswith("/"):
        base = base[:-1]
    if path.startswith("/"):
        path = path[1:]

    url = f"{base}/{path}"
    headers = {}
    incoming_auth = request.headers.get("Authorization")
    if incoming_auth:
        headers["Authorization"] = incoming_auth

    # --- INJEKSI X-User-Id ---
    if hasattr(g, 'user_claims') and g.user_claims:
        user_id = g.user_claims.get('user_id')
        if user_id:
            headers['X-User-Id'] = str(user_id)
    # -------------------------

    print(f"[Gateway] → {method} {url} data={data} headers={headers.get('X-User-Id', 'No ID')}")


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
    path = request.path.replace("/api/", "")
    return forward("user", path, request.method, body)


# PROTECTED USER ROUTES
@app.route("/api/users/me", methods=["GET", "PUT", "DELETE"])
@require_jwt(optional=False)
def users_me():
    body = request.get_json() if request.method == "PUT" or request.method == "DELETE" else None
    return forward("user", "users/me", request.method, body)


# WALLET ROUTES (Publik)
@app.route("/api/wallets/me", methods=["GET"])
@require_jwt(optional=False)
def wallets_me():
    return forward("wallet", "wallets/me", "GET")


# RUTE TOP UP
@app.route("/api/topup", methods=["POST"])
@require_jwt(optional=False)
def topup_saldo():
    user_id = g.user_claims.get('user_id')
    data = request.get_json()
    amount = data.get('amount')
    
    if not amount or float(amount) <= 0:
        return jsonify({"message": "Jumlah Top Up tidak valid"}), 400

    wallet_url = f"{SERVICES['wallet']}/internal/wallets/by-user/{user_id}"
    try:
        wallet_res = requests.get(wallet_url, timeout=5)
        wallet_res.raise_for_status() 
        wallet_id = wallet_res.json().get('id')
        
        if not wallet_id:
             return jsonify({"message": "ID Wallet tidak ditemukan di respon internal"}), 404
             
    except requests.exceptions.HTTPError as e:
         if e.response.status_code == 404:
             return jsonify({"message": "Wallet aktif tidak ditemukan untuk user ini"}), 404
         return jsonify({"message": f"Error di Wallet Service: {str(e)}"}), 500
    except requests.exceptions.ConnectionError:
        return jsonify({"message": "Wallet Service tidak terjangkau (saat GET)"}), 503

    balance_payload = {
        "type": "credit",
        "amount": amount
    }
    balance_url = f"{SERVICES['wallet']}/internal/wallets/{wallet_id}/balance"
    
    try:
        balance_res = requests.put(balance_url, json=balance_payload, timeout=5)
        balance_res.raise_for_status() 
        return jsonify(balance_res.json()), balance_res.status_code
        
    except requests.exceptions.RequestException as e:
        print(f"Error saat update balance: {e}")
        try:
            return jsonify(e.response.json()), e.response.status_code
        except:
            return jsonify({"message": f"Gagal Top Up di Wallet Service. Error: {str(e)}"}), 500


# TRANSACTIONS (Publik: GET Riwayat, POST Transfer)
@app.route("/api/transactions", methods=["GET", "POST"])
@require_jwt(optional=False)
def transactions_collection():
    body = request.get_json() if request.method == "POST" else None
    return forward("transaction", "transactions/", request.method, body) 


# --- TAMBAHAN BARU: RUTE PAYEE ---
# Rute ini menangani /api/payees (GET list, POST baru)
@app.route("/api/payees", methods=["GET", "POST"])
@require_jwt(optional=False)
def payees_collection():
    body = request.get_json() if request.method == "POST" else None
    # Forward ke /payees/ (dengan slash) karena service-payee menggunakan @payee_ns.route('/')
    return forward("payee", "payees/", request.method, body)

# Rute ini menangani /api/payees/<id> (GET, PUT, DELETE spesifik)
@app.route("/api/payees/<int:id>", methods=["GET", "PUT", "DELETE"])
@require_jwt(optional=False)
def payees_item(id):
    body = request.get_json() if request.method == "PUT" else None
    # Forward ke /payees/<id>
    return forward("payee", f"payees/{id}", request.method, body)
# ---------------------------------


# =================================================================
# ROUTE INTERNAL (Diakses HANYA oleh service lain)
# =================================================================

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