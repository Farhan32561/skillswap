# Pranay's part
from django.urls import path
from . import views

urlpatterns = [
    path('<objectid:pk>/accept/', views.respond_exchange, {'action': 'accept'}, name='accept_exchange'),
    path('<objectid:pk>/reject/', views.respond_exchange, {'action': 'reject'}, name='reject_exchange'),
    path('<objectid:pk>/cancel/', views.respond_exchange, {'action': 'cancel'}, name='cancel_exchange'),
    path('<objectid:pk>/complete/', views.respond_exchange, {'action': 'complete'}, name='complete_exchange'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('matches/', views.matches, name='matches'),
    path('requests/', views.exchange_requests, name='exchange_requests'),
    path('history/', views.exchange_history, name='exchange_history'),
    path('request/<objectid:pk>/', views.send_exchange_request, name='send_exchange_request'),
    path('<objectid:pk>/', views.exchange_detail, name='exchange_detail'),
    path('<objectid:pk>/respond/', views.respond_exchange, name='respond_exchange'),
    path('<objectid:pk>/review/', views.review, name='review'),
]
