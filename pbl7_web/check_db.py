# Script kiểm tra nhanh (check_db.py)
from sqlalchemy import create_engine, inspect

engine = create_engine("postgresql://postgres:123456@localhost:5432/postgres")
inspector = inspect(engine)

for table in ["keyword_daily_stats", "trending_keywords"]:
    columns = [c['name'] for c in inspector.get_columns(table)]
    print(f"Bảng {table} có các cột: {columns}")