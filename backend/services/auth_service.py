from backend.models.user import User
from backend.db.database import db
from blockchain_core.wallet import Wallet # Import Wallet để tạo ví mới

import logging
auth_logger = logging.getLogger(__name__)

class AuthService:
    @staticmethod
    def register_user(username, password):
        if User.query.filter_by(username=username).first():
            auth_logger.warning(f"Đăng ký thất bại: Tên người dùng '{username}' đã tồn tại.")
            return False, "Tên người dùng đã tồn tại."

        # Tạo ví blockchain mới cho người dùng
        new_wallet = Wallet()
        public_key = new_wallet.get_public_key()
        private_key_str = new_wallet.get_private_key()

        new_user = User(username=username)
        new_user.set_password(password)
        new_user.set_blockchain_keys(public_key, private_key_str) # Lưu public và private key (đã mã hóa)

        db.session.add(new_user)
        db.session.commit()
        auth_logger.info(f"Người dùng '{username}' đã đăng ký thành công với ví blockchain: {public_key[:10]}...")
        return True, "Đăng ký thành công."

    @staticmethod
    def login_user(username, password):
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            auth_logger.info(f"Người dùng '{username}' đăng nhập thành công.")
            return True, user
        auth_logger.warning(f"Đăng nhập thất bại: Tên người dùng hoặc mật khẩu không đúng cho '{username}'.")
        return False, "Tên người dùng hoặc mật khẩu không đúng."