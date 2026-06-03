from django.contrib import admin
from django.urls import path
from core import views  # IMPORT TRỰC TIẾP TỪ APP CORE

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('api/trending/', views.get_trending, name='get_trending'),
    path('api/topics/', views.get_topics, name='get_topics'),
    # 1. Đường dẫn mở trang giao diện tìm kiếm mới
    path('search/', views.search_page, name='search_page'),
    
    # 2. Đường dẫn API ngầm để Javascript gọi lấy bài báo
    path('api/search/', views.search_articles, name='api_search'),
]