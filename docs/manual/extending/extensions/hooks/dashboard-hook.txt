.. _dashboard-hook:

=============
DashboardHook
=============

:py:class:`reviewboard.extensions.hooks.DashboardHook` can be used to define a
custom dashboard page for your Extension. :py:class:`DashboardHook` requires
two arguments for initialization: the extension instance and a list of entries.
Each entry in this list must be a dictionary with the following keys:

* **label**: Label to appear on the dashboard's navigation pane.
* **url**: URL for the dashboard page.

If the extension needs only one dashboard, then it needs only one entry in
this list. (See :ref:`extension-navigation-bar-hook`)


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import DashboardHook
    from reviewboard.site.urlresolvers import local_site_reverse


    class SampleExtension(Extension):
        def initialize(self):
            DashboardHook(
                self,
                entries=[
                    {
                        'label': 'My Label',
                        'url': local_site_reverse('my-page-url-name'),
                    }
                ]
            )


Corresponding code in :file:`views.py`:

.. code-block:: python

    def dashboard(request, template_name='sample_extension/dashboard.html'):
        return render_to_response(template_name, RequestContext(request))


Corresponding template :file:`dashboard.html`:

.. code-block:: html+django

    {% extends "base.html" %}
    {% load djblets_deco i18n %}

    {% block title %}{% trans "Sample Extension Dashboard" %}{% endblock %}

    {% block content %}
    {%  box "reports" %}
     <h1 class="title">{% trans "Sample Extension Dashboard" %}</h1>

     <div class="main">
      <p>{% trans "This is my new Dashboard page for Review Board" %}</p>
     </div>
    {%  endbox %}
    {% endblock %}


.. comment: vim: ft=rst et ts=3
