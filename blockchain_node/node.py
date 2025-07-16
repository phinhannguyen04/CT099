import time
import json
import logging
from flask import Flask, request, jsonify
import os
from blockchain_core.blockchain import Blockchain
from blockchain_core.transaction import Transaction


# --- Cấu hình Logging cho Node ---
LOG_FILE_NODE = "node.log"  # Log file vẫn có thể nằm ở thư mục gốc của dự án
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_NODE, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
node_logger = logging.getLogger(__name__)
node_logger.info("Khởi động Blockchain Node...")

# --- Cài đặt Node ---
app = Flask(__name__)

# Set độ khó cho blockchain
DIFFICULTY = 2
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NODE_BLOCKCHAIN_FILE = os.path.join(BASE_DIR, "node_blockchain.json")

# Giả sử địa chỉ ví của người dừng ang đăng nhập
SYSTEM_INITIAL_FUND_RECIPIENT_ADDRESS = "9wuLehM6ANln0o3TfH/Up/Za7Ienp6IuJdXKmBfgxNQrfaZMLYq2oBgxoQI8tDrPFF/2GhVNCAhAHRz/XBKZ3w=="
INITIAL_FUND_AMOUNT = 10.0 # Số tiền ban đầu cho Genesis Block (khớp với giao dịch bạn đã thấy)

my_node_blockchain = None # Khởi tạo là None ban đầu

# --- LOGIC KHỞI TẠO HOẶC TẢI BLOCKCHAIN (ĐÃ SỬA CHỮA HOÀN TOÀN) ---
node_logger.info("Khởi động Blockchain Node...")
node_logger.info("Kiểm tra trạng thái Blockchain...")

loaded_successfully = False

# Bước 1: Thử tải từ file
# Tạo một instance Blockchain TẠM THỜI chỉ để gọi load_from_file trên đó.
# Các tham số này chỉ là placeholder vì chúng sẽ bị ghi đè nếu tải thành công.
# Tuy nhiên, chúng cần thiết nếu load_from_file không thành công và cần tạo Blockchain mới.
temp_blockchain_instance_for_loading = Blockchain(
    difficulty=DIFFICULTY,
    initial_funder_address="DUMMY_ADDRESS", # Địa chỉ giả
    initial_fund_amount=0 # Số tiền giả
)

if os.path.exists(NODE_BLOCKCHAIN_FILE):
    # Nếu file tồn tại, thử tải
    if temp_blockchain_instance_for_loading.load_from_file(NODE_BLOCKCHAIN_FILE):
        my_node_blockchain = temp_blockchain_instance_for_loading # Gán instance đã tải
        node_logger.info(f"Đã tải Blockchain thành công từ '{NODE_BLOCKCHAIN_FILE}'. Chuỗi có {len(my_node_blockchain.chain)} block.")
        loaded_successfully = True
    else:
        # Nếu file tồn tại nhưng tải thất bại (ví dụ: file hỏng), log cảnh báo
        node_logger.warning(f"Không thể tải Blockchain từ '{NODE_BLOCKCHAIN_FILE}'. File có thể bị hỏng hoặc không hợp lệ.")

# Nếu không tải được (hoặc file không tồn tại ban đầu), TẠO MỚI Blockchain
if not loaded_successfully:
    if not os.path.exists(NODE_BLOCKCHAIN_FILE):
        node_logger.info("Không tìm thấy file Blockchain. Tạo Blockchain mới.")
    else:
        node_logger.info("Do lỗi tải, tạo Blockchain mới.")

    my_node_blockchain = Blockchain(
        difficulty=DIFFICULTY,
        initial_funder_address=SYSTEM_INITIAL_FUND_RECIPIENT_ADDRESS,
        initial_fund_amount=INITIAL_FUND_AMOUNT
    )
    # Lưu Genesis Block mới tạo ngay lập tức
    node_logger.info("Lưu Genesis Block mới tạo vào file.")
    my_node_blockchain.save_to_file(NODE_BLOCKCHAIN_FILE)

# --- P2P Network (Mô phỏng đơn giản) ---
PEERS = set()

# --- API Endpoints cho Node (giữ nguyên) ---
@app.route('/chain', methods=['GET'])
def get_chain():
    node_logger.info("Yêu cầu lấy toàn bộ chuỗi blockchain.")
    chain_data = []
    for block in my_node_blockchain.chain:
        chain_data.append(block.to_dict())
    response = {
        'length': len(chain_data),
        'chain': chain_data
    }
    return jsonify(response), 200


@app.route('/mine', methods=['GET'])
def mine_block_api():
    miner_address = "NODE_MINER_ADDRESS_123456"

    if not my_node_blockchain.pending_transactions:
        node_logger.info("Không có giao dịch nào đang chờ xử lý để đào.")
        response = {
            "message": "Không có giao dịch nào đang chờ xử lý.",
            "chain_length": len(my_node_blockchain.chain)
        }
        return jsonify(response), 200

    last_block = my_node_blockchain.get_last_block()

    mined_block = my_node_blockchain.mine_pending_transactions(miner_address)

    if mined_block:
        if my_node_blockchain.save_to_file(NODE_BLOCKCHAIN_FILE): # KIỂM TRA GIÁ TRỊ TRẢ VỀ
            response = {
                'message': "Block mới đã được đào và lưu!",
                'index': mined_block.index,
                'transactions': [tx.to_dict() for tx in mined_block.transactions],
                'nonce': mined_block.nonce,
                'hash': mined_block.hash,
            }
            node_logger.info(f"API: Đã đào block #{mined_block.index}. Hash: {mined_block.hash[:10]}...")
            return jsonify(response), 200
        else:
            node_logger.error("API: Đã đào block nhưng lỗi khi lưu blockchain vào file!")
            return jsonify({"message": "Block được đào nhưng không thể lưu vào file."}), 500
    else:
        node_logger.error("API: Lỗi khi đào block.")
        return jsonify({"message": "Lỗi khi đào block."}), 500



@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    node_logger.info(f"API: Nhận yêu cầu giao dịch mới: {values}")

    required_fields = ['sender', 'receiver', 'amount', 'signature']
    if not all(field in values for field in required_fields):
        node_logger.warning(f"API: Thiếu trường trong yêu cầu giao dịch: {required_fields}")
        return jsonify({'message': 'Missing values'}), 400

    transaction = Transaction(
        values['sender'],
        values['receiver'],
        values['amount'],
        values['signature']
    )

    if my_node_blockchain.add_transaction_to_pool(transaction):
        # LƯU FILE NGAY LẬP TỨC
        my_node_blockchain.save_to_file(NODE_BLOCKCHAIN_FILE)

        response = {'message': f'Giao dịch sẽ được thêm vào Block {my_node_blockchain.get_last_block().index + 1}'}
        return jsonify(response), 201
    else:
        return jsonify({'message': 'Giao dịch không hợp lệ.'}), 400


@app.route('/transactions/pending', methods=['GET'])
def get_pending_transactions():
    node_logger.info("API: Yêu cầu lấy các giao dịch đang chờ xử lý.")
    pending_txs = [tx.to_dict() for tx in my_node_blockchain.pending_transactions]
    return jsonify(pending_txs), 200


from urllib.parse import unquote_plus


@app.route('/balance/<path:address>', methods=['GET'])
def get_balance(address):
    node_logger.info(f"Raw address received: {address}")
    decoded_address = unquote_plus(address)
    node_logger.info(f"Decoded address: {decoded_address}")

    # Debug: In ra tất cả các transaction
    for i, block in enumerate(my_node_blockchain.chain):
        node_logger.info(f"Block {i} has {len(block.transactions)} transactions")
        for j, tx in enumerate(block.transactions):
            node_logger.info(f"  Transaction {j}: {tx.sender} -> {tx.receiver}, amount: {tx.amount}")

    # Decode URL encoding
    decoded_address = unquote_plus(address)
    node_logger.info(f"API: Yêu cầu số dư cho địa chỉ: {decoded_address}")

    try:
        balance = my_node_blockchain.get_balance(decoded_address)
        response = {
            'address': decoded_address,
            'balance': balance
        }
        node_logger.info(f"API: Số dư cho {decoded_address}: {balance}")
        return jsonify(response), 200
    except Exception as e:
        node_logger.error(f"API: Lỗi khi lấy số dư cho {decoded_address}: {str(e)}")
        return jsonify({
            'error': f'Lỗi khi lấy số dư: {str(e)}',
            'address': decoded_address
        }), 500


@app.route('/nodes/register', methods=['POST'])
def register_node():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        PEERS.add(node)
        node_logger.info(f"API: Đã thêm node mới: {node}")

    response = {
        'message': 'Đã thêm các node mới',
        'total_nodes': list(PEERS)
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    node_logger.info("API: Kích hoạt giải quyết xung đột (đồng thuận).")
    replaced = False

    if my_node_blockchain.is_chain_valid():
        response = {
            'message': 'Chuỗi của node này đã được xác nhận và là hợp lệ.',
            'chain': [block.to_dict() for block in my_node_blockchain.chain]
        }
    else:
        response = {
            'message': 'Chuỗi của node này không hợp lệ, cần được thay thế (chưa triển khai tự động).',
            'chain': [block.to_dict() for block in my_node_blockchain.chain]
        }
        node_logger.warning("API: Chuỗi hiện tại của Node không hợp lệ!")

    return jsonify(response), 200

# --- Chạy Node ---
if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='Cổng để chạy node')
    args = parser.parse_args()
    port = args.port

    node_logger.info(f"Node sẽ chạy trên http://127.0.0.1:{port}")

    try:
        # Chạy server Flask. Lệnh này sẽ chặn luồng chính cho đến khi server tắt.
        app.run(host='0.0.0.0', port=port, debug=False)
    finally:
        # Khối 'finally' này sẽ LUÔN LUÔN được thực thi,
        # ngay cả khi server bị tắt đột ngột (ví dụ: bằng Ctrl+C).
        node_logger.info("Node đang tắt, lưu trạng thái blockchain cuối cùng.")
        if my_node_blockchain:  # Đảm bảo my_node_blockchain đã được khởi tạo
            # Thêm log để xác nhận số lượng block đang được lưu
            node_logger.info(f"Đang lưu chuỗi với {len(my_node_blockchain.chain)} block vào file.")
            my_node_blockchain.save_to_file(NODE_BLOCKCHAIN_FILE)

    # python -m blockchain_node.node --port 5000