.. _extension-class:

===============
Extension Class
===============

The main component of an extension is a class inheriting from
:py:class:`reviewboard.extensions.base.Extension`. It can optionally set
the following attributes on the class:

* :py:attr:`apps`
* :py:attr:`context_processors`
* :py:attr:`css_bundles`
* :py:attr:`default_settings`
* :py:attr:`has_admin_site`
* :py:attr:`is_configurable`
* :py:attr:`js_bundles`
* :py:attr:`js_extensions`
* :py:attr:`metadata`
* :py:attr:`middleware`
* :py:attr:`requirements`
* :py:attr:`resources`

The following are also available on an extension instance:

* :py:attr:`settings`


.. py:class:: reviewboard.extensions.base.Extension

   .. py:attribute:: apps

      A list of `Django apps`_ that the extension either provides or depends
      upon.

      Each "app" is a Python module path that Django will use when looking for
      models, template tags, and more.

      This does not need to include the app for the extension itself, but
      if the extension is grouped into separate Django apps, it can list
      those.

      This setting is equivalent to modifying ``settings.INSTALLED_APPS``
      in Django.

   .. py:attribute:: context_processors

      A list of `Django context processors`_, which inject variables into
      every rendered template. Certain third-party apps depend on context
      processors.

      This setting is equivalent to modifying
      ``settings.TEMPLATE_CONTEXT_PROCESSORS`` in Django.

   .. py:attribute:: css_bundles

      A list of custom CSS media bundles that can be used when rendering
      pages.

      See :ref:`extension-static-files` for more information.

   .. py:attribute:: default_settings

      A dictionary of default settings for the extension. These defaults
      are used when accessing :py:attr:`settings`, if the user hasn't
      provided a custom value. By default, this is empt.

      See :ref:`extension-settings-defaults` for more information.

   .. py:attribute:: has_admin_site

      A boolean that indicates whether a Django admin site should be generated
      for the extension.

      If ``True``, a :guilabel:`Database` link will be shown for the
      extension, allowing the user to inspect and modify the extension's
      database entries. The default is ``False``.

      See :ref:`extension-admin-site` for more information.

   .. py:attribute:: is_configurable

      A boolean indicating whether the extension supports global
      configuration by a system administrator.

      If ``True``, a :guilabel:`Configure` link will be shown for the
      extension when enabled, taking them to the configuration page provided
      by the extension. The default is ``False``.

      See :ref:`extension-configuration` for more information.

   .. py:attribute:: js_bundles

      A list of custom JavaScript media bundles that can be used when
      rendering pages.

      See :ref:`extension-static-files` for more information.

   .. py:attribute:: js_extensions

      A list of :py:class:`reviewboard.extensions.base.JSExtension`
      subclasses used for providing JavaScript-side extensions.

      See :ref:`js-extensions` for more information.

   .. py:attribute:: metadata

      A dictionary providing additional information on the extension,
      such as the name or a description.

      By default, the metadata from :file:`setup.py` is used when displaying
      information about the extension inside the administration UI. Extensions
      can override what the user sees by setting the values in this
      dictionary.

      The following metadata keys are supported:

      ``Name``
         The human-readable name of the extension, shown in the extension
         list.

      ``Version``
         The version of the extension. Usually, the version specified in
         :file:`setup.py` suffices.

      ``Summary``
         A brief summary of the extension, shown in the extension list.

      ``Description``
         A longer description of the extension. As of Review Board 2.0, this
         is not shown to the user, but it may be used in a future release.

      ``Author``
         The individual or company that authored the extension.

      ``Author-email``
         The contact e-mail address for the author of the extension.

      ``Author-home-page``
         The URL to the author's public site.

      ``Home-page``
         The URL to the extension's public site.

      We generally recommend setting ``Name``, ``Summary``, and the
      author information. ``Version`` is usually best left to the package,
      unless there's a special way it should be presented.

   .. py:attribute:: middleware

      A list of `Django middleware`_ classes, which hook into various levels
      of the HTTP request/response and page render process.

      This is an advanced feature, and is generally not needed by most
      extensions. Certain third-party apps may depend on middleware,
      though.

      This setting is equivalent to modifying
      ``settings.MIDDLEWARE_CLASSES`` in Django.

   .. py:attribute:: requirements

      A list of strings providing the names of other extensions the
      extension requires. Enabling the extension will in turn enable
      all required extensions, and can only be enabled if the required
      extensions can also be enabled.

      See :ref:`extension-egg-dependencies` for more information.

   .. py:attribute:: settings

      An instance of :py:class:`djblets.extensions.settings.Settings`. This
      attribute gives each extension an easy-to-use and persistent data store
      for settings.

      See :ref:`extension-settings` for more information.

   .. py:attribute:: resources

      A list of :py:class:`reviewboard.webapi.resources.WebAPIResource`
      subclasses. This is used to extend the Web API.

      See :ref:`extension-resources` for more information.


.. _`Django apps`: https://docs.djangoproject.com/en/dev/intro/reusable-apps/
.. _`Django context processors`:
   https://docs.djangoproject.com/en/dev/ref/templates/api/#subclassing-context-requestcontext
.. _`Django middleware`:
   https://docs.djangoproject.com/en/dev/topics/http/middleware/
