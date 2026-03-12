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
    path('analyze-bulk-matching/', views.analyze_bulk_matching, name='analyze_bulk_matching'),
    path('analyze-candidate-profile/', views.analyze_candidate_profile, name='analyze_candidate_profile'),
    path('ai-assist/', views.ai_assist, name='ai_assist'),
] 