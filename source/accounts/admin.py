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


admin.site.register(Person, PersonAdmin)
admin.site.register(EmailVerification)
admin.site.register(Country)
admin.site.register(Location)
admin.site.register(FamilyTree)
admin.site.register(Member)
admin.site.register(Media)
admin.site.register(Event)
admin.site.register(EventType)
admin.site.register(Relationship)
admin.site.register(RelationshipType)
admin.site.register(PhotoLocation)
admin.site.register(AdminAssignment)
admin.site.register(FileTable)
admin.site.register(UserPermissionRole)
admin.site.register(UserPermission)
admin.site.register(UserRole)
admin.site.register(UserGroupRole)
admin.site.register(Activation)