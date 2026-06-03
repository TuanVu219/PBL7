from sqlalchemy import create_engine, text

# Cấu hình Database (Phải giống hệt trong nlp_pipeline.py)
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"

# Khởi tạo engine
engine = create_engine(DB_URL)

if __name__ == '__main__':
    print("🧹 BẮT ĐẦU DỌN DẸP DỮ LIỆU RÁC...")

    try:
        with engine.connect() as conn:
            # Lệnh TRUNCATE CASCADE sẽ xóa sạch dữ liệu trong 3 bảng này
            # CASCADE giúp đảm bảo nếu có ràng buộc khóa ngoại thì nó cũng xử lý luôn
            sql_command = text("""
                TRUNCATE TABLE 
                    article_keyword_map, 
                    keyword_daily_stats, 
                    trending_keywords 
                CASCADE;
            """)
            
            conn.execute(sql_command)
            conn.commit()

        print("✅ Dọn dẹp thành công! Các bảng từ khóa đã trống trơn.")
        print("🚀 Bạn có thể yên tâm chạy lại lệnh 'python nlp_pipeline.py' ngay bây giờ!")

    except Exception as e:
        print(f"🚨 Có lỗi xảy ra trong quá trình dọn dẹp: {e}")