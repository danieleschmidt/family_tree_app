from django.shortcuts import render
from django.http import HttpResponse
from .models import Person

# Create your views here.


def index(request):
    return HttpResponse("Hello, world. You're at the family tree app")


def person_list(request):
    persons = Person.objects.all()
    return render(request, 'person_list.html', {'persons': persons})