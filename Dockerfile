# Sử dụng Python 3.10 siêu nhẹ
FROM python:3.12-slim
# Thiết lập thư mục làm việc trong Docker
WORKDIR /app

# Cài đặt các công cụ hệ thống cần thiết cho PostgreSQL và build thư viện
RUN apt-get update && apt-get install -y gcc libpq-dev build-essential

# Copy file requirements vào và cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code dự án vào Docker
COPY . .