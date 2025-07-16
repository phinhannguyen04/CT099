import time
from blockchain_core.smartContract import SmartContract
from blockchain_core.wallet import Wallet
from backend.services.blockchain_client import BlockchainClient
from backend.db.database import db
from backend.models.user import User
from backend.models.transasaction_detail import TransactionDetail

import logging

sc_logger = logging.getLogger(__name__)


class SmartContractService:
    def __init__(self, blockchain_client: BlockchainClient):
        self.blockchain_client = blockchain_client
        self.active_contracts = {}  # Lưu trữ các hợp đồng đang hoạt động theo ID hoặc hash

    def deploy_contract(self, sender_username, receiver_username, amount, deadline_seconds, description=""):
        sender_user = User.query.filter_by(username=sender_username).first()
        receiver_user = User.query.filter_by(username=receiver_username).first()

        if not sender_user or not receiver_user:
            sc_logger.warning(
                f"Triển khai hợp đồng thất bại: Người gửi '{sender_username}' hoặc người nhận '{receiver_username}' không tồn tại.")
            return False, "Người gửi hoặc người nhận không tồn tại."

        sender_wallet = Wallet(sender_user.get_blockchain_private_key())
        sender_pubkey = sender_wallet.get_public_key()
        receiver_pubkey = receiver_user.blockchain_public_key

        current_balance = self.blockchain_client.get_balance(sender_pubkey)
        if current_balance is None or current_balance < amount:
            sc_logger.warning(
                f"Triển khai hợp đồng thất bại: {sender_username} không đủ số dư ({current_balance} ETH) để gửi {amount} ETH.")
            return False, "Không đủ số dư để triển khai hợp đồng."

        deadline = time.time() + deadline_seconds

        # Mô phỏng "khóa" số tiền trên ví người gửi khi triển khai hợp đồng
        # Trong một blockchain thực, điều này sẽ được xử lý bằng cách tạo một loại giao dịch "contract deployment"
        # hoặc escrow contract. Ở đây, chúng ta sẽ giả định số dư bị "trừ" ngay khi hợp đồng được tạo.
        # Thực tế, giao dịch sẽ chỉ được tạo khi hợp đồng được "thực thi" hoặc "hoàn lại".

        contract_id = f"contract_{sender_username}_{receiver_username}_{int(time.time())}"
        my_contract = SmartContract(
            sender=sender_pubkey,
            receiver=receiver_pubkey,
            amount=amount,
            deadline=deadline
        )
        self.active_contracts[contract_id] = my_contract

        # Ghi log chi tiết hợp đồng off-chain (có thể thêm vào TransactionDetail)
        sc_logger.info(
            f"Hợp đồng thông minh '{contract_id}' đã được triển khai bởi {sender_username} ({sender_pubkey[:10]}...): {amount} ETH đến {receiver_username} ({receiver_pubkey[:10]}...) với hạn chót {time.ctime(deadline)}.")
        return True, {"message": "Hợp đồng thông minh đã được triển khai.", "contract_id": contract_id,
                      "deadline": time.ctime(deadline)}

    def execute_contract(self, contract_id):
        contract = self.active_contracts.get(contract_id)
        if not contract:
            sc_logger.warning(f"Thực thi hợp đồng thất bại: Không tìm thấy hợp đồng với ID '{contract_id}'.")
            return False, "Hợp đồng không tồn tại hoặc đã bị xóa."

        if contract.executed:
            sc_logger.info(f"Hợp đồng '{contract_id}' đã được thực hiện hoặc hoàn lại rồi.")
            return True, "Hợp đồng đã thực hiện rồi."

        current_time = time.time()

        # Tìm user gốc để lấy private key cho việc ký giao dịch
        sender_user = User.query.filter_by(blockchain_public_key=contract.sender).first()
        if not sender_user:
            sc_logger.error(f"Lỗi: Không tìm thấy người dùng gốc cho Public Key {contract.sender[:10]}...")
            return False, "Lỗi nội bộ: Không tìm thấy người gửi hợp đồng."

        sender_wallet = Wallet(sender_user.get_blockchain_private_key())
        message_to_sign = f"{contract.receiver}{contract.amount}"
        signature = sender_wallet.sign(message_to_sign)

        if current_time <= contract.deadline:
            # Hợp đồng được thực thi thành công
            tx_response = self.blockchain_client.send_transaction(
                sender_pubkey=contract.sender,
                receiver_pubkey=contract.receiver,
                amount=contract.amount,
                signature=signature
            )
            if tx_response:
                contract.executed = True
                sc_logger.info(
                    f"Hợp đồng '{contract_id}' được thực thi: {contract.amount} ETH từ {contract.sender[:10]}... đến {contract.receiver[:10]}... Giao dịch đã gửi đến Node.")
                # Cần cập nhật trạng thái giao dịch off-chain nếu có
                return True, "Hợp đồng đã thực thi thành công."
            else:
                sc_logger.error(f"Lỗi khi gửi giao dịch cho hợp đồng '{contract_id}' đến Node.")
                return False, "Lỗi khi gửi giao dịch đến Node."
        else:
            # Hợp đồng quá hạn, hoàn lại tiền
            # Trong một hệ thống thực, bạn sẽ tạo một giao dịch hoàn lại cho chính người gửi.
            # Đối với ví dụ này, chúng ta giả định tiền sẽ "quay lại" mà không cần giao dịch blockchain riêng.
            # Nếu bạn muốn tạo giao dịch hoàn lại:
            # refund_tx_response = self.blockchain_client.send_transaction(
            #     sender_pubkey=contract.receiver, # Giả định người nhận phải trả lại
            #     receiver_pubkey=contract.sender,
            #     amount=contract.amount,
            #     signature=signature_from_receiver # Cần chữ ký của người nhận
            # )
            # Tuy nhiên, trong mô hình này, tiền chưa chuyển đi, nên chỉ là log.

            # Cần một cơ chế để hoàn lại tiền hoặc hủy trạng thái giữ tiền.
            # Hiện tại, chỉ là thông báo. Nếu bạn có UTXO model, bạn sẽ "unspend" UTXO.
            contract.executed = True
            sc_logger.info(
                f"Hợp đồng '{contract_id}' quá hạn: {contract.amount} ETH được hoàn lại cho {contract.sender[:10]}...")
            return True, "Hợp đồng đã quá hạn, tiền được hoàn lại."

    def get_contract_status(self, contract_id):
        contract = self.active_contracts.get(contract_id)
        if not contract:
            return None
        return {
            "sender": contract.sender,
            "receiver": contract.receiver,
            "amount": contract.amount,
            "deadline": time.ctime(contract.deadline),
            "executed": contract.executed
        }