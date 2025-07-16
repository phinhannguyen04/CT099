from flask import Blueprint, request, jsonify, session
from backend.services.auth_service import AuthService
from backend.models.user import User
from backend.services.blockchain_client import BlockchainClient
import logging
from . import auth_bp

auth_logger = logging.getLogger(__name__)

# Flask session sẽ lưu user_id (là số nguyên)
def get_current_user_from_session():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)  # Truy vấn User bằng ID
    return None


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Thiếu tên người dùng hoặc mật khẩu"}), 400

    success, message = AuthService.register_user(username, password)
    if success:
        return jsonify({"message": message}), 201
    return jsonify({"message": message}), 409  # Conflict


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "Thiếu tên người dùng hoặc mật khẩu"}), 400

    success, user = AuthService.login_user(username, password)
    if success:
        session['user_id'] = user.id  # Lưu user_id vào session
        auth_logger.info(f"User {user.username} (ID: {user.id}) logged in, session['user_id'] set.")
        # Trả về ID thay vì username để client dùng cho các request sau
        return jsonify({"message": "Đăng nhập thành công", "user_id": user.id, "username": user.username}), 200
    return jsonify({"message": user}), 401  # Unauthorized


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)  # Xóa user_id khỏi session
    auth_logger.info("User logged out, session['user_id'] cleared.")
    return jsonify({"message": "Đăng xuất thành công"}), 200


@auth_bp.route('/profile', methods=['GET'])
def get_user_profile():
    # Lấy user từ session (dựa trên ID)
    user = get_current_user_from_session()
    if not user:
        return jsonify({"message": "Chưa đăng nhập. Yêu cầu xác thực"}), 401

    blockchain_client = BlockchainClient()  # Khởi tạo client
    balance = blockchain_client.get_balance(user.blockchain_public_key)

    if balance is None:
        balance_msg = "Không thể truy vấn số dư blockchain. Node có thể không hoạt động."
    else:
        balance_msg = f"{balance} ETH"

    return jsonify({
        "id": user.id,  # Thêm ID vào response
        "username": user.username,
        "blockchain_public_key": user.blockchain_public_key,
        "balance": balance_msg,
        "created_at": user.created_at.isoformat()
    }), 200