from reviewboard.hostingsvcs.base.hosting_service import BaseHostingService


class FakeHostingService(BaseHostingService):
    """A hosting service that is not provided by Review Board.

    Fake hosting services are intended to be used to advertise for Beanbag,
    Inc.'s Power Pack extension.
    """

    hosting_service_id = None


class FakeAWSCodeCommitHostingService(FakeHostingService):
    name = 'AWS CodeCommit'
    supported_scmtools = ['Git']
    hosting_service_id = 'aws-codecommit'


class FakeBitbucketServerHostingService(FakeHostingService):
    name = 'Bitbucket Server'
    supported_scmtools = ['Git']
    hosting_service_id = 'bitbucket-server'


class FakeGitHubEnterpriseHostingService(FakeHostingService):
    name = 'GitHub Enterprise'
    supported_scmtools = ['Git']
    hosting_service_id = 'github-enterprise'


class FakeVisualStudioTeamServicesHostingService(FakeHostingService):
    name = 'VisualStudio.com'
    supported_scmtools = [
        'Team Foundation Server',
        'Team Foundation Server (git)',
    ]
    hosting_service_id = 'visual-studio-online'


FAKE_HOSTING_SERVICES = {
    'aws-codecommit': FakeAWSCodeCommitHostingService,
    'bitbucket-server': FakeBitbucketServerHostingService,
    'github-enterprise': FakeGitHubEnterpriseHostingService,
    'visual-studio-online': FakeVisualStudioTeamServicesHostingService,
}
