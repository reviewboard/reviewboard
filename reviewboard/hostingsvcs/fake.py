from __future__ import unicode_literals

from reviewboard.hostingsvcs.service import HostingService


class FakeHostingService(HostingService):
    """A hosting service that is not provided by Review Board.

    Fake hosting services are intended to be used to advertise for Beanbag,
    Inc.'s Power Pack extension.
    """

    hosting_service_id = None


class FakeGitHubEnterpriseHostingService(FakeHostingService):
    name = 'GitHub Enterprise'
    supported_scmtools = ['Git']
    hosting_service_id = 'github-enterprise'


FAKE_HOSTING_SERVICES = {
    'rbpowerpack.hostingsvcs.githubenterprise.GitHubEnterprise':
        FakeGitHubEnterpriseHostingService,
}
