import pandas as pd
import re
import os
import time
import numpy as np
from sqlalchemy import create_engine, text
from underthesea import word_tokenize, text_normalize
from tqdm import tqdm
import gensim
from gensim.models import LdaModel
import gensim.corpora as corpora
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. CẤU HÌNH ĐƯỜNG DẪN & DATABASE
# ==========================================
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"
engine = create_engine(DB_URL)

MODEL_PATH = 'D:/PBL7_web/pbl7_web/core/ai_models/lda_model.gensim'
DICT_PATH = 'D:/PBL7_web/pbl7_web/core/ai_models/lda_dictionary.dict'

# 🟢 ĐÃ SỬA 1: Trả về 11 chủ đề
TOPIC_LABELS = {
    1: "Giáo dục Đại học & Nghiên cứu", 2: "Thể thao & Bóng đá",
    3: "Doanh nghiệp & Phát triển Xanh", 4: "Tuyển sinh & Giáo dục phổ thông",
    5: "Chính trị Quốc tế & Xung đột", 6: "Văn hóa & Sự kiện Xã hội",
    7: "Y tế, Sức khỏe & Thực phẩm", 8: "Đời sống, Gia đình & Xã hội",
    9: "Giải trí & Nghệ thuật", 10: "Kinh tế, Tài chính & Ngân hàng",
    11: "Quản lý Hành chính & Đô thị"
}

# ==========================================
# 2. HÀM LÀM SẠCH VĂN BẢN 
# ==========================================
CUSTOM_NOISE_WORDS = {
    'đồng', 'triệu', 'tỷ', 'nghìn', 'việt_nam', 'hà_nội', 'thế_giới', 'quốc_tế', 'tỉnh', 'khu_vực', 'quốc_gia',
    'phát_triển', 'quy_định', 'thị_trường', 'cơ_quan', 'tổ_chức', 'hệ_thống', 'công_ty', 'dự_án', 
    'hoạt_động', 'thực_hiện', 'quản_lý', 'thông_tin', 'cơ_sở', 'xác_định', 'trường_hợp', 'nội_dung',
    'chiều', 'khả_năng', 'yếu_tố', 'mà_còn', 'nhất_độ', 'rõ_ràng', 'tương_tự', 'viết', 'tên', 
    'nhanh_chóng', 'trở_lại', 'tuần', 'phiên', 'cho_biết', 'được_biết', 'liên_quan', 'tại_đây',
    'nêu_trên', 'trước_đó', 'hiện_nay', 'ngày_nay', 'hôm_nay', 'hôm_qua', 'ngày_mai', 'nói_chung',
    'tất_cả', 'theo_đó', 'cụ_thể', 'vẫn_đang', 'nhằm', 'giúp', 'mang_lại', 'trở_thành', 'vừa_qua'
}
STOPWORDS = CUSTOM_NOISE_WORDS.union({"và", "của", "là", "có", "được", "cho", "trong", "một"})

def clean_text_for_lda(text_content):
    if not isinstance(text_content, str): return ""
    text_content = re.sub(r'([.,!?:;()\[\]{}])', r' \1 ', text_content)
    text_content = text_normalize(text_content).lower()
    text_content = re.sub(r'http\S+|www\S+|https\S+|\S+@\S+|@\S+|#\S+', '', text_content)
    text_content = re.sub(r'\b\d+\w*\b', '', text_content)
    text_content = re.sub(r'[^\w\s]', ' ', text_content).strip()
    if not text_content: return ""
    
    words = word_tokenize(text_content, format="text").split()
    final_words = [w for w in words if w not in STOPWORDS and ("_" in w or len(w) > 4)]
    return " ".join(final_words)

# ==========================================
# 3. CHẠY CẬP NHẬT DATABASE
# ==========================================
if __name__ == '__main__':
    start_time = time.time()
    print("🚀 BẮT ĐẦU CHIẾN DỊCH CẬP NHẬT CHỦ ĐỀ CHO BÀI BÁO ĐÃ PROCESSED (11 CHỦ ĐỀ)")
    
    # 1. Tải Model
    print("⏳ Đang tải mô hình LDA mới...")
    lda_model = LdaModel.load(MODEL_PATH)
    id2word = corpora.Dictionary.load(DICT_PATH)
    
    # 2. Lấy dữ liệu
    print("⏳ Đang tải dữ liệu gốc từ Database...")
    query = """
        SELECT id, title, content, published_at
        FROM raw_articles 
        WHERE title IS NOT NULL 
          AND content IS NOT NULL 
          AND status = 'PROCESSED'
    """
    df = pd.read_sql(query, engine)
    
    if df.empty:
        print("✅ Không tìm thấy bài báo. Kết thúc.")
        exit()
        
    print(f"✅ Đã tải {len(df)} bài báo (PROCESSED).")

    # 3. Phân cụm
    tqdm.pandas(desc="🧠 Đang phân tích chủ đề")
    def assign_new_topic(row):
        text = str(row['title']) + " " + str(row['content'])
        cleaned = clean_text_for_lda(text)
        if not cleaned.strip(): return 1
        bow = id2word.doc2bow(cleaned.split())
        if not bow: return 1
        probs = lda_model.get_document_topics(bow)
        best_topic = sorted(probs[0] if isinstance(probs, tuple) else probs, key=lambda x: x[1], reverse=True)[0][0] + 1
        return best_topic

    df['topic_id'] = df.progress_apply(assign_new_topic, axis=1)

    # Tính toán lại bảng thống kê ngày
    print("\n⏳ Đang tính toán lại thống kê % chủ đề theo ngày...")
    df['date'] = pd.to_datetime(df['published_at']).dt.date
    trend_data = df.groupby(['date', 'topic_id']).size().reset_index(name='article_count')
    total_per_day = trend_data.groupby('date')['article_count'].transform('sum')
    trend_data['percentage'] = (trend_data['article_count'] / total_per_day) * 100

    # 4. Ghi đè vào Database
    print("⏳ Đang ghi đè dữ liệu mới vào Database...")
    df_map = df[['id', 'topic_id']].rename(columns={'id': 'article_id'})
    
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE article_topic_map CASCADE"))
        conn.execute(text("TRUNCATE TABLE lda_topics CASCADE"))
        conn.execute(text("TRUNCATE TABLE topic_daily_stats CASCADE")) 
        conn.commit()
    
    # Nạp dữ liệu mới
    df_map.to_sql('article_topic_map', engine, if_exists='append', index=False)
    trend_data.rename(columns={'date': 'Date'}).to_sql('topic_daily_stats', engine, if_exists='append', index=False)
    
    # Tính toán độ dốc (Acceleration) dựa trên trend_data
    topic_records = []
    
    # 🟢 ĐÃ SỬA 2: Vòng lặp chạy từ 1 đến 11 (range(1, 12))
    for t_id in range(1, 12): 
        t_data = trend_data[trend_data['topic_id'] == t_id].sort_values('date')
        
        if len(t_data) > 1:
            from scipy.stats import linregress
            slope = linregress(np.arange(len(t_data)), t_data['percentage'].values)[0]
        else:
            slope = 0.0
        
        trend_type = "🔥 Đang bùng nổ" if slope > 0.5 else ("❄️ Đang hạ nhiệt" if slope < -0.5 else "⚖️ Đi ngang")
        topic_records.append({
            'topic_id': t_id, 
            'topic_name': TOPIC_LABELS.get(t_id, f"Chủ đề {t_id}"), 
            'acceleration': float(slope), 
            'trend_type': trend_type
        })
        
    pd.DataFrame(topic_records).to_sql('lda_topics', engine, if_exists='append', index=False)

    print("=" * 80)
    print(f"🎉 HOÀN TẤT THAY MÁU HỆ THỐNG TRONG {round(time.time() - start_time, 2)} GIÂY!")