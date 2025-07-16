import base64
import hashlib
import json
from ecdsa import SigningKey, VerifyingKey, SECP256k1
import os
import logging

logger = logging.getLogger(__name__)


class Wallet:
    def __init__(self, private_key_str=None):
        if private_key_str:
            self.private_key = SigningKey.from_string(base64.b64decode(private_key_str), curve=SECP256k1)
            logger.debug("Ví được khởi tạo từ private key đã cho.")
        else:
            self.private_key = SigningKey.generate(curve=SECP256k1)
            logger.debug("Ví mới được tạo ngẫu nhiên.")

        self.public_key = self.private_key.get_verifying_key()
        self.public_key_pem = self.public_key.to_pem().decode()
        self.address = self.get_address()

        logger.debug(f"Địa chỉ ví: {self.address[:10]}...")

    def get_private_key(self):
        return base64.b64encode(self.private_key.to_string()).decode()

    def get_public_key(self):
        return base64.b64encode(self.public_key.to_string()).decode()

    def sign(self, message):
        if isinstance(message, str):
            message = message.encode('utf-8')
        signature = base64.b64encode(self.private_key.sign(message)).decode()
        logger.debug(f"Đã ký tin nhắn với ví {self.address[:10]}... Chữ ký: {signature[:10]}...")
        return signature

    @staticmethod
    def verify(public_key_str, message, signature_str):
        try:
            logger.debug(f"Verify - Public key: {public_key_str[:20]}...")
            logger.debug(f"Verify - Message: {str(message)[:50]}...")
            logger.debug(f"Verify - Signature: {signature_str[:20]}...")

            vk = VerifyingKey.from_string(base64.b64decode(public_key_str), curve=SECP256k1)

            if isinstance(message, str):
                message = message.encode('utf-8')

            is_valid = vk.verify(base64.b64decode(signature_str), message)
            logger.debug(f"Verify result: {is_valid}")

            if not is_valid:
                logger.warning(f"Xác minh chữ ký thất bại cho Public Key {public_key_str[:10]}...")

            return is_valid

        except Exception as e:
            logger.error(f"Lỗi khi xác minh chữ ký: {e}", exc_info=True)
            return False

    def get_address(self):
        pubkey_bytes = base64.b64decode(self.get_public_key())
        sha256_hash = hashlib.sha256(pubkey_bytes).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        address = ripemd160.hexdigest()
        logger.debug(f"Địa chỉ RIPEMD160: {address[:10]}...")
        return address

    def save_to_file(self, filename):
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        with open(filename, "w") as f:
            json.dump({"private_key": self.get_private_key()}, f)
        logger.info(f"Ví đã được lưu vào '{filename}'.")

    @staticmethod
    def load_from_file(filename):
        try:
            with open(filename, "r") as f:
                data = json.load(f)
            wallet = Wallet(data["private_key"])
            logger.info(f"Ví đã được tải từ '{filename}'.")
            return wallet
        except FileNotFoundError:
            logger.error(f"File ví '{filename}' không tìm thấy.")
            return None
        except Exception as e:
            logger.error(f"Lỗi khi tải ví từ '{filename}': {e}", exc_info=True)
            return None

    def test_signature(self):
        test_message = "test message"
        signature = self.sign(test_message)
        is_valid = Wallet.verify(self.get_public_key(), test_message, signature)
        logger.info(f"Test signature: {is_valid}")
        return is_valid

    def to_dict(self):
        return {
            "address": self.address,
            "public_key": self.get_public_key(),
            "private_key": self.get_private_key(),
        }
