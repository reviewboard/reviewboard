.. _webapi-capabilities-hook:

======================
WebAPICapabilitiesHook
======================

.. versionadded:: 2.5

:py:class:`reviewboard.extensions.hooks.WebAPICapabilitiesHook` allows
extensions to register new capabilities with the web API.

Extensions must provide a :py:attr:`caps` dictionary, and pass it as a
parameter to :py:class:`WebAPICapabilitiesHook`. The API capabilities payload
will contain a new key matching the extension ID, with the provided
capabilities as the value.

Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import WebAPICapabilitiesHook


    class SampleExtension(Extension):
        def initialize(self):
            WebAPICapabilitiesHook(
                self,
                {
                    'commit_ids': True,
                    'tested': True,
                })

The resulting payload would like this:

.. code-block:: javascript

    "capabilities": {
        ...

        "SampleExtensionID": {
            "commit_ids": True,
            "tested": True
        }
    }
