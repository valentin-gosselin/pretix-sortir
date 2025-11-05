from django.urls import path
from . import views

urlpatterns = [
    # Niveau organisateur
    path('control/organizer/<str:organizer>/settings/sortir/',
         views.SortirOrganizerSettingsView.as_view(),
         name='organizer-settings'),

    # Niveau événement
    path('control/event/<str:organizer>/<str:event>/settings/sortir/',
         views.SortirEventSettingsView.as_view(),
         name='event-settings'),

    # Historique
    path('control/event/<str:organizer>/<str:event>/sortir/usage/',
         views.SortirUsageListView.as_view(),
         name='usage-list'),

    # API AJAX pour validation carte (boutique)
    path('<str:organizer>/<str:event>/sortir/validate/',
         views.SortirCardValidationView.as_view(),
         name='validate-card'),

    # API pour nettoyer les pending de la session
    path('<str:organizer>/<str:event>/sortir/cleanup-session/',
         views.SortirCleanupSessionView.as_view(),
         name='cleanup-session'),
]
