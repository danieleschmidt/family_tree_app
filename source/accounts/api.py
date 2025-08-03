"""
Family Tree Application REST API

This module provides REST API endpoints for family tree operations,
enabling frontend-backend communication and external integrations.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.serializers import serialize
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.views.generic import View
from django.utils.decorators import method_decorator
import json
from typing import Dict, List, Any

from .models import FamilyTree, Person, User
from .services import RelationshipCalculator, FamilyTreeSearchService, FamilyTreeAnalytics


class APIResponseMixin:
    """Mixin for standardized API responses."""
    
    def success_response(self, data: Any = None, message: str = "Success") -> JsonResponse:
        """Return a standardized success response."""
        response_data = {
            'status': 'success',
            'message': message
        }
        if data is not None:
            response_data['data'] = data
        return JsonResponse(response_data)
    
    def error_response(self, message: str, status: int = 400, 
                      errors: Dict = None) -> JsonResponse:
        """Return a standardized error response."""
        response_data = {
            'status': 'error',
            'message': message
        }
        if errors:
            response_data['errors'] = errors
        return JsonResponse(response_data, status=status)
    
    def validate_json_request(self, request) -> Dict:
        """Validate and parse JSON request body."""
        try:
            return json.loads(request.body)
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON in request body")


@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class FamilyTreeAPIView(View, APIResponseMixin):
    """API view for family tree operations."""
    
    def get(self, request, tree_id=None):
        """
        GET /api/family-trees/ - List user's family trees
        GET /api/family-trees/{id}/ - Get specific family tree details
        """
        try:
            if tree_id:
                return self._get_family_tree_details(request, tree_id)
            else:
                return self._list_family_trees(request)
        except Exception as e:
            return self.error_response(f"Error retrieving family trees: {str(e)}", 500)
    
    def post(self, request):
        """
        POST /api/family-trees/ - Create new family tree
        """
        try:
            data = self.validate_json_request(request)
            
            # Validate required fields
            required_fields = ['name']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return self.error_response(
                    "Missing required fields",
                    errors={'missing_fields': missing_fields}
                )
            
            # Create family tree
            family_tree = FamilyTree.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                super_admin=request.user
            )
            
            return self.success_response(
                data=self._serialize_family_tree(family_tree),
                message="Family tree created successfully"
            )
            
        except ValidationError as e:
            return self.error_response(str(e))
        except Exception as e:
            return self.error_response(f"Error creating family tree: {str(e)}", 500)
    
    def put(self, request, tree_id):
        """
        PUT /api/family-trees/{id}/ - Update family tree
        """
        try:
            data = self.validate_json_request(request)
            family_tree = self._get_user_family_tree(request.user, tree_id)
            
            # Update allowed fields
            updatable_fields = ['name', 'description']
            for field in updatable_fields:
                if field in data:
                    setattr(family_tree, field, data[field])
            
            family_tree.save()
            
            return self.success_response(
                data=self._serialize_family_tree(family_tree),
                message="Family tree updated successfully"
            )
            
        except ObjectDoesNotExist:
            return self.error_response("Family tree not found", 404)
        except Exception as e:
            return self.error_response(f"Error updating family tree: {str(e)}", 500)
    
    def delete(self, request, tree_id):
        """
        DELETE /api/family-trees/{id}/ - Delete family tree
        """
        try:
            family_tree = self._get_user_family_tree(request.user, tree_id)
            
            # Only super admin can delete
            if family_tree.super_admin != request.user:
                return self.error_response("Insufficient permissions", 403)
            
            family_tree.delete()
            
            return self.success_response(message="Family tree deleted successfully")
            
        except ObjectDoesNotExist:
            return self.error_response("Family tree not found", 404)
        except Exception as e:
            return self.error_response(f"Error deleting family tree: {str(e)}", 500)
    
    def _list_family_trees(self, request):
        """List all family trees accessible to the user."""
        trees = FamilyTree.objects.filter(super_admin=request.user)
        
        trees_data = [self._serialize_family_tree(tree) for tree in trees]
        
        return self.success_response(data=trees_data)
    
    def _get_family_tree_details(self, request, tree_id):
        """Get detailed information about a specific family tree."""
        family_tree = self._get_user_family_tree(request.user, tree_id)
        
        # Get analytics
        analytics = FamilyTreeAnalytics(family_tree)
        stats = analytics.get_tree_statistics()
        
        tree_data = self._serialize_family_tree(family_tree)
        tree_data['statistics'] = stats
        
        return self.success_response(data=tree_data)
    
    def _get_user_family_tree(self, user: User, tree_id: int) -> FamilyTree:
        """Get family tree that user has access to."""
        return FamilyTree.objects.get(
            id=tree_id,
            super_admin=user  # For now, only super admin has access
        )
    
    def _serialize_family_tree(self, tree: FamilyTree) -> Dict:
        """Serialize family tree object to dictionary."""
        return {
            'id': tree.id,
            'name': tree.name,
            'description': tree.description,
            'super_admin': tree.super_admin.username,
            'created_at': tree.id,  # Assuming created_at field exists
            'member_count': Person.objects.filter(family_tree=tree).count()
        }


@method_decorator(login_required, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class PersonAPIView(View, APIResponseMixin):
    """API view for person/family member operations."""
    
    def get(self, request, tree_id, person_id=None):
        """
        GET /api/family-trees/{tree_id}/members/ - List all members
        GET /api/family-trees/{tree_id}/members/{person_id}/ - Get specific person
        """
        try:
            family_tree = FamilyTree.objects.get(id=tree_id, super_admin=request.user)
            
            if person_id:
                return self._get_person_details(family_tree, person_id)
            else:
                return self._list_people(request, family_tree)
                
        except ObjectDoesNotExist:
            return self.error_response("Family tree not found", 404)
        except Exception as e:
            return self.error_response(f"Error retrieving people: {str(e)}", 500)
    
    def post(self, request, tree_id):
        """
        POST /api/family-trees/{tree_id}/members/ - Add new person
        """
        try:
            family_tree = FamilyTree.objects.get(id=tree_id, super_admin=request.user)
            data = self.validate_json_request(request)
            
            # Validate required fields
            required_fields = ['first_name', 'last_name']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return self.error_response(
                    "Missing required fields",
                    errors={'missing_fields': missing_fields}
                )
            
            # Create person
            with transaction.atomic():
                person = Person.objects.create(
                    family_tree=family_tree,
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    middle_name=data.get('middle_name', ''),
                    birth_date=data.get('birth_date'),
                    death_date=data.get('death_date'),
                    birth_location=data.get('birth_location', ''),
                    death_location=data.get('death_location', ''),
                    biography=data.get('biography', '')
                )
                
                # Set relationships if provided
                if data.get('father_id'):
                    person.father_id = data['father_id']
                if data.get('mother_id'):
                    person.mother_id = data['mother_id']
                if data.get('spouse_id'):
                    person.spouse_id = data['spouse_id']
                
                person.save()
            
            return self.success_response(
                data=self._serialize_person(person),
                message="Person added successfully"
            )
            
        except ObjectDoesNotExist:
            return self.error_response("Family tree not found", 404)
        except Exception as e:
            return self.error_response(f"Error adding person: {str(e)}", 500)
    
    def put(self, request, tree_id, person_id):
        """
        PUT /api/family-trees/{tree_id}/members/{person_id}/ - Update person
        """
        try:
            family_tree = FamilyTree.objects.get(id=tree_id, super_admin=request.user)
            person = Person.objects.get(id=person_id, family_tree=family_tree)
            data = self.validate_json_request(request)
            
            # Update allowed fields
            updatable_fields = [
                'first_name', 'last_name', 'middle_name', 'birth_date', 
                'death_date', 'birth_location', 'death_location', 'biography',
                'father_id', 'mother_id', 'spouse_id'
            ]
            
            with transaction.atomic():
                for field in updatable_fields:
                    if field in data:
                        setattr(person, field, data[field])
                
                person.save()
            
            return self.success_response(
                data=self._serialize_person(person),
                message="Person updated successfully"
            )
            
        except ObjectDoesNotExist:
            return self.error_response("Person or family tree not found", 404)
        except Exception as e:
            return self.error_response(f"Error updating person: {str(e)}", 500)
    
    def delete(self, request, tree_id, person_id):
        """
        DELETE /api/family-trees/{tree_id}/members/{person_id}/ - Delete person
        """
        try:
            family_tree = FamilyTree.objects.get(id=tree_id, super_admin=request.user)
            person = Person.objects.get(id=person_id, family_tree=family_tree)
            
            person.delete()
            
            return self.success_response(message="Person deleted successfully")
            
        except ObjectDoesNotExist:
            return self.error_response("Person or family tree not found", 404)
        except Exception as e:
            return self.error_response(f"Error deleting person: {str(e)}", 500)
    
    def _list_people(self, request, family_tree: FamilyTree):
        """List all people in a family tree with optional filtering."""
        # Get query parameters for filtering
        search_query = request.GET.get('search', '')
        birth_year = request.GET.get('birth_year')
        
        people = Person.objects.filter(family_tree=family_tree)
        
        # Apply filters
        if search_query:
            search_service = FamilyTreeSearchService(family_tree)
            people = search_service.search_people(query=search_query)
        
        if birth_year:
            try:
                year = int(birth_year)
                people = people.filter(birth_date__year=year)
            except ValueError:
                pass
        
        # Serialize and return
        people_data = [self._serialize_person(person) for person in people]
        
        return self.success_response(data=people_data)
    
    def _get_person_details(self, family_tree: FamilyTree, person_id: int):
        """Get detailed information about a specific person."""
        person = Person.objects.get(id=person_id, family_tree=family_tree)
        
        person_data = self._serialize_person(person, include_relationships=True)
        
        return self.success_response(data=person_data)
    
    def _serialize_person(self, person: Person, include_relationships: bool = False) -> Dict:
        """Serialize person object to dictionary."""
        data = {
            'id': person.id,
            'first_name': person.first_name,
            'last_name': person.last_name,
            'middle_name': person.middle_name,
            'birth_date': person.birth_date.isoformat() if person.birth_date else None,
            'death_date': person.death_date.isoformat() if person.death_date else None,
            'birth_location': person.birth_location,
            'death_location': person.death_location,
            'biography': person.biography,
            'father_id': person.father_id,
            'mother_id': person.mother_id,
            'spouse_id': person.spouse_id
        }
        
        if include_relationships:
            # Add relationship information
            data['father'] = self._serialize_person_basic(person.father) if person.father else None
            data['mother'] = self._serialize_person_basic(person.mother) if person.mother else None
            data['spouse'] = self._serialize_person_basic(person.spouse) if person.spouse else None
            
            # Add children
            children = Person.objects.filter(
                family_tree=person.family_tree
            ).filter(
                models.Q(father=person) | models.Q(mother=person)
            )
            data['children'] = [self._serialize_person_basic(child) for child in children]
        
        return data
    
    def _serialize_person_basic(self, person: Person) -> Dict:
        """Serialize person with basic information only."""
        if not person:
            return None
        
        return {
            'id': person.id,
            'first_name': person.first_name,
            'last_name': person.last_name,
            'birth_date': person.birth_date.isoformat() if person.birth_date else None,
            'death_date': person.death_date.isoformat() if person.death_date else None
        }


@login_required
@require_http_methods(["GET"])
def search_people_api(request, tree_id):
    """
    GET /api/family-trees/{tree_id}/search/?q=query&birth_year_min=1900&birth_year_max=2000
    Advanced search for people in a family tree.
    """
    try:
        family_tree = FamilyTree.objects.get(id=tree_id, super_admin=request.user)
        search_service = FamilyTreeSearchService(family_tree)
        
        # Get search parameters
        query = request.GET.get('q', '')
        birth_year_min = request.GET.get('birth_year_min')
        birth_year_max = request.GET.get('birth_year_max')
        location = request.GET.get('location', '')
        relationship_to_id = request.GET.get('relationship_to')
        
        # Parse birth year range
        birth_year_range = None
        if birth_year_min and birth_year_max:
            try:
                birth_year_range = (int(birth_year_min), int(birth_year_max))
            except ValueError:
                pass
        
        # Get relationship_to person
        relationship_to = None
        if relationship_to_id:
            try:
                relationship_to = Person.objects.get(
                    id=relationship_to_id, 
                    family_tree=family_tree
                )
            except Person.DoesNotExist:
                pass
        
        # Perform search
        results = search_service.search_people(
            query=query,
            birth_year_range=birth_year_range,
            location=location,
            relationship_to=relationship_to
        )
        
        # Serialize results
        api_view = PersonAPIView()
        results_data = [api_view._serialize_person(person) for person in results]
        
        return JsonResponse({
            'status': 'success',
            'data': results_data,
            'count': len(results_data)
        })
        
    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Family tree not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Search error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def relationship_api(request, tree_id, person1_id, person2_id):
    """
    GET /api/family-trees/{tree_id}/relationships/{person1_id}/{person2_id}/
    Calculate relationship between two people.
    """
    try:
        family_tree = FamilyTree.objects.get(id=tree_id, super_admin=request.user)
        person1 = Person.objects.get(id=person1_id, family_tree=family_tree)
        person2 = Person.objects.get(id=person2_id, family_tree=family_tree)
        
        calculator = RelationshipCalculator(family_tree)
        relationship = calculator.calculate_relationship(person1, person2)
        
        # Add person information to response
        relationship['person1'] = {
            'id': person1.id,
            'name': f"{person1.first_name} {person1.last_name}"
        }
        relationship['person2'] = {
            'id': person2.id,
            'name': f"{person2.first_name} {person2.last_name}"
        }
        
        return JsonResponse({
            'status': 'success',
            'data': relationship
        })
        
    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Family tree or person not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Relationship calculation error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def family_tree_analytics_api(request, tree_id):
    """
    GET /api/family-trees/{tree_id}/analytics/
    Get analytics and statistics for a family tree.
    """
    try:
        family_tree = FamilyTree.objects.get(id=tree_id, super_admin=request.user)
        analytics = FamilyTreeAnalytics(family_tree)
        
        stats = analytics.get_tree_statistics()
        
        return JsonResponse({
            'status': 'success',
            'data': stats
        })
        
    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Family tree not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Analytics error: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def search_suggestions_api(request, tree_id):
    """
    GET /api/family-trees/{tree_id}/suggestions/?q=partial_query
    Get search suggestions for autocomplete.
    """
    try:
        family_tree = FamilyTree.objects.get(id=tree_id, super_admin=request.user)
        search_service = FamilyTreeSearchService(family_tree)
        
        query = request.GET.get('q', '')
        suggestions = search_service.get_suggestions(query)
        
        return JsonResponse({
            'status': 'success',
            'data': suggestions
        })
        
    except ObjectDoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Family tree not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Suggestions error: {str(e)}'
        }, status=500)