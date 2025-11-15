# service-wallet/models.py

from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal # Wajib untuk uang

db = SQLAlchemy()

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Ini adalah ID user dari 'db_users'
    user_id = db.Column(db.Integer, unique=True, nullable=False) 
    # Gunakan Numeric/Decimal untuk uang, BUKAN float
    balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    label = db.Column(db.String(100), nullable=True, default='Dompet Utama')
    
    # --- TAMBAHAN BARU (Sesuai service-user) ---
    status = db.Column(db.String(20), nullable=False, default='active') # (active, closed)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'balance': str(self.balance), # Selalu kirim uang sebagai string di JSON
            'label': self.label,
            'status': self.status
        }