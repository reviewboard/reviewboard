from django import forms
from django.core import validators
from django.core.validators import ValidationError
from reviewboard.reviews.models import Group, Person, ReviewRequest

class ChangeNumberManipulator(UserProfile.Manipulator):
    def __init__(self, request):
        pass
