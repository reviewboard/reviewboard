from __future__ import unicode_literals

from django.db.models import Manager, Q


class FileAttachmentManager(Manager):
    """Manages FileAttachment objects.

    Adds utility functions for looking up FileAttachments based on other
    objects.
    """

    def create_from_filediff(self, filediff, from_modified=True, save=True,
                             **kwargs):
        """Create a new FileAttachment for a FileDiff.

        FileAttachments created from a FileDiff are used to represent changes
        to binary files which would otherwise not be displayed with the diff.

        An individual FileAttachment can represent either the original or
        modified copy of the file. If 'from_modified' is True, then the
        FileAttachment will be created using the information (filename,
        revision, etc.) for the modified version. If it is False, the
        FileAttachment will be created using the information for the original
        version.
        """
        if filediff.is_new:
            assert from_modified

            attachment = self.model(added_in_filediff=filediff, **kwargs)
        elif from_modified:
            attachment = self.model(repo_path=filediff.dest_file,
                                    repo_revision=filediff.dest_detail,
                                    repository=filediff.diffset.repository,
                                    **kwargs)
        else:
            attachment = self.model(repo_path=filediff.source_file,
                                    repo_revision=filediff.source_revision,
                                    repository=filediff.diffset.repository,
                                    **kwargs)

        if save:
            attachment.save()

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
                            repository=filediff.diffset.repository)
        else:
            return self.get(repo_path=filediff.source_file,
                            repo_revision=filediff.source_revision,
                            repository=filediff.diffset.repository)
