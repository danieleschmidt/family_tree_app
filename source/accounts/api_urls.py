"""
URL configuration for Family Tree REST API endpoints.
"""

from django.urls import path, include
from . import api

app_name = 'api'

urlpatterns = [
    # Family Tree API endpoints
    path('family-trees/', api.FamilyTreeAPIView.as_view(), name='family-trees-list'),
    path('family-trees/<int:tree_id>/', api.FamilyTreeAPIView.as_view(), name='family-tree-detail'),
    
    # Person/Member API endpoints
    path('family-trees/<int:tree_id>/members/', api.PersonAPIView.as_view(), name='person-list'),
    path('family-trees/<int:tree_id>/members/<int:person_id>/', api.PersonAPIView.as_view(), name='person-detail'),
    
    # Search and relationship endpoints
    path('family-trees/<int:tree_id>/search/', api.search_people_api, name='search-people'),
    path('family-trees/<int:tree_id>/suggestions/', api.search_suggestions_api, name='search-suggestions'),
    path('family-trees/<int:tree_id>/relationships/<int:person1_id>/<int:person2_id>/', 
         api.relationship_api, name='relationship-calculation'),
    
    # Analytics endpoint
    path('family-trees/<int:tree_id>/analytics/', api.family_tree_analytics_api, name='analytics'),
]