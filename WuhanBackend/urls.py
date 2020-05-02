"""WuhanBackend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
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
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # 以下为api
    path('foo', views.foo, name='foo_url'),
    path('search_main', views.search_main, name='search_main_url'),
    path('search_xuanti', views.search_xuanti, name='search_news_url'),
    path('search_view', views.search_view, name='search_view_url'),
    path('search_eventa',views.search_eventa, name="search_eventa_url")
    # path('api/views/', views.foo, name='foo_url'),
    # path('api/events/', views.foo, name='foo_url'),

]
