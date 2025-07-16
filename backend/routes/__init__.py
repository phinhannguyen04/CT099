# my_bank_blockchain/backend/routes/__init__.py
from flask import Blueprint

# Khởi tạo các Blueprint
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')
wallet_bp = Blueprint('wallet_bp', __name__, url_prefix='/wallet')
transaction_bp = Blueprint('transaction_bp', __name__, url_prefix='/transaction')
smart_contract_bp = Blueprint('smart_contract_bp', __name__, url_prefix='/smart_contract')
user_bp = Blueprint('user_bp', __name__, url_prefix='/users')

# Import các routes cụ thể từ các file tương ứng
from . import auth, wallet, transaction, smart_contract, user