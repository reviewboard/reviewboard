"""Privacy support for user accounts."""

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from djblets.privacy.consent import get_consent_requirements_registry
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
