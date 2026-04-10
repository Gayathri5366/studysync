from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('session/start/', views.start_session, name='start_session'),
    path('session/stop/', views.stop_session, name='stop_session'),
    path('session/status/', views.timer_status, name='timer_status'),
    path('reports/daily/', views.daily_report, name='daily_report'),
    path('reports/weekly/', views.weekly_report, name='weekly_report'),
    path('history/', views.session_history, name='session_history'),
    path('profile/', views.profile_settings, name='profile_settings'),
    path('admin-panel/stats/', views.admin_stats, name='admin_stats'),
    path('admin-panel/users/', views.admin_user_list, name='admin_user_list'),
    path('admin-panel/users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('session/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('admin-panel/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
]
