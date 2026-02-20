"""
URL configuration for satlingo project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from web import views as web_views
from api.models import Lesson, Passage, WritingSection, MathSection

def reading_view(request):
    """Custom view for Reading category"""
    context = {
        **admin.site.each_context(request),
        'title': 'Reading Content Management',
        'lessons': Lesson.objects.filter(lesson_type='reading').order_by('-display_order', '-created_at'),
        'passages': Passage.objects.all().order_by('-display_order', '-created_at'),
        'opts': {'app_label': 'api', 'model_name': 'reading'},
    }
    return render(request, 'admin/api/reading_category.html', context)

def writing_view(request):
    """Custom view for Writing category"""
    context = {
        **admin.site.each_context(request),
        'title': 'Writing Content Management',
        'lessons': Lesson.objects.filter(lesson_type='writing').order_by('-display_order', '-created_at'),
        'writing_sections': WritingSection.objects.all().order_by('-display_order', '-created_at'),
        'opts': {'app_label': 'api', 'model_name': 'writing'},
    }
    return render(request, 'admin/api/writing_category.html', context)

def math_view(request):
    """Custom view for Math category"""
    context = {
        **admin.site.each_context(request),
        'title': 'Math Content Management',
        'lessons': Lesson.objects.filter(lesson_type='math').order_by('-display_order', '-created_at'),
        'math_sections': MathSection.objects.all().order_by('-display_order', '-created_at'),
        'opts': {'app_label': 'api', 'model_name': 'math'},
    }
    return render(request, 'admin/api/math_category.html', context)

urlpatterns = [
    # Custom category pages - must come BEFORE admin.site.urls
    path('admin/api/reading/', admin.site.admin_view(reading_view), name='api_reading'),
    path('admin/api/writing/', admin.site.admin_view(writing_view), name='api_writing'),
    path('admin/api/math/', admin.site.admin_view(math_view), name='api_math'),
    # Standard admin URLs
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    
    # Web frontend routes
    path('', web_views.index, name='web-index'),
    path('web/', web_views.index, name='web-index'),
    path('web/passages', web_views.index, name='web-passages'),
    path('web/passages/', web_views.index, name='web-passages-slash'),
    path('web/subscription/success', web_views.subscription_success, name='subscription-success'),
    path('web/subscription/cancel', web_views.subscription_cancel, name='subscription-cancel'),
    # Legal and support (canonical URLs for app stores and links)
    path('terms/', web_views.terms, name='terms'),
    path('privacy/', web_views.privacy, name='privacy'),
    path('support/', web_views.support, name='support'),
    path('delete-account/', web_views.delete_account, name='delete-account'),
]

if settings.DEBUG:
    # Serve static files from STATICFILES_DIRS in development
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


