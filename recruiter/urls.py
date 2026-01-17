from django.urls import path
from . import views

app_name = 'recruiter'

urlpatterns = [
    path('', views.RecruiterDashboardView.as_view(), name='dashboard'),
    path('api/upload/', views.upload_batch, name='upload_batch'),
    path('api/analyze/', views.analyze_batch, name='analyze_batch'),
    path('api/status/', views.get_batch_status, name='batch_status'),
    path('api/clear/', views.clear_batch, name='clear_batch'),
]