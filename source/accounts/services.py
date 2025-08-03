"""
Family Tree Application Services

This module contains business logic services for family tree operations,
including relationship calculations, search functionality, and tree management.
"""

from typing import Dict, List, Optional, Tuple, Set
from collections import deque, defaultdict
from django.core.cache import cache
from django.db.models import Q
from .models import Person, FamilyTree


class RelationshipCalculator:
    """
    Service for calculating relationships between people in a family tree.
    
    Handles complex relationship calculations including:
    - Direct relationships (parent, child, spouse)
    - Extended relationships (cousin, aunt/uncle, etc.)
    - Step and adoptive relationships
    - Multi-generational calculations
    """
    
    RELATIONSHIP_CACHE_TIMEOUT = 3600  # 1 hour cache
    
    def __init__(self, family_tree: FamilyTree):
        self.family_tree = family_tree
        self.cache_prefix = f"relationship_{family_tree.id}"
    
    def calculate_relationship(self, person1: Person, person2: Person) -> Dict[str, str]:
        """
        Calculate the relationship between two people.
        
        Args:
            person1: First person
            person2: Second person
            
        Returns:
            Dictionary with relationship information:
            {
                'relationship': 'second cousin',
                'degree': 2,
                'generation_diff': 0,
                'common_ancestor': Person object,
                'path_description': 'detailed path explanation'
            }
        """
        if person1 == person2:
            return {'relationship': 'self', 'degree': 0, 'generation_diff': 0}
        
        # Check cache first
        cache_key = f"{self.cache_prefix}_{person1.id}_{person2.id}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Find shortest path between the two people
        path = self._find_shortest_path(person1, person2)
        
        if not path:
            result = {'relationship': 'no relation', 'degree': -1, 'generation_diff': 0}
        else:
            result = self._analyze_relationship_path(path)
        
        # Cache the result
        cache.set(cache_key, result, self.RELATIONSHIP_CACHE_TIMEOUT)
        return result
    
    def _find_shortest_path(self, start: Person, end: Person) -> Optional[List[Person]]:
        """
        Find the shortest path between two people using BFS.
        
        Returns:
            List of Person objects representing the path, or None if no path exists
        """
        if start == end:
            return [start]
        
        visited = set()
        queue = deque([(start, [start])])
        
        while queue:
            current_person, path = queue.popleft()
            
            if current_person in visited:
                continue
            visited.add(current_person)
            
            # Get all connected people (parents, children, spouses)
            connected_people = self._get_connected_people(current_person)
            
            for connected_person in connected_people:
                if connected_person == end:
                    return path + [connected_person]
                
                if connected_person not in visited:
                    queue.append((connected_person, path + [connected_person]))
        
        return None
    
    def _get_connected_people(self, person: Person) -> Set[Person]:
        """Get all people directly connected to a person."""
        connected = set()
        
        # Add parents
        if person.father:
            connected.add(person.father)
        if person.mother:
            connected.add(person.mother)
        
        # Add children
        children = Person.objects.filter(
            Q(father=person) | Q(mother=person),
            family_tree=self.family_tree
        )
        connected.update(children)
        
        # Add spouse
        if person.spouse:
            connected.add(person.spouse)
        
        # Add anyone who has this person as spouse
        spouses = Person.objects.filter(spouse=person, family_tree=self.family_tree)
        connected.update(spouses)
        
        return connected
    
    def _analyze_relationship_path(self, path: List[Person]) -> Dict[str, str]:
        """
        Analyze a path between two people to determine their relationship.
        
        Args:
            path: List of Person objects representing the connection path
            
        Returns:
            Dictionary with relationship details
        """
        if len(path) == 2:
            return self._analyze_direct_relationship(path[0], path[1])
        
        # Find common ancestor (lowest point in the path)
        common_ancestor_idx = self._find_common_ancestor_index(path)
        
        if common_ancestor_idx == -1:
            return {'relationship': 'unknown', 'degree': -1, 'generation_diff': 0}
        
        # Split path at common ancestor
        up_path = path[:common_ancestor_idx + 1]
        down_path = path[common_ancestor_idx:]
        
        # Calculate generations up and down
        generations_up = len(up_path) - 1
        generations_down = len(down_path) - 1
        
        # Determine relationship type
        return self._determine_relationship_type(
            generations_up, generations_down, path[common_ancestor_idx]
        )
    
    def _analyze_direct_relationship(self, person1: Person, person2: Person) -> Dict[str, str]:
        """Analyze direct relationships (parent-child, spouse)."""
        # Check if spouse relationship
        if person1.spouse == person2 or person2.spouse == person1:
            return {
                'relationship': 'spouse',
                'degree': 1,
                'generation_diff': 0,
                'common_ancestor': None,
                'path_description': f"{person1.first_name} is married to {person2.first_name}"
            }
        
        # Check parent-child relationships
        if person1.father == person2 or person1.mother == person2:
            return {
                'relationship': 'child',
                'degree': 1,
                'generation_diff': -1,
                'common_ancestor': person2,
                'path_description': f"{person1.first_name} is the child of {person2.first_name}"
            }
        
        if person2.father == person1 or person2.mother == person1:
            return {
                'relationship': 'parent',
                'degree': 1,
                'generation_diff': 1,
                'common_ancestor': person1,
                'path_description': f"{person1.first_name} is the parent of {person2.first_name}"
            }
        
        return {'relationship': 'unknown', 'degree': -1, 'generation_diff': 0}
    
    def _find_common_ancestor_index(self, path: List[Person]) -> int:
        """Find the index of the common ancestor in the path."""
        # For now, assume the middle person is the common ancestor
        # This is a simplified implementation - a more complex one would
        # analyze the actual family structure
        return len(path) // 2
    
    def _determine_relationship_type(
        self, generations_up: int, generations_down: int, common_ancestor: Person
    ) -> Dict[str, str]:
        """
        Determine the relationship type based on generational differences.
        
        Args:
            generations_up: Generations from first person to common ancestor
            generations_down: Generations from common ancestor to second person
            common_ancestor: The common ancestor person
        """
        generation_diff = generations_down - generations_up
        
        # Direct descendants/ancestors
        if generations_up == 1 and generations_down > 1:
            if generations_down == 2:
                relationship = 'grandchild'
            elif generations_down == 3:
                relationship = 'great grandchild'
            else:
                relationship = f"great{'×' + str(generations_down - 3) if generations_down > 3 else ''} grandchild"
        elif generations_down == 1 and generations_up > 1:
            if generations_up == 2:
                relationship = 'grandparent'
            elif generations_up == 3:
                relationship = 'great grandparent'
            else:
                relationship = f"great{'×' + str(generations_up - 3) if generations_up > 3 else ''} grandparent"
        
        # Siblings and cousins
        elif generations_up == 1 and generations_down == 1:
            relationship = 'sibling'
        elif generations_up == 2 and generations_down == 2:
            relationship = 'cousin'
        elif generations_up == 3 and generations_down == 3:
            relationship = 'second cousin'
        elif generations_up > 3 and generations_down > 3 and generations_up == generations_down:
            degree = generations_up - 2
            relationship = f"{self._ordinal(degree)} cousin"
        
        # Aunt/Uncle relationships
        elif generations_up == 2 and generations_down == 1:
            relationship = 'aunt/uncle'
        elif generations_up == 1 and generations_down == 2:
            relationship = 'niece/nephew'
        elif generations_up > 2 and generations_down == 1:
            relationship = f"grand aunt/uncle"
        elif generations_up == 1 and generations_down > 2:
            relationship = f"grand niece/nephew"
        
        # Cousin with removal
        elif abs(generation_diff) > 0:
            base_degree = min(generations_up, generations_down) - 1
            removal = abs(generation_diff)
            if base_degree == 1:
                relationship = f"cousin {removal} time{'s' if removal > 1 else ''} removed"
            else:
                relationship = f"{self._ordinal(base_degree - 1)} cousin {removal} time{'s' if removal > 1 else ''} removed"
        
        else:
            relationship = 'distant relative'
        
        return {
            'relationship': relationship,
            'degree': min(generations_up, generations_down),
            'generation_diff': generation_diff,
            'common_ancestor': common_ancestor,
            'path_description': self._create_path_description(
                generations_up, generations_down, relationship, common_ancestor
            )
        }
    
    def _ordinal(self, number: int) -> str:
        """Convert number to ordinal (1st, 2nd, 3rd, etc.)."""
        if 10 <= number % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
        return f"{number}{suffix}"
    
    def _create_path_description(
        self, generations_up: int, generations_down: int, 
        relationship: str, common_ancestor: Person
    ) -> str:
        """Create a human-readable description of the relationship path."""
        if common_ancestor:
            return (
                f"Related through {common_ancestor.first_name} {common_ancestor.last_name} "
                f"({generations_up} generations up, {generations_down} generations down)"
            )
        return f"Direct {relationship} relationship"


class FamilyTreeSearchService:
    """
    Service for searching and filtering family tree data.
    
    Provides advanced search capabilities including:
    - Name-based search with fuzzy matching
    - Date range filtering
    - Location-based search
    - Relationship-based discovery
    """
    
    def __init__(self, family_tree: FamilyTree):
        self.family_tree = family_tree
    
    def search_people(
        self, 
        query: str = "", 
        birth_year_range: Tuple[int, int] = None,
        location: str = "",
        relationship_to: Person = None,
        limit: int = 50
    ) -> List[Person]:
        """
        Search for people in the family tree based on various criteria.
        
        Args:
            query: Name search query
            birth_year_range: Tuple of (min_year, max_year)
            location: Location filter
            relationship_to: Find people related to this person
            limit: Maximum number of results
            
        Returns:
            List of Person objects matching the criteria
        """
        queryset = Person.objects.filter(family_tree=self.family_tree)
        
        # Text search on names
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(middle_name__icontains=query)
            )
        
        # Birth year range filter
        if birth_year_range:
            min_year, max_year = birth_year_range
            queryset = queryset.filter(
                birth_date__year__gte=min_year,
                birth_date__year__lte=max_year
            )
        
        # Location filter
        if location:
            queryset = queryset.filter(
                Q(birth_location__icontains=location) |
                Q(death_location__icontains=location)
            )
        
        # Relationship-based filtering
        if relationship_to:
            related_people = self._find_related_people(relationship_to)
            queryset = queryset.filter(id__in=[p.id for p in related_people])
        
        return queryset.distinct()[:limit]
    
    def _find_related_people(self, person: Person, max_degree: int = 3) -> List[Person]:
        """
        Find all people related to a given person within a certain degree.
        
        Args:
            person: The person to find relatives for
            max_degree: Maximum relationship degree to search
            
        Returns:
            List of related Person objects
        """
        calculator = RelationshipCalculator(self.family_tree)
        related_people = []
        all_people = Person.objects.filter(family_tree=self.family_tree).exclude(id=person.id)
        
        for other_person in all_people:
            relationship = calculator.calculate_relationship(person, other_person)
            if relationship['degree'] <= max_degree and relationship['degree'] > 0:
                related_people.append(other_person)
        
        return related_people
    
    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """
        Get search suggestions based on partial query.
        
        Args:
            query: Partial search query
            limit: Maximum number of suggestions
            
        Returns:
            List of suggested search terms
        """
        if len(query) < 2:
            return []
        
        # Get unique first and last names that start with the query
        first_names = Person.objects.filter(
            family_tree=self.family_tree,
            first_name__istartswith=query
        ).values_list('first_name', flat=True).distinct()
        
        last_names = Person.objects.filter(
            family_tree=self.family_tree,
            last_name__istartswith=query
        ).values_list('last_name', flat=True).distinct()
        
        suggestions = list(set(list(first_names) + list(last_names)))
        return sorted(suggestions)[:limit]


class FamilyTreeAnalytics:
    """
    Service for analyzing family tree data and generating insights.
    """
    
    def __init__(self, family_tree: FamilyTree):
        self.family_tree = family_tree
    
    def get_tree_statistics(self) -> Dict[str, int]:
        """Get basic statistics about the family tree."""
        people = Person.objects.filter(family_tree=self.family_tree)
        
        return {
            'total_people': people.count(),
            'living_people': people.filter(death_date__isnull=True).count(),
            'deceased_people': people.filter(death_date__isnull=False).count(),
            'generations': self._calculate_generations(),
            'families': self._count_family_units(),
            'oldest_person': self._get_oldest_person_age(),
            'most_recent_birth': self._get_most_recent_birth_year(),
            'oldest_birth': self._get_oldest_birth_year()
        }
    
    def _calculate_generations(self) -> int:
        """Calculate the number of generations in the tree."""
        # This is a simplified calculation - could be enhanced
        people = Person.objects.filter(family_tree=self.family_tree)
        if not people.exists():
            return 0
        
        # Find people with no parents (oldest generation)
        roots = people.filter(father__isnull=True, mother__isnull=True)
        if not roots.exists():
            return 1
        
        max_depth = 0
        for root in roots:
            depth = self._calculate_depth_from_person(root)
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _calculate_depth_from_person(self, person: Person, visited: Set[int] = None) -> int:
        """Calculate the maximum depth from a given person."""
        if visited is None:
            visited = set()
        
        if person.id in visited:
            return 0
        
        visited.add(person.id)
        
        # Find children
        children = Person.objects.filter(
            Q(father=person) | Q(mother=person),
            family_tree=self.family_tree
        )
        
        if not children.exists():
            return 1
        
        max_child_depth = 0
        for child in children:
            child_depth = self._calculate_depth_from_person(child, visited.copy())
            max_child_depth = max(max_child_depth, child_depth)
        
        return 1 + max_child_depth
    
    def _count_family_units(self) -> int:
        """Count the number of family units (couples with children)."""
        # This is a simplified calculation
        couples = Person.objects.filter(
            family_tree=self.family_tree,
            spouse__isnull=False
        ).count() // 2  # Divide by 2 since each couple is counted twice
        
        return couples
    
    def _get_oldest_person_age(self) -> Optional[int]:
        """Get the age of the oldest person in the tree."""
        from django.utils import timezone
        from datetime import date
        
        people = Person.objects.filter(
            family_tree=self.family_tree,
            birth_date__isnull=False
        ).order_by('birth_date')
        
        if not people.exists():
            return None
        
        oldest_person = people.first()
        if oldest_person.death_date:
            age = (oldest_person.death_date - oldest_person.birth_date).days // 365
        else:
            age = (date.today() - oldest_person.birth_date).days // 365
        
        return age
    
    def _get_most_recent_birth_year(self) -> Optional[int]:
        """Get the year of the most recent birth."""
        people = Person.objects.filter(
            family_tree=self.family_tree,
            birth_date__isnull=False
        ).order_by('-birth_date')
        
        if people.exists():
            return people.first().birth_date.year
        return None
    
    def _get_oldest_birth_year(self) -> Optional[int]:
        """Get the year of the oldest birth."""
        people = Person.objects.filter(
            family_tree=self.family_tree,
            birth_date__isnull=False
        ).order_by('birth_date')
        
        if people.exists():
            return people.first().birth_date.year
        return None