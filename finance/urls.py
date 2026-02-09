from django.urls import path 

from . import views

urlpatterns = [
    path('dashboard/', views.dashboardpage, name='dashboard'),

    # partie compte 
    path('comptes/', views.compte_list, name='compte_list'),
    path('compte/create/', views.creation_compte, name='compte'),
    path('compte/ajouter/',views.ajouter_revenu , name='revenus'),
    path('compte/retrait/',views.enregistrer_depense ,name='depenses'),
    path('comptes/<int:compte_id>/delete/', views.compte_delete, name='compte_delete'),
    path('comptes/<int:compte_id>/edit/',   views.compte_update, name='compte_update'),

    path('profile/', views.profilpage, name='profile'),

    path('transaction/',views.transaction_page,name='transaction'),
    path('logout/',views.logout,name='logout'),
    
  
]

  