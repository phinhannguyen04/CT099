from backend.db.database import db
from datetime import datetime


class TransactionDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blockchain_tx_id = db.Column(db.String(256), unique=False, nullable=True) # Hash của transaction nếu có
    sender_username = db.Column(db.String(80), nullable=False)
    receiver_username = db.Column(db.String(80), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(50), default="Pending") # Pending, Confirmed, Failed, Refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TxDetail {self.id} {self.sender_username} -> {self.receiver_username}>'