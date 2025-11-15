# service-wallet/app.py

from flask import Flask, request
from flask_restx import Api, Resource, fields
from decimal import Decimal

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
# Namespace dipisah antara Publik (Frontend) dan Internal (Antar Service)
wallets_ns = api.namespace('wallets', description='Operasi Dompet Publik (Butuh Token)')
internal_ns = api.namespace('internal', description='Operasi Dompet Internal (Antar Service)')

# Model untuk output (menampilkan saldo)
wallet_model = api.model('Wallet', {
    'id': fields.Integer,
    'user_id': fields.Integer,
    'balance': fields.String,
    'label': fields.String,
    'status': fields.String
})

# Model untuk input (membuat dompet baru, internal)
internal_wallet_input = api.model('InternalWalletInput', {
    'user_id': fields.Integer(required=True, description='ID User dari service-user')
})

# Model untuk input (debit/kredit, internal)
balance_update_input = api.model('BalanceUpdateInput', {
    'type': fields.String(required=True, enum=['debit', 'credit']),
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
@wallets_ns.route('/me')
class MyWallet(Resource):
    @wallets_ns.doc('get_my_wallet', security='apiKey')
    @wallets_ns.marshal_with(wallet_model)
    def get(self):
        """(R)EAD: Mendapatkan info dompet dan saldo saya"""
        user_id = get_user_id_from_header()
        wallet = Wallet.query.filter_by(user_id=user_id, status='active').first()
        if not wallet:
            api.abort(404, 'Dompet aktif tidak ditemukan untuk user ini.')
        return wallet.to_dict()

# --- 5. ENDPOINTS INTERNAL (Hanya untuk Service Lain) ---

# Endpoint ini akan dipanggil oleh service-user saat registrasi
@internal_ns.route('/wallets')
class InternalWalletCreate(Resource):
    @internal_ns.doc('internal_create_wallet')
    @internal_ns.expect(internal_wallet_input)
    @internal_ns.marshal_with(wallet_model, code=201)
    def post(self):
        """(C)REATE: (INTERNAL) Membuat dompet baru saat user registrasi"""
        data = api.payload
        user_id = data['user_id']
        
        if Wallet.query.filter_by(user_id=user_id).first():
            api.abort(400, f'Dompet untuk user_id {user_id} sudah ada.')
            
        new_wallet = Wallet(user_id=user_id, balance=Decimal('0.00'), status='active')
        db.session.add(new_wallet)
        db.session.commit()
        return new_wallet.to_dict(), 201

# Endpoint ini akan dipanggil oleh service-transaction (nanti)
@internal_ns.route('/wallets/by-user/<int:user_id>')
class InternalWalletByUser(Resource):
    @internal_ns.doc('internal_get_wallet_by_user_id')
    @internal_ns.marshal_with(wallet_model)
    def get(self, user_id):
        """(R)EAD: (INTERNAL) Mendapatkan dompet berdasarkan user_id (aktif saja)"""
        wallet = Wallet.query.filter_by(user_id=user_id, status='active').first()
        if not wallet:
            api.abort(404, 'Dompet aktif tidak ditemukan.')
        return wallet.to_dict()

# Endpoint ini akan dipanggil oleh service-transaction (nanti)
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
        if wallet.status == 'closed':
            api.abort(403, 'Dompet sudah ditutup.')
            
        data = api.payload
        amount = Decimal(str(data['amount'])) 

        if data['type'] == 'debit':
            if wallet.balance < amount:
                api.abort(400, 'Saldo tidak mencukupi.')
            wallet.balance -= amount
        elif data['type'] == 'credit':
            wallet.balance += amount
        else:
            api.abort(400, 'Tipe harus "debit" atau "credit".')
            
        db.session.commit()
        return wallet.to_dict()

# Endpoint ini akan dipanggil oleh service-user saat tutup akun
@internal_ns.route('/wallets/by-user/<int:user_id>/close')
class InternalWalletClose(Resource):
    @internal_ns.doc('internal_close_wallet')
    def delete(self, user_id):
        """(D)ELETE: (INTERNAL) Menutup dompet (Soft Delete)"""
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            api.abort(404, 'Dompet tidak ditemukan.')
        
        # Logika Bisnis: Hanya boleh tutup akun jika saldo 0
        if wallet.balance > 0:
            api.abort(400, f'Dompet tidak bisa ditutup, sisa saldo: {wallet.balance}. Tarik saldo dulu.')
            
        wallet.status = 'closed'
        db.session.commit()
        return {'message': 'Dompet berhasil ditutup.'}, 200

# --- 6. BUAT TABEL & JALANKAN SERVER ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Port 3002 untuk service-wallet
    app.run(port=3002, debug=True)