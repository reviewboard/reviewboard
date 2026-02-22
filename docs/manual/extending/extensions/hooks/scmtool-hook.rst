.. _scmtool-hook:

===========
SCMToolHook
===========

:py:class:`reviewboard.extensions.hooks.SCMToolHook` allows extensions to
register new SCMTools, which can be used to configure repositories.

Extensions must provide a subclass of
:py:class:`reviewboard.scmtools.core.SCMTool`, and pass it as a parameter to
:py:class:`SCMToolHook`. For examples of attributes and methods that an SCMTool
subclass can implement, refer to :py:class:`reviewboard.scmtools.core.SCMTool`.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import SCMToolHook
    from reviewboard.scmtools.core import SCMTool


    class SampleSCMTool(SCMTool):
        name = 'Sample SCMTool'
        scmtool_id = 'sample'


    class SampleExtension(Extension):
        def initialize(self):
            SCMToolHook(self, SampleSCMTool)
