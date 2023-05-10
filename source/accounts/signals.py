from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Person


@receiver(post_save, sender=User)
def create_person_for_new_user(sender, instance, created, **kwargs):
    if created:
        person = Person(user=instance)
        person.save()