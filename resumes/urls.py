from django.urls import path
from . import views

app_name = 'resumes'

urlpatterns = [
    path('', views.ResumeListView.as_view(), name='list'),
    path('upload/', views.ResumeUploadView.as_view(), name='upload'),
    path('<uuid:pk>/', views.ResumeDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.ResumeEditView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.ResumeDeleteView.as_view(), name='delete'),
    path('<uuid:pk>/download/', views.ResumeDownloadView.as_view(), name='download'),
    path('<uuid:pk>/reparse/', views.reparse_resume, name='reparse'),
]