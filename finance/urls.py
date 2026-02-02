from django.urls import path 

from . import views

urlpatterns = [
    path('dashboard/', views.dashboardpage, name='dashboard'),
    path('profile/', views.profilpage, name='profile'),
    path('logout/',views.logout,name='logout'),
]
