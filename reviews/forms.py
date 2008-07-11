import re

from django import newforms as forms
from django.utils.translation import ugettext as _
from PIL import Image

from reviewboard.diffviewer.forms import UploadDiffForm, EmptyDiffError
from reviewboard.reviews.errors import ChangeNumberInUseError, \
                                       ChangeSetError, \
                                       OwnershipError
from reviewboard.reviews.models import ReviewRequest, \
                                       ReviewRequestDraft, Screenshot
from reviewboard.scmtools.models import Repository


class NewReviewRequestForm(forms.Form):
    """
    A form that handles creationg of new review requests. These take
    information on the diffs, the repository the diffs are against, and
    optionally a changelist number (for use in certain repository types
    such as Perforce).
    """
    basedir = forms.CharField(label=_("Base Diff Path"), required=False)
    diff_path = forms.CharField(label=_("Diff"),
                                widget=forms.FileInput, required=True)
    parent_diff_path = forms.CharField(label=_("Parent Diff (optional)"),
                                       widget=forms.FileInput, required=False)
    repository = forms.ChoiceField(label=_("Repository"), required=True)
    changenum = forms.IntegerField(label=_("Change Number"), required=False)

    def __init__(self, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['repository'].choices = \
            [(repo.id, repo.name) for repo in Repository.objects.order_by('name')]

    @staticmethod
    def create_from_list(data, constructor, error):
        """Helper function to combine the common bits of clean_target_people
           and clean_target_groups"""
        names = [x for x in map(str.strip, re.split(',\s*', data)) if x]
        return set([constructor(name) for name in names])

    def create(self, user, diff_file, parent_diff_file):
        repository = Repository.objects.get(pk=self.cleaned_data['repository'])
        changenum = self.cleaned_data['changenum'] or None

        # It's a little odd to validate this here, but we want to have access to
        # the user.
        if changenum:
            try:
                changeset = repository.get_scmtool().get_changeset(changenum)
                if not changeset:
                    self.errors['changenum'] = forms.util.ErrorList([
                        'This change number does not represent a valid '
                        'changeset.'])
                    raise ChangeSetError()

                if user.username != changeset.username:
                    self.errors['changenum'] = forms.util.ErrorList([
                        'This change number is owned by another user.'])
                    raise OwnershipError()
            except NotImplementedError:
                # This scmtool doesn't have changesets
                pass

        try:
            review_request = ReviewRequest.objects.create(user, repository,
                                                          changenum)
        except ChangeNumberInUseError:
            # The user is updating an existing review request, rather than
            # creating a new one.
            review_request = ReviewRequest.objects.get(changenum=changenum)
            review_request.update_from_changenum(changenum)

            if review_request.status == 'D':
                # Act like we're creating a brand new review request if the
                # old one is discarded.
                review_request.status = 'P'
                review_request.public = False

            review_request.save()

        diff_form = UploadDiffForm(repository, data={
            'basedir': self.cleaned_data['basedir'],
        },
        files={
            'path': self.cleaned_data['diff_path'],
            'parent_diff_path': self.cleaned_data['parent_diff_path'],
        })
        diff_form.full_clean()

        try:
            diff_form.create(diff_file, parent_diff_file,
                             review_request.diffset_history)
            if 'path' in diff_form.errors:
                review_request.delete()
                self.errors['diff_path'] = diff_form.errors['path']
            elif 'base_diff_path' in diff_form.errors:
                review_request.delete()
                self.errors['base_diff_path'] = diff_form.errors['base_diff_path']
        except EmptyDiffError:
            review_request.delete()
            self.errors['diff_path'] = forms.util.ErrorList([
                'The selected file does not appear to be a diff.'])
            raise
        except Exception, e:
            review_request.delete()
            self.errors['diff_path'] = forms.util.ErrorList([e])
            raise

        review_request.add_default_reviewers()
        review_request.save()
        return review_request


class UploadScreenshotForm(forms.Form):
    """
    A form that handles uploading of new screenshots.
    A screenshot takes a path argument and optionally a caption.
    """
    caption = forms.CharField(required=False)
    path = forms.CharField(widget=forms.FileInput())

    def create(self, data, review):
        screenshot = Screenshot(caption=self.cleaned_data['caption'],
                                draft_caption=self.cleaned_data['caption'])
        screenshot.save()
        screenshot.save_image_file(data['filename'], data['content'])

        try:
            image = Image.open(screenshot.get_image_filename())
            image.load()
        except:
            screenshot.delete()
            raise ValueError('The file does not appear to be an image')

        draft = ReviewRequestDraft.create(review)
        review.screenshots.add(screenshot)
        draft.screenshots.add(screenshot)
        draft.save()

        return screenshot
