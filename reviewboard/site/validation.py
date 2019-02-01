from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


def validate_repositories(form, field='repositories'):
    """Validate that the repositories all have valid, matching LocalSites.

    This will compare the LocalSite associated with the form to that of each
    added Repository. Each Repository must have the same LocalSite that the
    form is using.

    Args:
        form (django.forms.Form):
            The form to validate.

        field (unicode):
            The name of the form field to validate.

    Returns:
        list of reviewboard.scmtools.models.Repository:
        The list of repositories.

    Raises:
        django.core.exceptions.ValidationError:
            The selected groups contained ones which were not properly limited
            to the local site.
    """
    repositories = form.cleaned_data.get(field, [])
    local_site = form.cleaned_data['local_site']

    for repository in repositories:
        if repository.local_site != local_site:
            raise ValidationError(
                [_("The repository '%s' doesn't exist on the local site.")
                   % repository.name])

    return repositories


def validate_review_groups(form, field='review_groups'):
    """Validate that the review groups all have valid, matching LocalSites.

    This will compare the LocalSite associated with the form to that of
    each added Group. Each Group must have the same LocalSite that the form
    is using.

    Args:
        form (django.forms.Form):
            The form to validate.

        field (unicode):
            The name of the form field to validate.

    Returns:
        list of reviewboard.reviews.models.group.Group:
        The list of groups.

    Raises:
        django.core.exceptions.ValidationError:
            The selected groups contained ones which were not properly limited
            to the local site.
    """
    groups = form.cleaned_data.get(field, [])
    local_site = form.cleaned_data['local_site']

    for group in groups:
        if group.local_site != local_site:
            raise ValidationError(
                [_("The review group %s does not exist.") % group.name])

    return groups


def validate_users(form, field='users'):
    """Validate that the users all have valid, matching LocalSites.

    This will compare the LocalSite associated with the form to that of
    each added User. If the form has a LocalSite set, then all Users are
    required to be a part of that LocalSite. Otherwise, any User is allowed.

    Args:
        form (django.forms.Form):
            The form to validate.

        field (unicode):
            The name of the form field to validate.

    Returns:
        list of django.contrib.auth.models.User:
        The list of users.

    Raises:
        django.core.exceptions.ValidationError:
            The selected users contained ones which were not properly limited
            to the local site.
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
