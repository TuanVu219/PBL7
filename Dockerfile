# 1. Sử dụng phiên bản Python 3.12 slim (nhẹ và nhanh)
FROM python:3.12-slim

# 2. Thiết lập biến môi trường để ép Docker dùng chuẩn UTF-8 (Fix lỗi font tiếng Việt)
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1 
ENV PYTHONUNBUFFERED=1       

# 3. Thiết lập thư mục làm việc
WORKDIR /app

# 4. Cài đặt các công cụ hệ thống cần thiết 
# (Thêm một số công cụ cho việc build các thư viện AI/Data)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Tối ưu hóa việc cài đặt thư viện (Chỉ copy file requirements để cache tầng này)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy toàn bộ code dự án vào Docker
COPY . .

# 7. (Tùy chọn) Expose cổng Django nếu cần
EXPOSE 8000

# 8. Lệnh mặc định khi chạy container
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]