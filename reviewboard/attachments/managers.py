"""Manager for FileAttachment objects."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Manager, Q

from reviewboard.diffviewer.commit_utils import exclude_ancestor_filediffs
from reviewboard.diffviewer.models import FileDiff

if TYPE_CHECKING:
    from reviewboard.attachments.models import FileAttachment


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

            review_request.file_attachments.add(attachment)

            # If there's a draft, we also need to add it there, otherwise it
            # will disappear as soon as the draft is published.
            draft = review_request.get_draft()

            if draft:
                draft.file_attachments.add(attachment)

        return attachment

    def filter_for_repository(self, repository):
        """Filter results for those on a given repository."""
        return self.filter(
            Q(repository=repository) |
            Q(added_in_filediff__diffset__repository=repository))

    def get_for_filediff(
        self,
        filediff: FileDiff,
        modified: bool = True,
    ) -> Optional[FileAttachment]:
        """Return the FileAttachment matching a FileDiff.

        The FileAttachment associated with the path, revision and repository
        matching the DiffSet will be returned, if it exists.

        It is up to the caller to check for errors.

        Args:
            filediff (reviewboard.diffviewer.models.FileDiff):
                The FileDiff to get the attachment for.

            modified (bool, optional):
                If ``True``, return the FileDiff corresponding to the modified
                revision. If ``False``, return the FileDiff corresponding to
                the original revision.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The attachment for the given FileDiff, if one exists.
        """
        if filediff.is_new:
            if not modified:
                return None

            try:
                return self.get(added_in_filediff=filediff)
            except ObjectDoesNotExist:
                pass

            # In the case of review requests created with commit history, we
            # can have multiple FileDiffs for the same file--one as part of the
            # commit, and one as part of the cumulative diff. If we're loading
            # the cumulative diff, we need to look up the attachment
            # corresponding with the latest commit.
            diffset = filediff.diffset

            if not diffset.commit_count:
                return None

            commit_filediffs = list(FileDiff.objects.filter(
                diffset_id=diffset.pk,
                commit__isnull=False,
                dest_file=filediff.dest_file))

            commit_filediffs = exclude_ancestor_filediffs(commit_filediffs)

            if len(commit_filediffs) == 1:
                return self.get(added_in_filediff=commit_filediffs[0])
        else:
            review_request = filediff.get_review_request()
            assert review_request is not None

            try:
                if modified:
                    return self.get(review_request=review_request,
                                    repo_path=filediff.dest_file,
                                    repo_revision=filediff.dest_detail,
                                    repository=filediff.get_repository())
                else:
                    return self.get(review_request=review_request,
                                    repo_path=filediff.source_file,
                                    repo_revision=filediff.source_revision,
                                    repository=filediff.get_repository())
            except ObjectDoesNotExist:
                pass

        return None
