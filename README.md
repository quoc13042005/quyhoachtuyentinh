# Web Quy Hoạch Tuyến Tính (Linear Programming Solver)

Đây là ứng dụng web giải các bài toán Quy Hoạch Tuyến Tính bằng các thuật toán:
- Đơn hình (Simplex)
- Quy tắc Bland (Bland's Rule)
- Đơn hình 2 Pha (Two-Phase Simplex)
- Đơn hình Đối ngẫu (Dual Simplex)
- Đơn hình 2 Pha Đối ngẫu (Two-Phase Dual Simplex)
- Phương pháp Hình học (Geometric Method)

Giao diện trực quan, hiển thị các bước giải bằng bảng Từ vựng (Dictionary) cực kỳ chi tiết và thân thiện.

## Hướng dẫn cài đặt

Để chạy mã nguồn này trên máy của bạn, hãy làm theo các bước sau:

**1. Clone kho lưu trữ về máy**
```bash
git clone https://github.com/quoc13042005/quyhoachtuyentinh.git
cd quyhoachtuyentinh
```

**2. Tạo và kích hoạt môi trường ảo (Khuyến nghị)**
- Trên Windows:
```bash
python -m venv venv
venv\Scripts\activate
```
- Trên macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Cài đặt các thư viện cần thiết**
```bash
pip install -r requirements.txt
```

**4. Khởi chạy Server Web**
```bash
python app.py
```

Sau khi chạy xong, hãy mở trình duyệt và truy cập vào đường dẫn: [http://localhost:5000](http://localhost:5000) để sử dụng ứng dụng!
