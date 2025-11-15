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
    "transaction": os.getenv("TRANSACTION_SERVICE_URL", "http://localhost:3003")
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
            # Tambahkan header X-User-Id untuk backend service
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

        # Jika backend kirim JSON → forward JSON
        try:
            return jsonify(res.json()), res.status_code
        except ValueError:
            # Jika bukan JSON (misal: DELETE tanpa body)
            return res.text, res.status_code, {"Content-Type": res.headers.get("Content-Type")}

    except requests.exceptions.ConnectionError:
        return jsonify({
            "error": f"{service_name} service unreachable",
            "url": url
        }), 503


# =============================
# ROUTES
# =============================

# PUBLIC USER ROUTES (Tidak butuh token)
@app.route("/api/users/login", methods=["POST"])
@app.route("/api/users/register", methods=["POST"])
def users_public():
    body = request.get_json()
    path = request.path.replace("/api/", "")  # contoh: users/login
    return forward("user", path, request.method, body)


# PROTECTED USER ROUTES (Butuh token, diteruskan ke service-user)
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


# --- INI ADALAH RUTE YANG ANDA BUTUHKAN UNTUK TOP UP ---
@app.route("/api/topup", methods=["POST"])
@require_jwt(optional=False)
def topup_saldo():
    """
    Endpoint publik untuk Top Up.
    Ini akan memanggil 2 endpoint internal di service-wallet:
    1. GET /internal/wallets/by-user/{user_id} (untuk dapat wallet_id)
    2. PUT /internal/wallets/{wallet_id}/balance (untuk melakukan CREDIT)
    """
    
    # 1. Ambil ID user yang sedang login dari token
    user_id = g.user_claims.get('user_id')
    data = request.get_json()
    amount = data.get('amount')
    
    if not amount or float(amount) <= 0:
        return jsonify({"message": "Jumlah Top Up tidak valid"}), 400

    # 2. Panggil internal endpoint service-wallet untuk mendapatkan ID wallet user
    wallet_url = f"{SERVICES['wallet']}/internal/wallets/by-user/{user_id}"
    try:
        # Kita tidak perlu token untuk panggil internal, karena asumsinya internal network
        wallet_res = requests.get(wallet_url, timeout=5)
        wallet_res.raise_for_status() # Cek jika user punya wallet (status 200)
        wallet_id = wallet_res.json().get('id')
        
        if not wallet_id:
             return jsonify({"message": "ID Wallet tidak ditemukan di respon internal"}), 404
             
    except requests.exceptions.HTTPError as e:
         if e.response.status_code == 404:
             return jsonify({"message": "Wallet aktif tidak ditemukan untuk user ini"}), 404
         return jsonify({"message": f"Error di Wallet Service: {str(e)}"}), 500
    except requests.exceptions.ConnectionError:
        return jsonify({"message": "Wallet Service tidak terjangkau (saat GET)"}), 503

    # 3. Lakukan kredit saldo (PUT ke internal balance endpoint)
    balance_payload = {
        "type": "credit",
        "amount": amount
    }
    balance_url = f"{SERVICES['wallet']}/internal/wallets/{wallet_id}/balance"
    
    try:
        balance_res = requests.put(balance_url, json=balance_payload, timeout=5)
        balance_res.raise_for_status() # Cek jika update berhasil (status 200)
        
        # Kembalikan respon sukses dari service-wallet
        return jsonify(balance_res.json()), balance_res.status_code
        
    except requests.exceptions.RequestException as e:
        # Tangani error jika gagal (misal: saldo tidak cukup, service mati)
        print(f"Error saat update balance: {e}")
        try:
            return jsonify(e.response.json()), e.response.status_code
        except:
            return jsonify({"message": f"Gagal Top Up di Wallet Service. Error: {str(e)}"}), 500
# --- SELESAI RUTE TOP UP ---


# TRANSACTIONS (Publik: GET Riwayat, POST Transfer)
@app.route("/api/transactions", methods=["GET", "POST"])
@require_jwt(optional=False)
def transactions_collection():
    body = request.get_json() if request.method == "POST" else None
    return forward("transaction", "transactions", request.method, body)


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