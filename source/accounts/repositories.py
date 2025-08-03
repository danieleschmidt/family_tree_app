"""
Repository pattern implementation for Family Tree application.

This module provides repository classes that encapsulate data access logic
and provide a clean interface for business logic services.
"""

from django.db import models, transaction
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q, Count, Prefetch
from typing import List, Optional, Dict, Any, Union
from abc import ABC, abstractmethod
import logging

from .models import FamilyTree, Person, User
from .database.connection import db_optimizer

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """
    Abstract base repository providing common database operations.
    """
    
    model = None
    cache_timeout = 3600  # 1 hour default cache
    
    def __init__(self):
        if not self.model:
            raise NotImplementedError("Repository must define a model class")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_by_id(self, obj_id: int) -> Optional[models.Model]:
        """Get object by ID with caching."""
        cache_key = f"{self.model.__name__.lower()}_{obj_id}"
        cached_obj = cache.get(cache_key)
        
        if cached_obj:
            return cached_obj
        
        try:
            obj = self.model.objects.get(id=obj_id)
            cache.set(cache_key, obj, self.cache_timeout)
            return obj
        except ObjectDoesNotExist:
            return None
    
    def get_all(self, limit: Optional[int] = None, **filters) -> List[models.Model]:
        """Get all objects with optional filtering and limiting."""
        queryset = self.model.objects.filter(**filters)
        queryset = self._apply_default_optimizations(queryset)
        
        if limit:
            queryset = queryset[:limit]
        
        return list(queryset)
    
    def create(self, **data) -> models.Model:
        """Create a new object."""
        try:
            with transaction.atomic():
                obj = self.model.objects.create(**data)
                self._invalidate_cache(obj)
                return obj
        except Exception as e:
            self.logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            raise
    
    def update(self, obj_id: int, **data) -> Optional[models.Model]:
        """Update an existing object."""
        try:
            with transaction.atomic():
                obj = self.model.objects.get(id=obj_id)
                for field, value in data.items():
                    setattr(obj, field, value)
                obj.save()
                self._invalidate_cache(obj)
                return obj
        except ObjectDoesNotExist:
            return None
        except Exception as e:
            self.logger.error(f"Error updating {self.model.__name__} {obj_id}: {str(e)}")
            raise
    
    def delete(self, obj_id: int) -> bool:
        """Delete an object by ID."""
        try:
            with transaction.atomic():
                obj = self.model.objects.get(id=obj_id)
                self._invalidate_cache(obj)
                obj.delete()
                return True
        except ObjectDoesNotExist:
            return False
        except Exception as e:
            self.logger.error(f"Error deleting {self.model.__name__} {obj_id}: {str(e)}")
            raise
    
    def count(self, **filters) -> int:
        """Count objects matching filters."""
        return self.model.objects.filter(**filters).count()
    
    def exists(self, **filters) -> bool:
        """Check if objects matching filters exist."""
        return self.model.objects.filter(**filters).exists()
    
    def _apply_default_optimizations(self, queryset):
        """Apply default query optimizations."""
        return db_optimizer.optimize_queryset(queryset, 'select_related')
    
    def _invalidate_cache(self, obj):
        """Invalidate cache for the object."""
        cache_key = f"{self.model.__name__.lower()}_{obj.id}"
        cache.delete(cache_key)


class FamilyTreeRepository(BaseRepository):
    """
    Repository for FamilyTree model operations.
    """
    
    model = FamilyTree
    
    def get_user_trees(self, user: User) -> List[FamilyTree]:
        """Get all family trees accessible to a user."""
        cache_key = f"user_trees_{user.id}"
        cached_trees = cache.get(cache_key)
        
        if cached_trees:
            return cached_trees
        
        trees = list(
            FamilyTree.objects.filter(super_admin=user)
            .select_related('super_admin')
            .prefetch_related('person_set')
        )
        
        cache.set(cache_key, trees, self.cache_timeout)
        return trees
    
    def get_tree_with_members(self, tree_id: int, user: User) -> Optional[FamilyTree]:
        """Get family tree with all members, ensuring user has access."""
        try:
            return (
                FamilyTree.objects
                .select_related('super_admin')
                .prefetch_related(
                    Prefetch(
                        'person_set',
                        queryset=Person.objects.select_related('father', 'mother', 'spouse')
                    )
                )
                .get(id=tree_id, super_admin=user)
            )
        except ObjectDoesNotExist:
            return None
    
    def get_tree_statistics(self, tree_id: int) -> Dict[str, Any]:
        """Get comprehensive statistics for a family tree."""
        cache_key = f"tree_stats_{tree_id}"
        cached_stats = cache.get(cache_key)
        
        if cached_stats:
            return cached_stats
        
        try:
            tree = FamilyTree.objects.get(id=tree_id)
            
            # Basic counts
            total_people = Person.objects.filter(family_tree=tree).count()
            living_people = Person.objects.filter(
                family_tree=tree, death_date__isnull=True
            ).count()
            
            # Gender distribution (if gender field exists)
            gender_stats = Person.objects.filter(family_tree=tree).values(
                'gender'
            ).annotate(count=Count('id'))
            
            # Age distribution
            from django.utils import timezone
            from datetime import date
            
            people_with_birth_dates = Person.objects.filter(
                family_tree=tree, birth_date__isnull=False
            )
            
            ages = []
            for person in people_with_birth_dates:
                if person.death_date:
                    age = (person.death_date - person.birth_date).days // 365
                else:
                    age = (date.today() - person.birth_date).days // 365
                ages.append(age)
            
            stats = {
                'total_people': total_people,
                'living_people': living_people,
                'deceased_people': total_people - living_people,
                'gender_distribution': {item['gender']: item['count'] for item in gender_stats},
                'average_age': sum(ages) / len(ages) if ages else 0,
                'oldest_age': max(ages) if ages else 0,
                'youngest_age': min(ages) if ages else 0,
                'people_with_birth_dates': len(ages),
                'completion_rate': len(ages) / total_people if total_people > 0 else 0
            }
            
            cache.set(cache_key, stats, self.cache_timeout // 2)  # Shorter cache for stats
            return stats
            
        except ObjectDoesNotExist:
            return {}
    
    def search_trees(self, user: User, query: str) -> List[FamilyTree]:
        """Search family trees by name or description."""
        return list(
            FamilyTree.objects.filter(
                super_admin=user
            ).filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            ).select_related('super_admin')
        )


class PersonRepository(BaseRepository):
    """
    Repository for Person model operations.
    """
    
    model = Person
    
    def get_tree_members(self, family_tree: FamilyTree, 
                        optimize_relationships: bool = True) -> List[Person]:
        """Get all members of a family tree with optimized queries."""
        queryset = Person.objects.filter(family_tree=family_tree)
        
        if optimize_relationships:
            queryset = queryset.select_related('father', 'mother', 'spouse')
        
        return list(queryset)
    
    def get_person_with_relationships(self, person_id: int, 
                                    family_tree: FamilyTree) -> Optional[Person]:
        """Get person with all relationship information loaded."""
        try:
            return (
                Person.objects
                .select_related('father', 'mother', 'spouse', 'family_tree')
                .prefetch_related('children', 'siblings')
                .get(id=person_id, family_tree=family_tree)
            )
        except ObjectDoesNotExist:
            return None
    
    def get_children(self, person: Person) -> List[Person]:
        """Get all children of a person."""
        return list(
            Person.objects.filter(
                Q(father=person) | Q(mother=person),
                family_tree=person.family_tree
            ).select_related('father', 'mother', 'spouse')
        )
    
    def get_siblings(self, person: Person) -> List[Person]:
        """Get all siblings of a person."""
        siblings = Person.objects.filter(
            family_tree=person.family_tree
        ).exclude(id=person.id)
        
        # Find siblings through shared parents
        if person.father or person.mother:
            sibling_filters = Q()
            
            if person.father:
                sibling_filters |= Q(father=person.father)
            if person.mother:
                sibling_filters |= Q(mother=person.mother)
            
            siblings = siblings.filter(sibling_filters)
        else:
            # No parents defined, no siblings
            siblings = siblings.none()
        
        return list(siblings.select_related('father', 'mother', 'spouse'))
    
    def get_ancestors(self, person: Person, generations: int = 10) -> List[Person]:
        """Get ancestors up to specified number of generations."""
        ancestors = []
        current_generation = [person]
        
        for gen in range(generations):
            next_generation = []
            
            for current_person in current_generation:
                if current_person.father:
                    ancestors.append(current_person.father)
                    next_generation.append(current_person.father)
                
                if current_person.mother:
                    ancestors.append(current_person.mother)
                    next_generation.append(current_person.mother)
            
            if not next_generation:
                break
            
            current_generation = next_generation
        
        return ancestors
    
    def get_descendants(self, person: Person, generations: int = 10) -> List[Person]:
        """Get descendants up to specified number of generations."""
        descendants = []
        current_generation = [person]
        
        for gen in range(generations):
            next_generation = []
            
            for current_person in current_generation:
                children = self.get_children(current_person)
                descendants.extend(children)
                next_generation.extend(children)
            
            if not next_generation:
                break
            
            current_generation = next_generation
        
        return descendants
    
    def search_people(self, family_tree: FamilyTree, query: str, 
                     filters: Dict[str, Any] = None) -> List[Person]:
        """Advanced search for people in a family tree."""
        queryset = Person.objects.filter(family_tree=family_tree)
        
        # Text search
        if query:
            text_search = (
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(middle_name__icontains=query) |
                Q(biography__icontains=query)
            )
            queryset = queryset.filter(text_search)
        
        # Apply additional filters
        if filters:
            if 'birth_year_min' in filters and 'birth_year_max' in filters:
                queryset = queryset.filter(
                    birth_date__year__gte=filters['birth_year_min'],
                    birth_date__year__lte=filters['birth_year_max']
                )
            
            if 'gender' in filters:
                queryset = queryset.filter(gender=filters['gender'])
            
            if 'living' in filters:
                if filters['living']:
                    queryset = queryset.filter(death_date__isnull=True)
                else:
                    queryset = queryset.filter(death_date__isnull=False)
            
            if 'location' in filters:
                location_search = (
                    Q(birth_location__icontains=filters['location']) |
                    Q(death_location__icontains=filters['location'])
                )
                queryset = queryset.filter(location_search)
        
        return list(queryset.select_related('father', 'mother', 'spouse'))
    
    def get_people_by_generation(self, family_tree: FamilyTree) -> Dict[int, List[Person]]:
        """Group people by generation level."""
        all_people = self.get_tree_members(family_tree, optimize_relationships=True)
        generations = {}
        
        # Simple generation calculation based on parent relationships
        # This is a basic implementation - could be enhanced with more sophisticated algorithms
        
        # Find root people (no parents in the tree)
        roots = [p for p in all_people if not p.father and not p.mother]
        
        if not roots:
            # If no clear roots, use oldest people as generation 0
            roots = sorted(all_people, key=lambda p: p.birth_date or date(1900, 1, 1))[:5]
        
        # Assign generations using BFS
        visited = set()
        queue = [(person, 0) for person in roots]
        
        while queue:
            person, generation = queue.pop(0)
            
            if person.id in visited:
                continue
            
            visited.add(person.id)
            
            if generation not in generations:
                generations[generation] = []
            generations[generation].append(person)
            
            # Add children to next generation
            children = self.get_children(person)
            for child in children:
                if child.id not in visited:
                    queue.append((child, generation + 1))
        
        return generations
    
    def bulk_create_people(self, family_tree: FamilyTree, 
                          people_data: List[Dict[str, Any]]) -> List[Person]:
        """Efficiently create multiple people at once."""
        people_objects = []
        
        try:
            with transaction.atomic():
                for data in people_data:
                    person = Person(family_tree=family_tree, **data)
                    people_objects.append(person)
                
                created_people = Person.objects.bulk_create(people_objects)
                
                # Invalidate relevant caches
                cache.delete_pattern(f"user_trees_{family_tree.super_admin.id}")
                cache.delete_pattern(f"tree_stats_{family_tree.id}")
                
                return created_people
                
        except Exception as e:
            self.logger.error(f"Error bulk creating people: {str(e)}")
            raise


# Repository instances
family_tree_repository = FamilyTreeRepository()
person_repository = PersonRepository()