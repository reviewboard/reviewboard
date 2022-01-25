.. _filediff-acl-hook:

===============
FileDiffACLHook
===============

.. versionadded:: 4.0.5

.. admonition:: This feature is experimental.

   To use your hook, you will need to enable this feature for your server.
   You can set this in your :file:`conf/settings_local.py` file:

   .. code-block:: python

      ENABLED_FEATURES = {
          'reviews.diff_acls': True,
      }

   This feature will be enabled by default in Review Board 5.0.

:py:class:`reviewboard.extensions.hooks.FileDiffACLHook` allows extensions to
implement access controls for files in repositories. This is provided as an
extension hook due to the wide variety of ways in which Review Board can be
deployed (for example, it's not uncommon for repository usernames to be
different from Review Board usernames, especially when hosting services are
involved).

This is done by subclassing the
:py:class:`~reviewboard.extensions.hooks.FileDiffACLHook` and implementing the
:py:meth:`~reviewboard.extensions.hooks.FileDiffACLHook.is_accessible` method.
This method will be called for each
:py:class:`~reviewboard.diffviewer.models.DiffSet`. The implementation of the
hook should check access for each of the files in the diffset.

The hook is expected to return:

* ``True`` if the user does have access to all the files.
* ``False`` if the user does not have access to one or more files.
* ``None`` if the hook did not check the diff (for example, it might only check
  a single SCM or hosting service type, and ignore any others)

If any hook returns ``False``, the user will not have access to the diff.


Example
=======

.. code-block:: python

    import logging

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import FileDiffACLHook


    logger = logging.getLogger(__file__)


    class PerforceACLHook(FileDiffACLHook):
        """Hook for checking access for Perforce repositories."""

        def is_accessible(self, diffset, user, **kwargs):
            tool = diffset.repository.get_scmtool()

            # Allow normal access controls for non-Perforce repositories.
            if tool.scmtool_id != 'perforce':
                return None

            client = tool.client

            with client.run_worker():
                for filediff in diffset.files.all():
                    try:
                        # This assumes that the Perforce username matches the
                        # Review Board username.
                        protects = client.p4.run_protects(
                            '-M', '-u', user.username, filediff.source_file)[0]

                        if protects['permMax'] not in ('read', 'open', 'write',
                                                       'admin', 'super',
                                                       'owner'):
                            return False
                    except Exception as e:
                        logger.warning('Failed to get p4 protects information for '
                                       'file %s on server %s for user %s: %s',
                                       filediff.source_file, diffset.repository.name,
                                       user.username, e, exc_info=True)

            return True


    class SampleExtension(Extension):
        def initialize(self):
            PerforceACLHook(extension=self)
