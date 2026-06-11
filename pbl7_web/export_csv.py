import pandas as pd
from sqlalchemy import create_engine

# Kết nối database của bạn
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"
engine = create_engine(DB_URL)

print("⏳ Đang kéo dữ liệu bài báo từ Database...")

# Lấy các cột quan trọng (Bỏ cột nội dung nếu file quá nặng, hoặc dùng SELECT * để lấy hết)
query = """
    SELECT title,content
    FROM raw_articles 
    ORDER BY published_at DESC
"""
df = pd.read_sql(query, engine)

print(f"✅ Đã tải xong {len(df)} bài báo. Đang lưu ra file CSV...")

# Lưu ra CSV, dùng utf-8-sig để Excel đọc tiếng Việt chuẩn xác
df.to_csv("danh_sach_bai_bao.csv", index=False, encoding='utf-8-sig')

print("🎉 Xuất CSV thành công! File 'danh_sach_bai_bao.csv' đã nằm trong máy của bạn.")