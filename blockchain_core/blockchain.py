import time
import json
import hashlib
import logging  # <-- Import logging
from blockchain_core.block import Block
from blockchain_core.transaction import Transaction

logger = logging.getLogger(__name__)  # <-- Lấy logger cho module này


class Blockchain:
    def __init__(self, difficulty=2, initial_funder_address=None, initial_fund_amount=1000000):
        self.difficulty = difficulty
        self.pending_transactions = []
        self.initial_funder_address = initial_funder_address
        self.initial_fund_amount = initial_fund_amount
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        """Tạo Block đầu tiên (Genesis Block) của chuỗi"""
        genesis = Block(
            index=0,
            timestamp=time.time(),
            transactions=[Transaction(
                sender="SYSTEM_INITIAL_FUND",
                recipient=self.initial_funder_address,
                amount=self.initial_fund_amount,
                signature="SYSTEM_INITIAL_FUND"
            )],
            prev_hash="0",
            difficulty=self.difficulty
        )

        genesis.hash = genesis.mine_block()

        logger.info(f"Genesis Block được tạo: {genesis.hash[:10]}...")

        return genesis

    def get_last_block(self):
        return self.chain[-1]

    def add_transaction_to_pool(self, transaction):
        # Allow SYSTEM_INITIAL_FUND transaction to bypass full validation for simulation purposes
        if transaction.sender != "SYSTEM_INITIAL_FUND" and not transaction.is_valid():
            logger.warning(f"Giao dịch không hợp lệ từ {transaction.sender[:10]}... không được thêm vào pool.")
            return False
        self.pending_transactions.append(transaction)
        logger.info(
            f"Giao dịch từ {transaction.sender[:10]}... đến {transaction.receiver[:10]}... với số tiền {transaction.amount} đã được thêm vào pool. (Hiện có {len(self.pending_transactions)} giao dịch chờ xử lý)")
        return True

    def mine_pending_transactions(self, miner_address):
        if not self.pending_transactions:
            logger.info("Không có giao dịch nào đang chờ xử lý để đào.")
            return None

        # Thêm giao dịch thưởng cho thợ đào
        mining_reward_transaction = Transaction(
            sender="MINING_REWARD",
            recipient=miner_address,
            amount=10, # Giả sử phần thưởng là 10 đơn vị
            signature="MINING_REWARD_SIGNATURE",
            transaction_type="MINING_REWARD"
        )
        block_transactions = [mining_reward_transaction] + list(self.pending_transactions)
        # Clear pending transactions after they are included in a block
        self.pending_transactions = []

        new_block = Block(
            len(self.chain),
            time.time(),
            block_transactions,
            self.get_last_block().hash,
            self.difficulty
        )
        # ĐÀO BLOCK VÀ GÁN HASH
        new_block.hash = new_block.mine_block()
        self.chain.append(new_block)

        logger.info(
            f"Block mới #{new_block.index} đã được đào bởi {miner_address[:10]}... với hash: {new_block.hash[:10]}... Chứa {len(block_transactions)} giao dịch.")
        return new_block

    def is_chain_valid(self):
        logger.info("Bắt đầu kiểm tra tính hợp lệ của chuỗi...")
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.hash != current_block.calculate_hash():
                logger.error(
                    f"Hash không hợp lệ tại block {current_block.index}. Expected: {current_block.calculate_hash()[:10]}..., Got: {current_block.hash[:10]}...")
                return False

            if current_block.prev_hash != previous_block.hash:
                logger.error(
                    f"Prev_hash không khớp tại block {current_block.index}. Expected: {previous_block.hash[:10]}..., Got: {current_block.prev_hash[:10]}...")
                return False

            # Check proof-of-work (hash starts with correct prefix)
            prefix = '0' * current_block.difficulty
            if not current_block.hash.startswith(prefix):
                logger.error(
                    f"Proof-of-Work không hợp lệ tại block {current_block.index}. Hash không bắt đầu với '{prefix}'.")
                return False

            for tx in current_block.transactions:
                # Special handling for initial funding transaction during validation within block
                if tx.sender == "SYSTEM_INITIAL_FUND":
                    logger.debug(f"Bỏ qua xác thực giao dịch cấp quỹ ban đầu trong block {current_block.index}.")
                    continue
                if not tx.is_valid():
                    logger.error(f"Giao dịch không hợp lệ trong block {current_block.index}: {tx.to_dict()}")
                    return False
        logger.info("Kiểm tra chuỗi thành công: Blockchain hợp lệ.")
        return True

    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == address:
                    balance -= tx.amount
                elif tx.receiver == address:  # Use elif to avoid double counting if sender == receiver
                    balance += tx.amount
                elif tx.sender == "SYSTEM_INITIAL_FUND" and tx.receiver == address:  # Special case for initial funding
                    balance += tx.amount
        logger.debug(f"Số dư cho địa chỉ {address[:10]}... là: {balance}")
        return balance

    def save_to_file(self, filename):
        chain_data = [blk.to_dict() for blk in self.chain]
        chain_hash = self.calculate_chain_hash(chain_data)
        try:
            with open(filename, "w") as f:
                json.dump({"chain_data": chain_data, "chain_hash": chain_hash}, f, indent=4)
            logger.info(f"Blockchain đã lưu vào '{filename}'.")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi lưu blockchain vào '{filename}': {e}", exc_info=True)
            return False

    def calculate_chain_hash(self, chain_data):
        content = json.dumps(chain_data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def load_from_file(self, filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Không tìm thấy file blockchain '{filename}'.")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"Lỗi đọc JSON từ file blockchain '{filename}': {e}")
            return False

        chain_data = data.get("chain_data")
        stored_chain_hash = data.get("chain_hash")

        if not chain_data or not stored_chain_hash:
            logger.error("Lỗi: File không chứa dữ liệu blockchain hoặc chain_hash.")
            return False

        recalculated_chain_hash = self.calculate_chain_hash(chain_data)

        if recalculated_chain_hash != stored_chain_hash:
            logger.critical("CẢNH BÁO: Chain hash không khớp! Dữ liệu có thể đã bị thay đổi bên ngoài. KHÔNG TẢI.")
            return False

        loaded_chain = []
        for block_data in chain_data:
            block = Block.from_dict(block_data)
            # Need to re-calculate hash to verify proof-of-work on load
            recalculated_block_hash = block.calculate_hash()
            if recalculated_block_hash != block_data["hash"]:  # Compare with the hash saved in the dict
                logger.critical(f"CẢNH BÁO: Block {block.index} bị thay đổi! Hash không khớp sau khi tải.")
                return False

            # Also re-verify PoW prefix (Block.from_dict will re-mine if nonce is not passed, which is slow)
            prefix = '0' * block.difficulty
            if not block.hash.startswith(prefix):
                logger.critical(
                    f"CẢNH BÁO: Block {block.index} không đáp ứng PoW sau khi tải. Hash: {block.hash[:10]}...")
                return False

            loaded_chain.append(block)

        self.chain = loaded_chain
        logger.info(f"Đã tải blockchain từ '{filename}' và kiểm tra thành công.")
        # Re-check the full chain validity after loading
        if not self.is_chain_valid():
            logger.critical("Blockchain đã tải không hợp lệ sau khi kiểm tra đầy đủ!")
            return False
        return True