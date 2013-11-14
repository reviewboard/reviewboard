from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


def validate_users(form, field='users'):
    """Validates that the users all have valid, matching LocalSites.

    This will compare the LocalSite associated with the form to that of
    each added User. If the form has a LocalSite set, then all Users are
    required to be a part of that LocalSite. Otherwise, any User is allowed.
    """
    local_site = form.cleaned_data['local_site']
    users = form.cleaned_data.get(field, [])

    if local_site:
        for user in users:
            if not user.local_site.filter(pk=local_site.pk).exists():
                raise ValidationError(
                    [_("The user %s is not a member of this site.")
                     % user.username])

    return users


def validate_review_groups(form, field='review_groups'):
    """Validates that the review groups all have valid, matching LocalSites.

    This will compare the LocalSite associated with the form to that of
    each added Group. Each Group must have the same LocalSite that the form
    is using.
    """
    groups = form.cleaned_data.get(field, [])
    local_site = form.cleaned_data['local_site']

    for group in groups:
        if group.local_site != local_site:
            raise ValidationError(
                [_("The review group %s does not exist.") % group.name])

    return groups
