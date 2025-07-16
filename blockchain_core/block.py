import time
import json
import hashlib
import base64
import logging # <-- Import logging

logger = logging.getLogger(__name__) # <-- Lấy logger cho module này

class Block:
    def __init__(self, index, timestamp, transactions, prev_hash, difficulty, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.prev_hash = prev_hash
        self.difficulty = difficulty
        self.nonce = nonce
        self.hash = None

    def calculate_hash(self):
        tx_str = json.dumps([tx.to_dict() for tx in self.transactions], sort_keys=True)
        content = f"{self.index}{self.timestamp}{tx_str}{self.prev_hash}{self.nonce}"
        return hashlib.sha256(content.encode()).hexdigest()

    def mine_block(self):
        prefix = '0' * self.difficulty
        logger.info(f"Bắt đầu đào block #{self.index} với độ khó {self.difficulty} (prefix: '{prefix}')...")
        while True:
            hash_attempt = self.calculate_hash()
            if hash_attempt.startswith(prefix):
                logger.info(f"Đã đào thành công block #{self.index} với nonce {self.nonce}, hash: {hash_attempt[:10]}...")
                return hash_attempt
            self.nonce += 1
            # logger.debug(f"Thử hash: {hash_attempt} (nonce: {self.nonce})") # Quá nhiều log cho DEBUG
            if self.nonce % 100000 == 0: # Log tiến độ đào
                logger.debug(f"Đang đào block #{self.index}, đã thử {self.nonce} nonce...")


    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(data):
        from blockchain_core.transaction import Transaction

        # Tạo danh sách các đối tượng Transaction từ dữ liệu
        transactions = [Transaction.from_dict(tx) for tx in data["transactions"]]

        # Tạo đối tượng Block và gán trực tiếp các giá trị từ dữ liệu
        block = Block(
            index=data["index"],
            transactions=transactions,
            prev_hash=data["prev_hash"],
            difficulty=data["difficulty"],
            timestamp=data["timestamp"],
            nonce=data["nonce"]
        )
        block.hash = data["hash"]
        logger.debug(f"Block #{block.index} được khởi tạo với hash: {block.hash[:10]}...")
        return block