# service-transaction/models.py

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ID dompet PENGIRIM (dari service-wallet)
    sender_wallet_id = db.Column(db.Integer, nullable=False, index=True)
    # ID dompet PENERIMA (dari service-wallet)
    receiver_wallet_id = db.Column(db.Integer, nullable=False, index=True)
    
    # Jenis transaksi
    type = db.Column(db.String(20), nullable=False, default='transfer') # 'transfer', 'topup', 'payment'
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    # Status transaksi
    status = db.Column(db.String(20), nullable=False, default='success') # 'pending', 'success', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_wallet_id': self.sender_wallet_id,
            'receiver_wallet_id': self.receiver_wallet_id,
            'type': self.type,
            'amount': str(self.amount),
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }