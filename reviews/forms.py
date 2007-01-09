from django import newforms as forms
from django.core import validators
from django.core.validators import ValidationError
from reviewboard.reviews.models import Group, Person, ReviewRequest

class NewReviewRequestForm(forms.Form):
    summary = forms.CharField()
    description = forms.CharField(widget=forms.Textarea)
    testing_done = forms.CharField(widget=forms.Textarea)
    bugs_closed = forms.CharField()
    branch = forms.CharField()
    target_groups = forms.CharField()
    target_people = forms.CharField()

    def create(self):
        target_groups = self.clean_data['target_groups']
        target_people = self.clean_data['target_people']
        del(self.clean_data['target_groups'])
        del(self.clean_data['target_people'])

        review_request = ReviewRequest(**self.clean_data)
        review_request.save()

        if target_groups and target_groups.strip().lower():
            for group_name in target_groups.split(','):
                group_name = group_name.strip().lower()
                group, group_is_new = \
                    Group.objects.get_or_create(name=group_name)

                if group_is_new:
                    group.save()

                print 'group = %s, new = %s, id = %s' % \
                    (group_name, group_is_new, group.id)
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
        return review_request
