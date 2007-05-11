import re

from django import newforms as forms
from django.contrib.auth.models import User

from reviewboard.diffviewer.forms import UploadDiffForm
from reviewboard.diffviewer.models import DiffSetHistory
from reviewboard.reviews.models import Review, ReviewRequest, \
                                       ReviewRequestDraft, Screenshot
from reviewboard.scmtools.models import Repository
import reviewboard.reviews.db as reviews_db


class NewReviewRequestForm(forms.Form):
    basedir = forms.CharField(required=False)
    diff_path = forms.CharField(widget=forms.FileInput, required=True)
    repository = forms.ChoiceField(required=True)
    changenum = forms.IntegerField(required=False)

#    summary = forms.CharField(max_length=300)
#    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}))
#    testing_done = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}))
#    bugs_closed = forms.CharField()
#    branch = forms.CharField()
#    target_groups = forms.CharField()
#    target_people = forms.CharField()

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['repository'].choices = \
            [(repo.id, repo.name) for repo in Repository.objects.all()]

    @staticmethod
    def create_from_list(data, constructor, error):
        """Helper function to combine the common bits of clean_target_people
           and clean_target_groups"""
        result = []
        names = [x for x in map(str.strip, re.split(',\s*', data)) if x]
        for name in names:
            result.append(constructor(name))
        return set(result)

    def create(self, user, file):
        repository = Repository.objects.get(pk=self.clean_data['repository'])
        changenum = self.clean_data['changenum'] or None

        review_request = reviews_db.create_review_request(user,
                                                          repository,
                                                          changenum)

        diff_form = UploadDiffForm(data={
            'basedir': self.clean_data['basedir'],
            'path': self.clean_data['diff_path'],
            'repositoryid': repository.id,
        })
        diff_form.full_clean()

        diff_form.create(file, review_request.diffset_history)

        return review_request


class UploadScreenshotForm(forms.Form):
    caption = forms.CharField(required=False)
    path = forms.CharField(widget=forms.FileInput())

    def create(self, data, review):
        draft = ReviewRequestDraft.create(review)

        screenshot = Screenshot(caption=self.clean_data['caption'])
        screenshot.save()
        screenshot.save_image_file(data["filename"], data["content"])

        draft.screenshots.add(screenshot)

        return screenshot
