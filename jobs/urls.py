from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.JobDescriptionListView.as_view(), name='list'),
    path('create/', views.JobDescriptionCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.JobDescriptionDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.JobDescriptionEditView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.JobDescriptionDeleteView.as_view(), name='delete'),
]