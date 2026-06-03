from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"
engine = create_engine(DB_URL)

with engine.connect() as conn:
    # Lệnh xóa sạch dữ liệu và reset lại ID về số 1
    conn.execute(text("TRUNCATE TABLE raw_articles RESTART IDENTITY CASCADE;"))
    conn.commit()
print("✅ Đã dọn sạch Database! Sẵn sàng đón dữ liệu Gốc.")