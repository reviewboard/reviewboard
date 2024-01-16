"""Manager for FileAttachment objects."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Manager, Q

if TYPE_CHECKING:
    from reviewboard.attachments.models import FileAttachment
    from reviewboard.diffviewer.models import FileDiff


class FileAttachmentManager(Manager):
    """Manages FileAttachment objects.

    Adds utility functions for looking up FileAttachments based on other
    objects.
    """

    def create_from_filediff(
        self,
        filediff: FileDiff,
        from_modified: bool = True,
        save: bool = True,
        **kwargs,
    ) -> FileAttachment:
        """Create a new FileAttachment for a FileDiff.

        FileAttachments created from a FileDiff are used to represent changes
        to binary files which would otherwise not be displayed with the diff.

        An individual FileAttachment can represent either the original or
        modified copy of the file. If 'from_modified' is True, then the
        FileAttachment will be created using the information (filename,
        revision, etc.) for the modified version. If it is False, the
        FileAttachment will be created using the information for the original
        version.

        Args:
            filediff (reviewboard.diffviewer.models.filediff.FileDiff):
                The FileDiff to create the attachment for.

            from_modified (bool, optional):
                Whether to create an attachment for the modified version of the
                file.

            save (bool, optional):
                Whether to save the new object before returning.

            **kwargs (dict):
                Additional keyword arguments to pass through to the
                FileAttachment model.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The newly-created file attachment.
        """
        review_request = filediff.get_review_request()
        assert review_request is not None

        local_site = review_request.local_site

        if filediff.is_new:
            assert from_modified

            attachment = self.model(
                local_site=local_site,
                added_in_filediff=filediff,
                **kwargs)
        elif from_modified:
            attachment = self.model(
                local_site=local_site,
                repo_path=filediff.dest_file,
                repo_revision=filediff.dest_detail,
                repository=filediff.get_repository(),
                **kwargs)
        else:
            attachment = self.model(
                local_site=local_site,
                repo_path=filediff.source_file,
                repo_revision=filediff.source_revision,
                repository=filediff.get_repository(),
                **kwargs)

        if save:
            attachment.save()
            attachment.review_request.add(review_request)

        return attachment

    def filter_for_repository(self, repository):
        """Filter results for those on a given repository."""
        return self.filter(
            Q(repository=repository) |
            Q(added_in_filediff__diffset__repository=repository))

    def get_for_filediff(self, filediff, modified=True):
        """Return the FileAttachment matching a DiffSet.

        The FileAttachment associated with the path, revision and repository
        matching the DiffSet will be returned, if it exists.

        It is up to the caller to check for errors.
        """
        if filediff.is_new:
            if modified:
                return self.get(added_in_filediff=filediff)
            else:
                return None
        elif modified:
            return self.get(repo_path=filediff.dest_file,
                            repo_revision=filediff.dest_detail,
                            repository=filediff.get_repository())
        else:
            return self.get(repo_path=filediff.source_file,
                            repo_revision=filediff.source_revision,
                            repository=filediff.get_repository())
