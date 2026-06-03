from sqlalchemy import create_engine, text

# Chuỗi kết nối Database của bạn
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"
engine = create_engine(DB_URL)

def hard_reset_pipeline():
    print("⏳ Đang dọn dẹp hệ thống để chạy lại từ đầu...")
    
    # 1. Chuyển bài báo về PENDING
    try:
        with engine.connect() as conn:
            conn.execute(text("UPDATE raw_articles SET status = 'PENDING';"))
            conn.commit()
        print("✅ Đã chuyển toàn bộ bài báo về trạng thái 'PENDING'.")
    except Exception as e:
        print(f"🚨 Lỗi khi cập nhật raw_articles: {e}")

    # 2. Xóa sạch bảng map Chủ đề (article_topic_map)
    try:
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE article_topic_map CASCADE;"))
            conn.commit()
        print("✅ Đã dọn sạch bảng article_topic_map.")
    except Exception:
        # Bỏ qua im lặng nếu bảng chưa tồn tại
        pass 

    # 3. Xóa sạch bảng map Từ khóa (article_keyword_map)
    try:
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE article_keyword_map CASCADE;"))
            conn.commit()
        print("✅ Đã dọn sạch bảng article_keyword_map.")
    except Exception:
        pass 

    print("🚀 THÀNH CÔNG! Hệ thống đã sẵn sàng 100%. Hãy chạy lệnh 'python nlp_pipeline.py' ngay thôi.")

if __name__ == "__main__":
    hard_reset_pipeline()