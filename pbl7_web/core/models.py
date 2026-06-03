from django.db import models

# =========================================================
# ARTICLE - KEYWORD MAP (MICRO)
# =========================================================
class ArticleKeywordMap(models.Model):
    # Dùng article_id làm primary key tạm thời vì bảng không có id
    article_id = models.BigIntegerField(
        primary_key=True,
        blank=True,
        null=False
    )

    keyword = models.TextField(
        db_column='Keyword',
        blank=True,
        null=True
    )

    class Meta:
        managed = False
        db_table = 'article_keyword_map'

    def __str__(self):
        return f"{self.article_id} - {self.keyword}"


# =========================================================
# KEYWORD DAILY STATS (MICRO)
# =========================================================
class KeywordDailyStats(models.Model):
    date = models.TextField(
        db_column='Date',
        primary_key=True
    )

    keyword = models.TextField(
        db_column='Keyword'
    )

    count = models.BigIntegerField(
        db_column='Count',
        blank=True,
        null=True
    )

    class Meta:
        managed = False
        db_table = 'keyword_daily_stats'


# =========================================================
# RAW ARTICLES
# =========================================================
class RawArticles(models.Model):
    published_at = models.DateTimeField(blank=True, null=True)
    source = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    clean_title = models.TextField(blank=True, null=True)
    clean_content = models.TextField(blank=True, null=True)
    full_clean_text = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'raw_articles'

    def __str__(self):
        return self.title if self.title else "No Title"


# =========================================================
# TRENDING KEYWORDS (MICRO)
# =========================================================
# =========================================================
# TRENDING KEYWORDS (MICRO)
# =========================================================
class TrendingKeywords(models.Model):
    keyword = models.TextField(
        primary_key=True,
        db_column='Keyword'
    )

    popularity = models.FloatField(
        db_column='Popularity',
        blank=True,
        null=True
    )

    trend = models.FloatField(
        db_column='Trend',
        blank=True,
        null=True
    )

    z_score = models.FloatField(
        db_column='Z_Score',
        blank=True,
        null=True
    )

    super_hot_score = models.FloatField(
        db_column='Super_Hot_Score', # Sửa đúng chữ Super_Hot_Score trong ảnh
        blank=True,
        null=True
    )
    date = models.DateField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'trending_keywords'

    def __str__(self):
        return self.keyword

# =========================================================
# LDA TOPIC (MACRO)
# =========================================================
class LdaTopic(models.Model):
    topic_id = models.IntegerField(primary_key=True)
    topic_name = models.CharField(max_length=255)
    acceleration = models.FloatField(default=0.0)
    trend_type = models.CharField(max_length=100)

    class Meta:
        db_table = 'lda_topics'


# =========================================================
# TOPIC DAILY STATS (MACRO)
# =========================================================
class TopicDailyStats(models.Model):
    # Thay tên thuộc tính từ 'date' thành 'topic_date' để tránh xung đột với chính tên cột
    topic_date = models.DateField(db_column='Date', primary_key=True) 
    
    # Django yêu cầu mỗi model phải có một primary key. 
    # Nếu bảng không có id, bạn nên set một cột làm primary_key.
    # Ở đây tôi set 'topic_date' làm primary_key=True
    
    topic = models.ForeignKey(LdaTopic, on_delete=models.CASCADE, db_column='topic_id')
    
    article_count = models.IntegerField(db_column='article_count', default=0)
    percentage = models.FloatField(db_column='percentage', default=0.0)

    class Meta:
        managed = False
        db_table = 'topic_daily_stats'

# =========================================================
# ARTICLE TOPIC MAP (MACRO)
# =========================================================
class ArticleTopicMap(models.Model):
    # 🎯 FIX: Khai báo primary_key=True để Django không đòi cột "id"
    article_id = models.BigIntegerField(primary_key=True)
    
    # 🎯 FIX: Đảm bảo Django trỏ vào cột topic_id của cơ sở dữ liệu
    topic = models.ForeignKey(LdaTopic, on_delete=models.CASCADE, db_column='topic_id')

    class Meta:
        db_table = 'article_topic_map'
class NerKeywordDailyStats(models.Model):
    date = models.DateField(blank=True, null=True)
    keyword = models.TextField(blank=True, null=True)
    count = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False # Báo cho Django biết bảng này do AI quản lý, Django không cần tạo migrate
        db_table = 'ner_keyword_daily_stats'


class NerArticleKeywordMap(models.Model):
    article_id = models.BigIntegerField(blank=True, null=True)
    keyword = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ner_article_keyword_map'