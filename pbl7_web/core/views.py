from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Sum, Max, Q
from datetime import datetime, timedelta
import random

from .models import (
    TrendingKeywords, NerKeywordDailyStats, RawArticles,
    NerArticleKeywordMap, LdaTopic, TopicDailyStats, ArticleTopicMap
)

def index(request):
    return render(request, 'core/index.html')

def search_page(request):
    return render(request, 'core/search_results.html')

# ==========================================
# API 1: TRENDING KEYWORDS (MICRO)
# ==========================================
def get_trending(request):
    time_filter = request.GET.get('time', '24h') 
    # Nhận bộ lọc từ Frontend (chuyển về chữ thường để dễ so sánh)
    lda_filter = request.GET.get('category', 'all').lower() 
    
    EXCLUDED_KEYWORDS = ['vnexpress', 'thanh_nien', 'video', 'news','tv360','thành_đông','data','độc_quyền','tứcca_sĩ',
                        'công_an_tỉnh','văn_hóa_thể_thao','triệu_đồng','triệu_lượt','thủ_tục_hành_chính','năm_2026','năm_2025',
                        'sức_khỏe','nam_bộ','tháng_5','tháng_6','giờ_việt_nam','miền_bắc',
                        'công_thương','khánh_hòa','ninh_bình ','hải_phòng','nghệ_an','bắc_ninh','cần_thơ','thanh_hóa','tây_ninh','năm_2030','quảng_ngãi','quảng_trị','ninh_bình','hóa_chất_6','diễn_đàn_kinh_tế_quốc_tế_st','vinh_danh_top',
                        'tiếng_anh','môn_toán','and_the_beast','đắk_lắk','đồng_tháp'
                        ]
    
    try:
        latest_stat = NerKeywordDailyStats.objects.aggregate(Max('date'))
        latest_date_val = latest_stat['date__max']
        if not latest_date_val: 
            return JsonResponse([], safe=False)

        latest_date = datetime.strptime(latest_date_val, '%Y-%m-%d').date() if isinstance(latest_date_val, str) else latest_date_val
        response_data = []

        # 🟢 Lấy dư dả từ khóa (khoảng 150) để trừ hao lúc áp dụng bộ lọc LDA
        if time_filter == '24h':
            trending_qs = TrendingKeywords.objects.filter(date=latest_date).exclude(keyword__in=EXCLUDED_KEYWORDS).order_by('-super_hot_score')[:300]
            if not trending_qs.exists():
                trending_qs = TrendingKeywords.objects.exclude(keyword__in=EXCLUDED_KEYWORDS).order_by('-super_hot_score')[:300]
            
            keywords_list = [{'keyword': item.keyword, 'z_score': float(item.z_score or 0), 'super_hot_score': float(item.super_hot_score or 0), 'popularity': float(item.popularity or 0), 'trend': float(item.trend or 0)} for item in trending_qs]
        else:
            target_date_str = (latest_date - timedelta(days=1)).strftime('%Y-%m-%d')
            trending_qs = NerKeywordDailyStats.objects.filter(date__gte=target_date_str).exclude(keyword__in=EXCLUDED_KEYWORDS).values('keyword').annotate(total_pop=Sum('count')).order_by('-total_pop')[:300]
            keywords_list = [{'keyword': item['keyword'], 'z_score': 0.0, 'super_hot_score': float(item['total_pop']), 'popularity': float(item['total_pop']), 'trend': 0.0} for item in trending_qs]

        seven_days_ago = latest_date - timedelta(days=7)

        for item in keywords_list:
            # 🟢 Chỉ trả về đúng 20 từ khóa hợp lệ để nhồi lên màn hình
            if len(response_data) >= 20:
                break
                
            keyword = item['keyword']
            article_ids = list(NerArticleKeywordMap.objects.filter(keyword=keyword).values_list('article_id', flat=True))

            dominant_topic = "Tổng hợp"
            if article_ids:
                top_topic = ArticleTopicMap.objects.filter(article_id__in=article_ids).values('topic__topic_name').annotate(count=Count('topic')).order_by('-count').first()
                if top_topic: 
                    dominant_topic = top_topic['topic__topic_name']

            # 🟢 BỘ LỌC CHÍNH XÁC: Nếu chọn Thể thao mà LDA Topic không chứa chữ Thể thao thì BỎ QUA
            if lda_filter != 'all':
                if lda_filter not in dominant_topic.lower():
                    continue

            # Nếu lọt qua bộ lọc, tiếp tục lấy data vẽ biểu đồ
            stats = NerKeywordDailyStats.objects.filter(keyword=keyword).order_by('date')
            articles = list(RawArticles.objects.filter(
                id__in=article_ids,
                published_at__gte=seven_days_ago
            ).order_by('-published_at').values('title', 'url', 'source', 'published_at', 'category'))
            
            for art in articles:
                if art['published_at']:
                    try:
                        d_obj = datetime.strptime(art['published_at'], '%Y-%m-%d %H:%M:%S') if isinstance(art['published_at'], str) else art['published_at']
                        art['published_at'] = d_obj.strftime('%Y-%m-%d %H:%M')
                    except: 
                        pass

            trend_data = [{"date": str(stat.date), "count": stat.count} for stat in stats]

            response_data.append({
                "keyword": keyword, "dominant_topic": dominant_topic,
                "z_score": item['z_score'], "super_hot_score": item['super_hot_score'],
                "popularity": item['popularity'], "trend": item['trend'],
                "trend_data": trend_data, "articles": articles
            })
            
        return JsonResponse(response_data, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        print(f"🚨 LỖI TẠI API TRENDING: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

# ==========================================
# API 2: LDA TOPICS (MACRO)
# ==========================================
def get_topics(request):
    try:
        topics = LdaTopic.objects.all().order_by('-acceleration')
        response_data = []
        
        # 🟢 Tính mốc thời gian 7 ngày trước để lọc toàn bộ báo
        seven_days_ago = datetime.now().date() - timedelta(days=7)

        for t in topics:
            stats = TopicDailyStats.objects.filter(topic=t).order_by('topic_date')
            chart_data = [{"date": str(stat.topic_date), "percentage": round(float(stat.percentage), 2)} for stat in stats]
            
            # 🟢 Khôi phục lấy TOÀN BỘ báo trong 7 ngày gần nhất cho Topic
            article_ids = list(ArticleTopicMap.objects.filter(topic=t).values_list('article_id', flat=True))
            articles_qs = RawArticles.objects.filter(
                id__in=article_ids,
                published_at__gte=seven_days_ago
            ).order_by('-published_at')
            
            articles = []
            for article in articles_qs:
                pub_str = ""
                if article.published_at:
                    try:
                        d_obj = datetime.strptime(article.published_at, '%Y-%m-%d %H:%M:%S') if isinstance(article.published_at, str) else article.published_at
                        pub_str = d_obj.strftime('%Y-%m-%d %H:%M')
                    except: 
                        pub_str = str(article.published_at)

                articles.append({
                    "title": article.title or "", "url": article.url or "",
                    "source": article.source or "", "published_at": pub_str,
                    "category": article.category or ""
                })

            response_data.append({
                "topic_id": t.topic_id, "topic_name": t.topic_name,
                "acceleration": round(float(t.acceleration), 2),
                "trend_type": t.trend_type, "chart_data": chart_data,
                "articles": articles # Trả về danh sách báo đầy đủ
            })
        return JsonResponse(response_data, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

# ==========================================
# API 3: DEEP SEARCH
# ==========================================
def search_articles(request):
    query = request.GET.get('q', '').strip()
    time_filter = request.GET.get('time', 'all')
    page = int(request.GET.get('page', 1))
    limit = int(request.GET.get('limit', 10))

    if not query:
        return JsonResponse({"results": [], "total": 0, "related": []}, safe=False)

    try:
        clean_query = query.replace('_', ' ')
        articles_qs = RawArticles.objects.filter(
            Q(title__icontains=clean_query) | Q(content__icontains=clean_query)
        )

        today = datetime.now().date()
        if time_filter == '24h': 
            articles_qs = articles_qs.filter(published_at__gte=today)
        elif time_filter == '48h': 
            articles_qs = articles_qs.filter(published_at__gte=today - timedelta(days=1))
        elif time_filter == '7d': 
            articles_qs = articles_qs.filter(published_at__gte=today - timedelta(days=7))

        total_count = articles_qs.count()
        offset = (page - 1) * limit
        articles_page = articles_qs.order_by('-published_at')[offset:offset+limit]

        articles = []
        for article in articles_page:
            pub_str = ""
            if article.published_at:
                if isinstance(article.published_at, str): 
                    pub_str = article.published_at
                else: 
                    pub_str = article.published_at.strftime('%Y-%m-%d %H:%M')

            articles.append({
                "title": article.title or "", "url": article.url or "",
                "source": article.source or "", "published_at": pub_str,
                "category": article.category or ""
            })

        related_qs = TrendingKeywords.objects.filter(date=today).exclude(keyword__icontains=clean_query).order_by('?')[:5]
        related_entities = [item.keyword for item in related_qs]

        return JsonResponse({
            "results": articles,
            "total": total_count,
            "related": related_entities,
            "page": page,
            "has_next": (offset + limit) < total_count
        }, safe=False, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)