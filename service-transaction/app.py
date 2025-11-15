# service-transaction/app.py

from flask import Flask, request
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from decimal import Decimal
import requests # Untuk memanggil API lain

# Import dari file kita sendiri
from config import Config
from models import db, Transaction

# --- 1. INISIALISASI APLIKASI ---
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db.init_app(app)
api = Api(app, 
          doc='/api-docs/', 
          title='Transaction Service API', 
          description='Layanan untuk membuat dan melihat Transaksi (Transfer).',
          security='apiKey')

# --- 2. MODEL API (Flask-RESTX) ---
trans_ns = api.namespace('transactions', description='Operasi Transaksi (Butuh Token)')

# Model untuk output
transaction_model = api.model('Transaction', {
    'id': fields.Integer,
    'sender_wallet_id': fields.Integer,
    'receiver_wallet_id': fields.Integer,
    'type': fields.String,
    'amount': fields.String,
    'description': fields.String,
    'status': fields.String,
    'created_at': fields.String
})

# Model untuk input (Transfer baru)
transfer_input_model = api.model('TransferInput', {
    # Kita tidak perlu ID pengirim, karena itu didapat dari Token
    'receiver_phone_number': fields.String(required=True, description='No. HP penerima (cth: 0812...)'),
    'amount': fields.Float(required=True, description='Jumlah uang yang dikirim'),
    'description': fields.String(description='Catatan untuk penerima')
})

# --- 3. HELPER (Ambil User ID dari Header) ---
def get_user_id_from_header():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        api.abort(401, 'Header X-User-Id tidak ada. Request harus melalui API Gateway.')
    return int(user_id)

# --- 4. ENDPOINTS (Logika Inti Transfer) ---

@trans_ns.route('/')
class TransactionList(Resource):
    
    @trans_ns.doc('get_my_transactions', security='apiKey')
    @trans_ns.marshal_list_with(transaction_model)
    def get(self):
        """(R)EAD: Mendapatkan riwayat transaksi saya"""
        user_id = get_user_id_from_header()
        
        # 1. Dapatkan dompet saya dulu (panggil service-wallet)
        try:
            wallet_resp = requests.get(f"{app.config['WALLET_SERVICE_URL']}/internal/wallets/by-user/{user_id}")
            wallet_resp.raise_for_status()
            my_wallet_id = wallet_resp.json()['id']
        except requests.exceptions.RequestException as e:
            return api.abort(503, f'Tidak bisa mengambil data dompet: {e}')
            
        # 2. Cari transaksi di DB ini berdasarkan ID dompet saya
        transactions = Transaction.query.filter(
            (Transaction.sender_wallet_id == my_wallet_id) | 
            (Transaction.receiver_wallet_id == my_wallet_id)
        ).order_by(Transaction.created_at.desc()).all()
        
        return [t.to_dict() for t in transactions]

    @trans_ns.doc('create_transfer', security='apiKey')
    @trans_ns.expect(transfer_input_model)
    @trans_ns.marshal_with(transaction_model, code=201)
    def post(self):
        """(C)REATE: Membuat transaksi transfer baru"""
        sender_user_id = get_user_id_from_header()
        data = api.payload
        amount_to_transfer = Decimal(str(data['amount']))
        receiver_phone = data['receiver_phone_number']
        
        # Validasi dasar
        if amount_to_transfer <= 0:
            api.abort(400, 'Jumlah transfer harus positif.')
            
        try:
            # --- ALUR KOMUNIKASI MICROSERVICE ---
            
            # 1. Dapatkan info dompet SAYA (PENGIRIM) (Panggil service-wallet)
            wallet_sender_resp = requests.get(f"{app.config['WALLET_SERVICE_URL']}/internal/wallets/by-user/{sender_user_id}")
            wallet_sender_resp.raise_for_status() # Error jika 404/500
            sender_wallet = wallet_sender_resp.json()
            sender_wallet_id = sender_wallet['id']
            sender_balance = Decimal(sender_wallet['balance'])
            
            # 2. Cek Saldo Pengirim
            if sender_balance < amount_to_transfer:
                api.abort(400, 'Saldo tidak mencukupi.')

            # 3. Dapatkan info user PENERIMA (Panggil service-user)
            user_receiver_resp = requests.get(f"{app.config['USER_SERVICE_URL']}/internal/by-phone/{receiver_phone}")
            user_receiver_resp.raise_for_status()
            receiver_user_id = user_receiver_resp.json()['id']
            
            # Cek jika kirim ke diri sendiri
            if sender_user_id == receiver_user_id:
                api.abort(400, 'Tidak bisa transfer ke diri sendiri.')

            # 4. Dapatkan info dompet PENERIMA (Panggil service-wallet)
            wallet_receiver_resp = requests.get(f"{app.config['WALLET_SERVICE_URL']}/internal/wallets/by-user/{receiver_user_id}")
            wallet_receiver_resp.raise_for_status()
            receiver_wallet_id = wallet_receiver_resp.json()['id']

            # --- EKSEKUSI (Jika semua validasi lolos) ---
            
            # 5. DEBIT Saldo Pengirim (Panggil service-wallet)
            debit_payload = {'type': 'debit', 'amount': data['amount']}
            debit_resp = requests.put(f"{app.config['WALLET_SERVICE_URL']}/internal/wallets/{sender_wallet_id}/balance", json=debit_payload)
            debit_resp.raise_for_status()

            # 6. CREDIT Saldo Penerima (Panggil service-wallet)
            credit_payload = {'type': 'credit', 'amount': data['amount']}
            credit_resp = requests.put(f"{app.config['WALLET_SERVICE_URL']}/internal/wallets/{receiver_wallet_id}/balance", json=credit_payload)
            credit_resp.raise_for_status()
            
            # 7. CATAT Transaksi (Simpan ke DB service-transaction)
            new_transaction = Transaction(
                sender_wallet_id=sender_wallet_id,
                receiver_wallet_id=receiver_wallet_id,
                type='transfer',
                amount=amount_to_transfer,
                description=data.get('description'),
                status='success'
            )
            db.session.add(new_transaction)
            db.session.commit()
            
            return new_transaction.to_dict(), 201

        except requests.exceptions.HTTPError as e:
            # Jika salah satu API call gagal (misal: user not found 404, saldo tidak cukup 400)
            return api.abort(e.response.status_code, e.response.json().get('message', 'Error eksternal'))
        except requests.exceptions.RequestException as e:
            # Jika service lain mati (connection error)
            return api.abort(503, f'Layanan eksternal tidak tersedia: {e}')
        except Exception as e:
            # Error internal di service ini
            db.session.rollback()
            return api.abort(500, f'Terjadi error internal: {e}')


# --- 5. BUAT TABEL & JALANKAN SERVER ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Port 3003 untuk service-transaction
    app.run(port=3003, debug=True)