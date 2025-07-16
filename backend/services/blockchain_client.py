import hashlib
import json
import logging
import os
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import base64

client_logger = logging.getLogger(__name__)

class BlockchainClient:
    def __init__(self, node_url=None):
        self.node_url = node_url or os.getenv("BLOCKCHAIN_NODE_URL")
        if not self.node_url:
            raise ValueError("BLOCKCHAIN_NODE_URL không được cấu hình.")

        client_logger.info(f"Blockchain Client được khởi tạo, kết nối tới Node: {self.node_url}")

    def sign_transaction_with_private_key(self, private_key_pem, message):
        """
        Ký giao dịch với private key

        Args:
            private_key_pem (str): Private key ở định dạng PEM
            message (str): Message cần ký

        Returns:
            tuple: (signature_b64, error_message) - signature được encode base64 và error
        """
        try:
            # Load private key từ PEM format
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )

            # Tạo hash của message
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()

            # Ký message hash
            signature = private_key.sign(
                message_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            # Encode signature thành base64 để dễ truyền tải
            signature_b64 = base64.b64encode(signature).decode('utf-8')

            client_logger.info(f"Đã ký thành công message với độ dài: {len(message)} chars")
            return signature_b64, None

        except Exception as e:
            client_logger.error(f"Lỗi khi ký giao dịch: {str(e)}")
            return None, f"Lỗi khi ký giao dịch: {str(e)}"

    def verify_signature(self, public_key_pem, message, signature_b64):
        """
        Verify signature với public key

        Args:
            public_key_pem (str): Public key ở định dạng PEM
            message (str): Message gốc
            signature_b64 (str): Signature được encode base64

        Returns:
            tuple: (is_valid, error_message) - True/False và error message
        """
        try:
            # Load public key từ PEM format
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )

            # Decode signature từ base64
            signature = base64.b64decode(signature_b64)

            # Tạo hash của message
            message_hash = hashlib.sha256(message.encode('utf-8')).digest()

            # Verify signature
            public_key.verify(
                signature,
                message_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            client_logger.info("Signature verification successful")
            return True, None

        except Exception as e:
            client_logger.error(f"Lỗi khi verify signature: {str(e)}")
            return False, f"Lỗi khi verify signature: {str(e)}"

    def sign_transaction_message(self, sender_pubkey, receiver_pubkey, amount, timestamp=None):
        """
        Tạo message chuẩn để ký cho giao dịch

        Args:
            sender_pubkey (str): Public key của người gửi
            receiver_pubkey (str): Public key của người nhận
            amount (float): Số tiền
            timestamp (int, optional): Timestamp. Nếu None sẽ tự động tạo

        Returns:
            str: Message được format chuẩn
        """
        import time

        if timestamp is None:
            timestamp = int(time.time())

        message_data = {
            "sender": sender_pubkey,
            "receiver": receiver_pubkey,
            "amount": str(amount),
            "timestamp": timestamp
        }

        # Sắp xếp keys để đảm bảo message luôn consistent
        return json.dumps(message_data, sort_keys=True)

    def send_transaction(self, sender_pubkey, receiver_pubkey, amount, signature, timestamp=None):
        """
        Gửi giao dịch đến blockchain node (tương thích với API hiện tại)

        Args:
            sender_pubkey (str): Public key của người gửi
            receiver_pubkey (str): Public key của người nhận
            amount (float): Số tiền
            signature (str): Signature đã ký
            timestamp (int, optional): Timestamp (optional)

        Returns:
            tuple: (response_data, error_message)
        """
        tx_data = {
            "sender": sender_pubkey,
            "receiver": receiver_pubkey,
            "amount": amount,
            "signature": signature,
        }

        # Kiểm tra timestamp và thêm vào nếu có giá trị
        if timestamp:
            tx_data["timestamp"] = timestamp

        try:
            response = requests.post(f'{self.node_url}/transactions/new', json=tx_data)

            # Log phản hồi từ Node để dễ debug
            client_logger.info(f"Phản hồi từ Node: Status Code={response.status_code}, Body={response.text}")

            response.raise_for_status()  # Ném lỗi HTTP nếu có

            # Nếu thành công
            response_data = response.json()
            client_logger.info(f"Đã gửi giao dịch tới Node: {response_data.get('message')}")
            return response_data, None

        except requests.exceptions.HTTPError as http_err:
            # Bắt lỗi HTTP cụ thể
            try:
                error_details = response.json().get('error', response.text)
            except json.JSONDecodeError:
                error_details = response.text

            client_logger.error(f"Lỗi HTTP khi gửi giao dịch tới Node ({http_err}): {error_details}")
            return None, f"Lỗi HTTP từ Node: {error_details}"

        except requests.exceptions.RequestException as e:
            # Bắt các lỗi khác như lỗi kết nối
            client_logger.error(f"Lỗi kết nối tới Blockchain Node: {e}")
            return None, f"Lỗi kết nối: {e}"

    def get_balance(self, address):
        """
        Lấy số dư của một địa chỉ (sử dụng logic hiện tại)
        """
        try:
            # Lấy toàn bộ chain
            chain_data, chain_error = self.get_chain()
            if chain_error:
                return None, chain_error

            balance = 0

            # Duyệt qua tất cả các block trong chain
            for block in chain_data.get('chain', []):
                for transaction in block.get('transactions', []):
                    # Nếu là người nhận
                    if transaction.get('recipient') == address:
                        balance += transaction.get('amount', 0)
                    # Nếu là người gửi (trừ SYSTEM_INITIAL_FUND)
                    elif transaction.get('sender') == address and transaction.get('sender') != 'SYSTEM_INITIAL_FUND':
                        balance -= transaction.get('amount', 0)

            client_logger.info(f"Calculated balance for {address}: {balance}")
            return balance, None

        except Exception as e:
            client_logger.error(f"Lỗi khi tính balance cho địa chỉ {address}: {e}")
            return None, f"Lỗi khi tính balance: {str(e)}"

    def get_chain(self):
        """
        Lấy toàn bộ blockchain chain (method hiện tại)
        """
        try:
            response = requests.get(f'{self.node_url}/chain')
            response.raise_for_status()
            return response.json(), None
        except requests.exceptions.RequestException as e:
            client_logger.error(f"Lỗi khi lấy chuỗi từ Blockchain Node: {e}")
            return None, f"Lỗi kết nối hoặc phản hồi không hợp lệ: {e}"

    def mine_block(self):
        """
        Kích hoạt đào block (method hiện tại)
        """
        try:
            response = requests.get(f'{self.node_url}/mine')
            response.raise_for_status()
            client_logger.info(f"Đã kích hoạt đào block trên Node: {response.json().get('message')}")
            return response.json(), None
        except requests.exceptions.RequestException as e:
            client_logger.error(f"Lỗi khi kích hoạt đào block trên Node: {e}")
            return None, f"Lỗi kết nối hoặc phản hồi không hợp lệ: {e}"

