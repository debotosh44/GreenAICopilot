from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('home/', views.home, name='home'),
    path('hiring-portal/', views.hiring_portal, name='hiring_portal'),
    path('match-engine/', views.match_engine, name='match_engine'),
    path('candidate-portal/', views.candidate_portal, name='candidate_portal'),
    path('candidate-shortlist/', views.get_role_candidates_ranked, name='candidate_shortlist'),
    path('candidate-learning-plan/', views.get_candidate_learning_plan, name='candidate_learning_plan'),
    path('role-candidates-popup/', views.get_role_candidates_popup, name='role_candidates_popup'),
    path('export-candidates/', views.export_candidates_csv, name='export_candidates_csv'),
    path('analyze-bulk-matching/', views.analyze_bulk_matching, name='analyze_bulk_matching'),
    path('analyze-candidate-profile/', views.analyze_candidate_profile, name='analyze_candidate_profile'),
    path('ai-assist/', views.ai_assist, name='ai_assist'),
] 