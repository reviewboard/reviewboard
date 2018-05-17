"""Privacy support for user accounts."""

from __future__ import unicode_literals

from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from djblets.privacy.consent import get_consent_requirements_registry
from djblets.privacy.consent.common import BaseGravatarConsentRequirement
from djblets.urls.staticfiles import static_lazy


class GravatarConsentRequirement(BaseGravatarConsentRequirement):
    intent_description = mark_safe(_(
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


def register_privacy_consents():
    """Register the built-in consent requirements for user privacy.

    This will only register the consents once. Calling this method multiple
    times will have no effect.
    """
    global _registered

    if not _registered:
        registry = get_consent_requirements_registry()
        registry.register(GravatarConsentRequirement())

        _registered = True
