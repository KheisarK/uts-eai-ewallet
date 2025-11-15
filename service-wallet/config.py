# service-wallet/config.py

import os
from dotenv import load_dotenv

load_dotenv() 

class Config:
    # Koneksi ke database 'db_wallets' Anda di XAMPP
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL_WALLETS', 'mysql+pymysql://root:@localhost:3306/db_wallets')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Kita tidak perlu SECRET_KEY di sini karena service ini tidak membuat JWT