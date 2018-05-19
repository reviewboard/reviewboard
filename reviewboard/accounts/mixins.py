"""Mixins for account-related views."""

from __future__ import unicode_literals

from django import forms
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from djblets.privacy.consent import (get_consent_tracker,
                                     get_consent_requirements_registry)
from djblets.privacy.consent.common import PolicyConsentRequirement
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.decorators import (check_login_required,
                                             valid_prefs_required)


class CheckLoginRequiredViewMixin(object):
    """View mixin to check if a user needs to be logged in.

    This is a convenience around using the :py:func:`@check_login_required
    <reviewboard.accounts.decorators.check_login_required>` decorator for
    class-based views.
    """

    @method_decorator(check_login_required)
    def dispatch(self, *args, **kwargs):
        """Dispatch a HTTP request to the right handler.

        Args:
            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        return super(CheckLoginRequiredViewMixin, self).dispatch(
            *args, **kwargs)


class LoginRequiredViewMixin(object):
    """View mixin to ensure a user is logged in.

    This is a convenience around using the :py:func:`@login_required
    <django.contrib.auth.decorators.login_required>` decorator for
    class-based views.
    """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        """Dispatch a HTTP request to the right handler.

        Args:
            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        return super(LoginRequiredViewMixin, self).dispatch(*args, **kwargs)


class UserProfileRequiredViewMixin(object):
    """View mixin to ensure a user has a profile set up.

    This is a convenience around using the :py:func:`@valid_prefs_required
    <reviewboard.accounts.decorators.valid_prefs_required>` decorator for
    class-based views.
    """

    @method_decorator(valid_prefs_required)
    def dispatch(self, *args, **kwargs):
        """Dispatch a HTTP request to the right handler.

        Args:
            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        return super(UserProfileRequiredViewMixin, self).dispatch(
            *args, **kwargs)


class PolicyConsentFormMixin(object):
    """Form mixin to add consent to privacy policy and terms of service."""

    def __init__(self, *args, **kwargs):
        """Initialize the mixin.

        Args:
            *args (tuple):
                Additional positional arguments to pass to the superclass
                constructor.

            **kwargs (dict):
                Additional keyword arguments to pass to the superclass
                constructor.
        """
        super(PolicyConsentFormMixin, self).__init__(*args, **kwargs)

        siteconfig = SiteConfiguration.objects.get_current()
        privacy_policy_url = siteconfig.get('privacy_policy_url')
        terms_of_service_url = siteconfig.get('terms_of_service_url')

        self.policies_enabled = bool(
            siteconfig.get('privacy_enable_user_consent') and
            (privacy_policy_url or terms_of_service_url))

        if self.policies_enabled:
            if privacy_policy_url and terms_of_service_url:
                label = mark_safe(
                    _('I agree to the <a href="%s">Privacy Policy</a> and '
                      '<a href="%s">Terms of Service</a>.')
                    % (privacy_policy_url, terms_of_service_url))
            elif privacy_policy_url:
                label = mark_safe(
                    _('I agree to the <a href="%s">Privacy Policy</a>.')
                    % privacy_policy_url)
            elif terms_of_service_url:
                label = mark_safe(
                    _('I agree to the <a href="%s">Terms of Service</a>.')
                    % terms_of_service_url)

            self.fields['agree_to_policies'] = forms.BooleanField(
                label=label,
                required=True)

    def accept_policies(self, user):
        """Accept the linked policies for the given user.

        Args:
            user (django.contrib.auth.models.User):
                The user who has accepted the privacy policy and/or terms of
                service.
        """
        if self.policies_enabled:
            consent_registry = get_consent_requirements_registry()
            requirement = consent_registry.get_consent_requirement(
                PolicyConsentRequirement.requirement_id)

            consent_tracker = get_consent_tracker()
            consent_tracker.record_consent_data(
                user, requirement.build_consent_data(granted=True))
