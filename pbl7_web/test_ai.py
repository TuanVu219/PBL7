import pandas as pd
from sqlalchemy import create_engine
from underthesea import ner

# Cấu hình Database
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"
engine = create_engine(DB_URL)

print("⏳ Đang kéo 1 bài báo từ Database ra kiểm tra...")
# Lấy đúng 1 bài báo đầu tiên
df = pd.read_sql("SELECT title, content FROM raw_articles LIMIT 1", engine)

if df.empty:
    print("🚨 DATABASE TRỐNG KHÔNG! Hãy kiểm tra lại file import_csv_to_db.py")
else:
    title = str(df.iloc[0]['title'])
    content = str(df.iloc[0]['content'])
    text_raw = title + ". " + content
    
    print("\n" + "="*80)
    print("🔍 ĐÂY LÀ ĐOẠN TEXT MÀ AI SẼ ĐỌC:")
    print("="*80)
    # Chỉ in 300 ký tự đầu tiên để đỡ rối mắt
    print(text_raw[:300] + "...") 
    print("="*80)
    
    print("\n⏳ Đang cho AI quét thử đoạn văn này...")
    tagged = ner(text_raw)
    
    print("✅ KẾT QUẢ AI NHẬN DIỆN ĐƯỢC (Tất cả các từ):")
    for item in tagged[:20]: # In thử 20 từ đầu tiên
        print(item)