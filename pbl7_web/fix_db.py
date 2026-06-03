from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"
engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        # Lệnh SQL thêm cột id tự động tăng (SERIAL) và làm Khóa chính (PRIMARY KEY)
        conn.execute(text("ALTER TABLE raw_articles ADD COLUMN id SERIAL PRIMARY KEY;"))
        conn.commit()
    print("✅ HOÀN TẤT: Đã thêm thành công cột 'id' vào bảng raw_articles!")
except Exception as e:
    print(f"⚠️ Có lỗi xảy ra (Hoặc cột id đã tồn tại): {e}")