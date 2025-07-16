import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # Giả lập cau hinh secret_key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_default_secret_key' # Thay bằng chuỗi ngẫu nhiên mạnh

    # Cấu hình sqlite
    db_filename = os.environ.get('DATABASE_FILENAME', 'bank.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, db_filename)}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Địa chỉ của Blockchain Node
    BLOCKCHAIN_NODE_URL = os.environ.get('BLOCKCHAIN_NODE_URL') or 'http://127.0.0.1:5000'