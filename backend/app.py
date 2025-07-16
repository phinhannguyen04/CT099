from flask import Flask, jsonify
from dotenv import load_dotenv
import os
import logging
from flask_migrate import Migrate

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import Config
from backend.config import Config
from backend.db.database import db, init_db

# Import Route: Đảm bảo TẤT CẢ các blueprint đều được import
from backend.routes import auth_bp, wallet_bp, transaction_bp, smart_contract_bp, user_bp

# --- Cấu hình Logging cho Backend App ---
LOG_FILE_BACKEND = "backend.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_BACKEND, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

app_logger = logging.getLogger(__name__)
app_logger.info("Khởi động Backend Bank App...")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    init_db(app) # Khởi tạo SQLAlchemy và tạo bảng

    migrate = Migrate(app, db)

    # Đăng ký các Blueprint: Đảm bảo TẤT CẢ các blueprint đều được đăng ký
    app.register_blueprint(auth_bp)
    app.register_blueprint(wallet_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(smart_contract_bp)
    app.register_blueprint(user_bp)

    @app.route('/')
    def index():
        return jsonify({"message": "Chào mừng đến với Blockchain Bank Backend!"})

    return app

app = create_app()

if __name__ == '__main__':
    # Chạy Flask app
    app_logger.info(f"Backend Flask App đang chạy trên http://127.0.0.1:8000")
    app.run(debug=True, port=8000)