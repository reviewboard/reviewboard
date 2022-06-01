"""Base classes for SSO views.

Version Added:
    5.0
"""

import logging

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import View


logger = logging.getLogger(__file__)


@method_decorator([sensitive_post_parameters(), never_cache],
                  name='dispatch')
class BaseSSOView(View):
    """Base class for SSO views.

    Version Added:
        5.0
    """

    #: The SSO backend.
    #:
    #: Type:
    #:     reviewboard.accounts.sso.backends.SSOBackend
    sso_backend = None
