from django.urls import path 

from . import views

urlpatterns = [
    path('dashboard/', views.dashboardpage, name='dashboard'),
    path('compte/create/', views.creation_compte, name='compte'),
    path('compte/ajouter/',views.ajouter_revenu , name='revenus'),
    path('compte/retrait/',views.enregistrer_depense ,name='depenses'),
    path('profile/', views.profilpage, name='profile'),
    path('logout/',views.logout,name='logout'),
]
