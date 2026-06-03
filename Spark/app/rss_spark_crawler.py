import time
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql import Row

import pandas as pd
from sqlalchemy import create_engine

# ==========================================
# 1. CẤU HÌNH DATABASE & NGUỒN RSS
# ==========================================
# 🌟 QUAN TRỌNG: Dùng 'host.docker.internal' thay vì 'localhost' để Docker tìm được Postgres trên máy thật
DB_URL = "postgresql://postgres:123456@host.docker.internal:5432/postgres"

SITE_CATEGORIES = {
    "dantri.com.vn": [
        "xa-hoi", "thoi-su", "phap-luat", "the-gioi", "kinh-doanh", 
        "bat-dong-san", "the-thao", "giai-tri", "giao-duc", "suc-khoe", 
        "khoa-hoc", "suc-manh-so", "oto-xe-may"
    ],
    "vietnamnet.vn": [
        "thoi-su", "chinh-tri", "giao-duc", "van-hoa-giai-tri", "kinh-doanh", 
        "the-gioi", "the-thao", "phap-luat", "suc-khoe", "cong-nghe", 
        "bat-dong-san", "oto-xe-may"
    ],
    "vnexpress.net": [
        "thoi-su", "the-gioi", "kinh-doanh", "the-thao", "phap-luat", 
        "giao-duc", "suc-khoe", "giai-tri", "khoa-hoc", "so-hoa", "xe"
    ],
    "tuoitre.vn": [
        "thoi-su", "the-gioi", "phap-luat", "kinh-doanh", "cong-nghe", 
        "xe", "the-thao", "giai-tri", "giao-duc", "suc-khoe"
    ]
}

RSS_CONFIGS = []
for site, categories in SITE_CATEGORIES.items():
    for cate in categories:
        RSS_CONFIGS.append({
            "source": site,
            "category": cate, 
            "url": f"https://{site}/rss/{cate}.rss"
        })

CRAWL_INTERVAL = 600

# ==========================================
# 2. HÀM XỬ LÝ TRÊN CÁC WORKER NODE
# ==========================================
def fetch_and_parse_rss(config, broadcast_seen_links):
    source = config['source']
    category = config['category']
    rss_url = config['url']
    
    parsed_feed = feedparser.parse(rss_url)
    seen_links = broadcast_seen_links.value
    new_articles = []
    
    today_date = datetime.now().date()
    
    for entry in parsed_feed.entries:
        link = entry.get('link', '')
        
        if not link or link in seen_links:
            continue
            
        raw_date = entry.get('published', '')
        try:
            parsed_date = date_parser.parse(raw_date).replace(tzinfo=None)
            article_date = parsed_date.date()
            pub_date_str = parsed_date.strftime('%Y-%m-%d %H:%M:%S') # Format chuẩn SQL
        except:
            continue
            
        if article_date != today_date:
            continue
            
        title = entry.get('title', 'Không có tiêu đề')
        
        raw_summary = entry.get('summary', '')
        content = BeautifulSoup(raw_summary, "html.parser").get_text(strip=True)
        
        tags = ""
        if 'tags' in entry:
            tags = ", ".join([t.term for t in entry.tags])
            
        new_articles.append({
            "published_at": pub_date_str,
            "source": source,
            "category": category,
            "title": title,
            "content": content,
            "tags": tags,
            "url": link
        })
        
    return new_articles

# ==========================================
# 3. CHƯƠNG TRÌNH CHÍNH (SPARK DRIVER)
# ==========================================
def main():
    print("⏳ Khởi tạo Spark Session...")
    spark = SparkSession.builder \
        .appName("Continuous_Daily_RSS_Crawler_To_DB") \
        .master("spark://spark-master:7077") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")
    seen_links = set()

    # Khởi tạo kết nối DB dùng chung cho cả phiên
    try:
        engine = create_engine(DB_URL)
        print("✅ Kết nối PostgreSQL thành công!")
        
        # ========================================================
        # 🌟 VŨ KHÍ MỚI: PHỤC HỒI TRÍ NHỚ TỪ DATABASE ĐỂ CHỐNG TRÙNG
        # ========================================================
        print("⏳ Đang kiểm tra lịch sử dữ liệu hôm nay trong Database...")
        today_str = datetime.now().strftime("%Y-%m-%d")
        query_history = f"SELECT url FROM raw_articles WHERE DATE(published_at) = '{today_str}'"
        
        try:
            # Rút các link đã cào trong ngày hôm nay từ DB lên
            df_history = pd.read_sql(query_history, engine)
            if not df_history.empty:
                # Đổ toàn bộ link cũ vào bộ nhớ đệm seen_links
                seen_links.update(df_history['url'].tolist())
            print(f"🛡 Đã nạp thành công {len(seen_links)} link bài báo cũ. Đảm bảo chống trùng lặp 100%!")
        except Exception:
            # Lỗi này chỉ xảy ra ở LẦN CHẠY ĐẦU TIÊN khi bảng raw_articles chưa được tạo
            print("📭 Bảng dữ liệu trống hoặc chưa được tạo. Đây là lần chạy đầu tiên!")
            
    except Exception as e:
        print(f"🚨 LỖI KẾT NỐI DATABASE: {e}")
        return

    print("\n" + "🔥"*35)
    print(f"BẮT ĐẦU CÀO BÁO (10 PHÚT/LẦN) ĐẨY THẲNG VÀO DATABASE")
    print("🔥"*35)

    while True:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 Bắt đầu quét {len(RSS_CONFIGS)} chuyên mục...")

        broadcast_seen = spark.sparkContext.broadcast(seen_links)
        
        rdd_configs = spark.sparkContext.parallelize(RSS_CONFIGS)
        rdd_articles = rdd_configs.flatMap(lambda conf: fetch_and_parse_rss(conf, broadcast_seen))
        
        new_articles_list = rdd_articles.collect()
        
        if not new_articles_list:
            print("📭 Không có tin nóng nào trong 10 phút vừa qua...")
        else:
            print(f"✅ Bắt được {len(new_articles_list)} tin tức mới xuất bản!")
            
            for article in new_articles_list:
                seen_links.add(article['url'])
                
            # 🌟 CỐT LÕI: Chuyển mảng List Dictionary thành Pandas DataFrame
            df_pd = pd.DataFrame(new_articles_list)
            
            # Ép kiểu dữ liệu ngày tháng
            df_pd['published_at'] = pd.to_datetime(df_pd['published_at'])
            
            # 🛑 MÀNG LỌC CUỐI: Xóa trùng lặp chéo ngay trong mẻ cào hiện tại
            # Giữ lại bản ghi đầu tiên, vứt bỏ các bản ghi trùng URL phía sau
            df_pd = df_pd.drop_duplicates(subset=['url'], keep='first')
            
            # Cập nhật lại list new_articles_list để báo cáo số lượng thực tế sau khi lọc
            actual_new_count = len(df_pd)
            print(f"🧹 Đã lọc bỏ bài trùng lặp. Số lượng thực tế chuẩn bị lưu: {actual_new_count}")

            # Gắn cờ PENDING cho Script AI phía sau xử lý
            df_pd['status'] = 'PENDING'
            
            # Đẩy thẳng vào Database (Đã xóa đoạn code thừa lưu lần 2)
            try:
                df_pd.to_sql(name='raw_articles', con=engine, if_exists='append', index=False)
                print(f"💾 Đã đổ thành công {actual_new_count} bài vào bảng 'raw_articles' trong PostgreSQL!")
            except Exception as e:
                print(f"❌ LỖI KHI GHI DATABASE: {e}")
            
        print(f"💤 Nghỉ 10 phút...\n")
        time.sleep(CRAWL_INTERVAL)

if __name__ == "__main__":
    main()