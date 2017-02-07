from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from reviewboard.accounts.models import (ReviewRequestVisit, Profile,
                                         LocalSiteProfile)
from reviewboard.reviews.models import Group


USERNAME_REGEX = r'^[-@\w.]+$'
USERNAME_HELP_TEXT = _("Required. 30 characters or fewer. Alphanumeric "
                       "characters (letters, digits, underscores, and "
                       "periods) and '@'.")
USERNAME_ERROR_MESSAGE = _("This value must contain only letters, numbers, "
                           "underscores, periods and '@'.")


class RBUserChangeForm(UserChangeForm):
    """A variation of UserChangeForm that allows "." in the username."""

    username = forms.RegexField(
        label=_("Username"), max_length=30,
        regex=USERNAME_REGEX,
        help_text=USERNAME_HELP_TEXT,
        error_message=USERNAME_ERROR_MESSAGE)


class RBUserCreationForm(UserCreationForm):
    """A variation of UserCreationForm that allows "." in the username."""

    username = forms.RegexField(
        label=_("Username"), max_length=30,
        regex=USERNAME_REGEX,
        help_text=USERNAME_HELP_TEXT,
        error_message=USERNAME_ERROR_MESSAGE)


class ProfileInline(admin.StackedInline):
    """Admin definitions for showing Profile information inline."""

    model = Profile
    raw_id_fields = ('user', 'starred_review_requests', 'starred_groups')
    fieldsets = (
        (_('Settings'), {
            'classes': ('wide',),
            'fields': ('should_send_email',
                       'should_send_own_updates',
                       'collapsed_diffs',
                       'syntax_highlighting',
                       'is_private',
                       'open_an_issue',
                       'show_closed',
                       'default_use_rich_text',
                       'timezone'),
        }),
        (_('Dashboard'), {
            'classes': ('wide', 'collapse'),
            'fields': ('sort_review_request_columns',
                       'sort_dashboard_columns',
                       'sort_submitter_columns',
                       'sort_group_columns',
                       'review_request_columns',
                       'dashboard_columns',
                       'submitter_columns',
                       'group_columns'),
        }),
        (_('State'), {
            'classes': ('wide', 'collapse'),
            'fields': ('first_time_setup_done',
                       'starred_review_requests',
                       'starred_groups',
                       'settings',
                       'extra_data'),
        }),
    )


class LocalSiteProfileInline(admin.StackedInline):
    """Admin definitions for showing LocalSiteProfile information inline."""

    model = LocalSiteProfile
    exclude = ('profile',)
    readonly_fields = ('local_site',)
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('local_site', 'permissions'),
        }),
        (_('Counters'), {
            'classes': ('wide', 'collapse'),
            'fields': ('direct_incoming_request_count',
                       'total_incoming_request_count',
                       'pending_outgoing_request_count',
                       'total_outgoing_request_count',
                       'starred_public_request_count'),
        }),
    )


class RBUserAdmin(UserAdmin):
    """Admin definitions for the User model."""

    form = RBUserChangeForm
    add_form = RBUserCreationForm
    filter_vertical = ('user_permissions',)
    filter_horizontal = ()

    inlines = [
        ProfileInline,
        LocalSiteProfileInline,
    ]


class ReviewRequestVisitAdmin(admin.ModelAdmin):
    """Admin definitions for the ReviewRequestVisit model."""

    list_display = ('review_request', 'user', 'timestamp')
    raw_id_fields = ('review_request',)


class ProfileAdmin(admin.ModelAdmin):
    """Admin definitions for the Profile model."""

    list_display = ('__str__', 'first_time_setup_done')
    raw_id_fields = ('user', 'starred_review_requests', 'starred_groups')


class LocalSiteProfileAdmin(admin.ModelAdmin):
    """Admin definitions for the LocalSiteProfile model."""

    list_display = ('__str__',)
    raw_id_fields = ('user', 'profile', 'local_site')


def fix_review_counts():
    """Clear out the review counts, so that they'll be regenerated."""
    LocalSiteProfile.objects.update(
        direct_incoming_request_count=None,
        total_incoming_request_count=None,
        pending_outgoing_request_count=None,
        total_outgoing_request_count=None,
        starred_public_request_count=None)
    Group.objects.update(incoming_request_count=None)


# Get rid of the old User admin model, and replace it with our own.
admin.site.unregister(User)
admin.site.register(User, RBUserAdmin)

admin.site.register(ReviewRequestVisit, ReviewRequestVisitAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(LocalSiteProfile, LocalSiteProfileAdmin)
