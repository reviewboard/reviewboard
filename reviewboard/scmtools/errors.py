from django.utils.translation import ugettext as _


class SCMError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class ChangeSetError(SCMError):
    pass


class InvalidChangeNumberError(ChangeSetError):
    def __init__(self):
        ChangeSetError.__init__(self, None)


class ChangeNumberInUseError(ChangeSetError):
    def __init__(self, review_request=None):
        ChangeSetError.__init__(self, None)
        self.review_request = review_request


class EmptyChangeSetError(ChangeSetError):
    def __init__(self, changenum):
        ChangeSetError.__init__(self, _('Changeset %s is empty') % changenum)


class FileNotFoundError(SCMError):
    def __init__(self, path, revision=None, detail=None):
        from reviewboard.scmtools.core import HEAD

        if revision == None or revision == HEAD:
            msg = "The file '%s' could not be found in the repository" % path
        else:
            msg = "The file '%s' (r%s) could not be found in the repository" \
                % (path, revision)
        if detail:
            msg += ': ' + detail
        Exception.__init__(self, msg)

        self.revision = revision
        self.path = path
        self.detail = detail
