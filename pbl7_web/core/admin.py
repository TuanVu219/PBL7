from django.contrib import admin
from .models import RawArticles, TrendingKeywords

@admin.register(RawArticles)
class RawArticlesAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at', 'status')
    list_filter = ('status',)

admin.site.register(TrendingKeywords)