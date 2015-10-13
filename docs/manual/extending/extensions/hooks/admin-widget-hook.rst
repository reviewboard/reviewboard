.. _admin-widget-hook:

===============
AdminWidgetHook
===============

.. versionadded:: 2.5

:py:class:`reviewboard.extensions.hooks.AdminWidgetHook` allows extensions to
register new widgets for the administration dashboard.

Extensions must provide a subclass of
:py:class:`reviewboard.admin.widgets.Widget`, and pass it as a
parameter to :py:class:`AdminWidgetHook`. Each class must provide
:py:attr:`widget_id` and :py:attr:`title` attributes, and should provide a
:py:attr:`template`.


Example
=======

.. code-block:: python

    from django.utils.translation import ugettext_lazy as _
    from reviewboard.admin.widgets import Widget
    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import AdminWidgetHook


    class SampleWidget(Widget):
        widget_id = 'myvendor_sample_widget'
        title = _('Sample Widget')
        template = 'sample/widgets/sample-widget.html'


    class SampleExtension(Extension):
        def initialize(self):
            AdminWidgetHook(self, SampleWidget)
