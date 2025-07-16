from flask import request, jsonify
from . import smart_contract_bp
from backend.services.smart_contract_service import SmartContractService
from backend.services.blockchain_client import BlockchainClient

# Khởi tạo dịch vụ hợp đồng thông minh
blockchain_client_sc = BlockchainClient()
smart_contract_service = SmartContractService(blockchain_client_sc)

@smart_contract_bp.route('/deploy', methods=['POST'])
def deploy_contract():
    data = request.get_json()
    sender_username = data.get('sender_username')
    receiver_username = data.get('receiver_username')
    amount = float(data.get('amount'))
    deadline_seconds = int(data.get('deadline_seconds', 300)) # Mặc định 5 phút

    if not sender_username or not receiver_username or not amount or amount <= 0 or deadline_seconds <= 0:
        return jsonify({"message": "Thiếu thông tin hoặc giá trị không hợp lệ để triển khai hợp đồng."}), 400

    success, result = smart_contract_service.deploy_contract(
        sender_username, receiver_username, amount, deadline_seconds
    )
    if success:
        return jsonify(result), 201
    else:
        return jsonify({"message": result}), 400

@smart_contract_bp.route('/execute', methods=['POST'])
def execute_contract():
    data = request.get_json()
    contract_id = data.get('contract_id')

    if not contract_id:
        return jsonify({"message": "Thiếu ID hợp đồng."}), 400

    success, message = smart_contract_service.execute_contract(contract_id)
    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"message": message}), 400

@smart_contract_bp.route('/status/<contract_id>', methods=['GET'])
def get_contract_status(contract_id):
    status = smart_contract_service.get_contract_status(contract_id)
    if status:
        return jsonify(status), 200
    else:
        return jsonify({"message": "Không tìm thấy hợp đồng."}), 404