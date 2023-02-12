from datetime import date
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Q
from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver
from django.urls import reverse
from itertools import chain
from opencage.geocoder import OpenCageGeocode
from operator import attrgetter
from people.fields import UncertainDateField
from people.relations import closest_common_ancestor, describe_relative
from taggit.managers import TaggableManager
from taggit.models import Tag, TaggedItem
from tinymce.models import HTMLField
import os
import settings
from django.db import models


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



class Person(models.Model):
    """

    """
    first_name = models.CharField(max_length=50,
                                  help_text='First/ given name')
    middle_name = models.CharField(blank=True,
                                   max_length=50,
                                   help_text='Middle name')
    last_name = models.CharField(max_length=50,
                                 help_text='Last/ surname')
    maiden_name = models.CharField(blank=True,
                                   max_length=50,
                                   help_text='Maiden name')
    nickname = models.CharField(blank=True,
                                max_length=20,
                                help_text='nickname')
    gender = models.CharField(max_length=1,
                              choices=(('M', 'Male'),
                                       ('F', 'Female'),
                                       ('T', 'Transgender',
                                        'N', 'Non-binary',
                                        'P', 'Prefers not to respond')),
                              blank=False,
                              default=None)


    id = models.AutoField(primary_key=True)

    def __str__(self):
        return self.text


class Identification(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class Name(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)


class Gender(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class ProfilePhoto(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class FatherID(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='father')


class MotherID(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='mother')


class SpouseID(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class EmailAddress(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)


class ContactNumber(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class PhysicalAddress(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)


class Bio(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)


class URLforStorage(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)