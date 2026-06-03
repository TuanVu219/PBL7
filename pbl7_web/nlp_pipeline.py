import pandas as pd
import numpy as np
import os
import time
import warnings
import re

from sqlalchemy import create_engine, text
from scipy.stats import linregress
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_extraction.text import CountVectorizer
from underthesea import word_tokenize, text_normalize, pos_tag
from pandarallel import pandarallel
from tqdm import tqdm

# Thư viện cho LDA
import gensim
from gensim.models import LdaModel
import gensim.corpora as corpora

warnings.filterwarnings('ignore')

# =========================================================
# 🌟 CẤU HÌNH DATABASE & ĐƯỜNG DẪN
# =========================================================
DB_URL = "postgresql://postgres:123456@localhost:5432/postgres"

engine = create_engine(
    DB_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

MODEL_PATH = 'D:/PBL7_web/pbl7_web/core/ai_models/lda_model.gensim'
DICT_PATH = 'D:/PBL7_web/pbl7_web/core/ai_models/lda_dictionary.dict'
STOPWORDS_FILE = 'D:/PBL7_web/pbl7_web/core/ai_models/vietnamese-stopwords.txt'

TOPIC_LABELS = {
    1: "Giáo dục Đại học & Nghiên cứu", 
    2: "Thể thao & Bóng đá",
    3: "Doanh nghiệp & Phát triển Xanh", 
    4: "Tuyển sinh & Giáo dục phổ thông",
    5: "Chính trị Quốc tế & Xung đột", 
    6: "Văn hóa & Sự kiện Xã hội",
    7: "Y tế, Sức khỏe & Thực phẩm", 
    8: "Đời sống, Gia đình & Xã hội",
    9: "Giải trí & Nghệ thuật", 
    10: "Kinh tế, Tài chính & Ngân hàng",
    11: "Quản lý Hành chính & Đô thị"
}

# =========================================================
# 🌟 CẤU HÌNH TIỀN XỬ LÝ
# =========================================================
def load_stopwords(filepath):
    EXTRA_STOPWORDS = {
        'cho_biết', 'được_biết', 'liên_quan', 'thực_hiện', 'tại_đây', 'nêu_trên',
        'trước_đó', 'hiện_nay', 'ngày_nay', 'hôm_nay', 'hôm_qua', 'ngày_mai',
        'nói_chung', 'tất_cả', 'theo_đó', 'cụ_thể', 'vẫn_đang', 'nhằm', 'giúp',
        'mang_lại', 'trở_thành', 'vừa_qua', 'mới_đây', 'trong_đó', 'này_nọ'
    }

    if not os.path.exists(filepath):
        print(f"⚠️ Cảnh báo: Không tìm thấy {filepath}. Tự động dùng bộ lọc mặc định.")
        return EXTRA_STOPWORDS.union({"và", "của", "là", "có", "được", "cho", "trong", "một"})

    with open(filepath, 'r', encoding='utf-8') as f:
        file_stopwords = set(line.strip().replace(" ", "_") for line in f if line.strip())

    return file_stopwords.union(EXTRA_STOPWORDS)

STOPWORDS = load_stopwords(STOPWORDS_FILE)

INVALID_EDGES = {
    'đóng', 'vai', 'trò', 'thay', 'vì', 'sự', 'những', 'các', 'vào', 'với',
    'đang', 'rất', 'hơn', 'nhất', 'bị', 'được', 'làm', 'của', 'là', 'có',
    'tham', 'gia', 'diễn', 'ra', 'việc', 'một', 'như', 'khi', 'cho', 'đến',
    'trong', 'và', 'từ', 'rằng', 'thì', 'mà', 'cùng', 'qua', 'lại', 'còn',
    'về', 'này', 'nọ', 'kia', 'mọi', 'mỗi', 'từng', 'đã', 'mang', 'những',
    'sẽ', 'vẫn', 'cứ', 'vừa', 'mới', 'tại', 'theo', 'trên', 'câu', 'chuyện',
    'dưới', 'ngoài', 'giữa', 'để', 'do', 'bởi', 'nên', 'nhưng', 'cái', 'thứ'
}

BLACKLIST_EXACT = {
    'đoạn_clip', 'xoay_quanh', 'chia_sẻ', 'bức_xúc', 'cộng_đồng', 'mạng_xã',
    'cho_biết', 'liên_quan', 'diễn_biến', 'cơ_quan', 'chức_năng', 'báo_cáo',
    'xử_lý', 'tiến_hành', 'hoạt_động', 'thực_hiện', 'phát_hiện', 'trường_hợp',
    'khu_vực', 'quá_trình', 'thời_gian', 'nội_dung', 'quy_định', 'chi_tiết',
    'người_dân', 'hiện_tượng', 'chủ_đề', 'vấn_đề', 'thông_tin', 'tuyến_đường',
    'trao_tận', 'tận_tay', 'chạy_xe', 'lan_truyền', 'bày_tỏ', 'lên_tiếng', 'vòng_giọng',
    'dân_trí', 'báo', 'vnexpress', 'thanh_niên', 'tuổi_trẻ', 'vtv', 'vietnamnet', 'pccc&cnch',
    'phòng_cháy_chữa_cháy', 'cảnh_sát_giao_thông', 'giáo_dục_việt_nam'
}

BLACKLIST_INNER = [
    'nhà', 'ban', 'tổ', 'hội', 'cơ sở', 'khoa học', 'đầu tư', 
    'sản xuất', 'lãnh đạo', 'hội đồng', 'thị trường', 'doanh nghiệp', 
    'công ty', 'người', 'việt nam'
]

MIN_TODAY_COUNT_2_WORDS = 2
MIN_TODAY_COUNT_3_WORDS = 3
SMOOTHING_FACTOR = 1.5

# =========================================================
# 🌟 HÀM XỬ LÝ VĂN BẢN (Gói trọn để tránh lỗi NameError)
# =========================================================
# =========================================================
# 🌟 HÀM XỬ LÝ VĂN BẢN (Gói trọn để tránh lỗi NameError)
# =========================================================
def process_vietnamese_text(text, custom_stopwords):
    import re
    from underthesea import word_tokenize, text_normalize
    
    if not isinstance(text, str): return ""
    
    text = re.sub(r'([.,!?:;()\[\]{}])', r' \1 ', text)
    text = text_normalize(text).lower()
    text = re.sub(r'http\S+|www\S+|https\S+|\S+@\S+|@\S+|#\S+', '', text)
    text = re.sub(r'\b\d+\w*\b', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    cleaned = re.sub(r'\s+', ' ', text).strip()
    
    if not cleaned: return ""

    tokenized = word_tokenize(cleaned, format="text")
    words = tokenized.split()

    final_words = [
        word for word in words
        if word not in custom_stopwords and ("_" in word or len(word) > 3)
    ]
    return " ".join(final_words)

# =========================================================
# MAIN PIPELINE
# =========================================================
if __name__ == '__main__':

    print("🚀 KHỞI ĐỘNG HỆ THỐNG PHÂN TÍCH TREND (ULTIMATE VERSION TÍCH HỢP NLP)")
    print("=" * 80)

    start_time_total = time.time()
    tqdm.pandas(desc="🧠 Tiến độ AI")
    
    # Khởi tạo pandarallel (giới hạn 4 nhân an toàn)
    pandarallel.initialize(progress_bar=True, nb_workers=4)


    # =========================================================
    # 🌟 1. TỰ ĐỘNG DỌN RÁC & LOAD DỮ LIỆU TỪ DATABASE
    # =========================================================
    print("\n⏳ Đang quét và dọn dẹp các bài báo trùng lặp trong Database...")
    try:
        with engine.connect() as conn:
            # Dùng SQL xóa thẳng tay các bài trùng URL, chỉ giữ lại bản gốc (id nhỏ nhất)
            dedup_query = text("""
                DELETE FROM raw_articles
                WHERE id IN (
                    SELECT id
                    FROM (
                        SELECT id,
                               ROW_NUMBER() OVER(PARTITION BY url ORDER BY id ASC) as row_num
                        FROM raw_articles
                    ) t
                    WHERE t.row_num > 1
                );
            """)
            result = conn.execute(dedup_query)
            conn.commit()
            
            if result.rowcount > 0:
                print(f"🧹 Đã tiêu diệt thành công {result.rowcount} bài báo bị trùng lặp URL!")
            else:
                print("✨ Database sạch sẽ, không phát hiện bài báo trùng lặp.")
    except Exception as e:
        print(f"⚠️ Cảnh báo khi dọn dẹp trùng lặp: {e}")

    print("\n⏳ Đang tải bài báo thô (PENDING) từ PostgreSQL...")
    
    query_pending = "SELECT * FROM raw_articles WHERE status = 'PENDING'"
    df = pd.read_sql(query_pending, engine)

    if df.empty:
        print("✅ Không có bài báo mới để xử lý. Hệ thống nghỉ ngơi!")
        exit()

    print(f"✅ Đã tải {len(df)} bài báo mới.")
    df = df.dropna(subset=['published_at', 'content', 'title']).reset_index(drop=True)
    df['published_at'] = pd.to_datetime(df['published_at'])
    df['date'] = df['published_at'].dt.date
    target_date = df['date'].max()

    print("🔥 Đang chạy NLP làm sạch văn bản đa luồng (Đã giới hạn 4 luồng an toàn)...")
    
    # TRUYỀN KÈM STOPWORDS VÀO LUỒNG CON THÔNG QUA args
    df['clean_title'] = df['title'].parallel_apply(process_vietnamese_text, args=(STOPWORDS,))
    df['clean_content'] = df['content'].parallel_apply(process_vietnamese_text, args=(STOPWORDS,))

    df['raw_full_text'] = df['clean_title'] + " " + df['clean_content']
    df = df[df['raw_full_text'].str.strip() != ""]
    
    print(f"✅ Đã tiền xử lý xong {len(df)} bài báo.")

    # =========================================================
    # 🌟 PHẦN 2: PHÂN TÍCH CHỦ ĐỀ (MACRO TRENDS - LDA)
    # =========================================================
    print("\n⏳ Đang khởi động bộ não LDA và phân loại chủ đề...")
    try:
        lda_model = LdaModel.load(MODEL_PATH)
        id2word = corpora.Dictionary.load(DICT_PATH)
        print("✅ Đã tải LDA Model.")
    except Exception as e:
        print(f"🚨 LỖI TẢI MÔ HÌNH LDA: Vui lòng kiểm tra lại đường dẫn. Chi tiết: {e}")
        exit()

    def assign_topic(text_content):
        try:
            if not isinstance(text_content, str) or text_content.strip() == "": 
                return 1
            bow = id2word.doc2bow(text_content.split())
            if not bow: 
                return 1
            topic_probs = lda_model.get_document_topics(bow)
            if isinstance(topic_probs, tuple): 
                topic_probs = topic_probs[0]
            best_topic = sorted(topic_probs, key=lambda x: x[1], reverse=True)[0][0]
            return best_topic + 1
        except:
            return 1

    print("\n🔪 Đang phân loại chủ đề...")
    df['topic_id'] = df['raw_full_text'].progress_apply(assign_topic)

    print("⏳ Đang lưu article_topic_map...")
    df_topic_map = df[['id', 'topic_id']].rename(columns={'id': 'article_id'})
    df_topic_map.columns = [c.lower() for c in df_topic_map.columns]
    
    df_topic_map.to_sql('article_topic_map', engine, if_exists='append', index=False)

    print("\n⏳ Tính toán Tỷ trọng Chủ đề...")
    query_topics = """
        SELECT ra.published_at, atm.topic_id
        FROM article_topic_map atm
        JOIN raw_articles ra ON atm.article_id = ra.id
    """
    df_all_topics = pd.read_sql(query_topics, engine)
    df_all_topics['date'] = pd.to_datetime(df_all_topics['published_at']).dt.date
    
    trend_data = df_all_topics.groupby(['date', 'topic_id']).size().reset_index(name='article_count')
    total_per_day = trend_data.groupby('date')['article_count'].transform('sum')
    trend_data['percentage'] = (trend_data['article_count'] / total_per_day) * 100
    trend_data = trend_data.rename(columns={'date': 'Date'}) 
    
    try:
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE IF EXISTS topic_daily_stats CASCADE"))
            conn.commit()
    except Exception:
        pass 
        
    trend_data[['Date', 'topic_id', 'article_count', 'percentage']].to_sql(
        'topic_daily_stats', engine, if_exists='append', index=False
    )

    print("⏳ Tính acceleration cho topics và cập nhật bảng lda_topics...")
    topic_records = []
    
    for t_id in range(1, 12):
        t_data = trend_data[trend_data['topic_id'] == t_id].sort_values('Date')
        slope = linregress(np.arange(len(t_data)), t_data['percentage'].values)[0] if len(t_data) > 1 else 0.0
            
        if slope > 0.5: trend_type = "🔥 Đang bùng nổ"
        elif slope < -0.5: trend_type = "❄️ Đang hạ nhiệt"
        else: trend_type = "⚖️ Đi ngang"
        
        topic_records.append({
            'topic_id': t_id,
            'topic_name': TOPIC_LABELS.get(t_id, f"Chủ đề {t_id}"),
            'acceleration': float(slope),
            'trend_type': trend_type
        })
            
    df_lda_topics = pd.DataFrame(topic_records)
    df_lda_topics.to_sql('lda_topics', engine, if_exists='replace', index=False)
    print("✅ Hoàn tất cập nhật bảng lda_topics")


    # =========================================================
    # 🌟 PHẦN 3: BÓC TÁCH TỪ KHÓA (MICRO TRENDS - N-GRAM)
    # =========================================================
    print("\n🔪 Đang trích xuất N-Gram từ văn bản...")

    text_corpus = df['raw_full_text'].str.lower().fillna("")
    min_df_val = 3 if len(text_corpus) >= 10 else (2 if len(text_corpus) >= 3 else 1)

    vectorizer = CountVectorizer(ngram_range=(2, 3), min_df=min_df_val)
    X = vectorizer.fit_transform(text_corpus)
    ngrams = vectorizer.get_feature_names_out()
    counts = np.array(X.sum(axis=0)).flatten()

    print(f"✅ Đã tạo {len(ngrams)} n-grams thô. Đang vào màng lọc chặn rác...")

    def is_good_keyword(kw):
        kw_str = str(kw)
        words = kw_str.split()
        if len(words) < 2: return False
        
        if words[0] in INVALID_EDGES or words[-1] in INVALID_EDGES: return False
        
        kw_under = kw_str.replace(" ", "_")
        if kw_under in BLACKLIST_EXACT: return False
        if any(b in kw_str for b in BLACKLIST_INNER): return False
        
        is_typo = False
        for w in words:
            if len(w) >= 8 and not any(char in w for char in 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'):
                continue 
            for junk in ['của', 'và', 'là', 'các', 'cho']:
                if w.endswith(junk) and len(w) > len(junk):
                    is_typo = True
                    break
            if is_typo: break
            
        if is_typo: return False
        return True

    valid_indices = []
    valid_kws = []
    MIN_FREQ_NGRAM = 2

    for i, kw in enumerate(ngrams):
        if counts[i] >= MIN_FREQ_NGRAM and is_good_keyword(kw):
            valid_indices.append(i)
            valid_kws.append(kw.replace(" ", "_"))

    word_idx_to_kw = dict(zip(valid_indices, valid_kws))

    if not valid_indices:
        print("🚨 Không có từ khóa N-gram nào hợp lệ.")
    else:
        print("⏳ Xây dựng ma trận Sparse Matrix & Article Keyword Map...")
        X_coo = X.tocoo()

        df_counts = pd.DataFrame({
            'doc_idx': X_coo.row,
            'word_idx': X_coo.col,
            'count': X_coo.data
        })

        df_counts = df_counts[df_counts['word_idx'].isin(valid_indices)]
        df_counts = df_counts[df_counts['count'] >= 2] 
        
        df_counts['Keyword'] = df_counts['word_idx'].map(word_idx_to_kw)
        df_counts['article_id'] = df['id'].iloc[df_counts['doc_idx']].values

        df_mapping = df_counts[['article_id', 'Keyword']]
        df_mapping.to_sql('article_keyword_map', engine, if_exists='append', index=False)

        # =========================================================
        # 🌟 TỐI ƯU HÓA: TÁI TẠO LỊCH SỬ BẰNG SQL GROUP BY
        # =========================================================
        print("\n⏳ Đang tái tạo lại lịch sử từ khóa bằng Engine SQL (Chống sập RAM)...")
        
        query_history_fast = """
            SELECT 
                DATE(ra.published_at) as "Date", 
                akm."Keyword" as "Keyword", 
                COUNT(akm.article_id) as "Count"
            FROM article_keyword_map akm
            JOIN raw_articles ra ON akm.article_id = ra.id
            GROUP BY DATE(ra.published_at), akm."Keyword"
        """
        df_daily = pd.read_sql(query_history_fast, engine)
        
        try:
            with engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE IF EXISTS keyword_daily_stats CASCADE"))
                conn.commit()
        except Exception:
            pass 
            
        df_daily.to_sql('keyword_daily_stats', engine, if_exists='append', index=False)
        print("✅ Đã cập nhật lại toàn bộ keyword_daily_stats.")

        # =========================================================
        # 🌟 PHẦN 4: ĐÁNH GIÁ ĐIỂM (Z-SCORE + POS TAGGING)
        # =========================================================
        print("\n⏳ Tính Z-Score, Trend & Phân rã POS Tagging...")
        
        df_history = df_daily.copy()
        df_history.columns = [c.lower() for c in df_history.columns]
        df_pivot = df_history.groupby(['date', 'keyword'])['count'].sum().unstack(fill_value=0).sort_index()

        dynamic_priority_entities = set()
        if 'tags' in df.columns:
            today_tags = df[df['date'] == target_date]['tags'].dropna()
            for tag_str in today_tags:
                tags = [t.strip().lower().replace(' ', '_') for t in str(tag_str).split(',')]
                dynamic_priority_entities.update(tags)

        keyword_metrics = []

        for kw in df_pivot.columns:
            counts = df_pivot[kw].values
            
            if len(counts) > 1:
                recent_count = counts[-1]
                word_count = len(kw.split('_'))

                if word_count == 2 and recent_count < MIN_TODAY_COUNT_2_WORDS:
                    continue
                elif word_count >= 3 and recent_count < MIN_TODAY_COUNT_3_WORDS:
                    continue

                historical = np.array(counts[:-1], dtype=float)
                kw_for_pos = kw.replace('_', ' ')
                specific_weight = 1.0

                is_in_tags = any(f"_{kw}_" in f"_{tag}_" for tag in dynamic_priority_entities)
                if is_in_tags: specific_weight += 0.6

                try:
                    tags_pos = pos_tag(kw_for_pos)
                    if tags_pos:
                        if any(tag[1] in ['Np', 'Ny'] for tag in tags_pos):
                            specific_weight += 0.4
                        elif not any(char in kw for char in 'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ'):
                            specific_weight += 0.4

                        if not is_in_tags and all(tag[1] in ['N', 'Nc', 'M'] for tag in tags_pos):
                            specific_weight -= 0.4

                        if tags_pos[0][1] in ['V', 'A', 'R', 'E', 'C', 'P']:
                            continue
                except Exception:
                    pass

                if len(historical) > 2:
                    baseline = np.median(historical)
                    for i in range(len(historical)):
                        if historical[i] > baseline * 3 and historical[i] > 5:
                            historical[i] *= 0.5

                z_score = (recent_count - np.mean(historical)) / (np.std(historical, ddof=1) + SMOOTHING_FACTOR)
                slope = linregress(np.arange(len(counts)), counts)[0]
                popularity = sum(counts)

                keyword_metrics.append({
                    'Keyword': kw,
                    'Word_Count': word_count,
                    'Popularity': float(popularity),
                    'Trend': float(slope),
                    'Z_Score': float(z_score),
                    'Specific_Weight': float(specific_weight)
                })

        # =========================================================
        # SCORING & DEDUPLICATION 
        # =========================================================
        df_metrics = pd.DataFrame(keyword_metrics)
        if not df_metrics.empty:
            scaler = MinMaxScaler()
            df_metrics[['pop_norm', 'trend_norm', 'z_norm']] = scaler.fit_transform(
                df_metrics[['Popularity', 'Trend', 'Z_Score']]
            )
            
            df_metrics['Length_Bonus'] = np.minimum(df_metrics['Word_Count'] * 0.02, 0.1)
            
            df_metrics['SUPER_HOT_SCORE'] = (
                (0.55 * df_metrics['z_norm'] +
                 0.15 * df_metrics['pop_norm'] +
                 0.20 * df_metrics['trend_norm']) * df_metrics['Specific_Weight']
                + df_metrics['Length_Bonus']
            )
            
            df_metrics = df_metrics.sort_values('SUPER_HOT_SCORE', ascending=False)

            def deduplicate_keywords(df_input):
                filtered_data = []
                saved_roots = []
                for _, row in df_input.iterrows():
                    roots = set([w for w in str(row['Keyword']).split('_') if len(w) >= 3])
                    if not roots:
                        filtered_data.append(row)
                        continue
                    
                    duplicate = False
                    for saved in saved_roots:
                        intersection = roots.intersection(saved)
                        if len(intersection) > 0 and (len(intersection) / min(len(roots), len(saved))) >= 0.6:
                            duplicate = True
                            break
                            
                    if not duplicate:
                        saved_roots.append(roots)
                        filtered_data.append(row)
                return pd.DataFrame(filtered_data)

            df_2_words = df_metrics[df_metrics['Word_Count'] == 2]
            df_3_words = df_metrics[df_metrics['Word_Count'] >= 3]

            df_2_words = deduplicate_keywords(df_2_words).head(10)
            df_3_words = deduplicate_keywords(df_3_words).head(10)

            df_final = pd.concat([df_2_words, df_3_words])

            df_save = df_final[['Keyword', 'Popularity', 'Trend', 'Z_Score', 'SUPER_HOT_SCORE']].copy()
            df_save.columns = ['Keyword', 'Popularity', 'Trend', 'Z_Score', 'Super_Hot_Score']            
            
            # =======================================================
            # 🔥 TÍNH NĂNG MỚI: LƯU NHẬT KÝ LỊCH SỬ TRENDING
            # =======================================================
            # Dùng target_date (ngày của mẻ bài báo) để lưu chính xác mốc thời gian
            analysis_date = target_date.strftime('%Y-%m-%d')
            df_save['date'] = analysis_date
            
            try:
                with engine.connect() as conn:
                    # Dùng DELETE chỉ xóa dữ liệu của ngày đang chạy để chống ghi trùng.
                    # TUYỆT ĐỐI giữ nguyên dữ liệu của các ngày hôm trước!
                    conn.execute(
                        text("DELETE FROM trending_keywords WHERE date = :d"), 
                        {"d": analysis_date}
                    )
                    conn.commit()
            except Exception as e:
                print(f"⚠️ Cảnh báo khi làm sạch data cũ: {e}") 
                
            # Ghi nối tiếp (append) vào Database
            df_save.to_sql('trending_keywords', engine, if_exists='append', index=False)
            print(f"✅ Đã cập nhật bảng trending_keywords (Lưu thành công mốc: {analysis_date})")

            display_cols = ['Keyword','Popularity', 'Trend', 'Z_Score', 'SUPER_HOT_SCORE']
            
            print("\n" + "="*70)
            print("🔥 TOP 10 HIỆN TƯỢNG/SỰ KIỆN NÓNG (CỤM 2 TỪ):")
            print("-" * 70)
            if df_2_words.empty:
                print("🚨 Không có hiện tượng 2 từ nào đột biến hôm nay.")
            else:
                df_2_disp = df_2_words[display_cols].copy()
                df_2_disp[['Trend', 'Z_Score', 'SUPER_HOT_SCORE']] = df_2_disp[['Trend', 'Z_Score', 'SUPER_HOT_SCORE']].round(3)
                print(df_2_disp.to_string(index=False))

            print("\n" + "="*70)
            print("🔥 TOP 10 THỰC THỂ/TÊN RIÊNG ĐỘT BIẾN (CỤM 3+ TỪ):")
            print("-" * 70)
            if df_3_words.empty:
                print("🚨 Không có thực thể 3+ từ nào đột biến hôm nay.")
            else:
                df_3_disp = df_3_words[display_cols].copy()
                df_3_disp[['Trend', 'Z_Score', 'SUPER_HOT_SCORE']] = df_3_disp[['Trend', 'Z_Score', 'SUPER_HOT_SCORE']].round(3)
                print(df_3_disp.to_string(index=False))

    # =========================================================
    # 🌟 5. UPDATE STATUS BÀI BÁO THÀNH 'PROCESSED'
    # =========================================================
    print("\n⏳ Update status bài báo...")
    processed_ids = tuple(df['id'].tolist())

    with engine.connect() as conn:
        if len(processed_ids) == 1:
            conn.execute(
                text("UPDATE raw_articles SET status = 'PROCESSED' WHERE id = :pid"),
                {"pid": processed_ids[0]}
            )
        else:
            conn.execute(
                text("UPDATE raw_articles SET status = 'PROCESSED' WHERE id IN :pids"),
                {"pids": processed_ids}
            )
        conn.commit()

    print("✅ Đã cập nhật status thành PROCESSED.")

    print("\n" + "=" * 80)
    print(f"🎉 HOÀN TẤT SIÊU TỐC SAU {round(time.time() - start_time_total, 2)} GIÂY")
    print("=" * 80)