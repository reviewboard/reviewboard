from __future__ import unicode_literals


class RemoteRepository(object):
    """A representation of a remote repository.

    This is used to represent the configuration for a repository that already
    exists on the hosting service. It does not necessarily match a repository
    configured on Review Board, but can be used to create one.
    """
    def __init__(self, hosting_service, repository_id, name, owner,
                 scm_type, path, mirror_path=None, extra_data={}):
        self.hosting_service = hosting_service
        self.hosting_service_account = hosting_service.account
        self.id = repository_id
        self.name = name
        self.owner = owner
        self.scm_type = scm_type
        self.path = path
        self.mirror_path = mirror_path
        self.extra_data = extra_data

    def __repr__(self):
        return ('<RemoteRepository: "%s" (owner=%s, scm_type=%s)>'
                % (self.name, self.owner, self.scm_type))
