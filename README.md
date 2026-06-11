# 📈 Trend Intelligence Dashboard

### Hệ thống Phân tích Xu hướng Báo chí Thời gian thực

Hệ thống thu thập, phân tích và trực quan hóa xu hướng tin tức (Trending News) theo thời gian thực.
Dự án ứng dụng kiến trúc **Big Data** kết hợp **AI/NLP (Natural Language Processing)** nhằm xử lý dữ liệu báo chí quy mô lớn và hiển thị trực quan các xu hướng nổi bật.

Hệ thống được đóng gói hoàn toàn bằng Docker và triển khai theo mô hình **Microservices / Decoupled Architecture**, tách biệt Frontend, Backend và tầng xử lý dữ liệu.

> 🎓 Dự án được phát triển phục vụ học phần **Đồ án Chuyên ngành 2 (PBL7)**.

---

# 🏗️ Kiến trúc Hệ thống (System Architecture)

Hệ thống được thiết kế theo tư duy **Decoupled Architecture** nhằm tối ưu hiệu suất xử lý dữ liệu lớn và dễ dàng mở rộng trong tương lai.

Toàn bộ hệ thống được chia thành 3 tầng hoạt động độc lập:

## 1️⃣ Data Ingestion Layer (Apache Spark Cluster)

Tầng thu thập dữ liệu sử dụng cụm **Apache Spark (Master/Worker)** để:

* Thu thập RSS từ nhiều trang báo song song
* Xử lý đa luồng dữ liệu lớn
* Giảm tải RAM và CPU cho Web Server

Spark hoạt động độc lập hoàn toàn với Backend nhằm đảm bảo hiệu năng hệ thống.

---

## 2️⃣ Processing & API Layer (Django + NLP)

Máy chủ Python đảm nhiệm hai vai trò:

### 🔹 RESTful API Server

Cung cấp dữ liệu JSON cho Frontend thông qua các API endpoint.

### 🔹 Background NLP Worker

Thực hiện:

* Tiền xử lý văn bản tiếng Việt
* Trích xuất từ khóa
* Topic Modeling (LDA)
* Tính toán Trending Score bằng Z-Score

Các thư viện AI/NLP chính:

* Underthesea
* Gensim
* Pandas
* NumPy

---

## 3️⃣ Presentation Layer (Static Frontend)

Frontend được xây dựng bằng:

* HTML5
* TailwindCSS
* Apache ECharts

Đặc điểm:

* Giao diện tĩnh hoàn toàn
* Không cần server-side rendering
* Tốc độ tải nhanh
* Gọi API trực tiếp từ Backend

---

# 🛠️ Tech Stack

| Thành phần | Công nghệ                       | Vai trò                            |
| ---------- | ------------------------------- | ---------------------------------- |
| Big Data   | Apache Spark, PySpark           | Xử lý phân tán và thu thập dữ liệu |
| Backend    | Python, Django                  | REST API & xử lý dữ liệu           |
| NLP / AI   | Gensim, Underthesea             | Topic Modeling & NLP               |
| Database   | PostgreSQL                      | Lưu trữ dữ liệu                    |
| Frontend   | HTML5, TailwindCSS, ECharts     | Dashboard trực quan                |
| DevOps     | Docker, Docker Compose, Crontab | Tự động hóa & triển khai           |

---

# 📂 Cấu trúc Thư mục

```plaintext
📦 PBL7_Trend_Intelligence
 ┣ 📂 Frontend/              
 ┃ ┣ 📜 index.html
 ┃ ┗ 📜 search.html
 ┃
 ┣ 📂 Spark/
 ┃ ┗ 📜 rss_spark_crawler.py
 ┃
 ┣ 📂 core/
 ┃ ┣ 📂 management/commands/
 ┃ ┃ ┗ 📜 auto_pipeline.py
 ┃ ┣ 📜 models.py
 ┃ ┣ 📜 views.py
 ┃ ┗ 📜 urls.py
 ┃
 ┣ 📜 docker-compose.yml
 ┣ 📜 Dockerfile
 ┣ 📜 requirements.txt
 ┗ 📜 README.md
```

---

# ⚙️ Yêu cầu Môi trường (Prerequisites)

Trước khi chạy hệ thống, cần cài đặt:

* Docker Desktop
* Docker Compose
* Git

## Kiểm tra Docker

```bash
docker --version
docker-compose --version
```

---

# 🚀 Hướng dẫn Cài đặt & Khởi động

# Bước 1: Clone Source Code

```bash
[git clone https://github.com/<your-username>/<your-repository>.git](https://github.com/TuanVu219/PBL7.git)
```

---

# Bước 2: Build & Khởi động Hệ thống Docker

Lệnh dưới đây sẽ:

* Build toàn bộ containers
* Tạo network nội bộ
* Khởi động:

  * PostgreSQL
  * Spark Master
  * Spark Worker
  * Django Web API
  * Scheduler Worker

```bash
docker-compose up -d --build
```

Kiểm tra trạng thái containers:

```bash
docker-compose ps
```

Tất cả containers phải ở trạng thái:

```plaintext
Up
```

---

# Bước 3: Khởi tạo Database

Thực hiện migrate PostgreSQL schema:

```bash
docker exec -it pbl7_django python manage.py migrate
```

---

# 🏃 Quy trình Pipeline Dữ liệu

Hệ thống hoạt động theo 2 giai đoạn chính:

---

# Giai đoạn 1: Thu thập Dữ liệu (Spark Crawling)

Spark sẽ thu thập RSS từ các trang báo điện tử:

```bash
docker exec -it pbl7-spark-master \
/opt/spark/bin/spark-submit /app/rss_spark_crawler.py
```

Sau bước này:

* Tin tức thô sẽ được lưu vào PostgreSQL

---

# Giai đoạn 2: Xử lý NLP & Phân tích Xu hướng

Backend sẽ:

* Tokenize tiếng Việt
* Trích xuất từ khóa
* Gán chủ đề bằng LDA
* Tính toán Z-Score

Chạy script NLP:

```bash
docker exec -it pbl7_django python nlp_engine.py
```

# 🤖 Tự động hóa Hệ thống (Automation)

Hệ thống hỗ trợ pipeline tự động hoàn toàn.

---

# 2️⃣ Tự động NLP Processing bằng Scheduler

Container `pbl7_scheduler` đã được tích hợp:

* Python Schedule
* Background Worker

Scheduler sẽ:

* Tự động chạy lúc 23:00 mỗi ngày
* Xử lý NLP
* Cập nhật bảng thống kê xu hướng

Không cần cấu hình thêm.

---

# 🖥️ Khởi chạy Web

## Chạy giao diện:

Chạy script:

```bash
python manage.py runserver
```



# 🔧 Cấu hình API Endpoint

Nếu Backend chạy trên VPS / Cloud:

```javascript
const API_BASE_URL = "http://<SERVER-IP>:8000";
```

Cập nhật biến trên trong:

* `index.html`
* `search.html`

---

# 📡 API Documentation

| Endpoint         | Method | Chức năng                      | Parameters           |
| ---------------- | ------ | ------------------------------ | -------------------- |
| `/api/trending/` | GET    | Lấy danh sách từ khóa xu hướng | `time`, `category`   |
| `/api/topics/`   | GET    | Lấy danh sách chủ đề LDA       | Không có             |
| `/api/search/`   | GET    | Tìm kiếm bài báo               | `q`, `page`, `limit` |

---

# 📊 Chức năng Chính

## 🔥 Trending Keyword Analysis

* Phân tích từ khóa nổi bật
* Xếp hạng bằng Z-Score
* Theo dõi theo thời gian

## 🧠 Topic Modeling

* Phân cụm chủ đề bằng LDA
* Phân tích xu hướng vĩ mô

## 📈 Real-time Visualization

* Dashboard trực quan
* Biểu đồ động với ECharts

## 🔍 News Search Engine

* Tìm kiếm bài báo theo từ khóa
* Phân trang dữ liệu

---

# 🧠 Công nghệ AI/NLP được sử dụng

## Underthesea

Dùng cho:

* Word Segmentation
* POS Tagging
* Vietnamese NLP preprocessing

## Gensim LDA

Dùng cho:

* Topic Modeling
* Phân tích chủ đề báo chí

## Z-Score Algorithm

Dùng để:

* Phát hiện xu hướng bất thường
* Xếp hạng độ hot của từ khóa

---

# 🐳 Docker Architecture

Hệ thống gồm 5 containers:

| Container    | Vai trò                 |
| ------------ | ----------------------- |
| PostgreSQL   | Database                |
| Spark Master | Điều phối Spark Cluster |
| Spark Worker | Xử lý dữ liệu           |
| Django Web   | REST API                |
| Scheduler    | NLP Background Worker   |

---

# 📌 Mục tiêu Dự án

* Ứng dụng Big Data vào xử lý báo chí
* Xây dựng hệ thống phân tích xu hướng thời gian thực
* Triển khai mô hình Microservices
* Tối ưu pipeline dữ liệu tự động
* Kết hợp AI/NLP vào hệ thống thực tế

