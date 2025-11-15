# service-transaction/config.py

import os
from dotenv import load_dotenv

load_dotenv() 

class Config:
    # Koneksi ke database 'db_transactions' Anda di XAMPP
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL_TRANSACTIONS', 'mysql+pymysql://root:@localhost:3306/db_transactions')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- URL LAYANAN LAIN ---
    # URL ini digunakan untuk memanggil service user dan wallet
    USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://localhost:3001')
    WALLET_SERVICE_URL = os.getenv('WALLET_SERVICE_URL', 'http://localhost:3002')