.. _oauth2:

=====================
OAuth2 Authentication
=====================

.. versionadded:: 3.0

Review Board supports the :term:`OAuth2` authorization code grant mechanism for
connecting third-party services. Supporting OAuth2 allows your application to
use Review Board's APIs without storing any user credentials.


Registering an OAuth2 Application
=================================

In order to use OAuth2, you'll need to register an application. To do this,
from the Review Board UI, go to the :ref:`account-settings` page. From here,
select :guilabel:`OAuth2 Applications`, and then :guilabel:`Add application`.

There are several fields to fill out in the application creation form:

:guilabel:`Name`
    The name of the application. This can be anything, and is only used to help
    keep track of your various registered applications.

:guilabel:`Enabled`
    Whether the application should be enabled or not.

:guilabel:`Redirect URIs`
    After a user authenticates, Review Board will redirect back to your
    application. The specific location of the redirect will be specified as
    part of the :ref:`oauth2-authorization-flow`. This field defines a whitelist of
    which URIs will be accepted therein.

:guilabel:`Client Type`
    The client type, as defined in :rfc:`RFC 6749 Section 2.1
    <6749#section-2.1>`.

:guilabel:`Authorization Grant Type`
    The type of authorization flow desired by the client. We recommend using
    the :guilabel:`Authorization code` grant type.

:guilabel:`Restrict To`
    If your server uses :term:`local sites`, you can optionally restrict your
    OAuth2 application to authenticate to only a specific local site. If the
    drop-down field is empty, this field can safely be ignored.


Once you save your application, you will see two new settings. These will be
used by your application code when requesting authorization:

:guilabel:`Client ID`
    An ID for your client which will be sent along with requests for
    authorization.

:guilabel:`Client Secret`
    A shared secret, used for verification of requests.


.. _oauth2-authorization-flow:

Authorization Flow
==================

Authenticating via OAuth2 happens in several steps:

1. Your application redirects users to Review Board to log in.
2. Review Board redirects the user back to your site and provides an
   authorization code.
3. Your application uses the authorization code to request an access token.
4. Your application uses the new access token to connect to Review Board's API.
5. Refresh your access token when necessary.


1. Redirecting users to the authorization URL
---------------------------------------------

To start, create a "Log In" link which redirects the user to the following URL
on your Review Board server::

    https://reviewboard.example.com/oauth2/authorize/?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}

There are several values to fill in in the query string for this URL:

* ``client_id`` is the Client ID from your registered application.
* ``redirect_uri`` is the URI you want the user to be redirected to after a
  successful authentication. This must be listed in the
  :guilabel:`Redirect URIs` field of your registered application.
* ``scope`` is an optional, space-delimited list of :ref:`scopes
  <oauth2-scopes>` that your application is requesting access to. If omitted,
  the application will request access to the entire Review Board API.
* ``state`` is an optional value which your application can use to verify
  consistency between the request and the callback at the redirect URI.

When this URL is loaded by the client's browser, the user will be asked to log
in (if needed), and then asked if they want to authorize the application. Upon
doing so, they'll be redirect back to your specified redirect URI.


2. Getting the authorization callback
-------------------------------------

Once the user authorizes your application, they will be redirected back to your
application's redirect URI. For example, if you had set the redirect URI as
``https://myapp.example.com/oauth2/cb``, the user would be redirected to::

    https://myapp.example.com/oauth2/cb?code={authorization code}

The authorization code is a 30-character string which will be used to get an
access token.


3. Getting an access token
--------------------------

The access token is what is actually used to authenticate to Review Board. Once
you have an authorization code, it can be used to request an access token. This
is done via a POST operation to the token URL::

    POST https://reviewboard.example.com/oauth2/token/

This POST should include the authorization code returned in step 2 and the
grant type in the body::

    code={authorization code}&grant_type=authorization_code&

This will return a JSON blob containing the access token, the expiration of
that access token, and a refresh token::

    {
        "access_token": "sometoken",
        "refresh_token": "new authorization code for refreshing",
        "expires_in": 3600,
        "scope": "...",
        "token_type": "Bearer"
    }


4. Making use of the Review Board API
-------------------------------------

Once you have an access token, you can use it to :ref:`authenticate to the Web
API <webapi2.0-oauth2-authentication>` by passing it in the HTTP
:mailheader:`Authorization` header.


5. Refresh the access token
---------------------------

Access tokens have an expiration date. When your access token was first
returned, the payload also included a ``refresh_token`` field. This can be used
with the ``token`` endpoint originally used in step 3 to get a new access token.


.. _oauth2-scopes:

OAuth2 Scopes
=============

When your application requests authorization, you can optionally include a list
of scopes. These scopes are defined via the API resource names and a method
type (``read``, ``write``, or ``delete``). For example, to request read access
to the review request resource, the scope ID would be ``review-request:read``.

.. note:: These scopes do not automatically grant access to the parent
          resources, so granting read or write access to ``review`` also
          requires granting read access to its parent, ``review-request``.
