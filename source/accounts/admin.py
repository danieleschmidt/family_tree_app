from django.contrib import admin
from .models import (EmailVerification, Country, Location, FamilyTree, Member, Media, Event,
                     EventType, Relationship, RelationshipType, Person, PhotoLocation,
                     AdminAssignment, FileTable, UserPermissionRole, UserPermission,
                     UserRole, UserGroupRole, Activation)


class PersonAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'birthdate', 'deathdate', 'gender', 'email', 'phone', 'address', 'user', 'family_tree')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('gender', )
    ordering = ('last_name', 'first_name')


class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'country_code')
    search_fields = ('name', 'country_code')
    ordering = ('name',)


admin.site.register(Person)
admin.site.register(Country)

models = [EmailVerification, Location, FamilyTree, Member, Media, Event,
          EventType, Relationship, RelationshipType, PhotoLocation,
          AdminAssignment, FileTable, UserPermissionRole, UserPermission,
          UserRole, UserGroupRole, Activation]

for model in models:
    admin.site.register(model)