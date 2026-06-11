import pandas as pd
import numpy as np
import os
import time
import re
from scipy.stats import linregress
from sklearn.preprocessing import MinMaxScaler
from underthesea import word_tokenize, text_normalize, ner, sent_tokenize 
from tqdm import tqdm
from sqlalchemy import create_engine, text
import warnings

# Thư viện cho LDA
import gensim
from gensim.models import LdaModel
import gensim.corpora as corpora

warnings.filterwarnings('ignore')

# =========================================================
# 🌟 CẤU HÌNH DATABASE & ĐƯỜNG DẪN AI
# =========================================================
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"
engine = create_engine(DB_URL)

MODEL_PATH = 'D:/PBL7_web/pbl7_web/core/ai_models/lda_model.gensim'
DICT_PATH = 'D:/PBL7_web/pbl7_web/core/ai_models/lda_dictionary.dict'
STOPWORDS_FILE = 'D:/PBL7_web/pbl7_web/core/ai_models/vietnamese-stopwords.txt'

TOPIC_LABELS = {
    1: "Giáo dục Đại học & Nghiên cứu", 2: "Thể thao & Bóng đá",
    3: "Doanh nghiệp & Phát triển Xanh", 4: "Tuyển sinh & Giáo dục phổ thông",
    5: "Chính trị Quốc tế & Xung đột", 6: "Văn hóa & Sự kiện Xã hội",
    7: "Y tế, Sức khỏe & Thực phẩm", 8: "Đời sống, Gia đình & Xã hội",
    9: "Giải trí & Nghệ thuật", 10: "Kinh tế, Tài chính & Ngân hàng",
    11: "Quản lý Hành chính & Đô thị"
}

# =========================================================
# 🌟 CÁC HÀM TIỀN XỬ LÝ LÕI AI
# =========================================================
def load_stopwords(filepath):
    EXTRA_STOPWORDS = {'cho_biết', 'được_biết', 'liên_quan', 'thực_hiện', 'tại_đây'}
    if not os.path.exists(filepath): return EXTRA_STOPWORDS
    with open(filepath, 'r', encoding='utf-8') as f:
        return set(line.strip().replace(" ", "_") for line in f if line.strip()).union(EXTRA_STOPWORDS)

STOPWORDS = load_stopwords(STOPWORDS_FILE)

PREFIX_REGEX = re.compile(
    r'^(ủy ban nhân dân|ubnd|công an|sở gd\&đt|bộ|sở|ban|ngành|'
    r'tỉnh|thành phố|tp\.?|quận|huyện|phường|xã|thị trấn|thôn|ấp|bản|'
    r'đường|phố|đại lộ|cầu|sông|hồ|trường đại học|trường|trung tâm|viện|công ty|tập đoàn|'
    r'tuổi|thứ|cái|chiếc)\s+',
    re.IGNORECASE
)

def process_vietnamese_text(text_content, custom_stopwords):
    if not isinstance(text_content, str): return ""
    text_content = re.sub(r'([.,!?:;()\[\]{}])', r' \1 ', text_content)
    text_content = text_normalize(text_content).lower()
    text_content = re.sub(r'http\S+|www\S+|https\S+|\S+@\S+|@\S+|#\S+', '', text_content)
    text_content = re.sub(r'\b\d+\w*\b', '', text_content)
    text_content = re.sub(r'[^\w\s]', ' ', text_content).strip()
    if not text_content: return ""
    words = word_tokenize(text_content, format="text").split()
    return " ".join([w for w in words if w not in custom_stopwords and ("_" in w or len(w) > 3)])

def extract_entities_by_ner(text_content):
    if not isinstance(text_content, str) or text_content.strip() == "": return []
    try:
        text_raw = text_content.replace('_', ' ')
        sentences = sent_tokenize(text_raw)
        entities = set()
        
        BLACK_LIST = {
            'dân_trí', 'báo', 'vnexpress', 'thanh_niên', 'tuổi_trẻ', 'vietnamnet', 'vtv',
            'chủ_tịch', 'tổng_thống', 'giám_đốc', 'lãnh_đạo', 'thủ_tướng', 'đại_sứ',
            'đảng', 'trung_ương', 'nhà_nước', 'chính_phủ', 'quốc_hội', 'bộ_chính_trị',
            'người', 'tuổi', 'biển', 'công_nghiệp', 'hệ_thống', 'đối_thoại', 'trung_tâm',
            'trường', 'tỉnh', 'thành_phố', 'phường', 'xã', 'huyện', 'quận', 'công_an',
            'ngày', 'tháng', 'năm', 'nước', 'đường', 'phóng_viên', 'video', 'news', 'pccc&cnch',
            'triệu_đồng', 'tỷ_đồng', 'nghìn_tỷ', 'st', 'vn' 
        }

        GENERIC_LOCATIONS = {
            'việt_nam', 'hà_nội', 'tp_hcm', 'tphcm', 'hồ_chí_minh', 'đà_nẵng', 'quốc_gia', 'thế_giới',
            'trung_quốc', 'mỹ', 'nga', 'pháp', 'anh', 'đức', 'nhật_bản', 'hàn_quốc', 'thái_lan', 'campuchia',
            'ukraine', 'iran', 'israel', 'palestine', 'syria', 'indonesia', 'malaysia', 'philippines',
            'châu_á', 'châu_âu', 'châu_phi', 'châu_mỹ', 'đông_nam_á', 'biển_đông',
            'an_giang', 'phú_thọ', 'lâm_đồng', 'bình_dương', 'đồng_nai', 'long_an'
        }

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10: continue
            
            tagged = ner(sentence)
            current_entity = []
            
            for word, pos, chunk, label in tagged:
                clean_word = word.replace('_', ' ')
                if label != 'O' and any(t in label for t in ['PER', 'LOC', 'ORG']):
                    if label.startswith('B-'):
                        if current_entity: entities.add(" ".join(current_entity))
                        if pos in ['Np', 'Ny', 'N']: current_entity = [clean_word]
                        else: current_entity = []
                    elif label.startswith('I-'):
                        if current_entity: current_entity.append(clean_word)
                else:
                    if current_entity: entities.add(" ".join(current_entity)); current_entity = []
            if current_entity: entities.add(" ".join(current_entity))

        final_entities = []
        for ent in entities:
            old_ent = ""
            while old_ent != ent:
                old_ent = ent
                ent = PREFIX_REGEX.sub('', ent).strip() 
                
            ent_lower = ent.lower().replace(' ', '_')
            
            if re.search(r'(năm_\d{4}|tháng_\d{1,2}|ngày_\d{1,2}|quý_\d|thế_kỷ)', ent_lower): continue
            if re.search(r'(giờ_việt_nam|sáng_nay|chiều_nay|tối_nay|hiện_nay)', ent_lower): continue
            if re.search(r'(miền_bắc|miền_trung|miền_nam|tây_bắc|đông_bắc|đồng_bằng)', ent_lower): continue
            if re.search(r'(lớp_\d{1,2})', ent_lower): continue
            
            if (len(ent_lower) >= 4 and '_' in ent_lower and not ent_lower.isnumeric() and 
                not any(char in ent_lower for char in ['|', '-', ':', '/', '.']) and 
                ent_lower not in BLACK_LIST and ent_lower not in GENERIC_LOCATIONS):
                final_entities.append(ent_lower)
                
        return final_entities
    except:
        return []

# =========================================================
# 🌟 BƯỚC 2: MAIN PIPELINE (CHẾ ĐỘ TEST - KHÔNG GHI DATABASE)
# =========================================================
if __name__ == '__main__':
    print("🚀 BƯỚC 2: PHÂN TÍCH TRENDING BÀI BÁO (CHẾ ĐỘ TEST / DRY-RUN)")
    print("=" * 80)
    start_time_total = time.time()

    print("\n⏳ Đang tải các bài báo MỚI (PENDING) để xử lý thử...")
    query = """
        SELECT id, title, content, published_at, tags 
        FROM raw_articles 
        WHERE title IS NOT NULL 
          AND content IS NOT NULL
          AND status = 'PENDING'
    """
    df = pd.read_sql(query, engine)

    if df.empty:
        print("✅ Không có bài báo PENDING nào để phân tích! Hệ thống nghỉ ngơi.")
        exit()

    print("⏳ Kiểm tra và loại bỏ các bài báo trùng lặp (Chỉ lọc trên RAM)...")
    duplicate_mask = df.duplicated(subset=['title'], keep='first') | df.duplicated(subset=['content'], keep='first')
    df_duplicates = df[duplicate_mask]
    df = df[~duplicate_mask] 

    if not df_duplicates.empty:
        print(f"♻️ Phát hiện {len(df_duplicates)} bài báo trùng lặp. [TEST MODE: Đã bỏ qua, không ghi status DUPLICATE vào DB]")

    if df.empty:
        print("✅ Sau khi lọc trùng trên RAM, không còn bài báo nào. Hệ thống nghỉ ngơi.")
        exit()

    df['published_at'] = pd.to_datetime(df['published_at'])
    df['date'] = df['published_at'].dt.date
    target_date = df['date'].max()

    print(f"✅ Đã tải {len(df)} bài báo mới KHÔNG TRÙNG LẶP. Phân tích thử cho mốc: {target_date.strftime('%Y-%m-%d')}")
    df['raw_full_text_ner'] = df['title'].astype(str) + ". " + df['content'].astype(str)
    
    # ---------------------------------------------------------
    # 2. PHÂN TÍCH CHỦ ĐỀ VĨ MÔ (LDA)
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("⏳ Đang phân tích chủ đề bài viết bằng LDA (Không lưu DB)...")
    
    tqdm.pandas(desc="🧠 Làm sạch Text cho LDA")
    df['clean_text_lda'] = df['title'].progress_apply(lambda x: process_vietnamese_text(x, STOPWORDS)) + " " + df['content'].progress_apply(lambda x: process_vietnamese_text(x, STOPWORDS))
    
    try:
        lda_model = LdaModel.load(MODEL_PATH)
        id2word = corpora.Dictionary.load(DICT_PATH)
    except Exception as e:
        print(f"🚨 LỖI TẢI MÔ HÌNH LDA: {e}"); exit()

    def assign_topic(text_content):
        try:
            if not str(text_content).strip(): return 1
            bow = id2word.doc2bow(text_content.split())
            if not bow: return 1
            probs = lda_model.get_document_topics(bow)
            return sorted(probs[0] if isinstance(probs, tuple) else probs, key=lambda x: x[1], reverse=True)[0][0] + 1
        except: return 1

    tqdm.pandas(desc="🧠 Gắn nhãn LDA")
    df['topic_id'] = df['clean_text_lda'].progress_apply(assign_topic)
    
    # [TEST MODE] Tắt lưu article_topic_map
    print("✅ [TEST MODE] Đã phân tích xong LDA. Bỏ qua ghi bảng article_topic_map, topic_daily_stats và lda_topics.")

    # ---------------------------------------------------------
    # 3. BÓC TÁCH THỰC THỂ NER CHO CÁC BÀI BÁO MỚI
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("🔪 AI đang bóc tách NER cho các bài báo mới...")
    
    tqdm.pandas(desc="🧠 Chạy NER")
    df['extracted_entities'] = df['raw_full_text_ner'].progress_apply(extract_entities_by_ner)
    df_valid_ner = df[df['extracted_entities'].map(len) > 0]

    if not df_valid_ner.empty:
        all_entities = [ent for sublist in df_valid_ner['extracted_entities'] for ent in sublist]
        from collections import Counter
        top_preview = Counter(all_entities).most_common(30)
        
        print("\n" + "="*80)
        print("👀 [REVIEW NHANH] TOP 30 TỪ KHÓA AI VỪA TÌM THẤY TRONG MẺ BÁO NÀY:")
        print(f"👉 Tổng số thực thể hợp lệ đã bóc: {len(all_entities)} từ.")
        preview_text = " | ".join([f"{word} ({count})" for word, count in top_preview])
        print(f"   {preview_text}")
        print("="*80 + "\n")

        df_exploded = df_valid_ner[['id', 'extracted_entities']].explode('extracted_entities')
        df_exploded.columns = ['article_id', 'keyword']
        
        # [TEST MODE] Tắt lưu ner_article_keyword_map và update DB
        print("✅ [TEST MODE] Bỏ qua ghi bảng ner_article_keyword_map và ner_keyword_daily_stats vào Database.")

    # ---------------------------------------------------------
    # 4. CHẤM ĐIỂM Z-SCORE (GIẢ LẬP DỮ LIỆU TRÊN RAM)
    # ---------------------------------------------------------
    target_date_str = target_date.strftime('%Y-%m-%d')
    print("\n⏳ Đang tải lịch sử cũ & Giả lập dữ liệu hôm nay trên RAM để chấm điểm Z-Score...")
    
    # 1. Tính toán thống kê hôm nay ngay trên RAM bằng Pandas
    today_stats = df_exploded.groupby('keyword').size().reset_index(name='count')
    today_stats['date'] = target_date 
    
    # 2. Tải dữ liệu lịch sử từ DB (Loại bỏ hôm nay để phòng ngừa trùng lặp nếu lỡ có)
    df_history_ner = pd.read_sql(f"SELECT * FROM ner_keyword_daily_stats WHERE date < '{target_date_str}'", engine)
    
    # 3. Nối lịch sử với hiện tại
    df_daily_ner = pd.concat([df_history_ner, today_stats], ignore_index=True)
    
    df_pivot = df_daily_ner.pivot(index='date', columns='keyword', values='count').fillna(0).sort_index()
    keyword_metrics = []
    
    dynamic_tags = set()
    if 'tags' in df.columns:
        for tag_str in df[df['date'] == target_date]['tags'].dropna():
            dynamic_tags.update([t.strip().lower().replace(' ', '_') for t in str(tag_str).split(',')])

    for kw in df_pivot.columns:
        counts = df_pivot[kw].values
        if len(counts) > 1 and counts[-1] >= 2:
            spec_weight = 2.0 if any(f"_{kw}_" in f"_{tag}_" or kw == tag for tag in dynamic_tags) else 1.0
            slope = linregress(np.arange(len(counts)), counts)[0]
            
            hist = np.array(counts[:-1], dtype=float)
            if len(hist) > 2:
                baseline = np.median(hist)
                for i in range(len(hist)): 
                    if hist[i] > (baseline * 3) and hist[i] > 5: hist[i] *= 0.5
            
            z_score = (counts[-1] - np.mean(hist)) / (np.std(hist, ddof=1) + 1.0)
            keyword_metrics.append({'Keyword': kw, 'Popularity': float(sum(counts)), 'Trend': float(slope), 'Z_Score': float(z_score), 'Spec_W': float(spec_weight)})

    df_metrics = pd.DataFrame(keyword_metrics)
    if not df_metrics.empty:
        scaler = MinMaxScaler()
        df_metrics[['p_n', 't_n', 'z_n']] = scaler.fit_transform(df_metrics[['Popularity', 'Trend', 'Z_Score']])
        df_metrics['SUPER_HOT_SCORE'] = ((0.6 * df_metrics['z_n'] + 0.2 * df_metrics['p_n'] + 0.2 * df_metrics['t_n']) * df_metrics['Spec_W'])
        df_metrics = df_metrics.sort_values('SUPER_HOT_SCORE', ascending=False)
        
        def jaccard_filter(df_input):
            filtered, saved = [], []
            for _, row in df_input.iterrows():
                roots = set([w for w in str(row['Keyword']).split('_') if len(w) >= 3])
                if not roots: filtered.append(row); continue
                dup = False
                for s in saved:
                    inter = roots.intersection(s)
                    if len(inter) > 0 and (len(inter) / min(len(roots), len(s))) >= 0.6: dup = True; break
                if not dup: saved.append(roots); filtered.append(row)
            return pd.DataFrame(filtered)

        df_final = jaccard_filter(df_metrics).head(60)
        
        df_save = df_final[['Keyword', 'Popularity', 'Trend', 'Z_Score', 'SUPER_HOT_SCORE']].copy()
        df_save.columns = ['Keyword', 'Popularity', 'Trend', 'Z_Score', 'Super_Hot_Score']
        df_save['date'] = target_date_str
        
        # [TEST MODE] Tắt xóa/ghi bảng trending_keywords
        print("✅ [TEST MODE] Đã giả lập chấm điểm xong. Bỏ qua ghi đè bảng trending_keywords.")
        
        print("\n" + "="*80)
        print(f"👑 BẢNG XẾP HẠNG TOP 60 SỰ KIỆN & THỰC THỂ NÓNG NHẤT NGÀY {target_date_str} (BẢN TEST):")
        print("-" * 80)
        display_cols = ['Keyword', 'Popularity', 'Trend', 'Z_Score', 'Super_Hot_Score']
        print(df_save[display_cols].round(3).to_string(index=False))

    # ---------------------------------------------------------
    # 5. KHÓA SỔ CÁC BÀI BÁO PENDING THÀNH PROCESSED
    # ---------------------------------------------------------
    print("\n⏳ [TEST MODE] Bỏ qua bước update status bài báo thành PROCESSED. (Bài báo vẫn là PENDING)")

    print("\n" + "=" * 80)
    print(f"🎉 HOÀN TẤT CHẠY TEST SAU {round(time.time() - start_time_total, 2)} GIÂY!")
    print("=" * 80)