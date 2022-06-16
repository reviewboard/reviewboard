.. _authentication-settings:

=======================
Authentication Settings
=======================

* :ref:`auth-general-settings`
* :ref:`basic-authentication-settings`
* :ref:`active-directory-authentication-settings`
* :ref:`ldap-authentication-settings`
* :ref:`nis-authentication-settings`
* :ref:`legacy-authentication-settings`
* :ref:`fixing-a-broken-authentication-setup`
* :ref:`saml-settings`


.. _auth-general-settings:

General Settings
================

In this section you'll chose the type of authentication you'll be allowing
on the site (LDAP, Active Directory, etc.) and whether or not anonymous
users can access the site.

The following settings can be configured:

* **Allow anonymous read-only access:**
    Determines whether or not anonymous users should be able to view
    posted review requests and diffs.

    This is often safe to enable when the code being posted is public or when
    there's strict access controls to the site itself. If the code is
    confidential and it's possible for people without authority to access
    the server, this should be disabled.


.. _`Authentication Method`:
.. _authentication-method:

* **Authentication Method:**
    The method used for authenticating users on this Review Board server.

    Review Board has multiple ways of authenticating users. By default,
    "Standard registration" is used, but other methods can be selected. See
    :ref:`Authentication` for more information.

    Depending on the authentication method selected, additional settings may
    be available.

    Available options are:

    * Standard registration
    * Active Directory
    * LDAP
    * NIS
    * X.509 Public Key
    * Legacy Authentication Module


.. _basic-authentication-settings:

Basic Authentication Settings
=============================

This is available if `Authentication Method`_ is set to
``Standard registration``.

* **Enable registration:**
    You can use this to control whether or not new users can register accounts
    on the server.

    It may be useful to turn off registration if you're carefully controlling
    who's allowed to post on your server, or if you're being flooded with
    spam users.

* **Show a captcha for registration:**
    Public Review Board servers may encounter spam accounts from time to time.
    You can help prevent these by turning on captchas for registration.

    Review Board uses reCAPTCHA_ for its captcha system. reCAPTCHA is a
    widely used and maintained captcha system. In order to use it, you will
    need to register an account and fill in the following two fields with the
    public and private keys that the site provides.

* **reCAPTCHA Public Key:**
    The public key provided by the reCAPTCHA site registration for your site.

* **reCAPTCHA Private Key:**
    The private key provided by the reCAPTCHA site registration for your site.

.. _reCAPTCHA: https://www.google.com/recaptcha/intro/


.. _active-directory-authentication-settings:

Active Directory Authentication Settings
========================================

This is available if `Authentication Method`_ is set to ``Active Directory``.

* **Domain name:**
    The Active Directory Domain to authenticate against.
    For example: ``MYDOMAIN``

    If you can't login, you may need to use the fully qualified name.
    For example: ``MYDOMAIN.subdomain.topleveldomain``

    This setting is required.

* **Use TLS for authentication:**
    If checked, then TLS will be used for all authentication requests. This
    option is more secure, but must be enabled on the AD server.

* **Find DC from DNS:**
    If checked, find the Domain Controller from DNS.

* **Domain controller:**
    Enter the name or IP address of the Domain Controller of not using DNS lookup.

* **OU name:**
    Optionally restrict users to specified OU.

* **Group name:**
    Optionally restrict users to a specified group.

* **Custom search root:**
    Optionally specify a custom search root, overriding the built-in computed
    search root. If set, "OU name" is ignored.

* **Recursion Depth:**
    Depth to recurse when checking group membership. Set to 0 to turn off,
    -1 for unlimited.

.. _ldap-authentication-settings:

LDAP Authentication Settings
============================

This is available if `Authentication Method`_ is set to ``LDAP``.

* **LDAP Server:**
    The LDAP server to authenticate with.
    For example: ``ldap://localhost:389``

    This setting is required.

* **LDAP Base DN:**
    The LDAP Base DN for performing LDAP searches.
    For example: ``ou=users,dc=example,dc=com``

    This setting is required.

* **E-Mail Domain:**
    The domain name appended to the user's login name to form the e-mail
    address. For example: ``example.com``

    This setting is required.

* **Use TLS for authentication:**
    If checked, then TLS will be used for all authentication requests. This
    option is more secure, but must be enabled on the LDAP server.

* **User Mask:**
    The string representing the user. The string must contain the text
    ``%s`` where the username would normally go.
    For example: ``(uid=%s)``

    This setting is required.

* **Anonymous User Mask:**
    The user mask string for anonymous users. This should be in the same
    format as User Mask.

    This setting is optional. If not provided, anonymous logins will be
    disabled.

* **Anonymous User Password:**
    The password for the anonymous user.

    This setting is optional.


.. _nis-authentication-settings:

NIS Authentication Settings
===========================

This is available if `Authentication Method`_ is set to ``NIS``.

* **E-Mail Domain:**
    The domain name appended to the user's login name to form the e-mail
    address. For example: ``example.com``

    This setting is required.


.. _legacy-authentication-settings:

Legacy Authentication Module Settings
=====================================

This is available if `Authentication Method`_ is set to
``Legacy Authentication Module``.

* **Backends:**
    A comma-separated list of custom Django authentication backend classes.
    These are represented as Python module paths.

    This is an advanced setting and should only be used if you know what
    you're doing.

    This setting is required.


.. _fixing-a-broken-authentication-setup:

Fixing a Broken Authentication Setup
====================================

Misconfiguring authentication can leave you unable to log in to your Review
Board server to fix it. In this case, you can reset the authentication backend
back to the builtin database method with the :command:`rb-site` command::

    $ rb-site manage /path/to/site set-siteconfig -- --key=auth_backend --value=builtin


.. _saml-settings:

SAML 2.0 Authentication
=======================

Review Board supports SAML 2.0 for Single Sign-On (SSO). This requires
installing additional dependencies:

.. code-block:: console

    $ pip install -U 'ReviewBoard[saml]'

To enable SAML 2.0, you'll need to configure both the settings in Review Board
(the Service Provider) and your Identity Provider.


Review Board Configuration
--------------------------

For the Review Board configuration, you'll need to start by checking the
:guilabel:`Enable SAML 2.0 authentication` box. You'll then see a new section
to configure Review Board to know about your Identity Provider.

Your Identity Provider should provide the following for you to put into the
Review Board configuration:

1. URLs for the Issuer and SAML/SLO endpoints, as well as the binding type for
   each.
2. A copy of the X.509 certificate.
3. Possibly, specific digest and signature algorithm types.

The :guilabel:`Require login to link` setting allows you to control the
behavior when first authenticating a user via SSO who already has an account on
Review Board. If you have a trusted internal environment where you're confident
that the Identity Provider is sending the correct usernames, you can leave this
field unchecked. If you enable this, existing users will be asked to enter
their Review Board password a single time before linking the SAML identity.


Identity Provider Configuration
-------------------------------

On the Identity Provider side, you'll need to configure it with the following
URLs. Replace the server name with your configured server name.

Audience/Metadata
    Example: ``https://example.com/account/sso/saml/metadata/``

ACS/Recipient
    Example: ``https://example.com/account/sso/saml/acs/``

Single Logout
    Example: ``https://example.com/account/sso/saml/sls/``

You'll also need to configure your assertion parameters. The desired username
should be sent in the SAML ``NameID`` field. The other parameters that should
be sent in the assertion are ``User.email``, ``User.FirstName``, and
``User.LastName``.


User Authentication
-------------------

Depending on how authentication is configured with Review Board, users may or
may not have a working password. For example, a server that is using both
Active Directory and SAML will allow users to log in either with the SSO
provider or with the standard AD credentials. A server that is configured with
standard authentication and has registration turned off will force all users to
go through SSO.

In the case where users do not have a password, they will need to use API
tokens for any external tools, including the RBTools command-line. API tokens
can be created through the user's :ref:`account-settings`.

After creating an API token, users can use it to authenticate.

To configure RBTools to authenticate by adding the token to
:file:`.reviewboardrc`, include the following::

    API_TOKEN = "<token>"

Alternatively, if you don't want to store the token, pass it to :command:`rbt
login`. This will create a session cookie that will be used for subsequent
RBTools commands. This may require periodic re-authentication as the sessions
expire.

.. code-block:: console

    $ rbt login --api-token <token>

See :ref:`api-tokens` for more information on creating API tokens.
