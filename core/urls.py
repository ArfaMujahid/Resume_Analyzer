from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("talent/", views.talent_dashboard, name="talent_dashboard"),
    path("talent/analysis/", views.talent_analysis, name="talent_analysis"),
    path("talent/results/", views.talent_results, name="talent_results"),
    path("recruiter/", views.recruiter_dashboard, name="recruiter_dashboard"),
]
