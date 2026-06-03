from sqlalchemy import create_engine, text

# Cấu hình Database
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"

# Khởi tạo engine
engine = create_engine(DB_URL)

if __name__ == '__main__':
    print("☢️ BẮT ĐẦU 'SAN PHẲNG' TOÀN BỘ HỆ THỐNG DATABASE...")

    try:
        with engine.connect() as conn:
            # Lệnh DROP TABLE IF EXISTS CASCADE sẽ:
            # 1. Xóa hoàn toàn bảng (nếu bảng đó tồn tại)
            # 2. CASCADE: Tự động xóa các khóa ngoại (Foreign Keys) liên kết với nó
            sql_command = text("""
                DROP TABLE IF EXISTS article_topic_map;
                DROP TABLE IF EXISTS topic_daily_stats CASCADE;
                DROP TABLE IF EXISTS lda_topics CASCADE;
            """)
            
            conn.execute(sql_command)
            conn.commit()

        print("✅ THÀNH CÔNG: Đã xóa sạch sẽ toàn bộ dữ liệu và cấu trúc bảng!")
        print("💡 Database của bạn hiện tại đã 'trắng tinh' như lúc mới cài.")

    except Exception as e:
        print(f"🚨 Có lỗi xảy ra trong quá trình xóa: {e}")