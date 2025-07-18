### Cấu hình sử dụng
| Tool     | Tech     |
|-----------|-----------|
| IDE    | Pycharm  | 
| Database  | SQLite   | 
| Testing   | Postman   | 
### Cài đặt 
> Tiến hành seup môi trường đầy đủ

1. Clone git/.zip về máy
```bash
https://github.com/phinhannguyen04/CT099.git
```

2. Cài đặt các thư viện thông qua file requirement.txt
```bash
pip install -r requirements.txt
```

### Khởi chạy dự án
> Tạo terminal local(1)
1. Run blockchain node server
```bash
python -m blockchain_node.node --port 5000
```
> Tạo terminal local(2)
2. Run backend server
```bash
 python -m backend.app
```

### Cài đặt Postman
> Tiến hành download Postman tại dường dẫn [Download Postman To Test API](https://www.postman.com/downloads/)

Sau khi run Postman 
- Tải Postman Collection tại đường dẫn [Postman Collection](https://drive.google.com/file/d/1N4wh7FvCUDh4oEcChhW3Ps2Kida1o4-L/view?usp=sharing)
- Tiến hành import collection [How to Import Postman Collections in 2025 (Step-by-Step Guide)](https://www.youtube.com/watch?v=-4CNWIPJDgo)
- Run các API

