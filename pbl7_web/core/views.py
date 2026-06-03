from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Sum, Max
from datetime import datetime, timedelta
from django.db.models import Q

# ==========================================
# 🌟 ĐÃ SỬA LỖI 1: Import đúng bảng của AI NER
# ==========================================
from .models import (
    TrendingKeywords, NerKeywordDailyStats, RawArticles,
    NerArticleKeywordMap, LdaTopic, TopicDailyStats, ArticleTopicMap
)

def index(request):
    return render(request, 'core/index.html')

# ==========================================
# API 1: TRENDING KEYWORDS (MICRO)
# ==========================================
def get_trending(request):
    time_filter = request.GET.get('time', '24h') 
    EXCLUDED_KEYWORDS = ['vnexpress', 'thanh_nien', 'video', 'news','tv360','thành_đông','data','độc_quyền','tứcca_sĩ','công_an_tỉnh','văn_hóa_thể_thao','triệu_đồng','triệu_lượt','thủ_tục_hành_chính','năm_2026','năm_2025','sức_khỏe']
    
    try:
        # Dùng bảng NER mới
        latest_stat = NerKeywordDailyStats.objects.aggregate(Max('date'))
        latest_date_val = latest_stat['date__max']
        
        if not latest_date_val:
            return JsonResponse([], safe=False)

        if isinstance(latest_date_val, str):
            latest_date = datetime.strptime(latest_date_val, '%Y-%m-%d').date()
        else:
            latest_date = latest_date_val

        response_data = []

        if time_filter == '24h':
            trending_qs = TrendingKeywords.objects.filter(
                date=latest_date
            ).exclude(keyword__in=EXCLUDED_KEYWORDS).order_by('-super_hot_score')[:20]
            
            if not trending_qs.exists():
                trending_qs = TrendingKeywords.objects.exclude(
                    keyword__in=EXCLUDED_KEYWORDS
                ).order_by('-super_hot_score')[:20]
            
            keywords_list = [
                {
                    'keyword': item.keyword,
                    'z_score': float(item.z_score or 0),
                    'super_hot_score': float(item.super_hot_score or 0),
                    'popularity': float(item.popularity or 0),
                    'trend': float(item.trend or 0)
                } for item in trending_qs
            ]
            
        else:
            target_date = latest_date - timedelta(days=1)
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            # Dùng bảng NER mới
            trending_qs = NerKeywordDailyStats.objects.filter(date__gte=target_date_str)\
                .exclude(keyword__in=EXCLUDED_KEYWORDS)\
                .values('keyword')\
                .annotate(total_pop=Sum('count'))\
                .order_by('-total_pop')[:20]
                
            keywords_list = [
                {
                    'keyword': item['keyword'],
                    'z_score': 0.0,
                    'super_hot_score': float(item['total_pop']), 
                    'popularity': float(item['total_pop']),
                    'trend': 0.0
                } for item in trending_qs
            ]

        for item in keywords_list:
            keyword = item['keyword']
            
            # Dùng bảng NER mới
            stats = NerKeywordDailyStats.objects.filter(keyword=keyword).order_by('date')
            article_ids = list(NerArticleKeywordMap.objects.filter(keyword=keyword).values_list('article_id', flat=True))

            dominant_topic = "Tổng hợp"
            if article_ids:
                top_topic = ArticleTopicMap.objects.filter(article_id__in=article_ids)\
                    .values('topic__topic_name')\
                    .annotate(count=Count('topic'))\
                    .order_by('-count')\
                    .first()
                if top_topic:
                    dominant_topic = top_topic['topic__topic_name']

            articles = list(RawArticles.objects.filter(
                id__in=article_ids
            ).order_by('-published_at').values(
                'title', 'url', 'source', 'published_at', 'category'
            ))
            
            for art in articles:
                if art['published_at']:
                    try:
                        if isinstance(art['published_at'], str):
                            d_obj = datetime.strptime(art['published_at'], '%Y-%m-%d %H:%M:%S')
                            art['published_at'] = d_obj.strftime('%d/%m/%Y %H:%M')
                        else:
                            art['published_at'] = art['published_at'].strftime('%d/%m/%Y %H:%M')
                    except:
                        pass

            trend_data = [{"date": str(stat.date), "count": stat.count} for stat in stats]

            response_data.append({
                "keyword": keyword,
                "dominant_topic": dominant_topic,
                "z_score": item['z_score'],
                "super_hot_score": item['super_hot_score'],
                "popularity": item['popularity'],
                "trend": item['trend'],
                "trend_data": trend_data,
                "articles": articles
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

        for t in topics:
            stats = TopicDailyStats.objects.filter(topic=t).order_by('topic_date')
            chart_data = [{"date": str(stat.topic_date), "percentage": round(float(stat.percentage), 2)} for stat in stats]

            article_ids = list(ArticleTopicMap.objects.filter(topic=t).values_list('article_id', flat=True))
            articles_qs = RawArticles.objects.filter(id__in=article_ids).order_by('-published_at')
            
            articles = []
            for article in articles_qs:
                pub_str = ""
                if article.published_at:
                    if isinstance(article.published_at, str): pub_str = article.published_at
                    else: pub_str = article.published_at.strftime('%d/%m/%Y %H:%M')

                articles.append({
                    "title": article.title or "",
                    "url": article.url or "",
                    "source": article.source or "",
                    "published_at": pub_str,
                    "category": article.category or ""
                })

            response_data.append({
                "topic_id": t.topic_id,
                "topic_name": t.topic_name,
                "acceleration": round(float(t.acceleration), 2),
                "trend_type": t.trend_type,
                "chart_data": chart_data,
                "articles": articles
            })

        return JsonResponse(response_data, safe=False, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        print(f"🚨 LỖI TẠI API TOPICS: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


# ==========================================
# API 3: DEEP SEARCH (TÌM KIẾM SÂU KHÔNG GẠCH DƯỚI)
# ==========================================
def search_articles(request):
    query = request.GET.get('q', '').strip()
    time_filter = request.GET.get('time', '24h')

    if not query:
        return JsonResponse([], safe=False)

    try:
        # ==========================================
        # 🌟 ĐÃ SỬA LỖI 2: Dọn dẹp dấu gạch dưới của NER trước khi tìm kiếm
        # Chuyển 'hồ_chí_minh' thành 'hồ chí minh' để tìm kiếm chính xác
        # ==========================================
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

        articles_qs = articles_qs.order_by('-published_at')[:50]

        articles = []
        for article in articles_qs:
            pub_str = ""
            if article.published_at:
                if isinstance(article.published_at, str): pub_str = article.published_at
                else: pub_str = article.published_at.strftime('%d/%m/%Y %H:%M')

            articles.append({
                "title": article.title or "",
                "url": article.url or "",
                "source": article.source or "",
                "published_at": pub_str,
                "category": article.category or ""
            })

        return JsonResponse(articles, safe=False, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        print(f"🚨 LỖI TÌM KIẾM: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

def search_page(request):
    return render(request, 'core/search_results.html')