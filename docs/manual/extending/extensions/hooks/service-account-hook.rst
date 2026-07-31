.. _service-account-hook:

==================
ServiceAccountHook
==================

.. versionadded:: 8.1

Service accounts represent special managed users used for automations and
integrations. They can perform operations through the Review Board API,
but cannot otherwise log in, and do not take a seat on the license.

These are ideal for extensions and integrations that need to:

* Associate data (such as reviews, comments, or review requests) with a
  managed user account rather than a real user.

* Manage API tokens for a service that communicates with Review Board.

To provide a service account, you'll need to subclass
:py:class:`~reviewboard.accounts.service_accounts.ServiceAccount` and
register it using
:py:class:`~reviewboard.extensions.hooks.ServiceAccountHook`.


Creating Service Accounts
=========================

Your service account will subclass
:py:class:`~reviewboard.accounts.service_accounts.ServiceAccount`. You must
set the following:

* :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.
  service_account_id`:

  A unique ID for the service account, in :term:`slug` format. This should be
  prefixed with a vendor or extension ID to avoid collisions. It will be used
  as the username for the managed user, if :py:attr:`~reviewboard.accounts.
  service_accounts.ServiceAccount.preferred_username` isn't provided.

It may also define:

* :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.name`:

  The display name for the account, used for the managed user.

* :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.email`:

  The e-mail address for the managed user. If not provided, the server's
  default no-reply address is used.

* :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.
  preferred_username`:

  The username to use when looking up or creating the managed user, instead of
  :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.
  service_account_id`.

  If you have an existing user that you want to migrate to a service account,
  this should be set to its username.

* :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.avatar_urls`:

  A mapping of resolution indicators (``1x``, ``2x``, ``3x``) to image URLs,
  used as the managed user's avatar.

* :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.
  api_token_policy`:

  A :ref:`token policy <api-token-policies>` applied to any API tokens created
  for the account. It's recommended that you set a policy covering the minimum
  set of permissions the service account needs to perform its responsibilities.

  To ensure older tokens with an outdated policy are not used, increment
  :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.
  api_token_version` when updating the policy.

* :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.
  api_token_expiration_secs`:

  The expiration time for any created API tokens, in seconds.

Rather than subclassing, you can also provide these as keyword arguments when
constructing a :py:class:`~reviewboard.accounts.service_accounts.ServiceAccount`
directly.

If you've previously created a service account-like user and want to migrate
it over to a proper service account, you can claim that specific username by
setting it in :py:attr:`~reviewboard.accounts.service_accounts.ServiceAccount.
preferred_username` and passing ``claim_username=True`` during construction.


Using a Service Account
=======================

Once you have a registered service account, you can access its managed user and
API token:

* :py:meth:`~reviewboard.accounts.service_accounts.ServiceAccount.get_user`:

  Returns the managed :py:class:`~django.contrib.auth.models.User`, looking it
  up or creating it as needed. This may raise
  :py:class:`~reviewboard.accounts.errors.ServiceAccountUserError` if a user
  couldn't be fetched or created.

* :py:meth:`~reviewboard.accounts.service_accounts.ServiceAccount.
  get_api_token`:

  Returns a :py:class:`~reviewboard.webapi.models.WebAPIToken` for the account,
  reusing an existing valid token or creating a new one using the account's
  policy and expiration settings.


Example
=======

This example registers a service account for an extension, sets a token policy
limiting it to the API resources it needs, and shows how to fetch an API token
to hand off to an external service.

.. code-block:: python

    from typing import TYPE_CHECKING

    from reviewboard.accounts.service_accounts import ServiceAccount
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ServiceAccountHook

    if TYPE_CHECKING:
        from reviewboard.site.models import LocalSite


    class MyServiceAccount(ServiceAccount):
        service_account_id = 'myvendor_bot'
        name = 'My Vendor Bot'
        email = 'bot@myvendor.example.com'

        # Give the account full read access and allow it to post reviews.
        api_token_policy = {
            'resources': {
                '*': {
                    'allow': ['GET', 'HEAD', 'OPTIONS'],
                    'block': ['*'],
                },
                'review': {
                    '*': {
                        'allow': ['*'],
                        'block': [],
                    },
                },
                'review_diff_comment': {
                    '*': {
                        'allow': ['*'],
                        'block': [],
                    },
                },
                'review_file_attachment_comment': {
                    '*': {
                        'allow': ['*'],
                        'block': [],
                    },
                },
                'review_general_comment': {
                    '*': {
                        'allow': ['*'],
                        'block': [],
                    },
                },
            },
        }


    class SampleExtension(Extension):
        def initialize(self) -> None:
            self.service_account = MyServiceAccount()

            ServiceAccountHook(self, self.service_account)

        def post_review(
            self,
            *,
            local_site: LocalSite | None = None,
        ) -> None:
            # Fetch an API token to send to our external service, so it can
            # post to Review Board as the service account.
            api_token = self.service_account.get_api_token(
                local_site=local_site)

            my_external_service.post_review(token=api_token.token)
