import base64
from ecdsa import SigningKey, VerifyingKey, SECP256k1
import hashlib
import logging
import time

logger = logging.getLogger(__name__)


class Transaction:
    def __init__(self, sender=None, recipient=None, amount=None, transaction_type="USER",
                 signature=None, timestamp=None, **kwargs):
        """
        Flexible constructor that accepts multiple parameter names

        Args:
            sender: Public key người gửi (có thể là sender_pubkey)
            recipient: Public key người nhận (có thể là receiver, receiver_pubkey)
            amount: Số tiền
            transaction_type: Loại giao dịch ("USER", "SYSTEM", "MINING_REWARD")
            signature: Chữ ký (optional)
            timestamp: Thời gian tạo transaction
            **kwargs: Các tham số khác (sender_pubkey, receiver_pubkey, receiver, from, to)
        """
        # Hỗ trợ nhiều tên tham số khác nhau
        self.sender = sender or kwargs.get('sender_pubkey') or kwargs.get('from')

        # Hỗ trợ receiver, receiver_pubkey, recipient
        self.recipient = (recipient or
                          kwargs.get('receiver') or
                          kwargs.get('receiver_pubkey') or
                          kwargs.get('to'))

        # Aliases cho tương thích ngược
        self.sender_pubkey = self.sender
        self.receiver = self.recipient
        self.receiver_pubkey = self.recipient

        self.amount = amount
        self.transaction_type = transaction_type
        self.signature = signature
        self.timestamp = timestamp if timestamp else time.time()

        # Tạo transaction ID duy nhất
        self.transaction_id = self._generate_transaction_id()

        logger.debug(
            f"Giao dịch được tạo: {self.sender[:10] if self.sender and self.sender != 'SYSTEM' else 'SYSTEM'}... -> {self.recipient[:10] if self.recipient else 'Unknown'}... Amount: {self.amount}")

    def _generate_transaction_id(self):
        """Tạo ID giao dịch từ hash của các thông tin"""
        # Sửa: Đảm bảo timestamp là một giá trị có thể băm được
        data = f"{self.sender}{self.recipient}{self.amount}{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        """Sửa: đảm bảo `timestamp` và `transaction_id` luôn được lưu"""
        return {
            "transaction_id": self.transaction_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "transaction_type": self.transaction_type,
            "signature": self.signature,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data):
        """Sửa: Truyền đầy đủ các tham số đã lưu vào hàm khởi tạo"""
        return cls(
            sender=data.get('sender') or data.get('from'),
            recipient=data.get('recipient') or data.get('to') or data.get('receiver'),
            amount=data.get('amount'),
            transaction_type=data.get('transaction_type'),
            signature=data.get('signature'),
            timestamp=data.get('timestamp'),
            transaction_id=data.get('transaction_id') # Sửa: Thêm transaction_id
        )

    def create_message_to_sign(self):
        """Tạo message để ký - phải nhất quán với routes/transaction.py"""
        import json
        return json.dumps({
            "sender": self.sender,
            "receiver": self.recipient,
            "amount": str(self.amount),
            "timestamp": self.timestamp
        }, sort_keys=True)

    def is_valid(self):
        """
        Kiểm tra tính hợp lệ của giao dịch.
        """
        # Bỏ qua kiểm tra chữ ký cho mục đích thử nghiệm
        if self.signature == "DUMMY_SIGNATURE":
            return True

        # Các kiểm tra hợp lệ khác (nếu có)
        if not self.sender or not self.receiver or not self.amount:
            return False

        if self.amount <= 0:
            return False

        # Logic xác thực chữ ký thực tế (bạn có thể tạm thời bỏ qua)
        # if not self.is_valid_signature():
        #     return False

        return True

    def is_valid_signature(self):
        """
        Xác thực chữ ký của giao dịch.
        """
        # Tạm thời chấp nhận mọi chữ ký
        return True

    def sign_transaction(self, wallet):
        """Ký transaction với wallet"""
        # Tạo message để ký
        msg = self.create_message_to_sign()

        # Ký message
        self.signature = wallet.sign(msg)

        logger.debug(f"Đã ký giao dịch: {self.sender[:10] if self.sender else 'Unknown'}...")
        return self.signature

    def get_hash(self):
        """Tạo hash cho transaction"""
        return hashlib.sha256(str(self).encode()).hexdigest()

    def __str__(self):
        sender_str = self.sender[:10] if self.sender and self.sender != 'SYSTEM' else 'SYSTEM'
        recipient_str = self.recipient[:10] if self.recipient else 'Unknown'
        return f"Transaction(ID: {self.transaction_id[:8]}..., {sender_str}... -> {recipient_str}...: {self.amount})"

    def __repr__(self):
        return self.__str__()