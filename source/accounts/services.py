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
            return {
                'relationship': 'self',
                'degree': 0,
                'generation_diff': 0,
                'common_ancestor': None,
                'path_description': 'Same person'
            }
        
        # Check cache first
        cache_key = f"{self.cache_prefix}_{min(person1.id, person2.id)}_{max(person1.id, person2.id)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Find common ancestors and calculate relationship
        result = self._calculate_relationship_path(person1, person2)
        
        # Cache the result
        cache.set(cache_key, result, self.RELATIONSHIP_CACHE_TIMEOUT)
        return result
    
    def _calculate_relationship_path(self, person1: Person, person2: Person) -> Dict[str, str]:
        """Internal method to calculate relationship path between two people."""
        # Find all ancestors for both people
        ancestors1 = self._get_ancestors_with_path(person1)
        ancestors2 = self._get_ancestors_with_path(person2)
        
        # Find common ancestors
        common_ancestors = set(ancestors1.keys()) & set(ancestors2.keys())
        
        if not common_ancestors:
            return {
                'relationship': 'unrelated',
                'degree': -1,
                'generation_diff': 0,
                'common_ancestor': None,
                'path_description': 'No known relationship'
            }
        
        # Find the closest common ancestor (minimum total distance)
        closest_ancestor = min(
            common_ancestors,
            key=lambda a: ancestors1[a]['distance'] + ancestors2[a]['distance']
        )
        
        dist1 = ancestors1[closest_ancestor]['distance']
        dist2 = ancestors2[closest_ancestor]['distance']
        
        return self._determine_relationship_type(
            person1, person2, closest_ancestor, dist1, dist2
        )
    
    def _get_ancestors_with_path(self, person: Person) -> Dict[Person, Dict]:
        """Get all ancestors with their distance and path from the person."""
        ancestors = {}
        queue = deque([(person, 0, [person])])
        visited = set()
        
        while queue:
            current_person, distance, path = queue.popleft()
            
            if current_person.id in visited:
                continue
            visited.add(current_person.id)
            
            if distance > 0:  # Don't include self as ancestor
                ancestors[current_person] = {
                    'distance': distance,
                    'path': path.copy()
                }
            
            # Add parents to queue
            if current_person.father:
                queue.append((current_person.father, distance + 1, path + [current_person.father]))
            if current_person.mother:
                queue.append((current_person.mother, distance + 1, path + [current_person.mother]))
        
        return ancestors
    
    def _determine_relationship_type(self, person1: Person, person2: Person, 
                                   common_ancestor: Person, dist1: int, dist2: int) -> Dict:
        """Determine the specific relationship type based on distances to common ancestor."""
        generation_diff = abs(dist1 - dist2)
        
        # Direct relationships
        if dist1 == 1 and dist2 == 1:
            return self._sibling_relationship(person1, person2, common_ancestor)
        
        # Parent-child relationships
        if (dist1 == 0 and dist2 == 1) or (dist1 == 1 and dist2 == 0):
            return self._parent_child_relationship(person1, person2, dist1, dist2)
        
        # Grandparent-grandchild relationships
        if generation_diff > 1:
            return self._linear_relationship(person1, person2, dist1, dist2, common_ancestor)
        
        # Cousin relationships
        return self._cousin_relationship(person1, person2, dist1, dist2, common_ancestor)
    
    def _sibling_relationship(self, person1: Person, person2: Person, common_ancestor: Person) -> Dict:
        """Determine sibling relationship type."""
        # Check if they share both parents
        shared_parents = 0
        if person1.father and person1.father == person2.father:
            shared_parents += 1
        if person1.mother and person1.mother == person2.mother:
            shared_parents += 1
        
        if shared_parents == 2:
            relationship = 'sibling'
        elif shared_parents == 1:
            relationship = 'half-sibling'
        else:
            relationship = 'step-sibling'
        
        return {
            'relationship': relationship,
            'degree': 1,
            'generation_diff': 0,
            'common_ancestor': common_ancestor,
            'path_description': f'{relationship.title()} relationship'
        }
    
    def _parent_child_relationship(self, person1: Person, person2: Person, 
                                 dist1: int, dist2: int) -> Dict:
        """Determine parent-child relationship."""
        if dist1 == 0:  # person1 is the ancestor
            relationship = 'child'
            path_desc = f'{person2.get_full_name()} is the child of {person1.get_full_name()}'
        else:  # person2 is the ancestor
            relationship = 'parent'
            path_desc = f'{person2.get_full_name()} is the parent of {person1.get_full_name()}'
        
        return {
            'relationship': relationship,
            'degree': 1,
            'generation_diff': 1,
            'common_ancestor': person1 if dist1 == 0 else person2,
            'path_description': path_desc
        }
    
    def _linear_relationship(self, person1: Person, person2: Person, 
                           dist1: int, dist2: int, common_ancestor: Person) -> Dict:
        """Determine linear ancestor-descendant relationships."""
        if dist1 < dist2:
            generations = dist2 - dist1
            if generations == 2:
                relationship = 'grandparent'
            elif generations == 3:
                relationship = 'great-grandparent'
            else:
                relationship = f'{"great-" * (generations - 2)}grandparent'
        else:
            generations = dist1 - dist2
            if generations == 2:
                relationship = 'grandchild'
            elif generations == 3:
                relationship = 'great-grandchild'
            else:
                relationship = f'{"great-" * (generations - 2)}grandchild'
        
        return {
            'relationship': relationship,
            'degree': max(dist1, dist2),
            'generation_diff': abs(dist1 - dist2),
            'common_ancestor': common_ancestor,
            'path_description': f'{relationship.title()} relationship'
        }
    
    def _cousin_relationship(self, person1: Person, person2: Person, 
                           dist1: int, dist2: int, common_ancestor: Person) -> Dict:
        """Determine cousin relationship type."""
        cousin_degree = min(dist1, dist2) - 1
        removed = abs(dist1 - dist2)
        
        if cousin_degree == 1:
            if removed == 0:
                relationship = 'first cousin'
            else:
                relationship = f'first cousin {removed} times removed'
        elif cousin_degree == 2:
            if removed == 0:
                relationship = 'second cousin'
            else:
                relationship = f'second cousin {removed} times removed'
        else:
            if removed == 0:
                relationship = f'{self._ordinal(cousin_degree)} cousin'
            else:
                relationship = f'{self._ordinal(cousin_degree)} cousin {removed} times removed'
        
        return {
            'relationship': relationship,
            'degree': cousin_degree,
            'generation_diff': removed,
            'common_ancestor': common_ancestor,
            'path_description': f'{relationship.title()} relationship through {common_ancestor.get_full_name()}'
        }
    
    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal string (1st, 2nd, 3rd, etc.)."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f'{n}{suffix}'


class FamilyTreeSearchService:
    """
    Service for searching and discovering family tree information.
    
    Provides advanced search capabilities including:
    - Multi-criteria person search
    - Relationship-based queries
    - Timeline and event searches
    - Media and document searches
    """
    
    def __init__(self, family_tree: FamilyTree):
        self.family_tree = family_tree
        self.relationship_calc = RelationshipCalculator(family_tree)
    
    def search_people(self, query: str, filters: Optional[Dict] = None) -> List[Person]:
        """
        Search for people in the family tree.
        
        Args:
            query: Search query string
            filters: Optional filters (birth_year_range, location, etc.)
            
        Returns:
            List of matching Person objects
        """
        filters = filters or {}
        
        # Base queryset
        queryset = Person.objects.filter(family_tree=self.family_tree)
        
        # Text search across multiple fields
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(middle_name__icontains=query) |
                Q(maiden_name__icontains=query) |
                Q(nickname__icontains=query) |
                Q(biography__icontains=query)
            )
        
        # Apply filters
        if 'birth_year_range' in filters:
            start_year, end_year = filters['birth_year_range']
            queryset = queryset.filter(
                birth_date__year__range=(start_year, end_year)
            )
        
        if 'location' in filters:
            queryset = queryset.filter(
                Q(birth_location__name__icontains=filters['location']) |
                Q(death_location__name__icontains=filters['location'])
            )
        
        if 'gender' in filters:
            queryset = queryset.filter(gender=filters['gender'])
        
        return list(queryset.distinct())
    
    def find_relatives(self, person: Person, relationship_type: str, 
                      max_degree: int = 3) -> List[Tuple[Person, Dict]]:
        """
        Find all relatives of a specific type for a person.
        
        Args:
            person: The person to find relatives for
            relationship_type: Type of relationship to find
            max_degree: Maximum relationship degree to search
            
        Returns:
            List of tuples (Person, relationship_info)
        """
        relatives = []
        all_people = Person.objects.filter(family_tree=self.family_tree).exclude(id=person.id)
        
        for other_person in all_people:
            relationship = self.relationship_calc.calculate_relationship(person, other_person)
            
            if (relationship['relationship'] == relationship_type and 
                relationship['degree'] <= max_degree):
                relatives.append((other_person, relationship))
        
        return relatives
    
    def get_generation(self, person: Person, generation_offset: int = 0) -> List[Person]:
        """
        Get all people in the same generation as the person (or offset generation).
        
        Args:
            person: Reference person
            generation_offset: Offset from person's generation (0=same, 1=children, -1=parents)
            
        Returns:
            List of people in the target generation
        """
        generation_members = []
        all_people = Person.objects.filter(family_tree=self.family_tree)
        
        for other_person in all_people:
            relationship = self.relationship_calc.calculate_relationship(person, other_person)
            
            # Calculate generation difference
            if relationship['generation_diff'] == abs(generation_offset):
                if generation_offset == 0:  # Same generation
                    if relationship['relationship'] in ['sibling', 'half-sibling', 'cousin', 'self']:
                        generation_members.append(other_person)
                elif generation_offset > 0:  # Younger generation
                    if relationship['generation_diff'] == generation_offset:
                        generation_members.append(other_person)
                else:  # Older generation
                    if relationship['generation_diff'] == abs(generation_offset):
                        generation_members.append(other_person)
        
        return generation_members


class FamilyTreeVisualizationService:
    """
    Service for generating family tree visualization data.
    
    Provides data structures optimized for different visualization layouts:
    - Hierarchical tree layouts
    - Circular/radial layouts
    - Network graph layouts
    - Timeline visualizations
    """
    
    def __init__(self, family_tree: FamilyTree):
        self.family_tree = family_tree
    
    def generate_tree_data(self, root_person: Person, layout: str = 'hierarchical') -> Dict:
        """
        Generate tree visualization data for a specific layout.
        
        Args:
            root_person: Person to use as tree root
            layout: Layout type ('hierarchical', 'circular', 'network')
            
        Returns:
            Dictionary with nodes, edges, and layout data
        """
        if layout == 'hierarchical':
            return self._generate_hierarchical_data(root_person)
        elif layout == 'circular':
            return self._generate_circular_data(root_person)
        elif layout == 'network':
            return self._generate_network_data(root_person)
        else:
            raise ValueError(f"Unsupported layout type: {layout}")
    
    def _generate_hierarchical_data(self, root_person: Person) -> Dict:
        """Generate data for hierarchical tree layout."""
        nodes = []
        edges = []
        visited = set()
        
        def add_person_and_descendants(person, generation=0, x_offset=0):
            if person.id in visited:
                return x_offset
            
            visited.add(person.id)
            
            # Add person node
            node = {
                'id': person.id,
                'name': person.get_full_name(),
                'x': x_offset,
                'y': -generation * 100,  # Negative for downward tree
                'generation': generation,
                'data': {
                    'birth_date': person.birth_date.isoformat() if person.birth_date else None,
                    'death_date': person.death_date.isoformat() if person.death_date else None,
                    'photo_url': person.photo.url if person.photo else None,
                    'gender': person.gender
                }
            }
            nodes.append(node)
            
            # Add children
            children = person.children.all()
            child_x_start = x_offset - (len(children) - 1) * 50
            
            for i, child in enumerate(children):
                child_x = child_x_start + i * 100
                add_person_and_descendants(child, generation + 1, child_x)
                
                # Add edge from parent to child
                edges.append({
                    'source': person.id,
                    'target': child.id,
                    'type': 'parent-child'
                })
            
            return x_offset + len(children) * 100
        
        add_person_and_descendants(root_person)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'layout': 'hierarchical',
            'root_id': root_person.id
        }
    
    def _generate_circular_data(self, root_person: Person) -> Dict:
        """Generate data for circular/radial tree layout."""
        import math
        
        nodes = []
        edges = []
        visited = set()
        
        def add_person_circular(person, radius=0, angle=0, angle_span=2*math.pi):
            if person.id in visited:
                return
            
            visited.add(person.id)
            
            # Calculate position
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            node = {
                'id': person.id,
                'name': person.get_full_name(),
                'x': x,
                'y': y,
                'radius': radius,
                'angle': angle,
                'data': {
                    'birth_date': person.birth_date.isoformat() if person.birth_date else None,
                    'death_date': person.death_date.isoformat() if person.death_date else None,
                    'photo_url': person.photo.url if person.photo else None,
                    'gender': person.gender
                }
            }
            nodes.append(node)
            
            # Add children in next ring
            children = person.children.all()
            if children:
                child_angle_span = angle_span / len(children)
                start_angle = angle - angle_span / 2
                
                for i, child in enumerate(children):
                    child_angle = start_angle + i * child_angle_span + child_angle_span / 2
                    add_person_circular(child, radius + 150, child_angle, child_angle_span)
                    
                    edges.append({
                        'source': person.id,
                        'target': child.id,
                        'type': 'parent-child'
                    })
        
        add_person_circular(root_person)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'layout': 'circular',
            'root_id': root_person.id
        }
    
    def _generate_network_data(self, root_person: Person) -> Dict:
        """Generate data for network graph layout."""
        all_people = Person.objects.filter(family_tree=self.family_tree)
        
        nodes = []
        edges = []
        
        for person in all_people:
            node = {
                'id': person.id,
                'name': person.get_full_name(),
                'data': {
                    'birth_date': person.birth_date.isoformat() if person.birth_date else None,
                    'death_date': person.death_date.isoformat() if person.death_date else None,
                    'photo_url': person.photo.url if person.photo else None,
                    'gender': person.gender
                }
            }
            nodes.append(node)
            
            # Add parent-child edges
            for child in person.children.all():
                edges.append({
                    'source': person.id,
                    'target': child.id,
                    'type': 'parent-child'
                })
            
            # Add spouse edges
            if person.spouse:
                edges.append({
                    'source': person.id,
                    'target': person.spouse.id,
                    'type': 'spouse'
                })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'layout': 'network',
            'root_id': root_person.id
        }


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