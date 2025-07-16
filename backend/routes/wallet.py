from flask import request, jsonify
from . import wallet_bp
from backend.db.database import db
from backend.models.user import User
from backend.services.blockchain_client import BlockchainClient
from .auth import get_current_user_from_session
from datetime import date

# Khởi tạo client để giao tiếp với Blockchain Node
blockchain_client = BlockchainClient()


@wallet_bp.route('/debug-user', methods=['GET'])
def debug_user():
    user = get_current_user_from_session()
    if not user:
        return jsonify({"message": "Chưa đăng nhập"}), 401

    return jsonify({
        "user_id": user.id,
        "username": user.username,
        "has_blockchain_key": bool(user.blockchain_public_key),
        "blockchain_public_key": user.blockchain_public_key
    })

@wallet_bp.route('/info', methods=['GET'])
def get_wallet_info_current_user():
    user = get_current_user_from_session()
    if not user:
        return jsonify({"message": "Chưa đăng nhập. Yêu cầu xác thực"}), 401

    if not user.blockchain_public_key:
        return jsonify({"message": "Người dùng chưa có ví blockchain."}), 404

    public_key = user.blockchain_public_key

    # Thêm logging
    print(f"Trying to get balance for address: {public_key}")
    print(f"Blockchain node URL: {blockchain_client.node_url}")

    balance, error_message = blockchain_client.get_balance(public_key)

    if error_message:
        # Log chi tiết lỗi
        print(f"Error getting balance: {error_message}")
        return jsonify({
            "message": f"Không thể lấy số dư ví lúc này. {error_message}",
            "debug_info": {
                "public_key": public_key,
                "node_url": blockchain_client.node_url
            }
        }), 500

    return jsonify({
        "username": user.username,
        "public_key": public_key,
        "balance": balance
    }), 200


@wallet_bp.route('/info/<int:id>', methods=['GET'])
def get_wallet_info(id):
    user = User.query.filter_by(id=id).first()
    if not user:
        return jsonify({"message": "Người dùng không tồn tại."}), 404
    if not user.blockchain_public_key:
        return jsonify({"message": "Người dùng chưa có ví blockchain."}), 404

    public_key = user.blockchain_public_key

    # Sửa đổi: Nhận cả balance và error_message
    balance, error_message = blockchain_client.get_balance(public_key)

    if error_message:
        return jsonify({
            "message": f"Không thể lấy số dư ví lúc này. {error_message}"
        }), 500

    return jsonify({
        "username": user.username,
        "public_key": public_key,
        "balance": balance
    }), 200


# Chức năng Vay tiền ngân hàng (cấp tiền cho tài khoản blockchain)
# Đây là một chức năng "đặc biệt" chỉ ngân hàng (admin) mới có thể thực hiện
# để cấp một lượng tiền ban đầu vào ví blockchain của người dùng.
# Trong một hệ thống thực tế, cần cơ chế xác thực admin mạnh mẽ.
@wallet_bp.route('/lend', methods=['POST'])
def lend_money():
    # Lấy thông tin user từ session (đã đăng nhập)
    user = get_current_user_from_session()
    if not user:
        return jsonify({"message": "Chưa đăng nhập. Yêu cầu xác thực"}), 401

    data = request.get_json()
    amount = float(data.get('amount'))

    if not amount or amount <= 0:
        return jsonify({"message": "Thiếu số tiền hợp lệ."}), 400

    # Không cần kiểm tra user nữa, vì đã có từ session
    if not user.blockchain_public_key:
        return jsonify({"message": "Người dùng chưa có ví blockchain."}), 404

    # Tạo một transaction giả định từ "ngân hàng"
    message_to_sign_for_system = f"{user.blockchain_public_key}{amount}"
    signature_for_system = "SYSTEM_SIGNATURE_N/A"

    # Sửa đổi
    tx_response, tx_error = blockchain_client.send_transaction(
        sender_pubkey="SYSTEM_INITIAL_FUND",  # Địa chỉ đặc biệt
        receiver_pubkey=user.blockchain_public_key,
        amount=amount,
        signature=signature_for_system
    )

    if tx_error:
        return jsonify(
            {"message": f"Không thể cấp tiền. Lỗi khi gửi giao dịch đến Blockchain Node. Chi tiết: {tx_error}"}), 500

    # Nếu giao dịch thành công, tiếp tục
    mine_response, mine_error = blockchain_client.mine_block()

    if mine_error:
        return jsonify({
            "message": f"Đã cấp {amount} ETH cho {user.username}, nhưng không thể kích hoạt đào block. Chi tiết: {mine_error}",
            "blockchain_tx_status": tx_response.get("message")
        }), 200
    else:
        return jsonify({
            "message": f"Đã cấp {amount} ETH cho {user.username}. Giao dịch đang chờ xác nhận.",
            "blockchain_tx_status": tx_response.get("message")
        }), 200


# API mới: Mở thẻ tín dụng và nhận tiền
@wallet_bp.route('/credit-card/issue', methods=['POST'])
def issue_credit_card():
    # Lấy thông tin user từ session (đã đăng nhập)
    user = get_current_user_from_session()
    if not user:
        return jsonify({"message": "Chưa đăng nhập. Yêu cầu xác thực"}), 401

    current_date = date.today()

    # Reset số lần mượn trong ngày nếu đã sang ngày mới
    if user.last_credit_date != current_date:
        user.daily_credit_count = 0
        user.last_credit_date = current_date

    # Kiểm tra giới hạn mượn trong ngày
    if user.daily_credit_count >= 3:
        return jsonify({"message": "Bạn đã đạt giới hạn mượn tín dụng (3 lần/ngày)."}), 403

    # Số tiền cấp cho mỗi lần mượn
    loan_amount = 200000

    # Tăng số lần mượn trong ngày
    user.daily_credit_count += 1

    # Cộng tiền vào số dư blockchain của người dùng
    try:
        # Sửa đổi
        tx_response, tx_error = blockchain_client.send_transaction(
            sender_pubkey="SYSTEM_INITIAL_FUND",
            receiver_pubkey=user.blockchain_public_key,
            amount=loan_amount,
            signature="SYSTEM_SIGNATURE_N/A"  # Giả định chữ ký được Node chấp nhận
        )

        if tx_error:
            db.session.rollback()
            return jsonify({"message": f"Lỗi khi gửi giao dịch đến Blockchain Node. Chi tiết: {tx_error}"}), 500

        # Cập nhật số dư tín dụng trong DB
        user.credit_card_balance += loan_amount
        db.session.commit()

        # Kích hoạt đào block để xác nhận giao dịch trên blockchain
        # Sửa đổi
        mine_response, mine_error = blockchain_client.mine_block()

        if mine_error:
            return jsonify({
                "message": f"Bạn đã nhận thành công {loan_amount} ETH, nhưng không thể kích hoạt đào block. Chi tiết: {mine_error}",
                "daily_credit_count": user.daily_credit_count,
                "current_credit_balance": user.credit_card_balance,
                "blockchain_tx_status": tx_response.get("message")
            }), 200

        return jsonify({
            "message": f"Bạn đã nhận thành công {loan_amount} ETH từ thẻ tín dụng.",
            "daily_credit_count": user.daily_credit_count,
            "current_credit_balance": user.credit_card_balance,
            "blockchain_tx_status": tx_response.get("message")
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Đã xảy ra lỗi: {str(e)}"}), 500