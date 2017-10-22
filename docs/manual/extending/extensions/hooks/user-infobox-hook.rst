.. _user-infobox-hook:

===============
UserInfoboxHook
===============

.. currentmodule:: reviewboard.extensions.hooks

:py:class:`reviewboard.extensions.hooks.UserInfoboxHook` is used to extend the
:ref:`User Infobox <user-infobox>` with additional HTML, which will appear at
the bottom of the infobox. The HTML can include anything that the extension
may want to provide.

Extensions can either instantiate this hook or subclass it, depending on the
level of control they want to have over the content. If the information is
static for a given user, instantiating is generally fine. If the information
may change between views, they may want to subclass in order to have more
control over the caching information.


Rendering Infobox Content
=========================

When rendering additional content for a user infobox, the template will
contain all data normally provided for a page (through Django's
:py:class:`~django.template.RequestContext`), along with:

``extension``:
    Your extension's instance.

``user``:
    The :py:class:`~django.contrib.auth.models.User` model being viewed in
    the infobox.

The infobox will render the template passed to the hook during initialization.
This uses standard Django templates.

When subclassing, additional information can be provided by overriding
:py:meth:`~UserInfoboxHook.get_extra_context` and returning a dictionary of
context variables for the template.

Subclasses can also completely change the rendering behavior by overriding
:py:meth:`~UserInfoboxHook.render`.


Controlling Caching
===================

A rendered infobox is cached in order to prevent having to repeatedly ask the
server to re-render the contents. :mailheader:`ETag` headers are used to
ensure this. By default, the following data related to the user is included in
the cache key:

* Username
* User's first name
* User's last name
* User's e-mail address
* Time the user last explicitly logged in
* Configured timezone for the user
* Whether profile information is public or private
* Avatar-specific data

If the data being added to the infobox by the hook can change, and those
changes aren't based on the above information, the extension may want to
subclass the hook and override :py:meth:`~UserInfoboxHook.get_etag_data`. This
would return a string (of any length) representative of the dynamic state of
the infobox.


Examples
========

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import UserInfoboxHook


    class SampleUserInfoboxHook(UserInfoboxHook):
        def initialize(self):
            super(SampleUserInfoboxHook, self).initialize(
                'myextension/advanced-user-infobox.html')

        def get_etag_data(self, user, request, local_site, **kwargs):
            return self.extension.get_user_quote_of_the_day(user)

        def get_extra_context(self, user, request, local_site, **kwargs):
            return {
                'is_bob': user.username == 'bob',
                'quote': self.extension.get_user_quote_of_the_day(),
            }


    class SampleExtension(Extension):
        def initialize(self):
            # Add a simple hook that just renders a basic template.
            UserInfoboxHook(self, 'myextension/basic-user-infobox.html')

            # Add a more advanced hook that provides custom caching and
            # rendering.
            SampleUserInfoboxHook(self)

        def get_user_quote_of_the_day(self, user):
            return 'something fancy would go here'
