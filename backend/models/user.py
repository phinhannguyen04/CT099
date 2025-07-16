from backend.db.database import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import base64


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # Public key của ví blockchain của người dùng
    blockchain_public_key = db.Column(db.String(256), unique=True, nullable=True)  # Có thể null ban đầu
    # Private key được mã hóa của ví blockchain của người dùng
    # CÂN NHẮC BẢO MẬT: Không nên lưu Private Key trực tiếp trong DB!
    # Trong hệ thống thực, private key nên được giữ bởi người dùng (tại client)
    # hoặc được mã hóa mạnh mẽ và được quản lý bởi một dịch vụ quản lý khóa an toàn.
    # Tuy nhiên, để đơn giản hóa cho ví dụ, chúng ta sẽ lưu nó ở đây.
    # Trong ứng dụng thực, chỉ lưu public key và người dùng quản lý private key của họ.
    blockchain_private_key_encrypted = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Thêm các trường mới cho chức năng thẻ tín dụng
    credit_card_balance = db.Column(db.Integer, default=0, nullable=False)
    daily_credit_count = db.Column(db.Integer, default=0, nullable=False)
    last_credit_date = db.Column(db.Date, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_blockchain_keys(self, public_key, private_key_str):
        self.blockchain_public_key = public_key
        # Đây chỉ là mã hóa base64 để lưu trữ, KHÔNG PHẢI MÃ HÓA BẢO MẬT
        # Trong thực tế, bạn sẽ dùng mã hóa đối xứng với một key bảo mật khác.
        self.blockchain_private_key_encrypted = base64.b64encode(private_key_str.encode()).decode()

    def get_blockchain_private_key(self):
        if self.blockchain_private_key_encrypted:
            return base64.b64decode(self.blockchain_private_key_encrypted).decode()
        return None

    def __repr__(self):
        return f'<User {self.username}>'