.. _navigation-bar-hook:
.. _extension-navigation-bar-hook:

=================
NavigationBarHook
=================

:py:class:`reviewboard.extensions.hooks.NavigationBarHook` can be used to
introduce additional items to the main navigation bar.

:py:class:`NavigationBarHook` requires two arguments: the extension instance
and a list of entries. Each entry represents an item on the navigation bar,
and is a dictionary with the following keys:

    * **label**:    The label to display.
    * **url**:      The URL to point to.
    * **url_name**: The name of the URL to point to.

Only one of **url** or **url_name** is required. **url_name** will take
precedence, and is recommended.

If your extension needs to access the template context, you can define a
subclass from NavigationBarHook to override ``get_entries`` and return
results from there.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import NavigationBarHook


    class SampleExtension(Extension):
        def initialize(self):
            NavigationBarHook(
                self,
                entries = [
                    {
                        'label': 'An Item on Navigation Bar',
                        'url_name': 'page-name',
                    },
                    {
                        'label': 'Another Item on Navigation Bar',
                        'url_name': 'page-name',
                    },
                ]
            )
