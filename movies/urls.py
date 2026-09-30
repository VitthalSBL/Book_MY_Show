from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    path('', views.home, name='home'),
    path('movies/', views.movie_list, name='list'),
    path('movies/<slug:slug>/', views.movie_detail, name='detail'),
    path('movies/<slug:slug>/review/', views.add_review, name='add_review'),
    path('review/<int:pk>/edit/', views.edit_review, name='edit_review'),
    path('review/<int:pk>/report/', views.report_review, name='report_review'),
    path('search/', views.search, name='search'),
    path('api/search-count/', views.search_count_api, name='search_count'),
]
