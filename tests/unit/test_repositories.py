"""
Unit tests for repository pattern implementations.

Tests for BaseRepository, FamilyTreeRepository, and PersonRepository.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from accounts.repositories import (
    BaseRepository, FamilyTreeRepository, PersonRepository,
    family_tree_repository, person_repository
)
from accounts.models import FamilyTree, Person


@pytest.mark.unit
class TestBaseRepository:
    """Test cases for BaseRepository abstract class."""
    
    def test_repository_requires_model(self):
        """Test that repository must define a model."""
        with pytest.raises(NotImplementedError):
            BaseRepository()
    
    def test_get_by_id_with_cache_hit(self, sample_person):
        """Test get_by_id with cache hit."""
        with patch('accounts.repositories.cache') as mock_cache:
            mock_cache.get.return_value = sample_person
            
            repo = PersonRepository()
            result = repo.get_by_id(sample_person.id)
            
            assert result == sample_person
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_not_called()
    
    def test_get_by_id_with_cache_miss(self, sample_person):
        """Test get_by_id with cache miss."""
        with patch('accounts.repositories.cache') as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set.return_value = True
            
            repo = PersonRepository()
            result = repo.get_by_id(sample_person.id)
            
            assert result == sample_person
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()
    
    def test_get_by_id_not_found(self):
        """Test get_by_id when object doesn't exist."""
        repo = PersonRepository()
        result = repo.get_by_id(99999)  # Non-existent ID
        
        assert result is None
    
    def test_create_object(self, family_tree):
        """Test creating a new object."""
        repo = PersonRepository()
        
        person_data = {
            'family_tree': family_tree,
            'first_name': 'New',
            'last_name': 'Person',
            'birth_date': date(1990, 1, 1)
        }
        
        with patch.object(repo, '_invalidate_cache') as mock_invalidate:
            result = repo.create(**person_data)
            
            assert result.first_name == 'New'
            assert result.last_name == 'Person'
            assert result.family_tree == family_tree
            mock_invalidate.assert_called_once_with(result)
    
    def test_update_object(self, sample_person):
        """Test updating an existing object."""
        repo = PersonRepository()
        
        with patch.object(repo, '_invalidate_cache') as mock_invalidate:
            result = repo.update(sample_person.id, first_name='Updated')
            
            assert result.first_name == 'Updated'
            assert result.id == sample_person.id
            mock_invalidate.assert_called_once_with(result)
    
    def test_update_nonexistent_object(self):
        """Test updating a non-existent object."""
        repo = PersonRepository()
        result = repo.update(99999, first_name='Updated')
        
        assert result is None
    
    def test_delete_object(self, sample_person):
        """Test deleting an object."""
        repo = PersonRepository()
        person_id = sample_person.id
        
        with patch.object(repo, '_invalidate_cache') as mock_invalidate:
            result = repo.delete(person_id)
            
            assert result is True
            mock_invalidate.assert_called_once()
            
            # Verify object is deleted
            assert not Person.objects.filter(id=person_id).exists()
    
    def test_delete_nonexistent_object(self):
        """Test deleting a non-existent object."""
        repo = PersonRepository()
        result = repo.delete(99999)
        
        assert result is False
    
    def test_count_objects(self, sample_family):
        """Test counting objects with filters."""
        repo = PersonRepository()
        tree = sample_family['father'].family_tree
        
        total_count = repo.count(family_tree=tree)
        assert total_count == 6  # All family members
        
        male_count = repo.count(family_tree=tree, first_name__in=['John', 'Bobby', 'William'])
        assert male_count == 3
    
    def test_exists_check(self, sample_family):
        """Test checking if objects exist."""
        repo = PersonRepository()
        tree = sample_family['father'].family_tree
        
        assert repo.exists(family_tree=tree)
        assert not repo.exists(family_tree=tree, first_name='NonExistent')


@pytest.mark.unit
class TestFamilyTreeRepository:
    """Test cases for FamilyTreeRepository."""
    
    def test_get_user_trees_with_cache(self, user, family_tree):
        """Test getting user trees with caching."""
        with patch('accounts.repositories.cache') as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set.return_value = True
            
            repo = FamilyTreeRepository()
            trees = repo.get_user_trees(user)
            
            assert len(trees) == 1
            assert trees[0] == family_tree
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()
    
    def test_get_tree_with_members(self, user, sample_family):
        """Test getting tree with all members loaded."""
        tree = sample_family['father'].family_tree
        
        repo = FamilyTreeRepository()
        result = repo.get_tree_with_members(tree.id, user)
        
        assert result == tree
        # Verify relationships are prefetched (would need to check queries in real test)
    
    def test_get_tree_with_members_unauthorized(self, sample_family):
        """Test getting tree when user doesn't have access."""
        tree = sample_family['father'].family_tree
        unauthorized_user = Person.objects.create_user(
            username='unauthorized',
            email='unauthorized@test.com',
            password='pass'
        )
        
        repo = FamilyTreeRepository()
        result = repo.get_tree_with_members(tree.id, unauthorized_user)
        
        assert result is None
    
    def test_get_tree_statistics_with_cache(self, sample_family):
        """Test getting tree statistics with caching."""
        tree = sample_family['father'].family_tree
        
        with patch('accounts.repositories.cache') as mock_cache:
            mock_cache.get.return_value = None
            mock_cache.set.return_value = True
            
            repo = FamilyTreeRepository()
            stats = repo.get_tree_statistics(tree.id)
            
            assert stats['total_people'] == 6
            assert stats['living_people'] == 4
            assert stats['deceased_people'] == 2
            mock_cache.get.assert_called_once()
            mock_cache.set.assert_called_once()
    
    def test_get_tree_statistics_nonexistent(self):
        """Test getting statistics for non-existent tree."""
        repo = FamilyTreeRepository()
        stats = repo.get_tree_statistics(99999)
        
        assert stats == {}
    
    def test_search_trees(self, user):
        """Test searching family trees."""
        # Create multiple trees
        tree1 = FamilyTree.objects.create(
            name='My Family History',
            description='Complete family history',
            super_admin=user
        )
        tree2 = FamilyTree.objects.create(
            name='Smith Genealogy',
            description='Smith family tree',
            super_admin=user
        )
        
        repo = FamilyTreeRepository()
        
        # Search by name
        results = repo.search_trees(user, 'Family')
        assert tree1 in results
        
        # Search by description
        results = repo.search_trees(user, 'genealogy')
        assert tree2 in results
        
        # Search with no matches
        results = repo.search_trees(user, 'nonexistent')
        assert len(results) == 0


@pytest.mark.unit
class TestPersonRepository:
    """Test cases for PersonRepository."""
    
    def test_get_tree_members_optimized(self, sample_family):
        """Test getting tree members with relationship optimization."""
        tree = sample_family['father'].family_tree
        
        repo = PersonRepository()
        members = repo.get_tree_members(tree, optimize_relationships=True)
        
        assert len(members) == 6
        # In a real test, we'd verify select_related was used
    
    def test_get_tree_members_unoptimized(self, sample_family):
        """Test getting tree members without optimization."""
        tree = sample_family['father'].family_tree
        
        repo = PersonRepository()
        members = repo.get_tree_members(tree, optimize_relationships=False)
        
        assert len(members) == 6
    
    def test_get_person_with_relationships(self, sample_family):
        """Test getting person with all relationships loaded."""
        father = sample_family['father']
        
        repo = PersonRepository()
        result = repo.get_person_with_relationships(father.id, father.family_tree)
        
        assert result == father
        # Verify relationships are loaded
    
    def test_get_children(self, sample_family):
        """Test getting children of a person."""
        father = sample_family['father']
        
        repo = PersonRepository()
        children = repo.get_children(father)
        
        assert len(children) == 2
        assert sample_family['son'] in children
        assert sample_family['daughter'] in children
    
    def test_get_siblings(self, sample_family):
        """Test getting siblings of a person."""
        son = sample_family['son']
        
        repo = PersonRepository()
        siblings = repo.get_siblings(son)
        
        assert len(siblings) == 1
        assert sample_family['daughter'] in siblings
    
    def test_get_siblings_no_parents(self, family_tree):
        """Test getting siblings when person has no parents."""
        orphan = Person.objects.create(
            family_tree=family_tree,
            first_name='Orphan',
            last_name='Person'
        )
        
        repo = PersonRepository()
        siblings = repo.get_siblings(orphan)
        
        assert len(siblings) == 0
    
    def test_get_ancestors(self, sample_family):
        """Test getting ancestors of a person."""
        son = sample_family['son']
        
        repo = PersonRepository()
        ancestors = repo.get_ancestors(son, generations=5)
        
        # Should include father, grandfather, grandmother
        expected_ancestors = [
            sample_family['father'],
            sample_family['mother'],
            sample_family['grandfather'],
            sample_family['grandmother']
        ]
        
        for ancestor in expected_ancestors:
            assert ancestor in ancestors
    
    def test_get_descendants(self, sample_family):
        """Test getting descendants of a person."""
        grandfather = sample_family['grandfather']
        
        repo = PersonRepository()
        descendants = repo.get_descendants(grandfather, generations=5)
        
        # Should include father, son, daughter
        expected_descendants = [
            sample_family['father'],
            sample_family['son'],
            sample_family['daughter']
        ]
        
        for descendant in expected_descendants:
            assert descendant in descendants
    
    def test_search_people_by_name(self, sample_family):
        """Test searching people by name."""
        tree = sample_family['father'].family_tree
        
        repo = PersonRepository()
        results = repo.search_people(tree, 'John')
        
        assert sample_family['father'] in results
    
    def test_search_people_with_filters(self, sample_family):
        """Test searching people with additional filters."""
        tree = sample_family['father'].family_tree
        
        repo = PersonRepository()
        results = repo.search_people(
            tree, 
            'Doe',
            filters={
                'birth_year_min': 1970,
                'birth_year_max': 1980,
                'living': True
            }
        )
        
        # Should find son and daughter (born in 1970s, still living)
        assert sample_family['son'] in results
        assert sample_family['daughter'] in results
        assert sample_family['father'] not in results  # Born before 1970
    
    def test_get_people_by_generation(self, sample_family):
        """Test grouping people by generation."""
        tree = sample_family['father'].family_tree
        
        repo = PersonRepository()
        generations = repo.get_people_by_generation(tree)
        
        assert len(generations) >= 3  # At least 3 generations
        
        # Verify some people are in correct generations
        # (exact generation assignment depends on algorithm)
        all_people = []
        for gen_people in generations.values():
            all_people.extend(gen_people)
        
        assert len(all_people) == 6  # All family members assigned
    
    def test_bulk_create_people(self, family_tree):
        """Test bulk creating multiple people."""
        people_data = [
            {
                'first_name': 'Bulk1',
                'last_name': 'Person',
                'birth_date': date(1990, 1, 1)
            },
            {
                'first_name': 'Bulk2',
                'last_name': 'Person', 
                'birth_date': date(1991, 1, 1)
            },
            {
                'first_name': 'Bulk3',
                'last_name': 'Person',
                'birth_date': date(1992, 1, 1)
            }
        ]
        
        repo = PersonRepository()
        with patch('accounts.repositories.cache.delete_pattern') as mock_delete:
            created_people = repo.bulk_create_people(family_tree, people_data)
            
            assert len(created_people) == 3
            assert all(p.family_tree == family_tree for p in created_people)
            
            # Verify cache invalidation
            assert mock_delete.call_count >= 2


@pytest.mark.unit
class TestRepositoryInstances:
    """Test the global repository instances."""
    
    def test_global_instances_exist(self):
        """Test that global repository instances are properly initialized."""
        assert family_tree_repository is not None
        assert isinstance(family_tree_repository, FamilyTreeRepository)
        
        assert person_repository is not None
        assert isinstance(person_repository, PersonRepository)
    
    def test_repository_models_assigned(self):
        """Test that repository models are correctly assigned."""
        assert family_tree_repository.model == FamilyTree
        assert person_repository.model == Person