from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.home, name='home'),
    path('history/', views.history, name='history'),
    path('settings/', views.settings_view, name='settings'),
]
