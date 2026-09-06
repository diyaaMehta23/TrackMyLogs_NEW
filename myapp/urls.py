from myapp import views
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from .views import log_list,fetch_logs,analysis,terms_of_service, close_event

urlpatterns = [
    path('loginpage/', views.loginpage, name='loginpage'), 
    path('', views.home, name='home'),
    path('forgotpass/', views.forgotpass, name='forgotpass'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('logout', views.user_logout, name='logout'),
    path('download/', views.download_script, name='download_script'),
    path('GetAuthenticationToken', views.GetAuthenticationToken, name='GetAuthenticationToken'),
    path('profile', views.profile, name='profile'),
    path('logs', log_list, name='log_list'),
    path('api/fetch-logs/', fetch_logs, name='fetch_logs'),
    path('terms-of-service/', terms_of_service, name='terms_of_service'),
    path('analysis/', analysis, name='analysis'),
    path('resetpass/', views.reset_password_view, name='reset_password'),
     path('api/close-event/', close_event),
    path('', include('pwa.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)