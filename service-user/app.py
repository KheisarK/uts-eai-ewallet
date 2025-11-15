import os
import datetime
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from flask_bcrypt import Bcrypt
import jwt # PyJWT

# --- 1. INISIALISASI & KONFIGURASI ---
app = Flask(__name__)
CORS(app)

# --- KONFIGURASI XAMPP MYSQL ---
# Ganti 'root' jika user Anda berbeda.
# KOSONGKAN 'password' jika XAMPP Anda tidak pakai password (default).
# Pastikan nama database 'db_users' sesuai dengan yang Anda buat.
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost:3306/db_users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Kunci rahasia untuk JWT. Ganti ini di produksi.
app.config['SECRET_KEY'] = 'ini-rahasia-banget-dan-harus-diganti-nanti'

# Inisialisasi ekstensi
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
api = Api(app, 
          doc='/api-docs/', 
          title='User Service API', 
          description='Layanan untuk mengelola User, Registrasi, dan Login.')

# --- 2. MODEL DATABASE (SQLAlchemy) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone_number': self.phone_number
        }

# --- 3. MODEL API (Flask-RESTX untuk Validasi Input) ---
user_ns = api.namespace('users', description='Operasi Registrasi dan Login')

# Model untuk input registrasi
user_register_model = api.model('UserRegisterInput', {
    'name': fields.String(required=True, description='Nama lengkap'),
    'email': fields.String(required=True, description='Alamat email'),
    'password': fields.String(required=True, description='Password'),
    'phone_number': fields.String(required=True, description='Nomor HP (cth: 0812...)')
})

# Model untuk input login
user_login_model = api.model('UserLoginInput', {
    'email': fields.String(required=True, description='Alamat email'),
    'password': fields.String(required=True, description='Password')
})

# --- 4. ENDPOINTS API ---

# Endpoint untuk Registrasi
@user_ns.route('/register')
class UserRegister(Resource):
    @user_ns.expect(user_register_model)
    def post(self):
        """Membuat user baru (Registrasi)"""
        data = api.payload
        
        # Hash password sebelum disimpan
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
            
            # (Tambahan - Alur Komunikasi Antar Layanan)
            # Di sini kita nanti akan memanggil service-wallet untuk membuatkan dompet
            # Untuk sekarang, kita biarkan dulu.
            
            return {'message': 'User berhasil dibuat', 'user': new_user.to_dict()}, 201
        except Exception as e:
            db.session.rollback()
            return {'message': 'Gagal membuat user. Email atau No HP mungkin sudah ada.', 'error': str(e)}, 400

# Endpoint untuk Login
@user_ns.route('/login')
class UserLogin(Resource):
    @user_ns.expect(user_login_model)
    def post(self):
        """Login user untuk mendapatkan JWT Token"""
        data = api.payload
        user = User.query.filter_by(email=data['email']).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, data['password']):
            # Password cocok, buat token
            token = jwt.encode(
                {
                    'user_id': user.id,
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24) # Token berlaku 24 jam
                },
                app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            return {'message': 'Login berhasil', 'token': token}, 200
        else:
            return {'message': 'Login gagal. Email atau password salah.'}, 401

# Endpoint INTERNAL (Untuk dipanggil oleh service lain, BUKAN oleh frontend)
# Ini adalah endpoint yang akan dipanggil oleh 'service-transaction'
@user_ns.route('/internal/by-phone/<string:phone>')
class UserInternalByPhone(Resource):
    def get(self, phone):
        """(INTERNAL) Mendapatkan data user berdasarkan nomor HP"""
        user = User.query.filter_by(phone_number=phone).first()
        if user:
            return user.to_dict(), 200
        else:
            return {'message': 'User tidak ditemukan'}, 404

# --- 5. BUAT TABEL & JALANKAN SERVER ---
with app.app_context():
    # Ini akan membuat tabel 'user' di database 'db_users'
    # jika tabelnya belum ada.
    db.create_all()

if __name__ == '__main__':
    # Port 3001 untuk service-user
    app.run(port=3001, debug=True)