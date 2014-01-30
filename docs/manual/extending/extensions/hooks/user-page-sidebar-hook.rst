.. _user-page-sidebar-hook:

===================
UserPageSidebarHook
===================

:py:class:`reviewboard.extensions.hooks.UserPageSidebarHook` can be used to
introduce additional items in the user page. :py:class:`UserPageSidebarHook`
requires two arguments for initialization: the extension instance and a list
of entries. Each entry in this list must be a dictionary with the following
keys:

   * **label**: Label to appear on the UserPage navigation pane.
   * **url**: URL for the UserPage Entry.

The dictionary can also have an optional **subitems** key to show additional
items under a main label. Each entry of the subitems must be a dictionary with
the following keys:

   * **label**: Sub-Item to appear on the UserPage navigation pane.
   * **url**: URL for the Sub-Item


Example
=======

.. code-block:: python

    from django.conf import settings
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import UserPageSidebarHook


    class SampleExtension(Extension):
        def initialize(self):
            UserPageSidebarHook(
                self,
                entries = [
                    {
                        'label': 'A SampleExtension Label',
                        'url': settings.SITE_ROOT + 'sample_extension/',
                    }
                ]
            )


If you want to include sub-items in the sidebar::

    from django.conf import settings
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import UserPageSidebarHook


    class SampleExtension(Extension):
        def initialize(self):
            UserPageSidebarHook(
                self,
                entries = [
                    {
                        'label': 'User Menu with SubItems',
                        'url': settings.SITE_ROOT + 'sample_extension/',
                        'subitems': [
                            {
                                'label': 'SubItem entry',
                                'url': settings.SITE_ROOT + 'subitem/',
                            },
                            {
                                'label': 'Another SubItem entry',
                                'url': settings.SITE_ROOT + 'subitem2/',
                            }
                        ]
                    }
                ]
            )
