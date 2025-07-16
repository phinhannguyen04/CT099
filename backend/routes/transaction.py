import json
from datetime import datetime, time
from decimal import Decimal

from flask import request, jsonify
from sqlalchemy.exc import SQLAlchemyError

from . import transaction_bp
from backend.db.database import db
from backend.models.user import User
from backend.models.transasaction_detail import TransactionDetail
from backend.services.blockchain_client import BlockchainClient
from decimal import Decimal, InvalidOperation
import logging

from .auth import get_current_user_from_session

tx_logger = logging.getLogger(__name__)

blockchain_client = BlockchainClient()

# b1
# Thêm endpoint test
@transaction_bp.route('/test-session', methods=['GET'])
def test_session():
    try:
        sender_user = get_current_user_from_session()
        return jsonify({
            "user_exists": sender_user is not None,
            "has_blockchain_key": sender_user.blockchain_public_key if sender_user else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# b2
@transaction_bp.route('/test-blockchain', methods=['GET'])
def test_blockchain():
    try:
        # Test connection
        balance = blockchain_client.get_balance("test_key")
        return jsonify({"blockchain_status": "OK", "test_balance": balance})
    except Exception as e:
        return jsonify({"blockchain_error": str(e)}), 500


# b3 - Tạo giao dịch chuyển tiền
@transaction_bp.route('/transfer', methods=['POST'])
def transfer_money():
    """
    API để xử lý việc chuyển tiền giữa hai người dùng.
    1. Lấy thông tin người gửi từ session.
    2. Xác thực và kiểm tra dữ liệu đầu vào (người nhận, số tiền).
    3. Kiểm tra số dư hiện tại của người gửi trên blockchain.
    4. Ghi lại giao dịch vào cơ sở dữ liệu với trạng thái 'pending'.
    5. Gửi giao dịch đến Blockchain Node.
    6. Cập nhật trạng thái giao dịch trong cơ sở dữ liệu.
    7. Trả về kết quả cho người dùng.
    """
    try:
        # Bước 1: Lấy thông tin người gửi từ session
        sender_user = get_current_user_from_session()
        if not sender_user:
            tx_logger.warning("Unauthorized access attempt on /transfer.")
            return jsonify({"error": "Chưa đăng nhập. Yêu cầu xác thực"}), 401

        if not sender_user.blockchain_public_key:
            return jsonify({"error": "Người gửi chưa có ví blockchain."}), 400

        # Bước 2: Lấy và xác thực dữ liệu đầu vào
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dữ liệu trống."}), 400

        recipient_id = data.get('recipient_id')
        amount_str = data.get('amount')

        if not recipient_id or not amount_str:
            return jsonify({"error": "Thiếu recipient_id hoặc amount"}), 400

        try:
            amount = Decimal(str(amount_str))
            if amount <= 0:
                return jsonify({"error": "Số tiền phải lớn hơn 0."}), 400
        except (InvalidOperation, TypeError):
            return jsonify({"error": "Số tiền không hợp lệ."}), 400

        # Kiểm tra không thể chuyển cho chính mình
        if sender_user.id == recipient_id:
            return jsonify({"error": "Không thể tự chuyển tiền cho mình."}), 400

        # Tìm người nhận
        recipient_user = User.query.get(recipient_id)
        if not recipient_user:
            return jsonify({"error": "Người nhận không tồn tại."}), 404

        if not recipient_user.blockchain_public_key:
            return jsonify({"error": "Người nhận chưa có ví blockchain."}), 400

        # Bước 3: Kiểm tra số dư người gửi trên blockchain
        sender_balance, error = blockchain_client.get_balance(sender_user.blockchain_public_key)

        if error:
            tx_logger.error(f"Failed to get balance for user {sender_user.id}: {error}")
            return jsonify({"error": f"Không thể kiểm tra số dư. Lỗi: {error}"}), 500

        if sender_balance < float(amount):
            return jsonify({
                "error": "Số dư không đủ để thực hiện giao dịch.",
                "current_balance": sender_balance,
                "required_amount": float(amount)
            }), 400

        # Bước 4: Ghi lại giao dịch vào DB với trạng thái pending
        transaction = TransactionDetail(
            sender_username=sender_user.username,
            receiver_username=recipient_user.username,
            amount=amount,
            description="Transfer",
            status='db_pending',
            created_at=datetime.utcnow()
        )
        db.session.add(transaction)
        db.session.commit()

        # Bước 5: Gửi giao dịch lên blockchain
        try:
            tx_response_data, tx_error_message = blockchain_client.send_transaction(
                sender_pubkey=sender_user.blockchain_public_key,
                receiver_pubkey=recipient_user.blockchain_public_key,
                amount=float(amount),
                signature="DUMMY_SIGNATURE"
            )

            if tx_error_message:
                # Nếu có lỗi, xử lý lỗi và trả về thông báo lỗi
                db.session.rollback()
                transaction.status = 'failed'
                transaction.error_message = tx_error_message
                db.session.commit()
                return jsonify({
                    "error": "Giao dịch blockchain thất bại.",
                    "details": transaction.error_message
                }), 500


            transaction.status = 'blockchain_pending'
            db.session.commit()

            # Kích hoạt đào block để xác nhận giao dịch
            mine_response, mine_error = blockchain_client.mine_block()

            if mine_error:
                return jsonify({
                    "success": True,
                    "message": "Giao dịch đã được gửi thành công, nhưng không thể kích hoạt đào block.",
                    "status": "blockchain_pending",
                    "mine_error": mine_error
                }), 201

            return jsonify({
                "success": True,
                "message": "Giao dịch đã được gửi và đang chờ xác nhận trên blockchain.",
                "status": "blockchain_pending",
                "mine_response": mine_response
            }), 201

        except Exception as e:
            # Xử lý các lỗi bất ngờ khác
            db.session.rollback()
            transaction.status = 'failed'
            transaction.error_message = str(e)
            db.session.commit()
            return jsonify({"error": "Lỗi server nội bộ khi gửi giao dịch."}), 500

    except Exception as e:
        # Xử lý lỗi ở cấp độ cao nhất
        return jsonify({"error": f"Lỗi không mong muốn: {str(e)}"}), 500
