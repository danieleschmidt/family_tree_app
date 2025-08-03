"""
Advanced repository pattern implementation for Family Tree application.

This module provides repository classes that encapsulate data access logic
and provide a clean interface for business logic services.
"""

from django.db import models, transaction
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models import Q, Count, Prefetch, Avg, Max, Min
from django.db.models.query import QuerySet
from typing import List, Optional, Dict, Any, Union, Tuple
from abc import ABC, abstractmethod
from datetime import datetime, date
import logging

from .models import FamilyTree, Person, User

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """
    Abstract base repository providing common database operations with advanced features.
    """
    
    model = None
    cache_timeout = 3600  # 1 hour default cache
    
    def __init__(self):
        if not self.model:
            raise NotImplementedError("Repository must define a model class")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cache_prefix = f"{self.model.__name__.lower()}"
    
    def get_by_id(self, obj_id: int, use_cache: bool = True, 
                  select_related: List[str] = None) -> Optional[models.Model]:
        """Get object by ID with caching and optimization."""
        cache_key = f"{self.cache_prefix}_{obj_id}"
        
        if use_cache:
            cached_obj = cache.get(cache_key)
            if cached_obj:
                return cached_obj
        
        try:
            queryset = self.model.objects
            if select_related:
                queryset = queryset.select_related(*select_related)
            
            obj = queryset.get(id=obj_id)
            
            if use_cache:
                cache.set(cache_key, obj, self.cache_timeout)
            return obj
        except ObjectDoesNotExist:
            return None
    
    def get_by_ids(self, ids: List[int], use_cache: bool = True) -> Dict[int, Any]:
        """Get multiple objects by IDs efficiently."""
        result = {}
        missing_ids = []
        
        if use_cache:
            for obj_id in ids:
                cache_key = f"{self.cache_prefix}_{obj_id}"
                obj = cache.get(cache_key)
                if obj is not None:
                    result[obj_id] = obj
                else:
                    missing_ids.append(obj_id)
        else:
            missing_ids = ids
        
        if missing_ids:
            objects = self.model.objects.filter(id__in=missing_ids)
            for obj in objects:
                result[obj.id] = obj
                if use_cache:
                    cache_key = f"{self.cache_prefix}_{obj.id}"
                    cache.set(cache_key, obj, self.cache_timeout)
        
        return result
    
    def get_all(self, limit: Optional[int] = None, 
                order_by: List[str] = None,
                select_related: List[str] = None,
                prefetch_related: List[str] = None,
                **filters) -> QuerySet:
        """Get all objects with advanced filtering and optimization."""
        queryset = self.model.objects.filter(**filters)
        
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        if limit:
            queryset = queryset[:limit]
        
        return queryset
    
    @transaction.atomic
    def create(self, **kwargs) -> models.Model:
        """Create new object with transaction support."""
        try:
            obj = self.model.objects.create(**kwargs)
            self.logger.info(f"Created {self.model.__name__} with id {obj.id}")
            return obj
        except Exception as e:
            self.logger.error(f"Error creating {self.model.__name__}: {str(e)}")
            raise
    
    @transaction.atomic
    def bulk_create(self, objects: List[Dict], batch_size: int = 1000) -> List[models.Model]:
        """Bulk create objects efficiently."""
        try:
            model_objects = [self.model(**obj_data) for obj_data in objects]
            created_objects = self.model.objects.bulk_create(
                model_objects, 
                batch_size=batch_size
            )
            self.logger.info(f"Bulk created {len(created_objects)} {self.model.__name__} objects")
            return created_objects
        except Exception as e:
            self.logger.error(f"Error bulk creating {self.model.__name__}: {str(e)}")
            raise
    
    @transaction.atomic
    def update(self, obj_id: int, **kwargs) -> Optional[models.Model]:
        """Update object by ID with cache invalidation."""
        try:
            obj = self.get_by_id(obj_id, use_cache=False)
            if obj is None:
                return None
            
            for key, value in kwargs.items():
                setattr(obj, key, value)
            obj.save()
            
            # Invalidate cache
            cache_key = f"{self.cache_prefix}_{obj_id}"
            cache.delete(cache_key)
            
            self.logger.info(f"Updated {self.model.__name__} with id {obj_id}")
            return obj
        except Exception as e:
            self.logger.error(f"Error updating {self.model.__name__} {obj_id}: {str(e)}")
            raise
    
    @transaction.atomic
    def delete(self, obj_id: int) -> bool:
        """Delete object by ID with cache invalidation."""
        try:
            obj = self.get_by_id(obj_id, use_cache=False)
            if obj is None:
                return False
            
            # Invalidate cache
            cache_key = f"{self.cache_prefix}_{obj_id}"
            cache.delete(cache_key)
            
            obj.delete()
            self.logger.info(f"Deleted {self.model.__name__} with id {obj_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting {self.model.__name__} {obj_id}: {str(e)}")
            raise
    
    def count(self, **filters) -> int:
        """Count objects with optional filters."""
        return self.model.objects.filter(**filters).count()
    
    def exists(self, **filters) -> bool:
        """Check if objects exist with given filters."""
        return self.model.objects.filter(**filters).exists()


class PersonRepository(BaseRepository):
    """
    Repository for Person model with specialized genealogical methods.
    """
    
    model = Person
    
    def get_by_family_tree(self, family_tree: FamilyTree, 
                          include_relationships: bool = True) -> QuerySet:
        """Get all people in a family tree with optimized queries."""
        queryset = Person.objects.filter(family_tree=family_tree)
        
        if include_relationships:
            queryset = queryset.select_related(
                'father', 'mother', 'spouse', 'birth_location', 'death_location'
            ).prefetch_related('children')
        
        return queryset.order_by('last_name', 'first_name')
    
    def search_advanced(self, family_tree: FamilyTree, 
                       query: str = None,
                       birth_year_range: Tuple[int, int] = None,
                       location: str = None,
                       gender: str = None,
                       is_living: bool = None,
                       limit: int = 100) -> QuerySet:
        """Advanced search with multiple criteria."""
        queryset = Person.objects.filter(family_tree=family_tree)
        
        # Text search
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(middle_name__icontains=query) |
                Q(maiden_name__icontains=query) |
                Q(nickname__icontains=query) |
                Q(biography__icontains=query)
            )
        
        # Birth year range
        if birth_year_range:
            start_year, end_year = birth_year_range
            queryset = queryset.filter(
                birth_date__year__gte=start_year,
                birth_date__year__lte=end_year
            )
        
        # Location filter
        if location:
            queryset = queryset.filter(
                Q(birth_location__name__icontains=location) |
                Q(death_location__name__icontains=location)
            )
        
        # Gender filter
        if gender:
            queryset = queryset.filter(gender=gender)
        
        # Living status
        if is_living is not None:
            if is_living:
                queryset = queryset.filter(death_date__isnull=True)
            else:
                queryset = queryset.filter(death_date__isnull=False)
        
        return queryset.select_related('birth_location', 'death_location')[:limit]
    
    def get_family_group(self, person: Person) -> Dict[str, List[Person]]:
        """Get immediate family members grouped by relationship."""
        result = {
            'parents': [],
            'spouses': [],
            'children': [],
            'siblings': []
        }
        
        # Parents
        if person.father:
            result['parents'].append(person.father)
        if person.mother:
            result['parents'].append(person.mother)
        
        # Spouse
        if person.spouse:
            result['spouses'].append(person.spouse)
        
        # Children
        children = Person.objects.filter(
            Q(father=person) | Q(mother=person),
            family_tree=person.family_tree
        ).order_by('birth_date')
        result['children'] = list(children)
        
        # Siblings
        result['siblings'] = self.get_siblings(person)
        
        return result
    
    def get_ancestors(self, person: Person, max_generations: int = 10) -> List[Person]:
        """Get all ancestors efficiently using iterative approach."""
        ancestors = []
        seen_ids = set()
        current_generation = [person]
        
        for generation in range(max_generations):
            next_generation = []
            
            # Get all parent IDs for current generation
            parent_ids = set()
            for p in current_generation:
                if p.father_id and p.father_id not in seen_ids:
                    parent_ids.add(p.father_id)
                if p.mother_id and p.mother_id not in seen_ids:
                    parent_ids.add(p.mother_id)
            
            if not parent_ids:
                break
            
            # Fetch all parents in one query
            parents = Person.objects.filter(
                id__in=parent_ids,
                family_tree=person.family_tree
            ).select_related('father', 'mother')
            
            for parent in parents:
                if parent.id not in seen_ids:
                    ancestors.append(parent)
                    seen_ids.add(parent.id)
                    next_generation.append(parent)
            
            current_generation = next_generation
        
        return ancestors
    
    def get_descendants(self, person: Person, max_generations: int = 10) -> List[Person]:
        """Get all descendants efficiently."""
        descendants = []
        seen_ids = set()
        current_generation = [person]
        
        for generation in range(max_generations):
            # Get all children for current generation
            parent_ids = [p.id for p in current_generation]
            children = Person.objects.filter(
                Q(father_id__in=parent_ids) | Q(mother_id__in=parent_ids),
                family_tree=person.family_tree
            ).exclude(id__in=seen_ids).select_related('father', 'mother')
            
            if not children:
                break
            
            next_generation = []
            for child in children:
                if child.id not in seen_ids:
                    descendants.append(child)
                    seen_ids.add(child.id)
                    next_generation.append(child)
            
            current_generation = next_generation
        
        return descendants
    
    def get_siblings(self, person: Person, include_half_siblings: bool = True) -> List[Person]:
        """Get siblings with option to include half-siblings."""
        siblings = []
        
        # Get all potential siblings
        potential_siblings = Person.objects.filter(
            family_tree=person.family_tree
        ).exclude(id=person.id)
        
        if person.father_id or person.mother_id:
            # Find siblings sharing at least one parent
            sibling_query = Q()
            
            if person.father_id:
                sibling_query |= Q(father_id=person.father_id)
            
            if person.mother_id:
                sibling_query |= Q(mother_id=person.mother_id)
            
            potential_siblings = potential_siblings.filter(sibling_query)
            
            for sibling in potential_siblings:
                # Full siblings (same father and mother)
                if (person.father_id and sibling.father_id == person.father_id and
                    person.mother_id and sibling.mother_id == person.mother_id):
                    siblings.append(sibling)
                # Half siblings (if enabled)
                elif include_half_siblings:
                    if ((person.father_id and sibling.father_id == person.father_id) or
                        (person.mother_id and sibling.mother_id == person.mother_id)):
                        siblings.append(sibling)
        
        return siblings
    
    def get_statistics(self, family_tree: FamilyTree) -> Dict[str, Any]:
        """Get detailed statistics for people in a family tree."""
        people = Person.objects.filter(family_tree=family_tree)
        
        # Basic counts
        total_count = people.count()
        living_count = people.filter(death_date__isnull=True).count()
        deceased_count = people.filter(death_date__isnull=False).count()
        
        # Gender distribution
        gender_stats = people.values('gender').annotate(count=Count('id'))
        
        # Age statistics (for living people)
        living_people = people.filter(
            death_date__isnull=True,
            birth_date__isnull=False
        )
        
        age_stats = {}
        if living_people.exists():
            # Calculate ages
            current_year = datetime.now().year
            ages = []
            for person in living_people:
                age = current_year - person.birth_date.year
                ages.append(age)
            
            if ages:
                age_stats = {
                    'average_age': sum(ages) / len(ages),
                    'oldest_age': max(ages),
                    'youngest_age': min(ages)
                }
        
        # Birth year range
        birth_years = people.filter(birth_date__isnull=False).aggregate(
            earliest=Min('birth_date__year'),
            latest=Max('birth_date__year')
        )
        
        return {
            'total_people': total_count,
            'living_people': living_count,
            'deceased_people': deceased_count,
            'gender_distribution': {item['gender']: item['count'] for item in gender_stats},
            'age_statistics': age_stats,
            'birth_year_range': birth_years,
            'completion_rate': self._calculate_completion_rate(people)
        }
    
    def _calculate_completion_rate(self, people: QuerySet) -> float:
        """Calculate data completion rate for people."""
        if not people.exists():
            return 0.0
        
        total_fields = 0
        completed_fields = 0
        
        for person in people:
            # Essential fields
            fields_to_check = [
                'first_name', 'last_name', 'birth_date', 'gender',
                'father', 'mother', 'birth_location'
            ]
            
            for field in fields_to_check:
                total_fields += 1
                if getattr(person, field):
                    completed_fields += 1
        
        return (completed_fields / total_fields) * 100 if total_fields > 0 else 0.0


class FamilyTreeRepository(BaseRepository):
    """
    Repository for FamilyTree model with advanced tree management.
    """
    
    model = FamilyTree
    
    def get_user_trees(self, user, include_stats: bool = False) -> QuerySet:
        """Get all family trees accessible to a user."""
        queryset = FamilyTree.objects.filter(
            Q(created_by=user) | Q(members=user)
        ).distinct().select_related('created_by')
        
        if include_stats:
            queryset = queryset.prefetch_related('person_set')
        
        return queryset.order_by('-created_at')
    
    def get_public_trees(self, limit: int = 50) -> QuerySet:
        """Get public family trees."""
        return FamilyTree.objects.filter(
            is_public=True
        ).select_related('created_by').order_by('-created_at')[:limit]
    
    def get_tree_with_members(self, tree_id: int) -> Optional[FamilyTree]:
        """Get family tree with all members and permissions."""
        try:
            return FamilyTree.objects.select_related('created_by').prefetch_related(
                'members', 'person_set'
            ).get(id=tree_id)
        except FamilyTree.DoesNotExist:
            return None
    
    @transaction.atomic
    def add_member(self, family_tree: FamilyTree, user, role: str = 'member') -> bool:
        """Add a member to a family tree."""
        try:
            if not family_tree.members.filter(id=user.id).exists():
                family_tree.members.add(user)
                self.logger.info(f"Added user {user.id} to family tree {family_tree.id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error adding member to family tree: {str(e)}")
            raise
    
    @transaction.atomic
    def remove_member(self, family_tree: FamilyTree, user) -> bool:
        """Remove a member from a family tree."""
        try:
            if family_tree.members.filter(id=user.id).exists():
                family_tree.members.remove(user)
                self.logger.info(f"Removed user {user.id} from family tree {family_tree.id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing member from family tree: {str(e)}")
            raise
    
    def get_tree_statistics(self, family_tree: FamilyTree) -> Dict[str, Any]:
        """Get comprehensive statistics for a family tree."""
        person_repo = PersonRepository()
        person_stats = person_repo.get_statistics(family_tree)
        
        # Tree-specific statistics
        tree_stats = {
            'created_date': family_tree.created_at,
            'member_count': family_tree.members.count(),
            'is_public': family_tree.is_public,
            'generations': self._calculate_generations(family_tree),
            'family_units': self._count_family_units(family_tree),
            'tree_completeness': self._calculate_tree_completeness(family_tree)
        }
        
        return {**person_stats, **tree_stats}
    
    def _calculate_generations(self, family_tree: FamilyTree) -> int:
        """Calculate number of generations in the tree."""
        # Find root people (no parents)
        roots = Person.objects.filter(
            family_tree=family_tree,
            father__isnull=True,
            mother__isnull=True
        )
        
        if not roots.exists():
            return Person.objects.filter(family_tree=family_tree).count() > 0 and 1 or 0
        
        max_depth = 0
        for root in roots:
            depth = self._calculate_depth_iterative(root)
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _calculate_depth_iterative(self, person: Person) -> int:
        """Calculate tree depth iteratively to avoid recursion limits."""
        max_depth = 1
        queue = [(person, 1)]
        visited = set()
        
        while queue:
            current_person, depth = queue.pop(0)
            
            if current_person.id in visited:
                continue
            
            visited.add(current_person.id)
            max_depth = max(max_depth, depth)
            
            # Add children to queue
            children = Person.objects.filter(
                Q(father=current_person) | Q(mother=current_person),
                family_tree=person.family_tree
            )
            
            for child in children:
                if child.id not in visited:
                    queue.append((child, depth + 1))
        
        return max_depth
    
    def _count_family_units(self, family_tree: FamilyTree) -> int:
        """Count family units (couples with children)."""
        couples = Person.objects.filter(
            family_tree=family_tree,
            spouse__isnull=False
        ).count()
        
        return couples // 2  # Each couple is counted twice
    
    def _calculate_tree_completeness(self, family_tree: FamilyTree) -> float:
        """Calculate overall tree completeness score."""
        people = Person.objects.filter(family_tree=family_tree)
        
        if not people.exists():
            return 0.0
        
        total_score = 0
        total_people = people.count()
        
        for person in people:
            person_score = 0
            max_score = 8  # Maximum points per person
            
            # Basic information (4 points)
            if person.first_name:
                person_score += 1
            if person.last_name:
                person_score += 1
            if person.birth_date:
                person_score += 1
            if person.gender:
                person_score += 1
            
            # Relationships (4 points)
            if person.father:
                person_score += 1
            if person.mother:
                person_score += 1
            if person.spouse:
                person_score += 1
            
            # Has children
            if Person.objects.filter(
                Q(father=person) | Q(mother=person),
                family_tree=family_tree
            ).exists():
                person_score += 1
            
            total_score += (person_score / max_score) * 100
        
        return total_score / total_people if total_people > 0 else 0.0


class CacheManager:
    """
    Cache management utility for repositories.
    """
    
    @staticmethod
    def invalidate_family_tree_cache(family_tree_id: int):
        """Invalidate all cache keys related to a family tree."""
        keys_to_delete = []
        
        # Family tree cache
        keys_to_delete.append(f"familytree_{family_tree_id}")
        
        # Person cache for this family tree
        people = Person.objects.filter(family_tree_id=family_tree_id)
        for person in people:
            keys_to_delete.append(f"person_{person.id}")
        
        # Delete all keys
        cache.delete_many(keys_to_delete)
    
    @staticmethod
    def warm_up_cache(family_tree: FamilyTree):
        """Pre-load frequently accessed data into cache."""
        # Cache family tree
        cache.set(f"familytree_{family_tree.id}", family_tree, 3600)
        
        # Cache all people in the tree
        people = Person.objects.filter(family_tree=family_tree).select_related(
            'father', 'mother', 'spouse'
        )
        for person in people:
            cache.set(f"person_{person.id}", person, 3600)