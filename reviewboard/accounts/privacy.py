"""Privacy support for user accounts."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.privacy.consent import (Consent,
                                     get_consent_requirements_registry,
                                     get_consent_tracker)
from djblets.privacy.consent.common import (BaseGravatarConsentRequirement,
                                            PolicyConsentRequirement)
from djblets.registries.errors import ItemLookupError
from djblets.siteconfig.models import SiteConfiguration
from djblets.urls.staticfiles import static_lazy
from djblets.util.html import mark_safe_lazy


class GravatarConsentRequirement(BaseGravatarConsentRequirement):
    intent_description = mark_safe_lazy(_(
        "Gravatar is used by many services and applications to manage and "
        "serve <b>avatars</b>. We use Gravatars by default for your "
        "avatar. If you don't want to use it, you can block that here, "
        "or upload your own avatar in your Profile settings."
    ))

    icons = {
        '1x': static_lazy('rb/images/consent/gravatar.png'),
        '2x': static_lazy('rb/images/consent/gravatar@2x.png'),
    }


_registered = False


def register_privacy_consents(force=False):
    """Register the built-in consent requirements for user privacy.

    This will only register the consents once. Calling this method multiple
    times will have no effect.

    Args:
        force (bool, optional):
            Force all consent requirements to re-register.
    """
    global _registered

    if not _registered or force:
        registry = get_consent_requirements_registry()

        # Unregister our consent requirements (but leave ones provided by
        # extensions).
        for requirement in (GravatarConsentRequirement,
                            PolicyConsentRequirement):
            try:
                registry.unregister_by_attr(
                    'requirement_id', requirement.requirement_id)
            except ItemLookupError:
                pass

        siteconfig = SiteConfiguration.objects.get_current()
        privacy_policy = siteconfig.get('privacy_policy_url')
        terms_of_service = siteconfig.get('terms_of_service_url')

        if privacy_policy or terms_of_service:
            registry.register(PolicyConsentRequirement(
                privacy_policy,
                terms_of_service,
                siteconfig.get('site_admin_email')))

        registry.register(GravatarConsentRequirement())

        _registered = True


def is_consent_missing(user):
    """Return whether the user is missing any consent requirements.

    Args:
        user (django.contrib.auth.models.User):
            The user in question.

    Returns:
        bool:
        Whether or not the user is missing any consent requirements.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if not siteconfig.get('privacy_enable_user_consent'):
        return False

    consent_tracker = get_consent_tracker()
    pending_consent = consent_tracker.get_pending_consent_requirements(
        user)

    needs_accept_policies = (
        (siteconfig.get('privacy_policy_url') or
         siteconfig.get('terms_of_service_url')) and
        (consent_tracker.get_consent(
            user,
            PolicyConsentRequirement.requirement_id) !=
         Consent.GRANTED)
    )

    return needs_accept_policies or pending_consent
