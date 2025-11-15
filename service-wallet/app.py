# service-wallet/app.py

from flask import Flask, request
from flask_restx import Api, Resource, fields
from decimal import Decimal # Untuk mengelola uang (Decimal lebih akurat dari float)

# Import dari file kita sendiri
from config import Config
from models import db, Wallet

# --- 1. INISIALISASI APLIKASI ---
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
api = Api(app, 
          doc='/api-docs/', 
          title='Wallet Service API', 
          description='Layanan untuk mengelola Dompet dan Saldo.')

# --- 2. MODEL API (Flask-RESTX) ---
wallet_ns = api.namespace('wallets', description='Operasi Dompet (Publik, butuh Token)')
internal_ns = api.namespace('internal', description='Operasi Dompet (Internal, antar service)')

# Model untuk output (menampilkan saldo)
wallet_model = api.model('Wallet', {
    'id': fields.Integer(description='ID Dompet'),
    'user_id': fields.Integer(description='ID User Pemilik'),
    'balance': fields.String(description='Saldo dompet (format string)'),
    'label': fields.String(description='Label dompet')
})

# Model untuk input (membuat dompet baru, internal)
internal_wallet_input = api.model('InternalWalletInput', {
    'user_id': fields.Integer(required=True, description='ID User dari service-user')
})

# Model untuk input (update label dompet, publik)
wallet_update_input = api.model('WalletUpdateInput', {
    'label': fields.String(required=True, description='Label dompet baru')
})

# Model untuk input (debit/kredit, internal)
balance_update_input = api.model('BalanceUpdateInput', {
    'type': fields.String(required=True, description='Tipe transaksi (debit/credit)'),
    'amount': fields.Float(required=True, description='Jumlah uang')
})

# --- 3. HELPER (Ambil User ID dari Header) ---
# API Gateway akan meneruskan JWT yang sudah divalidasi
# dan mengirimkan ID user di header 'X-User-Id'
def get_user_id_from_header():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        api.abort(401, 'Header X-User-Id tidak ada. Request harus melalui API Gateway.')
    return int(user_id)

# --- 4. ENDPOINTS PUBLIK (Butuh Token, via API Gateway) ---

@wallet_ns.route('/me')
class MyWallet(Resource):
    @wallet_ns.doc('get_my_wallet', security='apiKey')
    @wallet_ns.marshal_with(wallet_model)
    def get(self):
        """(R)EAD: Mendapatkan info dompet dan saldo saya"""
        user_id = get_user_id_from_header()
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            api.abort(404, 'Dompet tidak ditemukan untuk user ini.')
        return wallet
        
    @wallet_ns.doc('update_my_wallet', security='apiKey')
    @wallet_ns.expect(wallet_update_input)
    @wallet_ns.marshal_with(wallet_model)
    def put(self):
        """(U)PDATE: Memperbarui label dompet saya"""
        user_id = get_user_id_from_header()
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            api.abort(404, 'Dompet tidak ditemukan.')
            
        data = api.payload
        wallet.label = data['label']
        db.session.commit()
        return wallet

# --- 5. ENDPOINTS INTERNAL (Hanya untuk Service Lain) ---

@internal_ns.route('/wallets')
class InternalWalletCreate(Resource):
    @internal_ns.doc('internal_create_wallet')
    @internal_ns.expect(internal_wallet_input)
    @internal_ns.marshal_with(wallet_model, code=201)
    def post(self):
        """(C)REATE: (INTERNAL) Membuat dompet baru saat user registrasi"""
        data = api.payload
        user_id = data['user_id']
        
        # Cek jika dompet sudah ada
        if Wallet.query.filter_by(user_id=user_id).first():
            api.abort(400, f'Dompet untuk user_id {user_id} sudah ada.')
            
        # Buat dompet baru dengan saldo 0
        new_wallet = Wallet(user_id=user_id, balance=0.00)
        db.session.add(new_wallet)
        db.session.commit()
        return new_wallet, 201

@internal_ns.route('/wallets/by-user/<int:user_id>')
class InternalWalletByUser(Resource):
    @internal_ns.doc('internal_get_wallet_by_user_id')
    @internal_ns.marshal_with(wallet_model)
    def get(self, user_id):
        """(R)EAD: (INTERNAL) Mendapatkan dompet berdasarkan user_id"""
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            api.abort(404, 'Dompet tidak ditemukan.')
        return wallet

@internal_ns.route('/wallets/<int:wallet_id>/balance')
class InternalWalletBalance(Resource):
    @internal_ns.doc('internal_update_balance')
    @internal_ns.expect(balance_update_input)
    @internal_ns.marshal_with(wallet_model)
    def put(self, wallet_id):
        """(U)PDATE: (INTERNAL) Mengubah saldo (debit/kredit)"""
        wallet = Wallet.query.get(wallet_id)
        if not wallet:
            api.abort(404, 'Dompet tidak ditemukan.')
            
        data = api.payload
        amount = Decimal(str(data['amount'])) # Konversi float ke Decimal dengan aman

        if data['type'] == 'debit':
            if wallet.balance < amount:
                api.abort(400, 'Saldo tidak mencukupi (Insufficient balance).')
            wallet.balance -= amount
        elif data['type'] == 'credit':
            wallet.balance += amount
        else:
            api.abort(400, 'Tipe harus "debit" atau "credit".')
            
        db.session.commit()
        return wallet

# --- 6. BUAT TABEL & JALANKAN SERVER ---
with app.app_context():
    # Ini akan membuat tabel 'wallet' di database 'db_wallets'
    db.create_all()

if __name__ == '__main__':
    # Port 3002 untuk service-wallet
    app.run(port=3002, debug=True)