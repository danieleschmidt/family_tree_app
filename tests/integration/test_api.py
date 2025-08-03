"""
Integration tests for the Family Tree REST API.

Tests API endpoints, authentication, and data flow between components.
"""

import pytest
import json
from django.urls import reverse
from django.contrib.auth import get_user_model

from accounts.models import FamilyTree, Person

User = get_user_model()


@pytest.mark.integration
@pytest.mark.api
class TestFamilyTreeAPI:
    """Integration tests for Family Tree API endpoints."""
    
    def test_list_family_trees_authenticated(self, authenticated_client, family_tree):
        """Test listing family trees for authenticated user."""
        url = reverse('api:family-trees-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == family_tree.name
    
    def test_list_family_trees_unauthenticated(self, client):
        """Test listing family trees without authentication."""
        url = reverse('api:family-trees-list')
        response = client.get(url)
        
        assert response.status_code == 302  # Redirect to login
    
    def test_create_family_tree(self, authenticated_client, api_headers):
        """Test creating a new family tree via API."""
        url = reverse('api:family-trees-list')
        data = {
            'name': 'New Family Tree',
            'description': 'Created via API test'
        }
        
        response = authenticated_client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data['status'] == 'success'
        assert response_data['data']['name'] == 'New Family Tree'
        
        # Verify tree was created in database
        assert FamilyTree.objects.filter(name='New Family Tree').exists()
    
    def test_create_family_tree_invalid_data(self, authenticated_client):
        """Test creating family tree with invalid data."""
        url = reverse('api:family-trees-list')
        data = {
            'description': 'Missing name field'
        }
        
        response = authenticated_client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        response_data = response.json()
        
        assert response_data['status'] == 'error'
        assert 'missing_fields' in response_data.get('errors', {})
    
    def test_get_family_tree_details(self, authenticated_client, family_tree):
        """Test getting detailed family tree information."""
        url = reverse('api:family-tree-detail', kwargs={'tree_id': family_tree.id})
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert data['data']['id'] == family_tree.id
        assert 'statistics' in data['data']
    
    def test_update_family_tree(self, authenticated_client, family_tree):
        """Test updating family tree information."""
        url = reverse('api:family-tree-detail', kwargs={'tree_id': family_tree.id})
        data = {
            'name': 'Updated Tree Name',
            'description': 'Updated description'
        }
        
        response = authenticated_client.put(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data['status'] == 'success'
        assert response_data['data']['name'] == 'Updated Tree Name'
        
        # Verify database was updated
        family_tree.refresh_from_db()
        assert family_tree.name == 'Updated Tree Name'
    
    def test_delete_family_tree(self, authenticated_client, family_tree):
        """Test deleting a family tree."""
        tree_id = family_tree.id
        url = reverse('api:family-tree-detail', kwargs={'tree_id': tree_id})
        
        response = authenticated_client.delete(url)
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data['status'] == 'success'
        
        # Verify tree was deleted
        assert not FamilyTree.objects.filter(id=tree_id).exists()
    
    def test_access_other_user_tree(self, client, family_tree):
        """Test that users can't access other users' trees."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='otherpass'
        )
        client.force_login(other_user)
        
        url = reverse('api:family-tree-detail', kwargs={'tree_id': family_tree.id})
        response = client.get(url)
        
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
class TestPersonAPI:
    """Integration tests for Person API endpoints."""
    
    def test_list_family_members(self, authenticated_client, sample_family):
        """Test listing all members of a family tree."""
        tree = sample_family['father'].family_tree
        url = reverse('api:person-list', kwargs={'tree_id': tree.id})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert len(data['data']) == 6  # All family members
    
    def test_get_person_details(self, authenticated_client, sample_family):
        """Test getting detailed person information."""
        person = sample_family['father']
        url = reverse('api:person-detail', kwargs={
            'tree_id': person.family_tree.id,
            'person_id': person.id
        })
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert data['data']['first_name'] == person.first_name
        assert data['data']['last_name'] == person.last_name
        assert 'father' in data['data']
        assert 'children' in data['data']
    
    def test_create_person(self, authenticated_client, family_tree):
        """Test creating a new person via API."""
        url = reverse('api:person-list', kwargs={'tree_id': family_tree.id})
        data = {
            'first_name': 'New',
            'last_name': 'Person',
            'birth_date': '1990-01-01',
            'birth_location': 'Test City',
            'biography': 'Test person created via API'
        }
        
        response = authenticated_client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data['status'] == 'success'
        assert response_data['data']['first_name'] == 'New'
        
        # Verify person was created
        assert Person.objects.filter(
            first_name='New',
            last_name='Person',
            family_tree=family_tree
        ).exists()
    
    def test_create_person_with_relationships(self, authenticated_client, sample_family):
        """Test creating person with parent relationships."""
        tree = sample_family['father'].family_tree
        father = sample_family['father']
        mother = sample_family['mother']
        
        url = reverse('api:person-list', kwargs={'tree_id': tree.id})
        data = {
            'first_name': 'New',
            'last_name': 'Child',
            'birth_date': '2000-01-01',
            'father_id': father.id,
            'mother_id': mother.id
        }
        
        response = authenticated_client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        
        # Verify relationships were set
        new_person = Person.objects.get(first_name='New', last_name='Child')
        assert new_person.father == father
        assert new_person.mother == mother
    
    def test_update_person(self, authenticated_client, sample_person):
        """Test updating person information."""
        url = reverse('api:person-detail', kwargs={
            'tree_id': sample_person.family_tree.id,
            'person_id': sample_person.id
        })
        data = {
            'first_name': 'Updated',
            'biography': 'Updated biography'
        }
        
        response = authenticated_client.put(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data['status'] == 'success'
        assert response_data['data']['first_name'] == 'Updated'
        
        # Verify database was updated
        sample_person.refresh_from_db()
        assert sample_person.first_name == 'Updated'
    
    def test_delete_person(self, authenticated_client, sample_person):
        """Test deleting a person."""
        person_id = sample_person.id
        url = reverse('api:person-detail', kwargs={
            'tree_id': sample_person.family_tree.id,
            'person_id': person_id
        })
        
        response = authenticated_client.delete(url)
        
        assert response.status_code == 200
        
        # Verify person was deleted
        assert not Person.objects.filter(id=person_id).exists()
    
    def test_search_people(self, authenticated_client, sample_family):
        """Test searching people via API."""
        tree = sample_family['father'].family_tree
        url = reverse('api:search-people', kwargs={'tree_id': tree.id})
        
        response = authenticated_client.get(url, {'q': 'John'})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert len(data['data']) >= 1
        assert any(person['first_name'] == 'John' for person in data['data'])
    
    def test_search_with_filters(self, authenticated_client, sample_family):
        """Test searching people with additional filters."""
        tree = sample_family['father'].family_tree
        url = reverse('api:search-people', kwargs={'tree_id': tree.id})
        
        response = authenticated_client.get(url, {
            'q': 'Doe',
            'birth_year_min': '1970',
            'birth_year_max': '1980',
            'location': 'Boston'
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        # Should find people matching criteria


@pytest.mark.integration
@pytest.mark.api  
class TestRelationshipAPI:
    """Integration tests for relationship calculation API."""
    
    def test_calculate_relationship(self, authenticated_client, sample_family):
        """Test calculating relationship between two people."""
        father = sample_family['father']
        son = sample_family['son']
        tree = father.family_tree
        
        url = reverse('api:relationship-calculation', kwargs={
            'tree_id': tree.id,
            'person1_id': father.id,
            'person2_id': son.id
        })
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert data['data']['relationship'] == 'parent'
        assert data['data']['person1']['id'] == father.id
        assert data['data']['person2']['id'] == son.id
    
    def test_calculate_sibling_relationship(self, authenticated_client, sample_family):
        """Test calculating sibling relationship."""
        son = sample_family['son']
        daughter = sample_family['daughter']
        tree = son.family_tree
        
        url = reverse('api:relationship-calculation', kwargs={
            'tree_id': tree.id,
            'person1_id': son.id,
            'person2_id': daughter.id
        })
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert data['data']['relationship'] == 'sibling'
    
    def test_calculate_no_relationship(self, authenticated_client, family_tree):
        """Test calculating relationship when none exists."""
        # Create two unrelated people
        person1 = Person.objects.create(
            family_tree=family_tree,
            first_name='Unrelated1',
            last_name='Person'
        )
        person2 = Person.objects.create(
            family_tree=family_tree,
            first_name='Unrelated2',
            last_name='Person'
        )
        
        url = reverse('api:relationship-calculation', kwargs={
            'tree_id': family_tree.id,
            'person1_id': person1.id,
            'person2_id': person2.id
        })
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert data['data']['relationship'] == 'no relation'


@pytest.mark.integration
@pytest.mark.api
class TestAnalyticsAPI:
    """Integration tests for analytics API."""
    
    def test_get_family_tree_analytics(self, authenticated_client, sample_family):
        """Test getting family tree analytics."""
        tree = sample_family['father'].family_tree
        url = reverse('api:analytics', kwargs={'tree_id': tree.id})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        stats = data['data']
        
        assert 'total_people' in stats
        assert 'living_people' in stats
        assert 'deceased_people' in stats
        assert 'generations' in stats
        assert stats['total_people'] == 6
    
    def test_get_suggestions(self, authenticated_client, sample_family):
        """Test getting search suggestions."""
        tree = sample_family['father'].family_tree
        url = reverse('api:search-suggestions', kwargs={'tree_id': tree.id})
        
        response = authenticated_client.get(url, {'q': 'Jo'})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['status'] == 'success'
        assert 'John' in data['data']


@pytest.mark.integration
class TestAPIErrorHandling:
    """Integration tests for API error handling."""
    
    def test_invalid_json_request(self, authenticated_client, family_tree):
        """Test API response to invalid JSON."""
        url = reverse('api:person-list', kwargs={'tree_id': family_tree.id})
        
        response = authenticated_client.post(
            url,
            'invalid json',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data['status'] == 'error'
    
    def test_nonexistent_family_tree(self, authenticated_client):
        """Test API response for non-existent family tree."""
        url = reverse('api:family-tree-detail', kwargs={'tree_id': 99999})
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 404
        data = response.json()
        assert data['status'] == 'error'
    
    def test_nonexistent_person(self, authenticated_client, family_tree):
        """Test API response for non-existent person."""
        url = reverse('api:person-detail', kwargs={
            'tree_id': family_tree.id,
            'person_id': 99999
        })
        
        response = authenticated_client.get(url)
        
        assert response.status_code == 404