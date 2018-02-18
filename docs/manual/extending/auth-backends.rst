.. _writing-auth-backends:

===============================
Writing Authentication Backends
===============================

Overview
========

Authentication in Review Board is handled by classes called Authentication
Backends. They perform the tasks of looking up users from some database or
server, authenticating against it given user credentials, and creating
local representations of the users in Review Board's database.

Review Board provides local database, NIS, LDAP and Active Directory backends
out of the box. New ones can be written to work with other types of
authentication schemes.


Authentication Classes
======================

An Authentication Backend class is a simple class inheriting from
:py:class:`reviewboard.accounts.backends.AuthBackend`. It must set the
following attributes:

* :py:attr:`backend_id`
* :py:attr:`name`

And can optionally set the following attributes:

* :py:attr:`login_instructions`
* :py:attr:`settings_form`
* :py:attr:`supports_registration`
* :py:attr:`supports_change_name`
* :py:attr:`supports_change_email`
* :py:attr:`supports_change_password`

It must also define the methods:

* :py:meth:`authenticate`
* :py:meth:`get_or_create_user`

And can optionally define these methods:

* :py:meth:`query_users`
* :py:meth:`search_users`

We'll go into each function and attribute in detail.


.. py:class:: reviewboard.accounts.backends.AuthBackend
   :noindex:

.. py:attribute:: backend_id

   This is the ID used for registering and looking up the authentication
   backend.

   This ID needs to be unique, and therefore should include some
   vendor-specific prefix.

.. py:attribute:: name

   This is the human-readable name of the authentication backend. This is what
   users will see when they go to select the authentication backend to use.

.. py:attribute:: login_instructions

   If set, this string is displayed on the login page.

.. py:attribute:: settings_form

   This is an optional attribute that can be used to specify a settings form
   to present for any configuration needed by the backend.

   If this is not ``None``, it must point to a
   :py:class:`djblets.siteconfig.forms.SiteSettingsForm` subclass. This works
   like a standard Django Form, where each field name is the name of the
   settings key that will be automatically loaded and saved. See
   :ref:`auth-settings-form` for more information.


.. py:attribute:: supports_registration

   A boolean that indicates whether the registration form can be used.
   If this is set to ``True``, then logged out users will have the ability
   to register a new account.

   The registration process will create a new
   :py:class:`User <django.contrib.auth.models.User>` in the database.
   Currently, there is no support for handing off registration to the
   authentication backend, but it's planned.

.. py:attribute:: supports_change_name

   A boolean that indicates whether a user can change his full name on
   the My Account page. If this is set to ``True``, fields for the first
   and last name will be available and editable.

   Currently, there is no support for allowing the authentication module to
   handle setting the name, so it cannot update the backend server. This
   is planned for the future.


.. py:attribute:: supports_change_email

   A boolean that indicates whether a user can change his e-mail address on
   the My Account page. If this is set to ``True``, a field for the e-mail
   address will be available and editable.

   Currently, there is no support for allowing the authentication module to
   handle setting the e-mail address, so it cannot update the backend server.
   This is planned for the future.


.. py:attribute:: supports_change_password

   A boolean that indicates whether a user can change his password on
   the My Account page. If this is set to ``True``, a field for the password
   will be available and editable.

   Currently, there is no support for allowing the authentication module to
   handle setting the password, so it cannot update the backend server.
   This is planned for the future.


.. py:method:: authenticate(username, password)

   :param username: The user's username.
   :param password: The user's password.
   :rtype: The authenticated user, if authentication succeeds. On failure,
           ``None``.

   Authenticates the user against a database or server.

   This is responsible for making any necessary communication with the
   database or server and determining the validity of the credentials
   passed.

   If the credentials are invalid, the function must return ``None``, which
   will allow it to fall back to the next authentication backend in the chain
   (or fail, if this is the last authentication backend).

   If the credentials are valid, the function must return a valid
   :py:class:`User <django.contrib.auth.models.User>`. Generally, rather than
   constructing one itself, it should call its own
   :py:meth:`get_or_create_user` with the username.

   To help with debugging, this function should log any errors in
   communication using Python's :py:mod:`logging` support.

   The function may need to strip whitespace from the username before
   authentication. If the server itself strips whitespace when authenticating,
   but this function does not, it can lead to duplicate users in the database.


.. py:method:: get_or_create_user(username, request)

   :param username: The user's username.
   :param request: The current Django Request object.
   :rtype: The user, if it exists. Otherwise, ``None``.

   Looks up or creates a :py:class:`User <django.contrib.auth.models.User>`
   based on information from the database or server.

   This tends to follow the pattern of:

   .. code-block:: python

      username = username.strip()

      try:
          user = User.objects.get(username=username)
      except User.DoesNotExist:
          # Construct a user from the database...
          return user

   Like :py:meth:`authenticate`, this will look up the user from the
   database or server. However, it will not verify anything other than the
   username. It also must make sure to strip the username.

   This function is used both when logging in and when adding a user to
   a review request as a reviewer. In the latter case, Review Board will
   look up the user using the authentication backend in order to see if
   the user exists and can be added.


.. py:method:: query_users(query, request)

   :param query: A user-query search string.
   :param request: The current Django Request object.
   :rtype: ``None``.

   This function is executed when querying :ref:`webapi2.0-user-list-resource`,
   before retrieving the list of users from the database.

   The response is always fetched directly from the database; however,
   this function allows backends to search an external service and
   create or update users in the Review Board database before the
   query is executed.

   To pass errors up to the web API layer, raise a
   :py:exc:`reviewboard.accounts.errors.UserQueryError`
   exception with a specific error message.


.. py:method:: search_users(query, request)

   :param query: A user-query search string.
   :param request: The current Django Request object.
   :rtype: django.db.models.Q or ``None``.

   This function is executed when querying :ref:`webapi2.0-user-list-resource`,
   when the ``q`` parameter is given, meaning there is a search query.  It
   can return a Django Q object to filter the database results, or it can
   return None (the default, if not overriden).  If None, this method is
   called on the next enabled auth backend, if any.  If all backends return
   None, the default filter is applied.


.. _auth-settings-form:

Settings Forms
==============

Authentication backends can provide a settings form just like the built-in
backends (NIS, LDAP, etc.). The backend class just needs to set
:py:attr:`settings_form` to a
:py:class:`djblets.siteconfig.forms.SiteSettingsForm` subclass (not an
instance).

This is a special sort of form where each field name is the name of the
key in the settings database to store the value. The proper convention
for these classes is to prefix the field name with :samp:`auth_{backendid}_`.
The ``backendid`` is a short, lowercase name that represents the auth
backend. For example, ``nis``, ``ldap``, or ``ad``.

Every field will be saved to the database with the exception of "blacklisted"
fields. See :ref:`auth-settings-form-blacklisting`.

The form can also include some metadata by way of a ``Meta`` class within
the form. It can contain a :py:attr:`title` attribute, containing the title
to show on the settings form, and a :py:attr:`save_blacklist` for blacklisting
fields.

The form may also provide custom :py:meth:`load` and :py:meth:`save` methods
for handling any custom loading and saving. These must always call the parent
class's methods.

An example class would be::

    from django import forms
    from djblets.siteconfig.forms import SiteSettingsForm


    class MySettingsForm(SiteSettingsForm):
        auth_myauth_foo = forms.CharField(
            label="Some setting",
            help_text="Some useful help text",
            required=True)

        auth_myauth_bar = forms.BooleanField(
            label="Another setting",
            help_text="Some more useful help text",
            required=False)

        class Meta:
            title = "My Auth Backend Settings"


These can use any Django form fields. The actual loading and saving of
settings from the database are handled under the hood.

You can also make use of standard Django form validation to ensure that
valid data was entered before save.


.. _auth-settings-form-blacklisting:

Blacklisting Fields
-------------------

Sometimes it's necessary to process a setting before it goes into the
database or when it comes out. In this case, you don't want the setting to
be handled automatically. The field can be prevented from saving/loading by
adding it to the ``Meta.save_blacklist`` attribute. This is a tuple of
field names that will be ignored during save/load.

This is usually used in conjunction with custom :py:meth:`load` and
:py:meth:`save` methods.

When loading a setting into a field, you should set the value in
:samp:`self.fields['{fieldname}'].initial` and retrieve the value from the
database when using :samp:`self.siteconfig.get('{settingname}')`.

When saving a setting from a field, you should set the value in the database
using :samp:`self.siteconfig.set('{settingname}', value)` and retrieving it
from the field using :samp:`self.cleaned_data['{fieldname}']`.

For example::

    class MySettingsForm(SiteSettingsForm):
        auth_myauth_list = forms.CharField(
            label="Comma-separated list of values")

        def load(self):
            self.fields['auth_myauth_list'].initial = \
                ','.join(self.siteconfig.get('auth_myauth_list'))

            super(MySettingsForm, self).load()

        def save(self):
            self.siteconfig.set(
                'auth_myauth_list',
                re.split(r',\*', self.cleaned_data['auth_myauth_list']))

            super(MySettingsForm, self).save()


Disabling Fields
----------------

It can be useful to disable fields based on different conditions, such as
a missing Python module. In this case, you can disable any fields in the
form and provide an inline message by setting the
:py:attr:`disabled_fields` and :py:attr:`disabled_reasons` attributes during
:py:meth:`load`.

Both of these attributes are dictionaries mapping from a field name to a
value. For :py:attr:`disabled_fields`, the value is a boolean indicating
whether the field is disabled. For :py:attr:`disabled_reasons`, the value is a
string describing why the field is disabled.

For example::

    def load(self):
        if not get_can_enable_myauth():
            self.disabled_fields['auth_myauth_foo'] = True
            self.disabled_reasons['auth_myauth_foo'] = \
                'You must do a handstand before you can enable this ' \
                'authentication backend.'

        super(MySettingsForm, self).load()



Accessing Settings
==================

The authentication backend can access any settings stored in the site
configuration database (such as those defined in the
:ref:`Settings form <site-settings>` through the
:py:class:`djblets.siteconfig.models.SiteConfiguration` API.

Working with this is pretty simple. First, you just need to get a
:py:class:`SiteConfiguration <djblets.siteconfig.models.SiteConfiguration>`
object::

    from djblets.siteconfig.models import SiteConfiguration


    siteconfig = SiteConfiguration.objects.get_current()


You can then load and save through :py:meth:`SiteConfiguration.set`
and :py:meth:`SiteConfiguration.get` methods. Each take a setting name and
work with any native Python primitive (strings, booleans, lists, tuples,
dictionaries).

For example::

    from djblets.siteconfig.models import SiteConfiguration


    siteconfig = SiteConfiguration.objects.get_current()
    siteconfig.set('auth_myauth_foo', 'Some value')
    bar = siteconfig.get('auth_myauth_bar')


Packaging
=========

Using Extensions
----------------

As of Review Board 2.0, authentication backends should be provided by
extensions, using :ref:`auth-backend-hook`. This allows the authentication
backends to be easily added or removed.


Using Entry Points
------------------

When extensions are, for some reason, not an ideal option, you can instead
fall back on using Python entry point registration. This is required
if your authentication backend needs to work on versions of Review Board
prior to 2.0.

For entry point registration, your authentication backends will need to be
packaged as a standard Python egg module. Generally, this looks something
like::

    setup.py
    myauth/__init__.py

The :file:`__init__.py` would contain your authentication backend's classes
and logic.

You can of course split this up into separate files (such as
:file:`backends.py` for the backend class and :file:`forms.py` for the
settings form). This is entirely up to you. However, to be a proper Python
module, you must have a :file:`__init__.py`, though it can be blank.

:file:`setup.py` must define an "entry point" for your module in order for
Review Board to find it. This is done through the ``entry_points`` parameter
passed to ``setup``. For example::

    setup(...,
          entry_points={
              'reviewboard.auth_backends': [
                  'myauth = myauth:MyAuthBackend',
              ],
          }
    )

Review Board will look in ``reviewboard.auth_backends`` for every module and
attempt to load it. The module path specified must be the full Python module
path for your class. The ID (``myauth`` in the example above) can be anything,
but generally should be consistent with your settings prefix for the settings
form, and must not conflict with any other authentication modules.

The authentication module can then be installed by typing (as root)::

    $ python setup.py install
