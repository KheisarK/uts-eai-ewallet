# service-user/config.py

import os
from dotenv import load_dotenv

load_dotenv() 

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL_USERS', 'mysql+pymysql://root:@localhost:3306/db_users')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'ini-rahasia-banget-dan-harus-diganti-nanti')
    
    # --- TAMBAHKAN INI ---
    # Kita asumsikan service-wallet akan berjalan di port 3002
    WALLET_SERVICE_URL = os.getenv('WALLET_SERVICE_URL', 'http://localhost:3002')
    # -----------------------