.. _url-hook:

=======
URLHook
=======

:py:class:`reviewboard.extensions.hooks.URLHook` is used to extend the URL
patterns that Review Board will recognize and respond to.

:py:class:`URLHook` requires two arguments for initialization: the extension
instance and the Django URL patterns.


Example
=======

.. code-block:: python

    from django.urls import include, path
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import URLHook


    class SampleExtension(Extension):
        def initialize(self) -> None:
            urlpatterns = [
                path('sample_extension/', include('sample_extension.urls')),
            ]

            URLHook(self, urlpatterns)


Notice how ``sample_extension.urls`` was included in the patterns. In this
case, ``sample_extension`` is the package name for the extension, and ``urls``
is the module that contains the patterns::

    from django.urls import path

    from sample_extension.views import DashboardView


    urlpatterns = [
        path('', DashboardView.as_view(), name='myvendor-urlname'),
    ]
