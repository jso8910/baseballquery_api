from django.urls import path
from rest_api import views

urlpatterns = [
    path('batting_stats', views.BattingStatQuery.as_view(), name='batting_stat_query'),
    path('pitching_stats', views.PitchingStatQuery.as_view(), name='pitching_stat_query'),
    path('saved_query', views.SavedQueries.as_view(), name='saved_query'),
]