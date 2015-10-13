from __future__ import unicode_literals

import os

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db.models import Q
from django.utils import six
from djblets.webapi.decorators import (webapi_login_required,
                                       webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import (DOES_NOT_EXIST, INVALID_FORM_DATA,
                                   NOT_LOGGED_IN, PERMISSION_DENIED)

from reviewboard.reviews.forms import UploadScreenshotForm
from reviewboard.reviews.models import Screenshot
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources


class BaseScreenshotResource(WebAPIResource):
    """A base resource representing screenshots."""
    model = Screenshot
    name = 'screenshot'
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the screenshot.',
        },
        'caption': {
            'type': six.text_type,
            'description': "The screenshot's descriptive caption.",
        },
        'path': {
            'type': six.text_type,
            'description': "The path of the screenshot's image file, "
                           "relative to the media directory configured "
                           "on the Review Board server.",
        },
        'filename': {
            'type': six.text_type,
            'description': "The base file name of the screenshot's image.",
            'added_in': '1.7.10',
        },
        'review_url': {
            'type': six.text_type,
            'description': 'The URL to the review UI for this screenshot.',
            'added_in': '1.7.10',
        },
        'url': {
            'type': six.text_type,
            'description': "The URL of the screenshot file. If this is not "
                           "an absolute URL (for example, if it is just a "
                           "path), then it's relative to the Review Board "
                           "server's URL. This is deprecated and will be "
                           "removed in a future version.",
            'deprecated_in': '2.0',
        },
        'absolute_url': {
            'type': six.text_type,
            'description': "The absolute URL of the screenshot file.",
            'added_in': '2.0',
        },
        'thumbnail_url': {
            'type': six.text_type,
            'description': "The URL of the screenshot's thumbnail file. "
                           "If this is not an absolute URL (for example, "
                           "if it is just a path), then it's relative to "
                           "the Review Board server's URL.",
        },
    }

    uri_object_key = 'screenshot_id'

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        review_request = resources.review_request.get_object(
            request, *args, **kwargs)

        q = Q(review_request=review_request)

        if not is_list:
            q = q | Q(inactive_review_request=review_request)

        if request.user == review_request.submitter:
            try:
                draft = resources.review_request_draft.get_object(
                    request, *args, **kwargs)

                q = q | Q(drafts=draft)

                if not is_list:
                    q = q | Q(inactive_drafts=draft)
            except ObjectDoesNotExist:
                pass

        return self.model.objects.filter(q)

    def serialize_path_field(self, obj, **kwargs):
        return obj.image.name

    def serialize_filename_field(self, obj, **kwargs):
        return os.path.basename(obj.image.name)

    def serialize_review_url_field(self, obj, **kwargs):
        return obj.get_absolute_url()

    def serialize_url_field(self, obj, **kwargs):
        return obj.image.url

    def serialize_absolute_url_field(self, obj, request, **kwargs):
        return request.build_absolute_uri(obj.image.url)

    def serialize_thumbnail_url_field(self, obj, **kwargs):
        return obj.get_thumbnail_url()

    def serialize_caption_field(self, obj, **kwargs):
        # We prefer 'caption' here, because when creating a new screenshot, it
        # won't be full of data yet (and since we're posting to screenshots/,
        # it doesn't hit DraftScreenshotResource). DraftScreenshotResource will
        # prefer draft_caption, in case people are changing an existing one.
        return obj.caption or obj.draft_caption

    def has_access_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_accessible_by(request.user)

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_mutable_by(request.user)

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        return obj.get_review_request().is_mutable_by(request.user)

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED,
                            INVALID_FORM_DATA)
    @webapi_request_fields(
        required={
            'path': {
                'type': file,
                'description': 'The screenshot to upload.',
            },
        },
        optional={
            'caption': {
                'type': six.text_type,
                'description': 'The optional caption describing the '
                               'screenshot.',
            },
        },
    )
    def create(self, request, *args, **kwargs):
        """Creates a new screenshot from an uploaded file.

        This accepts any standard image format (PNG, GIF, JPEG) and associates
        it with a draft of a review request.

        It is expected that the client will send the data as part of a
        :mimetype:`multipart/form-data` mimetype. The screenshot's name
        and content should be stored in the ``path`` field. A typical request
        may look like::

            -- SoMe BoUnDaRy
            Content-Disposition: form-data; name=path; filename="foo.png"

            <PNG content here>
            -- SoMe BoUnDaRy --
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self.get_no_access_error(request)

        form_data = request.POST.copy()
        form = UploadScreenshotForm(form_data, request.FILES)

        if not form.is_valid():
            return INVALID_FORM_DATA, {
                'fields': self._get_form_errors(form),
            }

        try:
            screenshot = form.create(request.FILES['path'], review_request)
        except ValueError as e:
            return INVALID_FORM_DATA, {
                'fields': {
                    'path': [six.text_type(e)],
                },
            }

        return 201, {
            self.item_result_key: screenshot,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_request_fields(
        optional={
            'caption': {
                'type': six.text_type,
                'description': 'The new caption for the screenshot.',
            },
        }
    )
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def update(self, request, caption=None, *args, **kwargs):
        """Updates the screenshot's data.

        This allows updating the screenshot in a draft. The caption, currently,
        is the only thing that can be updated.
        """
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not review_request.is_mutable_by(request.user):
            return self.get_no_access_error(request)

        try:
            screenshot = resources.screenshot.get_object(request, *args,
                                                         **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        try:
            resources.review_request_draft.prepare_draft(request,
                                                         review_request)
        except PermissionDenied:
            return self.get_no_access_error(request)

        screenshot.draft_caption = caption
        screenshot.save()

        return 200, {
            self.item_result_key: screenshot,
        }

    @webapi_check_local_site
    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, *args, **kwargs):
        try:
            review_request = \
                resources.review_request.get_object(request, *args, **kwargs)
            screenshot = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, screenshot, *args,
                                           **kwargs):
            return self.get_no_access_error(request)

        try:
            draft = resources.review_request_draft.prepare_draft(
                request, review_request)
        except PermissionDenied:
            return self.get_no_access_error(request)

        draft.screenshots.remove(screenshot)
        draft.inactive_screenshots.add(screenshot)
        draft.save()

        return 204, {}
