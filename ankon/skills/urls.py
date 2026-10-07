# Ankon's part
from django.urls import path
from . import views

urlpatterns = [
    path('<objectid:pk>/delete/', views.remove_skill, name='delete_skill'),
    path('', views.skills, name='skills'),
    path('mine/', views.my_skills, name='my_skills'),
    path('add/', views.add_skill, name='add_skill'),
    path('search/', views.search_skills, name='search_skills'),
    path('<objectid:pk>/', views.skill_detail, name='skill_detail'),
    path('<objectid:pk>/edit/', views.edit_skill, name='edit_skill'),
    path('<objectid:pk>/remove/', views.remove_skill, name='remove_skill'),
]
