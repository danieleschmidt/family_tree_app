"""
Pytest configuration and fixtures for the Family Tree application tests.

This module provides common test fixtures, database setup, and configuration
for all test modules in the application.
"""

import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from datetime import date, datetime

from accounts.models import FamilyTree, Person
from accounts.cache import cache_manager

User = get_user_model()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Setup test database with initial data.
    """
    with django_db_blocker.unblock():
        # Run migrations
        call_command('migrate', '--run-syncdb')


@pytest.fixture
def client():
    """Django test client fixture."""
    return Client()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def superuser():
    """Create a test superuser."""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def authenticated_client(client, user):
    """Client with authenticated user."""
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(client, superuser):
    """Client with authenticated superuser."""
    client.force_login(superuser)
    return client


@pytest.fixture
def family_tree(user):
    """Create a test family tree."""
    return FamilyTree.objects.create(
        name='Test Family Tree',
        description='A family tree for testing purposes',
        super_admin=user
    )


@pytest.fixture
def sample_person(family_tree):
    """Create a sample person for testing."""
    return Person.objects.create(
        family_tree=family_tree,
        first_name='John',
        last_name='Doe',
        middle_name='Michael',
        birth_date=date(1980, 5, 15),
        birth_location='New York, NY',
        biography='A test person for unit testing'
    )


@pytest.fixture
def sample_family(family_tree):
    """
    Create a sample family structure for testing.
    
    Creates:
    - Grandparents: William & Mary Doe
    - Parents: John & Jane Doe  
    - Children: Bobby & Sally Doe
    """
    # Grandparents
    grandfather = Person.objects.create(
        family_tree=family_tree,
        first_name='William',
        last_name='Doe',
        birth_date=date(1920, 3, 10),
        death_date=date(2000, 8, 22),
        birth_location='Boston, MA'
    )
    
    grandmother = Person.objects.create(
        family_tree=family_tree,
        first_name='Mary',
        last_name='Smith',
        birth_date=date(1925, 7, 18),
        death_date=date(2005, 12, 5),
        birth_location='Boston, MA'
    )
    
    # Set spouse relationship
    grandfather.spouse = grandmother
    grandfather.save()
    grandmother.spouse = grandfather
    grandmother.save()
    
    # Father
    father = Person.objects.create(
        family_tree=family_tree,
        first_name='John',
        last_name='Doe',
        birth_date=date(1950, 6, 12),
        birth_location='Boston, MA',
        father=grandfather,
        mother=grandmother
    )
    
    # Mother
    mother = Person.objects.create(
        family_tree=family_tree,
        first_name='Jane',
        last_name='Johnson',
        birth_date=date(1952, 9, 8),
        birth_location='New York, NY'
    )
    
    # Set spouse relationship
    father.spouse = mother
    father.save()
    mother.spouse = father
    mother.save()
    
    # Children
    son = Person.objects.create(
        family_tree=family_tree,
        first_name='Bobby',
        last_name='Doe',
        birth_date=date(1975, 2, 20),
        birth_location='Boston, MA',
        father=father,
        mother=mother
    )
    
    daughter = Person.objects.create(
        family_tree=family_tree,
        first_name='Sally',
        last_name='Doe',
        birth_date=date(1978, 11, 3),
        birth_location='Boston, MA',
        father=father,
        mother=mother
    )
    
    return {
        'grandfather': grandfather,
        'grandmother': grandmother,
        'father': father,
        'mother': mother,
        'son': son,
        'daughter': daughter
    }


@pytest.fixture
def large_family_tree(family_tree):
    """
    Create a larger family tree for performance testing.
    
    Creates multiple generations with various relationships.
    """
    people = []
    
    # Generation 1 (oldest)
    for i in range(4):
        person = Person.objects.create(
            family_tree=family_tree,
            first_name=f'Ancestor{i+1}',
            last_name='Smith',
            birth_date=date(1900 + i, 1, 1),
            death_date=date(1980 + i, 1, 1) if i < 2 else None
        )
        people.append(person)
    
    # Generation 2 (parents)
    for i in range(8):
        person = Person.objects.create(
            family_tree=family_tree,
            first_name=f'Parent{i+1}',
            last_name='Johnson' if i % 2 else 'Smith',
            birth_date=date(1925 + i, 1, 1),
            death_date=date(2000 + i, 1, 1) if i < 3 else None,
            father=people[i // 2] if i % 2 == 0 else None,
            mother=people[i // 2] if i % 2 == 1 else None
        )
        people.append(person)
    
    # Generation 3 (current)
    for i in range(15):
        person = Person.objects.create(
            family_tree=family_tree,
            first_name=f'Person{i+1}',
            last_name='Brown' if i % 3 == 0 else ('Davis' if i % 3 == 1 else 'Wilson'),
            birth_date=date(1950 + i, 1, 1),
            father=people[4 + (i // 2)] if i < 14 else None,
            mother=people[5 + (i // 2)] if i < 14 else None
        )
        people.append(person)
    
    return people


@pytest.fixture
def api_headers():
    """Standard headers for API requests."""
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


@pytest.fixture
def mock_cache():
    """Mock cache for testing cache functionality."""
    # Clear cache before each test
    cache_manager.cache.clear()
    return cache_manager


@pytest.fixture(autouse=True)
def clear_cache():
    """Automatically clear cache after each test."""
    yield
    try:
        cache_manager.cache.clear()
    except:
        pass


@pytest.fixture
def sample_gedcom_data():
    """Sample GEDCOM data for import testing."""
    return """
0 HEAD
1 SOUR Family Tree App Test
1 GEDC
2 VERS 5.5.1
2 FORM LINEAGE-LINKED
1 CHAR UTF-8
0 @I1@ INDI
1 NAME John /Doe/
2 GIVN John
2 SURN Doe
1 SEX M
1 BIRT
2 DATE 15 MAY 1980
2 PLAC New York, NY
1 FAMS @F1@
0 @I2@ INDI
1 NAME Jane /Smith/
2 GIVN Jane
2 SURN Smith
1 SEX F
1 BIRT
2 DATE 8 SEP 1982
2 PLAC Boston, MA
1 FAMS @F1@
0 @I3@ INDI
1 NAME Bobby /Doe/
2 GIVN Bobby
2 SURN Doe
1 SEX M
1 BIRT
2 DATE 20 FEB 2005
2 PLAC Boston, MA
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 MARR
2 DATE 12 JUN 2004
2 PLAC Boston, MA
0 TRLR
    """.strip()


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for import testing."""
    return """first_name,last_name,birth_date,birth_location,father_name,mother_name
John,Doe,1980-05-15,New York NY,William Doe,Mary Smith
Jane,Smith,1982-09-08,Boston MA,,
Bobby,Doe,2005-02-20,Boston MA,John Doe,Jane Smith
Sally,Doe,2007-11-03,Boston MA,John Doe,Jane Smith"""


# Performance testing fixtures
@pytest.fixture
def benchmark_setup():
    """Setup for performance benchmarking tests."""
    def _create_benchmark_data(num_people=100):
        """Create benchmark data with specified number of people."""
        user = User.objects.create_user(
            username=f'benchmark_user_{num_people}',
            email=f'benchmark_{num_people}@test.com',
            password='benchmarkpass'
        )
        
        tree = FamilyTree.objects.create(
            name=f'Benchmark Tree {num_people}',
            super_admin=user
        )
        
        people = []
        for i in range(num_people):
            person = Person.objects.create(
                family_tree=tree,
                first_name=f'Person{i}',
                last_name=f'Family{i // 10}',
                birth_date=date(1950 + (i % 50), 1, 1)
            )
            people.append(person)
        
        return tree, people
    
    return _create_benchmark_data


# Mock external services for testing
@pytest.fixture
def mock_email_backend(settings):
    """Mock email backend for testing."""
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


@pytest.fixture
def mock_cache_backend(settings):
    """Mock cache backend for testing."""
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    }


# Custom pytest markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.api = pytest.mark.api