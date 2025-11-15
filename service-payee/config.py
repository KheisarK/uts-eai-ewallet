# service-payee/config.py

import os
from dotenv import load_dotenv

load_dotenv() 

class Config:
    # Koneksi ke database 'db_payees' Anda di XAMPP
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL_PAYEES', 'mysql+pymysql://root:@localhost:3306/db_payees')
    SQLALCHEMY_TRACK_MODIFICATIONS = False