import os
import datetime
from flask import Flask, request
from flask_restx import Api, Resource, fields
import jwt # PyJWT
import requests # Pastikan ini ada di requirements.txt
from flask_cors import CORS

# Import dari file kita sendiri
from config import Config
from models import db, bcrypt, User

# Hapus variabel global di sini, kita akan pakai app.config
# JWT_SECRET = os.getenv("JWT_SECRET_KEY") 
# JWT_ALGORITHM = "HS256"

# --- 1. INISIALISASI APLIKASI ---
app = Flask(__name__)
app.config.from_object(Config) # Muat konfigurasi dari config.py
CORS(app)

# Inisialisasi ekstensi DENGAN aplikasi
db.init_app(app)
bcrypt.init_app(app)
api = Api(app, 
          doc='/api-docs/', 
          title='User Service API', 
          description='Layanan untuk mengelola User, Registrasi, dan Login.')

# Fungsi ini untuk mengambil user_id dari token yang dikirim di header
def get_user_id_from_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        api.abort(401, 'Token otentikasi tidak ada (missing).')
    
    try:
        token = auth_header.split(" ")[1] # Ambil token dari "Bearer <token>"
        
        # --- PERBAIKAN MASALAH #2 ---
        # Gunakan 'JWT_SECRET_KEY' agar SAMA dengan fungsi Login
        data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
        # -----------------------------
        
        return data['user_id']
    except jwt.ExpiredSignatureError:
        api.abort(401, 'Token sudah kedaluwarsa (expired).')
    except Exception as e:
        api.abort(401, f'Token tidak valid (invalid). Error: {str(e)}')

# --- 2. MODEL API (Flask-RESTX untuk Validasi Input) ---

user_ns = api.namespace('users', description='Operasi Pengguna (Registrasi, Login, Profil)')

user_register_model = api.model('UserRegisterInput', {
    'name': fields.String(required=True, description='Nama lengkap'),
    'email': fields.String(required=True, description='Alamat email'),
    'password': fields.String(required=True, description='Password'),
    'phone_number': fields.String(required=True, description='Nomor HP')
})

# --- PERBAIKAN MASALAH #1 ---
# Ubah model ini agar mengharapkan 'phone' dari frontend
user_login_model = api.model('UserLoginInput', {
    'phone': fields.String(required=True, description='Nomor HP untuk login'),
    'password': fields.String(required=True, description='Password')
})
# -----------------------------

user_update_model = api.model('UserUpdateInput', {
    'name': fields.String(description='Nama lengkap baru'),
    'phone_number': fields.String(description='Nomor HP baru')
})

# --- 3. ENDPOINTS API (Logika Bisnis) ---

@user_ns.route('/register')
class UserRegister(Resource):
    @user_ns.expect(user_register_model)
    def post(self):
        """Membuat user baru (Registrasi)"""
        data = api.payload
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        new_user = User(
            name=data['name'],
            email=data['email'],
            password_hash=hashed_password,
            phone_number=data['phone_number']
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # --- Memanggil Service-Wallet (Logika ini sudah SANGAT BAGUS!) ---
            try:
                wallet_url = f"{app.config['WALLET_SERVICE_URL']}/internal/wallets"
                wallet_payload = {'user_id': new_user.id}
                response = requests.post(wallet_url, json=wallet_payload, timeout=5)
                response.raise_for_status() # Error jika status code bukan 2xx
                print(f"Wallet berhasil dibuat untuk user {new_user.id}")
            except requests.exceptions.RequestException as e:
                # Jika service wallet gagal, kita harus membatalkan registrasi user (Rollback)
                db.session.delete(new_user)
                db.session.commit()
                print(f"Gagal memanggil wallet-service: {e}")
                api.abort(503, 'Layanan Wallet tidak tersedia. Registrasi dibatalkan.')
            # ---------------------------------
            
            return {'message': 'User berhasil dibuat', 'user': new_user.to_dict()}, 201
        except Exception as e:
            db.session.rollback()
            if 'Duplicate entry' in str(e):
                return {'message': 'Gagal membuat user. Email atau Nomor HP sudah terdaftar.'}, 409
            return {'message': 'Gagal membuat user.', 'error': str(e)}, 400

@user_ns.route('/login')
class UserLogin(Resource):
    @user_ns.expect(user_login_model) # <-- Sekarang akan memvalidasi 'phone'
    def post(self):
        """Login user untuk mendapatkan JWT Token"""
        data = api.payload
        
        # --- PERBAIKAN MASALAH #1 (Lanjutan) ---
        # Logika ini sekarang cocok dengan model input ('phone')
        # dan model database ('phone_number')
        user = User.query.filter_by(phone_number=data['phone']).first()
        # -----------------------------------
        
        if user and user.status == 'active' and bcrypt.check_password_hash(user.password_hash, data['password']):
            token = jwt.encode(
                {
                    'user_id': user.id,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                },
                app.config['JWT_SECRET_KEY'], # <-- Kunci A (Benar)
                algorithm='HS256'
            )
            return {'message': 'Login berhasil', 'token': token}, 200
        else:
            return {'message': 'Login gagal. Nomor HP, password salah, atau akun ditutup.'}, 401


@user_ns.route('/me')
class MyProfile(Resource):
    
    @user_ns.doc('get_my_profile', security='apiKey')
    def get(self):
        """(R)EAD: Mendapatkan profil saya sendiri (Butuh Token)"""
        try:
            # Panggil helper (yang sudah diperbaiki) untuk dapat ID user dari token
            user_id = get_user_id_from_token() 
            user = User.query.get(user_id)
            if not user or user.status == 'closed':
                return {'message': 'User tidak ditemukan atau ditutup'}, 404
            return user.to_dict(), 200
        except Exception as e:
            return {'message': str(e)}, 401

    @user_ns.doc('update_my_profile', security='apiKey')
    @user_ns.expect(user_update_model)
    def put(self):
        """(U)PDATE: Memperbarui profil saya (Butuh Token)"""
        try:
            user_id = get_user_id_from_token()
            user = User.query.get(user_id)
            if not user or user.status == 'closed':
                return {'message': 'User tidak ditemukan atau ditutup'}, 404
            
            data = api.payload
            
            if 'phone_number' in data:
                existing = User.query.filter(User.phone_number == data['phone_number'], User.id != user_id).first()
                if existing:
                    return {'message': 'Nomor HP sudah dipakai user lain.'}, 400
                user.phone_number = data['phone_number']

            if 'name' in data:
                user.name = data['name']
            
            db.session.commit()
            return {'message': 'Profil berhasil diperbarui', 'user': user.to_dict()}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 401

    @user_ns.doc('delete_my_profile', security='apiKey')
    def delete(self):
        """(D)ELETE: Menutup akun saya (Soft Delete) (Butuh Token)"""
        try:
            user_id = get_user_id_from_token()
            user = User.query.get(user_id)
            if not user or user.status == 'closed':
                return {'message': 'User tidak ditemukan atau sudah ditutup'}, 404
            
            # --- Memanggil Service-Wallet untuk menutup wallet (Logika ini sudah SANGAT BAGUS!) ---
            try:
                wallet_url = f"{app.config['WALLET_SERVICE_URL']}/internal/by-user/{user_id}/close"
                response = requests.delete(wallet_url, timeout=5)
                print(f"Response dari wallet-service: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Gagal memanggil wallet-service saat tutup akun: {e}")
            # ----------------------------------------------------

            user.status = 'closed'
            db.session.commit()
            return {'message': f'User {user.name} berhasil ditutup (soft delete).'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 401

@user_ns.route('/internal/by-phone/<string:phone>')
class UserInternalByPhone(Resource):
    def get(self, phone):
        """(INTERNAL) Mendapatkan data user berdasarkan nomor HP"""
        
        # Logika ini sudah BENAR
        user = User.query.filter_by(phone_number=phone, status='active').first()
        
        if user:
            return user.to_dict(), 200
        else:
            return {'message': 'User tidak ditemukan atau akun tidak aktif'}, 404
            
# --- 4. BUAT TABEL & JALANKAN SERVER ---
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(port=3001, debug=True)