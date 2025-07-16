from flask import Blueprint, jsonify, abort, session
from backend.models.user import User
from backend.services.blockchain_client import BlockchainClient
import logging
from . import user_bp
user_logger = logging.getLogger(__name__)

# Hàm giả định kiểm tra quyền admin.
def is_admin_user():
    # Placeholder: Trong ứng dụng thực, bạn sẽ kiểm tra vai trò người dùng từ DB/token/session.
    # user = User.query.get(session.get('user_id'))
    # return user and user.role == 'admin'
    return True


@user_bp.route('/', methods=['GET'])
def get_all_users():
    if not is_admin_user():
        user_logger.warning("Truy cập trái phép API danh sách người dùng.")
        abort(403)

    users = User.query.all()
    user_list = []
    blockchain_client = BlockchainClient()

    for user in users:
        balance = "N/A"
        if user.blockchain_public_key:
            try:
                b = blockchain_client.get_balance(user.blockchain_public_key)
                if b is not None:
                    balance = f"{b} ETH"
                else:
                    balance = "Không thể truy vấn số dư."
            except Exception as e:
                user_logger.error(f"Lỗi khi lấy số dư blockchain cho user {user.username} (ID: {user.id}): {e}")
                balance = "Lỗi truy vấn số dư."

        user_list.append({
            "id": user.id,  # Đảm bảo ID có trong response
            "username": user.username,
            "blockchain_public_key": user.blockchain_public_key,
            "balance": balance,
            "created_at": user.created_at.isoformat()
        })
    user_logger.info(f"Đã trả về danh sách {len(user_list)} người dùng.")
    return jsonify(user_list), 200


# Thay đổi từ <username> sang <int:user_id>
@user_bp.route('/<int:user_id>', methods=['GET'])
def get_user_by_id(user_id):
    # Thêm kiểm tra quyền ở đây nếu cần (admin hoặc chính user đó)
    user = User.query.get(user_id)  # Tìm kiếm user bằng ID
    if not user:
        user_logger.warning(f"Truy vấn thông tin người dùng với ID '{user_id}' không tìm thấy.")
        return jsonify({"message": "Người dùng không tồn tại"}), 404

    blockchain_client = BlockchainClient()
    balance = blockchain_client.get_balance(user.blockchain_public_key)

    if balance is None:
        balance_msg = "Không thể truy vấn số dư blockchain. Node có thể không hoạt động."
    else:
        balance_msg = f"{balance} ETH"

    user_logger.info(f"Đã trả về thông tin người dùng: {user.username} (ID: {user_id}).")
    return jsonify({
        "id": user.id,  # Đảm bảo ID có trong response
        "username": user.username,
        "blockchain_public_key": user.blockchain_public_key,
        "balance": balance_msg,
        "created_at": user.created_at.isoformat()
    }), 200