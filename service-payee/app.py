# service-payee/app.py

from flask import Flask, request
from flask_restx import Api, Resource, fields

# Import dari file kita sendiri
from config import Config
from models import db, Payee

# --- 1. INISIALISASI APLIKASI ---
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
api = Api(app, 
          doc='/api-docs/', 
          title='Payee Service API', 
          description='Layanan untuk mengelola Daftar Penerima (Payees).',
          security='apiKey') # Menandakan semua butuh proteksi

# --- 2. MODEL API (Flask-RESTX) ---
payee_ns = api.namespace('payees', description='Operasi CRUD Daftar Penerima (Butuh Token)')

# Model untuk output
payee_model = api.model('Payee', {
    'id': fields.Integer,
    'user_id': fields.Integer,
    'name': fields.String,
    'account_identifier': fields.String(description='No. HP atau No. Rekening'),
    'provider': fields.String(description='Misal: E-Wallet, Bank BCA')
})

# Model untuk input (tanpa ID)
payee_input_model = api.model('PayeeInput', {
    'name': fields.String(required=True, description='Nama penerima'),
    'account_identifier': fields.String(required=True, description='No. HP atau No. Rekening'),
    'provider': fields.String(description='Misal: E-Wallet, Bank BCA')
})

# --- 3. HELPER (Ambil User ID dari Header) ---
def get_user_id_from_header():
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        api.abort(401, 'Header X-User-Id tidak ada. Request harus melalui API Gateway.')
    return int(user_id)

# --- 4. ENDPOINTS CRUD (Semua terproteksi) ---

@payee_ns.route('/')
class PayeeList(Resource):
    @payee_ns.doc('get_my_payees', security='apiKey')
    @payee_ns.marshal_list_with(payee_model)
    def get(self):
        """(R)EAD: Mendapatkan SEMUA daftar penerima milik saya"""
        user_id = get_user_id_from_header()
        payees = Payee.query.filter_by(user_id=user_id).all()
        return [p.to_dict() for p in payees]

    @payee_ns.doc('create_my_payee', security='apiKey')
    @payee_ns.expect(payee_input_model)
    @payee_ns.marshal_with(payee_model, code=201)
    def post(self):
        """(C)REATE: Membuat penerima baru untuk akun saya"""
        user_id = get_user_id_from_header()
        data = api.payload
        
        new_payee = Payee(
            user_id=user_id,
            name=data['name'],
            account_identifier=data['account_identifier'],
            provider=data.get('provider', 'E-Wallet')
        )
        db.session.add(new_payee)
        db.session.commit()
        return new_payee.to_dict(), 201

@payee_ns.route('/<int:id>')
@payee_ns.param('id', 'ID unik penerima')
class PayeeResource(Resource):
    @payee_ns.doc('get_my_payee_by_id', security='apiKey')
    @payee_ns.marshal_with(payee_model)
    def get(self, id):
        """(R)EAD: Mendapatkan detail 1 penerima (spesifik)"""
        user_id = get_user_id_from_header()
        payee = Payee.query.get(id)
        if not payee:
            api.abort(404, 'Penerima tidak ditemukan.')
        if payee.user_id != user_id:
            api.abort(403, 'Akses ditolak. Ini bukan penerima milik Anda.')
        return payee.to_dict()

    @payee_ns.doc('update_my_payee', security='apiKey')
    @payee_ns.expect(payee_input_model)
    @payee_ns.marshal_with(payee_model)
    def put(self, id):
        """(U)PDATE: Memperbarui data 1 penerima"""
        user_id = get_user_id_from_header()
        payee = Payee.query.get(id)
        if not payee:
            api.abort(404, 'Penerima tidak ditemukan.')
        if payee.user_id != user_id:
            api.abort(403, 'Akses ditolak. Ini bukan penerima milik Anda.')
            
        data = api.payload
        payee.name = data['name']
        payee.account_identifier = data['account_identifier']
        payee.provider = data.get('provider', payee.provider)
        
        db.session.commit()
        return payee.to_dict()

    @payee_ns.doc('delete_my_payee', security='apiKey')
    @payee_ns.response(200, 'Penerima berhasil dihapus')
    def delete(self, id):
        """(D)ELETE: Menghapus 1 penerima"""
        user_id = get_user_id_from_header()
        payee = Payee.query.get(id)
        if not payee:
            api.abort(404, 'Penerima tidak ditemukan.')
        if payee.user_id != user_id:
            api.abort(403, 'Akses ditolak. Ini bukan penerima milik Anda.')
            
        db.session.delete(payee)
        db.session.commit()
        return {'message': 'Penerima berhasil dihapus.'}, 200

# --- 5. BUAT TABEL & JALANKAN SERVER ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Port 3004 untuk service-payee
    app.run(port=3004, debug=True)