from django import newforms as forms
from reviewboard.diffviewer.models import DiffSetHistory
from django.contrib.auth.models import User, Group
from reviewboard.reviews.models import ReviewRequest
import re

class NewReviewRequestForm(forms.Form):
    summary = forms.CharField(max_length=300)
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}))
    testing_done = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}))
    bugs_closed = forms.CharField()
    branch = forms.CharField()
    target_groups = forms.CharField()
    target_people = forms.CharField()

    def create_from_list(self, data, constructor, error):
        """Helper function to combine the common bits of clean_target_people
           and clean_target_groups"""
        return None # XXX Bail out for now. This is broken

        result = []
        names = [x for x in map(str.strip, re.split('[, ]+', data)) if x]
        for name in names:
            result.append(constructor(name))
        return set(result)

    def clean_target_people(self):
        try:
            return self.create_from_list(self.clean_data['target_people'],
                                         lambda x: User.objects.get(username=x),
                                         None)
        except User.DoesNotExist:
            # XXX: it'd be nice to have a way of getting the offending name
            raise forms.ValidationError('Reviewer does not exist')

    def clean_target_groups(self):
        try:
            return self.create_from_list(self.clean_data['target_groups'],
                                         lambda x: Group.objects.get(name=x),
                                         None)
        except Group.DoesNotExist:
            # XXX: it'd be nice to have a way of getting the offending name
            raise forms.ValidationError('Group does not exist')

    def clean(self):
        if 'target_people' in self.clean_data and \
           'target_groups' in self.clean_data and \
           not self.clean_data['target_people'] and \
           not self.clean_data['target_groups']:
            raise forms.ValidationError(
                'You must specify at least one reviewer or group')

    def create(self):
        diffset_history = DiffSetHistory()
        diffset_history.save()

        review_request = ReviewRequest(**self.clean_data)
        review_request.diffset_history = diffset_history
        review_request.save()
        return review_request
