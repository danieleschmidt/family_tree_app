"""
Performance tests for the Family Tree application.

Tests query performance, cache efficiency, and scalability with large datasets.
"""

import pytest
import time
from django.test import TransactionTestCase
from django.db import connection, reset_queries
from django.test.utils import override_settings

from accounts.models import FamilyTree, Person
from accounts.services import RelationshipCalculator, FamilyTreeSearchService
from accounts.repositories import person_repository, family_tree_repository
from accounts.cache import cache_manager


@pytest.mark.slow
class TestQueryPerformance:
    """Test database query performance and optimization."""
    
    def test_family_tree_loading_performance(self, large_family_tree, benchmark_setup):
        """Test performance of loading large family trees."""
        tree, people = benchmark_setup(500)  # 500 people
        
        start_time = time.time()
        reset_queries()
        
        # Load all people with relationships
        members = person_repository.get_tree_members(tree, optimize_relationships=True)
        
        end_time = time.time()
        query_count = len(connection.queries)
        
        # Performance assertions
        assert end_time - start_time < 2.0  # Should complete in under 2 seconds
        assert query_count < 10  # Should use minimal queries due to optimization
        assert len(members) == 500
    
    def test_relationship_calculation_performance(self, large_family_tree):
        """Test performance of relationship calculations."""
        people = large_family_tree[:10]  # Use first 10 people
        calculator = RelationshipCalculator(people[0].family_tree)
        
        start_time = time.time()
        
        # Calculate relationships between all pairs
        relationships = []
        for i, person1 in enumerate(people):
            for person2 in people[i+1:]:
                rel = calculator.calculate_relationship(person1, person2)
                relationships.append(rel)
        
        end_time = time.time()
        
        # Should calculate 45 relationships quickly
        assert end_time - start_time < 5.0  # Should complete in under 5 seconds
        assert len(relationships) == 45  # 10 choose 2
    
    def test_search_performance(self, large_family_tree):
        """Test search performance with large datasets."""
        tree = large_family_tree[0].family_tree
        search_service = FamilyTreeSearchService(tree)
        
        start_time = time.time()
        reset_queries()
        
        # Perform various searches
        results1 = search_service.search_people(query='Person')
        results2 = search_service.search_people(birth_year_range=(1950, 1970))
        results3 = search_service.search_people(location='Boston')
        
        end_time = time.time()
        query_count = len(connection.queries)
        
        # Performance assertions
        assert end_time - start_time < 3.0  # Should complete in under 3 seconds
        assert query_count < 20  # Should use reasonable number of queries
        assert len(results1) > 0
    
    @override_settings(DEBUG=True)  # Enable query logging
    def test_n_plus_one_queries(self, sample_family):
        """Test for N+1 query problems."""
        tree = sample_family['father'].family_tree
        
        reset_queries()
        
        # Load people and access their relationships
        people = Person.objects.filter(family_tree=tree)
        for person in people:
            # This should not cause additional queries if properly optimized
            _ = person.father
            _ = person.mother
            _ = person.spouse
        
        query_count = len(connection.queries)
        
        # Should use select_related to avoid N+1 queries
        # With 6 people, should not exceed reasonable query count
        assert query_count < 10  # Reasonable limit


@pytest.mark.slow
class TestCachePerformance:
    """Test cache performance and efficiency."""
    
    def test_cache_hit_rate(self, sample_family):
        """Test cache hit rate for repeated operations."""
        tree = sample_family['father'].family_tree
        calculator = RelationshipCalculator(tree)
        
        # Clear cache to start fresh
        cache_manager.cache.clear()
        initial_hits = cache_manager.cache_hits
        initial_misses = cache_manager.cache_misses
        
        # Perform same relationship calculation multiple times
        person1 = sample_family['father']
        person2 = sample_family['son']
        
        for _ in range(10):
            calculator.calculate_relationship(person1, person2)
        
        hits = cache_manager.cache_hits - initial_hits
        misses = cache_manager.cache_misses - initial_misses
        
        # First call should be cache miss, subsequent should be hits
        assert misses == 1  # Only first calculation
        assert hits >= 9   # Subsequent calculations cached
    
    def test_cache_invalidation_performance(self, large_family_tree):
        """Test performance of cache invalidation."""
        tree = large_family_tree[0].family_tree
        
        # Warm up cache with various operations
        family_tree_repository.get_tree_statistics(tree.id)
        person_repository.get_tree_members(tree)
        
        start_time = time.time()
        
        # Test cache invalidation
        cache_manager.invalidate_family_tree_cache(tree.id)
        
        end_time = time.time()
        
        # Cache invalidation should be fast
        assert end_time - start_time < 1.0
    
    def test_memory_usage_with_large_cache(self, benchmark_setup):
        """Test memory usage with large cached datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create large dataset and cache it
        tree, people = benchmark_setup(1000)
        
        # Cache various operations
        for person in people[:100]:  # Cache first 100 people
            cache_manager.set(f"person_{person.id}", person, 3600)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024  # 100MB


@pytest.mark.slow
class TestScalabilityLimits:
    """Test application behavior at scale limits."""
    
    def test_maximum_family_tree_size(self, benchmark_setup):
        """Test handling of maximum-sized family trees."""
        # Test with close to maximum allowed size
        tree, people = benchmark_setup(1000)  # Large but manageable
        
        start_time = time.time()
        
        # Test various operations still work
        stats = family_tree_repository.get_tree_statistics(tree.id)
        members = person_repository.get_tree_members(tree)
        generations = person_repository.get_people_by_generation(tree)
        
        end_time = time.time()
        
        # Operations should still complete in reasonable time
        assert end_time - start_time < 10.0  # 10 seconds max
        assert stats['total_people'] == 1000
        assert len(members) == 1000
        assert len(generations) > 0
    
    def test_concurrent_user_performance(self, sample_family):
        """Test performance with simulated concurrent users."""
        import threading
        import queue
        
        tree = sample_family['father'].family_tree
        results_queue = queue.Queue()
        
        def simulate_user_operations():
            """Simulate typical user operations."""
            start_time = time.time()
            
            # Typical user workflow
            members = person_repository.get_tree_members(tree)
            stats = family_tree_repository.get_tree_statistics(tree.id)
            search_service = FamilyTreeSearchService(tree)
            search_results = search_service.search_people('John')
            
            end_time = time.time()
            results_queue.put(end_time - start_time)
        
        # Simulate 10 concurrent users
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=simulate_user_operations)
            threads.append(thread)
        
        start_time = time.time()
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect individual operation times
        operation_times = []
        while not results_queue.empty():
            operation_times.append(results_queue.get())
        
        # Performance assertions
        assert len(operation_times) == 10  # All operations completed
        assert total_time < 15.0  # Total time reasonable
        assert max(operation_times) < 5.0  # No single operation too slow
        assert sum(operation_times) / len(operation_times) < 2.0  # Average time good
    
    def test_deep_family_tree_performance(self, user):
        """Test performance with very deep family trees (many generations)."""
        tree = FamilyTree.objects.create(
            name='Deep Family Tree',
            super_admin=user
        )
        
        # Create 10 generations deep
        previous_person = None
        people = []
        
        for generation in range(10):
            person = Person.objects.create(
                family_tree=tree,
                first_name=f'Gen{generation}',
                last_name='Deep',
                birth_date=f'{1900 + generation * 20}-01-01',
                father=previous_person if generation > 0 else None
            )
            people.append(person)
            previous_person = person
        
        # Test relationship calculation between distant generations
        calculator = RelationshipCalculator(tree)
        
        start_time = time.time()
        
        # Calculate relationship between first and last generation
        relationship = calculator.calculate_relationship(people[0], people[-1])
        
        end_time = time.time()
        
        # Should handle deep relationships efficiently
        assert end_time - start_time < 2.0
        assert relationship['degree'] > 0  # Should find relationship
    
    def test_bulk_operations_performance(self, family_tree):
        """Test performance of bulk operations."""
        # Prepare large amount of data
        people_data = []
        for i in range(500):
            people_data.append({
                'first_name': f'Bulk{i}',
                'last_name': 'Person',
                'birth_date': f'{1950 + (i % 50)}-01-01'
            })
        
        start_time = time.time()
        
        # Bulk create people
        created_people = person_repository.bulk_create_people(family_tree, people_data)
        
        end_time = time.time()
        
        # Bulk operations should be efficient
        assert end_time - start_time < 5.0  # Should complete quickly
        assert len(created_people) == 500
        
        # Verify all people were created
        total_people = Person.objects.filter(family_tree=family_tree).count()
        assert total_people == 500


@pytest.mark.slow
class TestMemoryLeaks:
    """Test for potential memory leaks."""
    
    def test_repeated_operations_memory_stable(self, sample_family):
        """Test that repeated operations don't cause memory leaks."""
        import psutil
        import os
        import gc
        
        process = psutil.Process(os.getpid())
        tree = sample_family['father'].family_tree
        
        # Get baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss
        
        # Perform many repeated operations
        for _ in range(100):
            # Various operations that might leak memory
            members = person_repository.get_tree_members(tree)
            stats = family_tree_repository.get_tree_statistics(tree.id)
            
            # Clear references
            del members
            del stats
            
            # Periodic garbage collection
            if _ % 20 == 0:
                gc.collect()
        
        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss
        memory_increase = final_memory - baseline_memory
        
        # Memory increase should be minimal (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB limit
    
    def test_cache_memory_cleanup(self, benchmark_setup):
        """Test that cache memory is properly cleaned up."""
        import gc
        
        tree, people = benchmark_setup(200)
        
        # Fill cache with data
        for person in people:
            cache_manager.set(f"test_person_{person.id}", person, 1)  # 1 second TTL
        
        # Wait for cache expiration
        time.sleep(2)
        
        # Force garbage collection
        gc.collect()
        
        # Cache should be cleaned up
        # Note: This is a basic test - more sophisticated memory tracking
        # would require additional tools in a real production environment