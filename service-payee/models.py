# service-payee/models.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Payee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Ini adalah ID user dari 'db_users'
    # Satu user bisa punya BANYAK payee, jadi ini BUKAN unique
    user_id = db.Column(db.Integer, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    # Ini bisa nomor HP (e-wallet) atau nomor rekening (bank)
    account_identifier = db.Column(db.String(100), nullable=False)
    provider = db.Column(db.String(50), nullable=True, default='E-Wallet') # Misal: 'E-Wallet', 'Bank BCA'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'account_identifier': self.account_identifier,
            'provider': self.provider
        }