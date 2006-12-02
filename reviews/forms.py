from django import forms
from django.core import validators
from django.core.validators import ValidationError
from reviewboard.reviews.models import Group, Person, ReviewRequest

class AddReviewRequestManipulator(ReviewRequest.AddManipulator):
    def __init__(self):
        ReviewRequest.AddManipulator.__init__(self)

        new_fields = []
        for field in self.fields:
            if field.field_name == 'target_groups' or \
               field.field_name == 'target_people':
               name = field.field_name
               field = forms.TextField(field_name=name,
                                       length=50, maxlength=500,
                                       is_required=False)
            new_fields.append(field)

        self.fields = new_fields

    def save(self, new_data):
        target_groups = new_data['target_groups']
        target_people = new_data['target_people']
        del(new_data['target_groups'])
        del(new_data['target_people'])

        review_request = super(AddReviewRequestManipulator, self).save(new_data)

        if target_groups and target_groups.strip().lower():
            for group_name in target_groups.split(','):
                group_name = group_name.strip().lower()
                group, group_is_new = \
                    Group.objects.get_or_create(name=group_name)

                if group_is_new:
                    group.save()

                review_request.target_groups.add(group)

        if target_people and target_people.strip().lower():
            for person_name in target_people.split(','):
                person_name = person_name.strip().lower()
                person, person_is_new = \
                    Person.objects.get_or_create(username=person_name)

                if person_is_new:
                    person.save()

                review_request.target_people.add(person)

        review_request.save()
        return review_request;
