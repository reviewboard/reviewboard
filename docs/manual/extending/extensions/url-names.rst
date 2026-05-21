.. _extension-url-names:

=====================
Pre-defined URL Names
=====================

Most URLs in Review Board have a name that can be referenced, making it easy
to link to the right pages in your extensions.

These are often used with:

* :py:func:`~reviewboard.site.urlresolvers.local_site_reverse`, which returns
  a URL for a name, values to plug into the URL, and an optional :term:`Local
  Site` or :py:class:`~django.http.HttpRequest`.

  (Despite the name, this is not specific to :term:`Local Sites`, and is
  recommended for URL resolution over :py:func:`django.urls.reverse`.)

* The :ttag:`{% url %} <django:url>` template tag.

* ``apply_to`` lists, used by several parts of our extension infrastructure,
  for applying customizations only to certain pages.

  For example, this can be used in:

  * :ref:`Static media bundles <extension-static-files>`
  * :ref:`JavaScript extensions <js-extensions>`
  * :ref:`TemplateHook <template-hook>`
  * :ref:`Actions <extension-actions>`

Some of the most common URL names you might want to use include:

.. list-table::

   * - ``dashboard``
     - The Dashboard page.

   * - ``file-attachment``
     - The file attachment review UI pages (note that this will apply to
       *all* types of file attachments with review UIs!).

   * - ``login``
     - The login page.

   * - ``register``
     - The user registration page.

   * - ``review-request-detail``
     - The review request page itself, where discussion is shown.

   * - ``root``
     - The root of the Review Board server.

   * - ``user-preferences``
     - The My Account page.

There are also lists of URL names that can be useful when applying something
(such as :ref:`static media <static-media-apply-to>`) to specific pages:

.. list-table::

   * - :py:data:`reviewboard.urls.all_review_request_url_names`
     - All pages for the review request and reviewable content (diffs
       and file attachments).

   * - :py:data:`reviewboard.urls.diffviewer_url_names`
     - All the diff viewer pages.

   * - :py:data:`reviewboard.urls.review_request_url_names`
     - All the review request and diff viewer pages.

   * - :py:data:`reviewboard.urls.reviewable_url_names`
     - All pages for reviewable content (diffs and file attachments),
       but not review requests (``review-request-detail``).

You can look at the :ref:`Review Board codebase reference
<reviewboard-coderef>` for all the URL names (they'll be listed in the
``*.urls`` modules).
