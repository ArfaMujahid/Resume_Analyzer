from django.urls import path
from . import views

app_name = 'talent'

urlpatterns = [
    path('', views.talent_dashboard, name='dashboard'),
    path('analysis/', views.talent_analysis, name='analysis'),
    path('analyze/', views.analyze_resume, name='analyze_resume'),
    path('suggestions/<int:resume_id>/', views.talent_suggestions, name='suggestions'),
    path('api/upload/', views.upload_resume_file, name='upload_api'),
    path('api/analyze/', views.analyze_resume_text, name='analyze_api'),
    path('api/improve-bullets/', views.improve_resume_bullets, name='improve_bullets_api'),
    path('api/get-suggestions/', views.get_suggestions, name='get_suggestions_api'),
]