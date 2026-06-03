import pandas as pd
from sqlalchemy import create_engine
import os

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN VÀ DATABASE
# ==========================================
# 1. Điền đường dẫn tới file CSV đã tiền xử lý trên máy của bạn
CSV_PATH = "D:/PBL7_web/pbl7_web/cleaned_news_data_new_30_5_v2.csv" 

# 2. Chuỗi kết nối tới PostgreSQL Local
# Thay '123456' bằng mật khẩu thật bạn vừa đặt lúc cài đặt PostgreSQL
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"

def import_data():
    if not os.path.exists(CSV_PATH):
        print(f"⚠️ LỖI: Không tìm thấy file CSV tại đường dẫn: {CSV_PATH}")
        return

    print("⏳ Bước 1: Đang đọc file CSV vào bộ nhớ...")
    df = pd.read_csv(CSV_PATH)
    
    # Ép kiểu dữ liệu ngày tháng về chuẩn để Database nhận diện chính xác
    if 'published_at' in df.columns:
        df['published_at'] = pd.to_datetime(df['published_at'])

    # 🌟 CỐT LÕI ELT: Thêm cột trạng thái 'status' mặc định là 'PENDING'
    # Các bài báo mới nạp vào sẽ ở trạng thái chờ để Script AI sau này bốc ra xử lý
    df['status'] = 'PENDING'

    print(f"📊 Đã tải thành công {len(df)} dòng dữ liệu từ CSV. Chuẩn bị kết nối Database...")

    try:
        # Khởi tạo động cơ kết nối
        engine = create_engine(DB_URL)
        
        print("⏳ Bước 2: Đang đổ dữ liệu vào bảng 'raw_articles' trong PostgreSQL...")
        
        # Thực hiện đẩy dữ liệu vào Database
        # name='raw_articles': Tên bảng sẽ được tạo trong DB
        # if_exists='append': Ghi nối tiếp dữ liệu vào bảng (Nếu bảng chưa có, tự động tạo mới)
        df.to_sql(name='raw_articles', con=engine, if_exists='append', index=False)
        
        print("\n" + "="*50)
        print("✅ THÀNH CÔNG! ĐỒNG BỘ DỮ LIỆU HOÀN TẤT!")
        print("🚀 Toàn bộ bài báo thô đã nằm an toàn trong PostgreSQL Local.")
        print("="*50)

    except Exception as e:
        print(f"❌ LỖI KHI KẾT NỐI HOẶC GHI DATABASE: {e}")

if __name__ == "__main__":
    import_data()