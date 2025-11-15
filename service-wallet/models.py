# service-wallet/models.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Wallet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # user_id ini adalah Foreign Key 'palsu'. Ini adalah ID user dari 'db_users'.
    # Kita buat unique=True karena 1 user hanya boleh punya 1 dompet.
    user_id = db.Column(db.Integer, unique=True, nullable=False) 
    balance = db.Column(db.Numeric(15, 2), nullable=False, default=0.00)
    label = db.Column(db.String(100), nullable=True, default='Dompet Utama')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            # Ubah Decimal jadi string agar aman di JSON
            'balance': str(self.balance), 
            'label': self.label
        }