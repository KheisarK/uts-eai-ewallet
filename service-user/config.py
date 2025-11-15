# service-user/config.py

import os
from dotenv import load_dotenv

# Memuat variabel dari file .env (jika ada)
load_dotenv() 

class Config:
    # Ambil dari environment variable, atau gunakan nilai default (XAMPP)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL_USERS', 'mysql+pymysql://root:@localhost:3306/db_users')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Ambil dari environment variable, atau gunakan nilai default
    SECRET_KEY = os.getenv('SECRET_KEY', 'ini-rahasia-banget-dan-harus-diganti-nanti')