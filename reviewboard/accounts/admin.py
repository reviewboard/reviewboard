from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.models import (ReviewRequestVisit, Profile,
                                         LocalSiteProfile)


USERNAME_REGEX = r'^[-@\w.]+$'
USERNAME_HELP_TEXT = _("Required. 30 characters or fewer. Alphanumeric "
                       "characters (letters, digits, underscores, and "
                       "periods) and '@'.")
USERNAME_ERROR_MESSAGE = _("This value must contain only letters, numbers, "
                           "underscores, periods and '@'.")


class RBUserChangeForm(UserChangeForm):
    """
    A variation of UserChangeForm that allows "." in the username.
    """
    username = forms.RegexField(
        label=_("Username"), max_length=30,
        regex=USERNAME_REGEX,
        help_text=USERNAME_HELP_TEXT,
        error_message=USERNAME_ERROR_MESSAGE)


class RBUserCreationForm(UserCreationForm):
    """
    A variation of UserCreationForm that allows "." in the username.
    """
    username = forms.RegexField(
        label=_("Username"), max_length=30,
        regex=USERNAME_REGEX,
        help_text=USERNAME_HELP_TEXT,
        error_message=USERNAME_ERROR_MESSAGE)


class RBUserAdmin(UserAdmin):
    form = RBUserChangeForm
    add_form = RBUserCreationForm
    filter_vertical = ('user_permissions',)
    filter_horizontal = ()


class ReviewRequestVisitAdmin(admin.ModelAdmin):
    list_display = ('review_request', 'user', 'timestamp')
    raw_id_fields = ('review_request',)


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'first_time_setup_done')
    raw_id_fields = ('user', 'starred_review_requests', 'starred_groups')


class LocalSiteProfileAdmin(admin.ModelAdmin):
    list_display = ('__str__',)
    raw_id_fields = ('user', 'profile', 'local_site')


# Get rid of the old User admin model, and replace it with our own.
admin.site.unregister(User)
admin.site.register(User, RBUserAdmin)

admin.site.register(ReviewRequestVisit, ReviewRequestVisitAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(LocalSiteProfile, LocalSiteProfileAdmin)
