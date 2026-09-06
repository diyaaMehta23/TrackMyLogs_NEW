"""
URL configuration for weblogs project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from myapp.views import submit_token, fetch_logs, analysis, fetch_analysis_data

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/submit-token/', submit_token, name='submit_token'),
    path('api/fetch-logs/', fetch_logs, name='fetch_logs'),
    path('logout/', auth_views.LogoutView.as_view(next_page='loginpage'), name='logout'),
    path('analysis/', analysis, name='analysis'),
    path('api/fetch-analysis-data/', fetch_analysis_data, name='fetch_analysis_data'),
    path('', include('myapp.urls')),
]
