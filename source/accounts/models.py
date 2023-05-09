from django.db import models
from datetime import date
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q
from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver
from django.urls import reverse
from itertools import chain
from opencage.geocoder import OpenCageGeocode
from operator import attrgetter
from taggit.managers import TaggableManager
from taggit.models import Tag, TaggedItem
from tinymce.models import HTMLField
import os
# import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now
from django.contrib.sites.models import Site


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=now)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)


class Country(models.Model):
    """

    """
    name = models.CharField(max_length=50)
    country_code = models.CharField(max_length=3)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'countries'


class Location(models.Model):
    pass


class FamilyTree(models.Model):
    name = models.CharField(max_length=100)
    super_admin = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    family_tree = models.ForeignKey(FamilyTree, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    profile_photo = models.ImageField(upload_to='profile_photos/')
    father = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='children_father')
    mother = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='children_mother')
    spouse = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='spouse_of')
    email_address = models.EmailField()
    contact_phone_number = models.CharField(max_length=15)
    address = models.TextField()
    short_bio = models.TextField()
    personal_cloud_storage_url = models.URLField()


class Media(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    file = models.FileField(upload_to='media/')
    is_shared = models.BooleanField(default=False)


class Event(models.Model):
    person = models.ForeignKey('Person', on_delete=models.CASCADE)
    event_type = models.ForeignKey('EventType', on_delete=models.CASCADE)
    date = models.DateField()
    place = models.CharField(max_length=200, blank=True, null=True)


class EventType(models.Model):
    event_type = models.CharField(max_length=50)


class Relationship(models.Model):
    from_person = models.ForeignKey('Person', related_name='from_relationships', on_delete=models.CASCADE)
    to_person = models.ForeignKey('Person', related_name='to_relationships', on_delete=models.CASCADE)
    relationship_type = models.ForeignKey('RelationshipType', on_delete=models.CASCADE)


class RelationshipType(models.Model):
    relationship_type = models.CharField(max_length=50)


class Person(models.Model):
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female'), ('O', 'Other')))
    birthdate = models.DateField()
    deathdate = models.DateField(blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    father = models.ForeignKey('self', related_name='children_as_father', blank=True, null=True,
                               on_delete=models.SET_NULL)
    mother = models.ForeignKey('self', related_name='children_as_mother', blank=True, null=True,
                               on_delete=models.SET_NULL)
    spouse = models.ForeignKey('self', related_name='spouse_as_person', blank=True, null=True,
                               on_delete=models.SET_NULL)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=200, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    personal_storage = models.URLField(blank=True, null=True)

    # links for family tree and user tables
    family_tree = models.ForeignKey(FamilyTree, on_delete=models.CASCADE, null=True, blank=True)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()


class PhotoLocation(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    location = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)


class AdminAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    family_tree = models.ForeignKey(FamilyTree, on_delete=models.CASCADE)


class FileTable(models.Model):
    name = models.CharField(max_length=50)
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class UserPermissionRole(models.Model):
    role_name = models.CharField(max_length=50)


class UserPermission(models.Model):
    permission_name = models.CharField(max_length=50)


class UserRole(models.Model):
    role_name = models.CharField(max_length=50)


class UserGroupRole(models.Model):
    role_name = models.CharField(max_length=50)


class User(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission_role = models.ForeignKey(UserPermissionRole, on_delete=models.CASCADE)
    user_role = models.ForeignKey(UserRole, on_delete=models.CASCADE)
    user_group_role = models.ForeignKey(UserGroupRole, on_delete=models.CASCADE)


class Activation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
