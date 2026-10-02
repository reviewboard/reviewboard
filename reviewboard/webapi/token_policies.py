"""Standard API token policies and registration.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import gettext_lazy as _

from reviewboard.registries.registry import OrderedRegistry

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import ClassVar

    from typelets.django.strings import StrOrPromise
    from typelets.json import JSONDictImmutable


class BaseWebAPITokenPolicy:
    """Base class for API token policies.

    Each API token policy can be used as a template for a new API token.
    The default document specified in the policy will be saved to the API
    token.

    Version Added:
        9.0
    """

    #: The ID of the API token policy.
    token_policy_id: ClassVar[str]

    #: The visible name of the API token policy.
    name: ClassVar[StrOrPromise]

    #: The default token policy document.
    #:
    #: A copy of this policy will be stored in the API token once created.
    default_token_policy_doc: ClassVar[JSONDictImmutable] = {}


class ReadOnlyWebAPITokenPolicy(BaseWebAPITokenPolicy):
    """A default read-only API token policy.

    This provides HTTP GET, HEAD, and OPTIONS requests for all API resources.

    Version Added:
        9.0
    """

    token_policy_id = 'read-only'
    name = _('Read-only')

    default_token_policy_doc = {
        'resources': {
            '*': {
                'allow': ['GET', 'HEAD', 'OPTIONS'],
                'block': ['*'],
            },
        },
    }


class FullAccessWebAPITokenPolicy(BaseWebAPITokenPolicy):
    """A default full-access API token policy.

    This provides full read/write access to all API resources.

    Version Added:
        9.0
    """

    token_policy_id = 'read-write'
    name = _('Full access')

    default_token_policy_doc = {}


class WebAPITokenPolicyRegistry(
    OrderedRegistry[type[BaseWebAPITokenPolicy]],
):
    """A registry of API token policies.

    Each API token policy will be available as an option when crafting a new
    API token. Policies are listed in the order in which they're registered.

    Version Added:
        9.0
    """

    lookup_attrs = ('token_policy_id',)

    def get_token_policy(
        self,
        token_policy_id: str,
    ) -> type[BaseWebAPITokenPolicy] | None:
        """Return the token policy with the given ID.

        Args:
            token_policy_id (str):
                The ID of the token policy to return.

        Returns:
            type:
            The token policy, or ``None`` if not found.
        """
        return self.get('token_policy_id', token_policy_id)

    def get_defaults(self) -> Iterator[type[BaseWebAPITokenPolicy]]:
        """Yield the default API token policies.

        Yields:
            type:
            Each API token policy type.
        """
        yield FullAccessWebAPITokenPolicy
        yield ReadOnlyWebAPITokenPolicy


#: The central registry of API token policies.
#:
#: Version Added:
#:     9.0
webapi_token_policies = WebAPITokenPolicyRegistry()
