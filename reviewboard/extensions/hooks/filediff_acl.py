"""A hook for checking ACLs on diff files."""

from __future__ import annotations

from djblets.extensions.hooks import ExtensionHook, ExtensionHookPoint


class FileDiffACLHook(ExtensionHook, metaclass=ExtensionHookPoint):
    """A hook for checking ACLs on diff files.

    Extensions can use this hook to connect repository ACLs into the Review
    Board access system. This is provided as an extension hook because
    systems may be deployed in various ways, and SCM usernames may not
    necessarily match Review Board usernames.

    Version Added:
        4.0.5:
        This is experimental in 4.0.x, with plans to make it stable for 5.0.
        The API may change during this time.
    """

    def is_accessible(self, diffset, user, **kwargs):
        """Return whether the given file is accessible by the given user.

        Args:
            diffset (reviewboard.diffviewer.models.DiffSet):
                The diffset containing the file.

            user (django.contrib.auth.models.User):
                The user to check.

            **kwargs (dict, unused):
                Additional keyword arguments for future expansion.

        Returns:
            bool:
            False if the user does not have access to the file. True if the
            user explicitly does have access. None if the extension did not
            check for this diffset or repository (so that other hook points can
            continue).
        """
        raise NotImplementedError
