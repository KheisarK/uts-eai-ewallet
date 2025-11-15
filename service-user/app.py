# service-user/app.py

import os
import datetime
from flask import Flask, request
from flask_restx import Api, Resource, fields
import jwt # PyJWT

# Import dari file kita sendiri
from config import Config
from models import db, bcrypt, User

# --- 1. INISIALISASI APLIKASI ---
app = Flask(__name__)
app.config.from_object(Config) # Muat konfigurasi dari config.py

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
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        return data['user_id']
    except jwt.ExpiredSignatureError:
        api.abort(401, 'Token sudah kedaluwarsa (expired).')
    except Exception as e:
        api.abort(401, f'Token tidak valid (invalid). Error: {str(e)}')

# --- 2. MODEL API (Flask-RESTX untuk Validasi Input) ---
user_ns = api.namespace('users', description='Operasi Registrasi dan Login')

user_register_model = api.model('UserRegisterInput', {
    'name': fields.String(required=True, description='Nama lengkap'),
    'email': fields.String(required=True, description='Alamat email'),
    'password': fields.String(required=True, description='Password'),
    'phone_number': fields.String(required=True, description='Nomor HP')
})

user_login_model = api.model('UserLoginInput', {
    'email': fields.String(required=True, description='Alamat email'),
    'password': fields.String(required=True, description='Password')
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
            
            # TODO (Nanti): Panggil service-wallet untuk buat dompet
            # requests.post('http://localhost:3002/internal/wallets', json={'user_id': new_user.id})
            
            return {'message': 'User berhasil dibuat', 'user': new_user.to_dict()}, 201
        except Exception as e:
            db.session.rollback()
            return {'message': 'Gagal membuat user. Email atau No HP mungkin sudah ada.', 'error': str(e)}, 400

@user_ns.route('/login')
class UserLogin(Resource):
    @user_ns.expect(user_login_model)
    def post(self):
        """Login user untuk mendapatkan JWT Token"""
        data = api.payload
        user = User.query.filter_by(email=data['email']).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, data['password']):
            token = jwt.encode(
                {
                    'user_id': user.id,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
                },
                app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            return {'message': 'Login berhasil', 'token': token}, 200
        else:
            return {'message': 'Login gagal. Email atau password salah.'}, 401

# Model untuk update profil (tidak wajib ganti semua)
user_update_model = api.model('UserUpdateInput', {
    'name': fields.String(description='Nama lengkap baru'),
    'phone_number': fields.String(description='Nomor HP baru')
    # Email & Password biasanya punya endpoint khusus karena lebih sensitif
})

# Namespace baru untuk operasi yang butuh login
me_ns = api.namespace('me', description='Operasi Profil Saya (Butuh Login/Token)')

@me_ns.route('/')
class MyProfile(Resource):
    
    @me_ns.doc('get_my_profile', security='apiKey') # 'security' menandakan ini butuh token
    def get(self):
        """(R)EAD: Mendapatkan profil saya sendiri"""
        try:
            # Panggil helper untuk dapat ID user dari token
            user_id = get_user_id_from_token() 
            user = User.query.get(user_id)
            if not user:
                return {'message': 'User tidak ditemukan'}, 404
            return user.to_dict(), 200
        except Exception as e:
            # Ini akan menangkap error 401 dari helper
            return {'message': str(e)}, 401

    @me_ns.doc('update_my_profile', security='apiKey')
    @me_ns.expect(user_update_model)
    def put(self):
        """(U)PDATE: Memperbarui profil saya (Nama atau No. HP)"""
        try:
            user_id = get_user_id_from_token()
            user = User.query.get(user_id)
            if not user:
                return {'message': 'User tidak ditemukan'}, 404
            
            data = api.payload
            
            # Cek duplikasi no. HP jika diubah
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

    @me_ns.doc('delete_my_profile', security='apiKey')
    def delete(self):
        """(D)ELETE: Menutup akun saya"""
        try:
            user_id = get_user_id_from_token()
            user = User.query.get(user_id)
            if not user:
                return {'message': 'User tidak ditemukan'}, 404
            
            # TODO (Nanti): Panggil service-wallet & service-payee untuk
            # menghapus data terkait sebelum user dihapus total.
            
            # Untuk sekarang, kita hapus langsung
            db.session.delete(user)
            db.session.commit()
            return {'message': f'User {user.name} berhasil dihapus.'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': str(e)}, 401

@user_ns.route('/internal/by-phone/<string:phone>')
class UserInternalByPhone(Resource):
    def get(self, phone):
        """(INTERNAL) Mendapatkan data user berdasarkan nomor HP"""
        user = User.query.filter_by(phone_number=phone).first()
        if user:
            return user.to_dict(), 200
        else:
            return {'message': 'User tidak ditemukan'}, 404

# --- 4. BUAT TABEL & JALANKAN SERVER ---
with app.app_context():
    # Buat tabel jika belum ada
    db.create_all()

if __name__ == '__main__':
    # Port 3001 untuk service-user
    app.run(port=3001, debug=True)