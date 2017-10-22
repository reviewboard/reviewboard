.. _hosting-service-hook:

==================
HostingServiceHook
==================

:py:class:`reviewboard.extensions.hooks.HostingServiceHook` allows extensions to
register new hosting services, which can be used to configure repositories
and to make use of third party APIs to perform special operations not
otherwise usable by generic repositories.

Extensions must provide a subclass of
:py:class:`reviewboard.hostingsvcs.service.HostingService`, and pass it as a
parameter to :py:class:`HostingServiceHook`. For examples of attributes, and
methods that a HostingService subclass can make use of refer to
:py:class:`reviewboard.hostingsvcs.service.HostingService`.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import HostingServiceHook
    from reviewboard.hostingsvcs.service import HostingService


    class SampleHostingService(HostingService):
        name = 'Sample Hosting Service'


    class SampleExtension(Extension):
        def initialize(self):
            HostingServiceHook(self, SampleHostingService)
