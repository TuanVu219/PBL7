import pandas as pd
import numpy as np
import os
import time
import re
from scipy.stats import linregress
from sklearn.preprocessing import MinMaxScaler
# 🟢 Đã thêm sent_tokenize vào import
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

# 🟢 Đã cập nhật PREFIX_REGEX để chém bỏ các từ "tuổi", "thứ", "cái", "chiếc" đứng trước tên
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
        
        # 🟢 VŨ KHÍ 1: Dùng sent_tokenize thay cho split('.') để giữ nguyên tên có dấu chấm (như St. Petersburg)
        sentences = sent_tokenize(text_raw)
        
        entities = set()
        
        # 🟢 VŨ KHÍ 2: Bổ sung Blacklist các từ rác
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
                
                # 🟢 VŨ KHÍ 3: Đã loại bỏ thẻ MISC để triệt tiêu các từ rác do gom cụm sai (chỉ giữ PER, LOC, ORG)
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
                ent = PREFIX_REGEX.sub('', ent).strip() # Cắt bỏ các tiền tố không mong muốn
                
            ent_lower = ent.lower().replace(' ', '_')
            
            # Lọc từ rác cuối cùng (đã thêm dấu '.' vào bộ lọc ký tự đặc biệt)
            if (len(ent_lower) >= 4 and '_' in ent_lower and not ent_lower.isnumeric() and 
                not any(char in ent_lower for char in ['|', '-', ':', '/', '.']) and 
                ent_lower not in BLACK_LIST and ent_lower not in GENERIC_LOCATIONS):
                final_entities.append(ent_lower)
                
        return final_entities
    except:
        return []

# =========================================================
# 🌟 BƯỚC 2: MAIN PIPELINE (CHẠY INCREMENTAL HÀNG NGÀY)
# =========================================================
if __name__ == '__main__':
    print("🚀 BƯỚC 2: PHÂN TÍCH TRENDING BÀI BÁO MỚI HÀNG NGÀY")
    print("=" * 80)
    start_time_total = time.time()

    # 1. LOAD CÁC BÀI BÁO PENDING TỪ DATABASE
    print("\n⏳ Đang tải các bài báo MỚI (PENDING) để xử lý...")
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

    # =========================================================
    # 🔥 THÊM MỚI: MÀNG LỌC BÁO TRÙNG LẶP
    # =========================================================
    print("⏳ Kiểm tra và loại bỏ các bài báo trùng lặp...")
    # Gom các bài trùng Tiêu đề hoặc Nội dung
    duplicate_mask = df.duplicated(subset=['title'], keep='first') | df.duplicated(subset=['content'], keep='first')
    df_duplicates = df[duplicate_mask]
    df = df[~duplicate_mask] # Chỉ giữ lại các bài duy nhất

    if not df_duplicates.empty:
        dup_ids = tuple(df_duplicates['id'].tolist())
        print(f"♻️ Phát hiện {len(dup_ids)} bài báo bị trùng lặp. Đang xóa sổ và khóa status...")
        with engine.connect() as conn:
            if len(dup_ids) == 1:
                conn.execute(text("UPDATE raw_articles SET status = 'DUPLICATE' WHERE id = :pid"), {"pid": dup_ids[0]})
            else:
                conn.execute(text("UPDATE raw_articles SET status = 'DUPLICATE' WHERE id IN :pids"), {"pids": dup_ids})
            conn.commit()

    if df.empty:
        print("✅ Sau khi lọc trùng, không còn bài báo PENDING nào để phân tích! Hệ thống nghỉ ngơi.")
        exit()
    # =========================================================

    df['published_at'] = pd.to_datetime(df['published_at'])
    df['date'] = df['published_at'].dt.date
    target_date = df['date'].max()

    print(f"✅ Đã tải {len(df)} bài báo mới KHÔNG TRÙNG LẶP. Phân tích cho mốc thời gian: {target_date.strftime('%Y-%m-%d')}")
    
    df['raw_full_text_ner'] = df['title'].astype(str) + ". " + df['content'].astype(str)
    
    # ---------------------------------------------------------
    # 2. PHÂN TÍCH CHỦ ĐỀ VĨ MÔ (LDA)
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("⏳ Đang phân tích chủ đề bài viết bằng LDA...")
    
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
    
    # Lưu Topic Map của các bài mới
    df[['id', 'topic_id']].rename(columns={'id': 'article_id'}).to_sql('article_topic_map', engine, if_exists='append', index=False)

    print("⏳ Cập nhật gia tốc LDA Chủ đề...")
    df_all_topics = pd.read_sql("SELECT ra.published_at, atm.topic_id FROM article_topic_map atm JOIN raw_articles ra ON atm.article_id = ra.id", engine)
    df_all_topics['date'] = pd.to_datetime(df_all_topics['published_at']).dt.date
    trend_data = df_all_topics.groupby(['date', 'topic_id']).size().reset_index(name='article_count')
    total_per_day = trend_data.groupby('date')['article_count'].transform('sum')
    trend_data['percentage'] = (trend_data['article_count'] / total_per_day) * 100
    
    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE topic_daily_stats CASCADE"))
        conn.commit()
    trend_data.rename(columns={'date': 'Date'}).to_sql('topic_daily_stats', engine, if_exists='append', index=False)

    topic_records = []
    for t_id in range(1, 12):
        t_data = trend_data[trend_data['topic_id'] == t_id].sort_values('date')
        slope = linregress(np.arange(len(t_data)), t_data['percentage'].values)[0] if len(t_data) > 1 else 0.0
        trend_type = "🔥 Đang bùng nổ" if slope > 0.5 else ("❄️ Đang hạ nhiệt" if slope < -0.5 else "⚖️ Đi ngang")
        topic_records.append({'topic_id': t_id, 'topic_name': TOPIC_LABELS.get(t_id), 'acceleration': float(slope), 'trend_type': trend_type})
    pd.DataFrame(topic_records).to_sql('lda_topics', engine, if_exists='replace', index=False)


    # ---------------------------------------------------------
    # 3. BÓC TÁCH THỰC THỂ NER CHO CÁC BÀI BÁO MỚI
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("🔪 AI đang bóc tách NER cho các bài báo mới...")
    
    tqdm.pandas(desc="🧠 Chạy NER")
    df['extracted_entities'] = df['raw_full_text_ner'].progress_apply(extract_entities_by_ner)
    df_valid_ner = df[df['extracted_entities'].map(len) > 0]

    # 🔥 IN RA MÀN HÌNH CONSOLE KIỂM TRA NHỮNG TỪ AI VỪA BẮT
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

        print("⏳ Đẩy từ khóa của bài mới vào Database (ner_article_keyword_map)...")
        df_exploded = df_valid_ner[['id', 'extracted_entities']].explode('extracted_entities')
        df_exploded.columns = ['article_id', 'keyword']
        df_exploded.to_sql('ner_article_keyword_map', engine, if_exists='append', index=False)

    # Chỉ tính và chèn thêm tần suất xuất hiện cho cái target_date hiện tại vào bảng chung
    target_date_str = target_date.strftime('%Y-%m-%d')
    print("⏳ Cập nhật bảng tần suất chung (ner_keyword_daily_stats)...")
    with engine.connect() as conn:
        conn.execute(text(f"DELETE FROM ner_keyword_daily_stats WHERE date = '{target_date_str}'"))
        conn.execute(text(f"""
            INSERT INTO ner_keyword_daily_stats (date, keyword, count)
            SELECT DATE(ra.published_at), akm.keyword, COUNT(akm.article_id)
            FROM ner_article_keyword_map akm JOIN raw_articles ra ON akm.article_id = ra.id
            WHERE DATE(ra.published_at) = '{target_date_str}'
            GROUP BY DATE(ra.published_at), akm.keyword
        """))
        conn.commit()


    # ---------------------------------------------------------
    # 4. CHẤM ĐIỂM Z-SCORE BẰNG CÁCH SO SÁNH VỚI QUÁ KHỨ VÀ LƯU TOP
    # ---------------------------------------------------------
    print("\n⏳ Đang tải toàn bộ dữ liệu lịch sử để chấm điểm Z-Score...")
    df_daily_ner = pd.read_sql("SELECT * FROM ner_keyword_daily_stats", engine)
    
    df_pivot = df_daily_ner.pivot(index='date', columns='keyword', values='count').fillna(0).sort_index()
    keyword_metrics = []
    
    dynamic_tags = set()
    if 'tags' in df.columns:
        for tag_str in df[df['date'] == target_date]['tags'].dropna():
            dynamic_tags.update([t.strip().lower().replace(' ', '_') for t in str(tag_str).split(',')])

    for kw in df_pivot.columns:
        counts = df_pivot[kw].values
        # Chỉ xét những từ có xuất hiện vào ngày hôm nay và xuất hiện >= 2 lần
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

        # Đã cập nhật thành .head(40) theo yêu cầu của bạn
        df_final = jaccard_filter(df_metrics).head(60)
        
        df_save = df_final[['Keyword', 'Popularity', 'Trend', 'Z_Score', 'SUPER_HOT_SCORE']].copy()
        df_save.columns = ['Keyword', 'Popularity', 'Trend', 'Z_Score', 'Super_Hot_Score']
        df_save['date'] = target_date_str
        
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM trending_keywords WHERE date = :d"), {"d": target_date_str})
            conn.commit()
        df_save.to_sql('trending_keywords', engine, if_exists='append', index=False)
        
        print("\n" + "="*80)
        print(f"👑 BẢNG XẾP HẠNG TOP 40 SỰ KIỆN & THỰC THỂ NÓNG NHẤT NGÀY {target_date_str}:")
        print("-" * 80)
        display_cols = ['Keyword', 'Popularity', 'Trend', 'Z_Score', 'Super_Hot_Score']
        print(df_save[display_cols].round(3).to_string(index=False))

    # ---------------------------------------------------------
    # 5. KHÓA SỔ CÁC BÀI BÁO PENDING THÀNH PROCESSED
    # ---------------------------------------------------------
    print("\n⏳ Đóng dấu PROCESSED cho các bài báo vừa xử lý...")
    processed_ids = tuple(df['id'].tolist())
    with engine.connect() as conn:
        if len(processed_ids) == 1: 
            conn.execute(text("UPDATE raw_articles SET status = 'PROCESSED' WHERE id = :pid"), {"pid": processed_ids[0]})
        else: 
            conn.execute(text("UPDATE raw_articles SET status = 'PROCESSED' WHERE id IN :pids"), {"pids": processed_ids})
        conn.commit()

    print("\n" + "=" * 80)
    print(f"🎉 HOÀN TẤT XỬ LÝ NGÀY MỚI NHẤT ({target_date_str})!")
    print(f"⏱️ Tổng thời gian chạy: {round(time.time() - start_time_total, 2)} giây.")
    print("=" * 80)