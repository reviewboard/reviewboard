from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField
from djblets.util.compat.django.core.validators import URLValidator
from multiselectfield import MultiSelectField

from reviewboard.notifications.managers import WebHookTargetManager
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite


@python_2_unicode_compatible
class WebHookTarget(models.Model):
    """A target for a webhook.

    A webhook target is a URL which will receive a POST request when the
    corresponding event occurs.
    """
    ALL_EVENTS = '*'

    EVENT_CHOICES = (
        (ALL_EVENTS, _('All events')),
        ('review_request_closed', _('Review request closed')),
        ('review_request_published', _('Review request published')),
        ('review_request_reopened', _('Review request reopened')),
        ('review_published', _('Review published')),
        ('reply_published', _('Reply published')),
    )

    ENCODING_JSON = 'application/json'
    ENCODING_XML = 'application/xml'
    ENCODING_FORM_DATA = 'application/x-www-form-urlencoded'

    ALL_ENCODINGS = (
        ENCODING_JSON,
        ENCODING_XML,
        ENCODING_FORM_DATA
    )

    ENCODINGS = (
        (ENCODING_JSON, _('JSON')),
        (ENCODING_XML, _('XML')),
        (ENCODING_FORM_DATA, _('Form Data')),
    )

    APPLY_TO_ALL = 'A'
    APPLY_TO_NO_REPOS = 'N'
    APPLY_TO_SELECTED_REPOS = 'S'

    APPLY_TO_CHOICES = (
        (APPLY_TO_ALL, _('All review requests')),
        (APPLY_TO_SELECTED_REPOS,
         _('Only review requests on selected repositories')),
        (APPLY_TO_NO_REPOS,
         _('Only review requests not associated with a repository (file '
           'attachments only)')),
    )

    # Standard information
    enabled = models.BooleanField(default=True)
    events = MultiSelectField(
        _('events'),
        choices=EVENT_CHOICES,
        blank=True,
        help_text=_('Select any or all events that should trigger this '
                    'Webhook.'))

    url = models.URLField(
        'URL',
        help_text=_('When the event is triggered, HTTP requests will be '
                    'made against this URL.'))

    encoding = models.CharField(
        _('encoding'),
        choices=ENCODINGS,
        default=ENCODING_JSON,
        max_length=40,
        help_text=_('Payload contents will be encoded in this format.'))

    # Custom content
    use_custom_content = models.BooleanField(
        _('use custom payload content'),
        default=False)

    custom_content = models.TextField(
        _('custom content'),
        blank=True,
        null=True,
        help_text=_('You can override what is sent to the URL above. If '
                    'left blank, the default payload will be sent.'))

    # HMAC payload signing
    secret = models.CharField(
        _('HMAC secret'),
        max_length=128, blank=True,
        help_text=_('If specified, the HMAC digest for the Webhook payload '
                    'will be signed with the given secret.'))

    # Apply to
    apply_to = models.CharField(
        _('apply to'),
        max_length=1,
        blank=False,
        default=APPLY_TO_ALL,
        choices=APPLY_TO_CHOICES)

    repositories = models.ManyToManyField(
        Repository,
        blank=True,
        related_name='webhooks',
        help_text=_('If set, this Webhook will be limited to these '
                    'repositories.'))

    local_site = models.ForeignKey(
        LocalSite,
        blank=True,
        null=True,
        related_name='webhooks',
        help_text=_('If set, this Webhook will be limited to this site.'))

    extra_data = JSONField(
        null=True,
        help_text=_('Extra JSON data that can be tied to this Webhook '
                    'registration. It will not be sent with the Webhook '
                    'request.'))

    objects = WebHookTargetManager()

    def __init__(self, *args, **kwargs):
        """Initialize the model.

        Args:
            *args (tuple):
                Positional arguments to pass through to the Model constructor.

            **kwargs (dict):
                Keyword arguments to pass through to the Model constructor.
        """
        super(WebHookTarget, self).__init__(*args, **kwargs)
        self._meta.get_field('url').validators = [URLValidator()]

    def is_accessible_by(self, user, local_site=None):
        """Return if the webhook can be accessed or modified by the user.

        All superusers and admins of the webhook's local site can access and
        modify the webhook.

        Args:
            user (django.contrib.auth.models.User):
                The user who is trying to access the webhook.

            local_site (reviewboard.site.models.LocalSite):
                The current local site, if it exists.

        Returns:
            bool:
            Whether or not the given user can access or modify the webhook
            through the given local site.
        """
        return (user.is_superuser or
                (user.is_authenticated() and
                 local_site and
                 self.local_site_id == local_site.pk and
                 local_site.is_mutable_by(user)))

    def __str__(self):
        return self.url

    class Meta:
        db_table = 'notifications_webhooktarget'
        verbose_name = _('Webhook')
        verbose_name_plural = _('Webhooks')
