"""
URL configuration for satlingo project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from web import views as web_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    
    # Web frontend routes
    path('', web_views.index, name='web-index'),
    path('web/', web_views.index, name='web-index'),
    path('web/subscription/success', web_views.subscription_success, name='subscription-success'),
    path('web/subscription/cancel', web_views.subscription_cancel, name='subscription-cancel'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


