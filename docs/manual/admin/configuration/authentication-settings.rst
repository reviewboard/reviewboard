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
