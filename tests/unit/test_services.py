"""
Unit tests for the Family Tree application services.

Tests for RelationshipCalculator, FamilyTreeSearchService, and FamilyTreeAnalytics.
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from accounts.services import RelationshipCalculator, FamilyTreeSearchService, FamilyTreeAnalytics
from accounts.models import Person, FamilyTree


@pytest.mark.unit
class TestRelationshipCalculator:
    """Test cases for RelationshipCalculator service."""
    
    def test_calculate_self_relationship(self, sample_person):
        """Test relationship calculation for same person."""
        calculator = RelationshipCalculator(sample_person.family_tree)
        result = calculator.calculate_relationship(sample_person, sample_person)
        
        assert result['relationship'] == 'self'
        assert result['degree'] == 0
        assert result['generation_diff'] == 0
    
    def test_calculate_parent_child_relationship(self, sample_family):
        """Test parent-child relationship calculation."""
        father = sample_family['father']
        son = sample_family['son']
        
        calculator = RelationshipCalculator(father.family_tree)
        
        # Test father to son
        result = calculator.calculate_relationship(father, son)
        assert result['relationship'] == 'parent'
        assert result['degree'] == 1
        assert result['generation_diff'] == 1
        
        # Test son to father
        result = calculator.calculate_relationship(son, father)
        assert result['relationship'] == 'child'
        assert result['degree'] == 1
        assert result['generation_diff'] == -1
    
    def test_calculate_spouse_relationship(self, sample_family):
        """Test spouse relationship calculation."""
        father = sample_family['father']
        mother = sample_family['mother']
        
        calculator = RelationshipCalculator(father.family_tree)
        result = calculator.calculate_relationship(father, mother)
        
        assert result['relationship'] == 'spouse'
        assert result['degree'] == 1
        assert result['generation_diff'] == 0
    
    def test_calculate_sibling_relationship(self, sample_family):
        """Test sibling relationship calculation."""
        son = sample_family['son']
        daughter = sample_family['daughter']
        
        calculator = RelationshipCalculator(son.family_tree)
        result = calculator.calculate_relationship(son, daughter)
        
        assert result['relationship'] == 'sibling'
        assert result['degree'] == 2  # Through common parents
    
    def test_calculate_grandparent_relationship(self, sample_family):
        """Test grandparent-grandchild relationship calculation."""
        grandfather = sample_family['grandfather']
        son = sample_family['son']
        
        calculator = RelationshipCalculator(grandfather.family_tree)
        
        # Test grandfather to grandson
        result = calculator.calculate_relationship(grandfather, son)
        assert result['relationship'] == 'grandparent'
        assert result['degree'] == 2
        
        # Test grandson to grandfather
        result = calculator.calculate_relationship(son, grandfather)
        assert result['relationship'] == 'grandchild'
        assert result['degree'] == 2
    
    def test_no_relationship(self, user):
        """Test calculation when no relationship exists."""
        tree = FamilyTree.objects.create(name='Test Tree', super_admin=user)
        
        person1 = Person.objects.create(
            family_tree=tree,
            first_name='Unrelated',
            last_name='Person1'
        )
        
        person2 = Person.objects.create(
            family_tree=tree,
            first_name='Unrelated',
            last_name='Person2'
        )
        
        calculator = RelationshipCalculator(tree)
        result = calculator.calculate_relationship(person1, person2)
        
        assert result['relationship'] == 'no relation'
        assert result['degree'] == -1
    
    @patch('accounts.services.cache')
    def test_relationship_caching(self, mock_cache, sample_family):
        """Test that relationship calculations are cached."""
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        
        father = sample_family['father']
        son = sample_family['son']
        
        calculator = RelationshipCalculator(father.family_tree)
        calculator.calculate_relationship(father, son)
        
        # Verify cache was checked and set
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()
    
    def test_get_connected_people(self, sample_family):
        """Test getting all connected people for a person."""
        father = sample_family['father']
        calculator = RelationshipCalculator(father.family_tree)
        
        connected = calculator._get_connected_people(father)
        
        # Father should be connected to his parents, spouse, and children
        expected_connections = {
            sample_family['grandfather'],  # father
            sample_family['grandmother'],  # mother
            sample_family['mother'],       # spouse
            sample_family['son'],          # child
            sample_family['daughter']      # child
        }
        
        assert connected == expected_connections


@pytest.mark.unit
class TestFamilyTreeSearchService:
    """Test cases for FamilyTreeSearchService."""
    
    def test_search_by_name(self, sample_family):
        """Test searching people by name."""
        tree = sample_family['father'].family_tree
        search_service = FamilyTreeSearchService(tree)
        
        # Search for "John"
        results = search_service.search_people(query='John')
        assert len(results) == 1
        assert results[0] == sample_family['father']
        
        # Search for "Doe" (should find multiple)
        results = search_service.search_people(query='Doe')
        doe_people = [sample_family['father'], sample_family['son'], sample_family['daughter']]
        for person in doe_people:
            assert person in results
    
    def test_search_by_birth_year_range(self, sample_family):
        """Test searching people by birth year range."""
        tree = sample_family['father'].family_tree
        search_service = FamilyTreeSearchService(tree)
        
        # Search for people born between 1970-1980
        results = search_service.search_people(
            birth_year_range=(1970, 1980)
        )
        
        # Should find son (1975) and daughter (1978)
        expected = [sample_family['son'], sample_family['daughter']]
        for person in expected:
            assert person in results
    
    def test_search_by_location(self, sample_family):
        """Test searching people by location."""
        tree = sample_family['father'].family_tree
        search_service = FamilyTreeSearchService(tree)
        
        # Search for people born in Boston
        results = search_service.search_people(location='Boston')
        
        # Should find multiple people born in Boston
        boston_people = [
            sample_family['grandfather'],
            sample_family['grandmother'], 
            sample_family['father'],
            sample_family['son'],
            sample_family['daughter']
        ]
        
        for person in boston_people:
            assert person in results
    
    def test_search_with_relationship_filter(self, sample_family):
        """Test searching for people related to a specific person."""
        tree = sample_family['father'].family_tree
        search_service = FamilyTreeSearchService(tree)
        
        # Find people related to the father
        results = search_service.search_people(
            relationship_to=sample_family['father']
        )
        
        # Should find family members (excluding father himself)
        assert sample_family['father'] not in results
        assert len(results) > 0  # Should find related people
    
    def test_get_suggestions(self, sample_family):
        """Test search suggestions functionality."""
        tree = sample_family['father'].family_tree
        search_service = FamilyTreeSearchService(tree)
        
        # Get suggestions for "Jo"
        suggestions = search_service.get_suggestions('Jo')
        
        assert 'John' in suggestions
        assert len(suggestions) <= 10  # Respects limit
    
    def test_combined_search_filters(self, sample_family):
        """Test search with multiple filters combined."""
        tree = sample_family['father'].family_tree
        search_service = FamilyTreeSearchService(tree)
        
        # Search for "Doe" people born after 1970 in Boston
        results = search_service.search_people(
            query='Doe',
            birth_year_range=(1970, 1990),
            location='Boston'
        )
        
        # Should find son and daughter
        assert sample_family['son'] in results
        assert sample_family['daughter'] in results
        assert sample_family['father'] not in results  # Born before 1970


@pytest.mark.unit
class TestFamilyTreeAnalytics:
    """Test cases for FamilyTreeAnalytics service."""
    
    def test_get_tree_statistics(self, sample_family):
        """Test getting basic tree statistics."""
        tree = sample_family['father'].family_tree
        analytics = FamilyTreeAnalytics(tree)
        
        stats = analytics.get_tree_statistics()
        
        assert stats['total_people'] == 6  # All family members
        assert stats['living_people'] == 4  # Grandparents are deceased
        assert stats['deceased_people'] == 2
        assert stats['generations'] > 0
        assert 'families' in stats
        assert 'oldest_person' in stats
    
    def test_calculate_generations(self, sample_family):
        """Test generation calculation."""
        tree = sample_family['father'].family_tree
        analytics = FamilyTreeAnalytics(tree)
        
        generations = analytics._calculate_generations()
        
        # Should have at least 3 generations
        assert generations >= 3
    
    def test_count_family_units(self, sample_family):
        """Test counting family units (couples)."""
        tree = sample_family['father'].family_tree
        analytics = FamilyTreeAnalytics(tree)
        
        family_count = analytics._count_family_units()
        
        # Should have 2 couples (grandparents + parents)
        assert family_count == 2
    
    def test_get_oldest_person_age(self, sample_family):
        """Test getting oldest person's age."""
        tree = sample_family['father'].family_tree
        analytics = FamilyTreeAnalytics(tree)
        
        oldest_age = analytics._get_oldest_person_age()
        
        # Grandfather should be oldest (even if deceased)
        assert oldest_age is not None
        assert oldest_age > 0
    
    def test_get_birth_year_range(self, sample_family):
        """Test getting birth year range."""
        tree = sample_family['father'].family_tree
        analytics = FamilyTreeAnalytics(tree)
        
        oldest_year = analytics._get_oldest_birth_year()
        newest_year = analytics._get_most_recent_birth_year()
        
        assert oldest_year == 1920  # Grandfather's birth year
        assert newest_year == 1978  # Daughter's birth year
        assert oldest_year < newest_year
    
    def test_empty_tree_statistics(self, user):
        """Test statistics for empty family tree."""
        empty_tree = FamilyTree.objects.create(
            name='Empty Tree',
            super_admin=user
        )
        
        analytics = FamilyTreeAnalytics(empty_tree)
        stats = analytics.get_tree_statistics()
        
        assert stats['total_people'] == 0
        assert stats['living_people'] == 0
        assert stats['deceased_people'] == 0
        assert stats['generations'] == 0
    
    @patch('accounts.services.FamilyTreeAnalytics._calculate_depth_from_person')
    def test_complex_generation_calculation(self, mock_depth, large_family_tree):
        """Test generation calculation with complex family structure."""
        mock_depth.return_value = 3
        
        tree = large_family_tree[0].family_tree
        analytics = FamilyTreeAnalytics(tree)
        
        generations = analytics._calculate_generations()
        
        # Should handle complex structures
        assert generations >= 0
        mock_depth.assert_called()