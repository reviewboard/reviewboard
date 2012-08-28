from django.test import TestCase
from django.utils import simplejson

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.scmtools.models import Repository


class ServiceTests(TestCase):
    service_name = None

    def __init__(self, *args, **kwargs):
        super(ServiceTests, self).__init__(*args, **kwargs)

        self.assertNotEqual(self.service_name, None)
        self.service_class = get_hosting_service(self.service_name)

    def setUp(self):
        self.assertNotEqual(self.service_class, None)
        self._old_http_post = self.service_class._http_post
        self._old_http_get = self.service_class._http_get

    def tearDown(self):
        self.service_class._http_post = self._old_http_post
        self.service_class._http_get = self._old_http_get

    def _get_repository_info(self, field, plan=None):
        if plan:
            self.assertNotEqual(self.service_class.plans, None)
            result = None

            for plan_type, info in self.service_class.plans:
                if plan_type == plan:
                    result = info[field]
                    break

            self.assertNotEqual(result, None)
            return result
        else:
            self.assertEqual(self.service_class.plans, None)
            self.assertTrue(hasattr(self.service_class, field))

            return getattr(self.service_class, field)

    def _get_form(self, plan=None, fields={}):
        form = self._get_repository_info('form', plan)
        self.assertNotEqual(form, None)

        form = form(fields)
        self.assertTrue(form.is_valid())

        return form

    def _get_hosting_account(self):
        return HostingServiceAccount(service_name=self.service_name,
                                     username='myuser')

    def _get_repository_fields(self, tool_name, fields, plan=None):
        form = self._get_form(plan, fields)
        account = self._get_hosting_account()
        service = account.service
        self.assertNotEqual(service, None)

        return service.get_repository_fields(account.username, plan,
                                             tool_name, form.clean())


class BitbucketTests(ServiceTests):
    """Unit tests for the Bitbucket hosting service."""
    service_name = 'bitbucket'
    fixtures = ['test_scmtools.json']

    def test_service_support(self):
        """Testing the Bitbucket service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values(self):
        """Testing the Bitbucket repository field values"""
        fields = self._get_repository_fields('Mercurial', fields={
            'bitbucket_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'http://bitbucket.org/myuser/myrepo/')
        self.assertEqual(fields['mirror_path'],
                         'ssh://hg@bitbucket.org/myuser/myrepo/')

    def test_bug_tracker_field(self):
        """Testing the Bitbucket bug tracker field value"""
        self.assertTrue(self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'bitbucket_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://bitbucket.org/myuser/myrepo/issue/%s/')


class BugzillaTests(ServiceTests):
    """Unit tests for the Bugzilla hosting service."""
    service_name = 'bugzilla'
    fixtures = ['test_scmtools.json']

    def test_service_support(self):
        """Testing the Bugzilla service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self):
        """Testing the Bugzilla bug tracker field value"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'bugzilla_url': 'http://bugzilla.example.com',
            }),
            'http://bugzilla.example.com/show_bug.cgi?id=%s')


class CodebaseHQTests(ServiceTests):
    """Unit tests for the Codebase HQ hosting service."""
    service_name = 'codebasehq'

    def test_service_support(self):
        """Testing the Codebase HQ service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values(self):
        """Testing the Codebase HQ repository field values"""
        fields = self._get_repository_fields('Git', fields={
            'codebasehq_project_name': 'myproj',
            'codebasehq_group_name': 'mygroup',
            'codebasehq_repo_name': 'myrepo',
            'codebasehq_api_username': 'myapiuser',
            'codebasehq_api_key': 'myapikey',
        })
        self.assertEqual(fields['username'], 'myapiuser')
        self.assertEqual(fields['password'], 'myapikey')
        self.assertEqual(fields['path'],
                        'git@codebasehq.com:mygroup/myproj/myrepo.git')
        self.assertEqual(fields['raw_file_url'],
                         'https://api3.codebasehq.com/myproj/myrepo/blob/'
                         '<revision>')


class FedoraHosted(ServiceTests):
    """Unit tests for the Fedora Hosted hosting service."""
    service_name = 'fedorahosted'

    def test_service_support(self):
        """Testing the Fedora Hosted service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_git(self):
        """Testing the Fedora Hosted repository field values for Git"""
        fields = self._get_repository_fields('Git', fields={
            'fedorahosted_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                        'git://git.fedorahosted.org/git/myrepo.git')
        self.assertEqual(fields['raw_file_url'],
                         'http://git.fedorahosted.org/cgit/myrepo.git/'
                         'tree/<filename>?id2=<revision>')

    def test_repo_field_values_mercurial(self):
        """Testing the Fedora Hosted repository field values for Mercurial"""
        fields = self._get_repository_fields('Mercurial', fields={
            'fedorahosted_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                        'http://hg.fedorahosted.org/hg/myrepo/')
        self.assertEqual(fields['mirror_path'],
                        'https://hg.fedorahosted.org/hg/myrepo/')

    def test_repo_field_values_svn(self):
        """Testing the Fedora Hosted repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'fedorahosted_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                        'http://svn.fedorahosted.org/svn/myrepo/')
        self.assertEqual(fields['mirror_path'],
                        'https://svn.fedorahosted.org/svn/myrepo/')

    def test_bug_tracker_field(self):
        """Testing the Fedora Hosted bug tracker field value"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'fedorahosted_repo_name': 'myrepo',
            }),
            'https://fedorahosted.org/myrepo/ticket/%s')


class GitHubTests(ServiceTests):
    """Unit tests for the GitHub hosting service."""
    service_name = 'github'

    def test_service_support(self):
        """Testing the GitHub service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_public_field_values(self):
        """Testing the GitHub public plan repository field values"""
        fields = self._get_repository_fields('Git', plan='public', fields={
            'github_public_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'git://github.com/myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'git@github.com:myuser/myrepo.git')

    def test_public_repo_api_url(self):
        """Testing the GitHub public repository API URL"""
        url = self._get_repo_api_url('public', {
            'github_public_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myuser/testrepo/')

    def test_public_bug_tracker_field(self):
        """Testing the GitHub public repository bug tracker field value"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('public'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('public', {
                'github_public_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://github.com/myuser/myrepo/issues#issue/%s')

    def test_public_org_field_values(self):
        """Testing the GitHub public-org plan repository field values"""
        fields = self._get_repository_fields('Git', plan='public-org', fields={
            'github_public_org_repo_name': 'myrepo',
            'github_public_org_name': 'myorg',
        })
        self.assertEqual(fields['path'], 'git://github.com/myorg/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'git@github.com:myorg/myrepo.git')

    def test_public_org_repo_api_url(self):
        """Testing the GitHub public-org repository API URL"""
        url = self._get_repo_api_url('public-org', {
            'github_public_org_name': 'myorg',
            'github_public_org_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myorg/testrepo/')

    def test_public_org_bug_tracker_field(self):
        """Testing the GitHub public-org repository bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username('public-org'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('public-org', {
                'github_public_org_name': 'myorg',
                'github_public_org_repo_name': 'myrepo',
            }),
            'http://github.com/myorg/myrepo/issues#issue/%s')

    def test_private_field_values(self):
        """Testing the GitHub private plan repository field values"""
        fields = self._get_repository_fields('Git', plan='private', fields={
            'github_private_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'], 'git@github.com:myuser/myrepo.git')
        self.assertEqual(fields['mirror_path'], '')

    def test_private_repo_api_url(self):
        """Testing the GitHub private repository API URL"""
        url = self._get_repo_api_url('private', {
            'github_private_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myuser/testrepo/')

    def test_private_bug_tracker_field(self):
        """Testing the GitHub private repository bug tracker field value"""
        self.assertTrue(
            self.service_class.get_bug_tracker_requires_username('private'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('private', {
                'github_private_repo_name': 'myrepo',
                'hosting_account_username': 'myuser',
            }),
            'http://github.com/myuser/myrepo/issues#issue/%s')

    def test_private_org_field_values(self):
        """Testing the GitHub private-org plan repository field values"""
        fields = self._get_repository_fields('Git', plan='private-org', fields={
            'github_private_org_repo_name': 'myrepo',
            'github_private_org_name': 'myorg',
        })
        self.assertEqual(fields['path'], 'git@github.com:myorg/myrepo.git')
        self.assertEqual(fields['mirror_path'], '')

    def test_private_org_repo_api_url(self):
        """Testing the GitHub private-org repository API URL"""
        url = self._get_repo_api_url('private-org', {
            'github_private_org_name': 'myorg',
            'github_private_org_repo_name': 'testrepo',
        })
        self.assertEqual(url, 'https://api.github.com/repos/myorg/testrepo/')

    def test_private_org_bug_tracker_field(self):
        """Testing the GitHub private-org repository bug tracker field value"""
        self.assertFalse(
            self.service_class.get_bug_tracker_requires_username('private-org'))
        self.assertEqual(
            self.service_class.get_bug_tracker_field('private-org', {
                'github_private_org_name': 'myorg',
                'github_private_org_repo_name': 'myrepo',
            }),
            'http://github.com/myorg/myrepo/issues#issue/%s')

    def test_authorization(self):
        """Testing that GitHub account authorization sends expected data"""
        http_post_data = {}

        def _http_post(self, *args, **kwargs):
            http_post_data['args'] = args
            http_post_data['kwargs'] = kwargs

            return simplejson.dumps({
                'id': 1,
                'url': 'https://api.github.com/authorizations/1',
                'scopes': ['user', 'repo'],
                'token': 'abc123',
                'note': '',
                'note_url': '',
                'updated_at': '2012-05-04T03:30:00Z',
                'created_at': '2012-05-04T03:30:00Z',
            }), {}

        self.service_class._http_post = _http_post

        account = HostingServiceAccount(service_name=self.service_name,
                                        username='myuser')
        service = account.service
        self.assertFalse(account.is_authorized)

        service.authorize('myuser', 'mypass')
        self.assertTrue(account.is_authorized)

        self.assertEqual(http_post_data['kwargs']['url'],
                         'https://api.github.com/authorizations')
        self.assertEqual(http_post_data['kwargs']['username'], 'myuser')
        self.assertEqual(http_post_data['kwargs']['password'], 'mypass')

    def _get_repo_api_url(self, plan, fields):
        account = self._get_hosting_account()
        service = account.service
        self.assertNotEqual(service, None)

        repository = Repository(hosting_account=account)
        repository.extra_data['repository_plan'] = plan

        form = self._get_form(plan, fields)
        form.save(repository)

        return service._get_repo_api_url(repository)


class GitoriousTests(ServiceTests):
    """Unit tests for the Gitorious hosting service."""
    service_name = 'gitorious'

    def test_service_support(self):
        """Testing the Gitorious service support capabilities"""
        self.assertFalse(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values(self):
        """Testing the Gitorious repository field values"""
        fields = self._get_repository_fields('Git', fields={
            'gitorious_project_name': 'myproj',
            'gitorious_repo_name': 'myrepo',
        })
        self.assertEqual(fields['path'],
                         'git://gitorious.org/myproj/myrepo.git')
        self.assertEqual(fields['mirror_path'],
                         'http://git.gitorious.org/myproj/myrepo.git')
        self.assertEqual(fields['raw_file_url'],
                         'http://git.gitorious.org/myproj/myrepo/blobs/raw/'
                         '<revision>')


class GoogleCodeTests(ServiceTests):
    """Unit tests for the Google Code hosting service."""
    service_name = 'googlecode'

    def test_service_support(self):
        """Testing the Google Code service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_mercurial(self):
        """Testing the Google Code repository field values for Mercurial"""
        fields = self._get_repository_fields('Mercurial', fields={
            'googlecode_project_name': 'myproj',
        })
        self.assertEqual(fields['path'], 'http://myproj.googlecode.com/hg')
        self.assertEqual(fields['mirror_path'],
                         'https://myproj.googlecode.com/hg')

    def test_repo_field_values_svn(self):
        """Testing the Google Code repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'googlecode_project_name': 'myproj',
        })
        self.assertEqual(fields['path'], 'http://myproj.googlecode.com/svn')
        self.assertEqual(fields['mirror_path'],
                         'https://myproj.googlecode.com/svn')


class RedmineTests(ServiceTests):
    """Unit tests for the Redmine hosting service."""
    service_name = 'redmine'
    fixtures = ['test_scmtools.json']

    def test_service_support(self):
        """Testing the Redmine service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self):
        """Testing the Redmine bug tracker field value"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'redmine_url': 'http://redmine.example.com',
            }),
            'http://redmine.example.com/issues/%s')


class SourceForgeTests(ServiceTests):
    """Unit tests for the SourceForge hosting service."""
    service_name = 'sourceforge'

    def test_service_support(self):
        """Testing the SourceForge service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertTrue(self.service_class.supports_repositories)

    def test_repo_field_values_bazaar(self):
        """Testing the SourceForge repository field values for Bazaar"""
        fields = self._get_repository_fields('Bazaar', fields={
            'sourceforge_project_name': 'myproj',
        })
        self.assertEqual(fields['path'],
                         'bzr://myproj.bzr.sourceforge.net/bzrroot/myproj')
        self.assertEqual(fields['mirror_path'],
                         'bzr+ssh://myproj.bzr.sourceforge.net/bzrroot/'
                         'myproj')

    def test_repo_field_values_cvs(self):
        """Testing the SourceForge repository field values for CVS"""
        fields = self._get_repository_fields('CVS', fields={
            'sourceforge_project_name': 'myproj',
        })
        self.assertEqual(fields['path'],
                         ':pserver:anonymous@myproj.cvs.sourceforge.net:'
                         '/cvsroot/myproj')
        self.assertEqual(fields['mirror_path'],
                         'myproj.cvs.sourceforge.net/cvsroot/myproj')

    def test_repo_field_values_mercurial(self):
        """Testing the SourceForge repository field values for Mercurial"""
        fields = self._get_repository_fields('Mercurial', fields={
            'sourceforge_project_name': 'myproj',
        })
        self.assertEqual(fields['path'],
                         'http://myproj.hg.sourceforge.net:8000/hgroot/myproj')
        self.assertEqual(fields['mirror_path'],
                         'ssh://myproj.hg.sourceforge.net/hgroot/myproj')

    def test_repo_field_values_svn(self):
        """Testing the SourceForge repository field values for Subversion"""
        fields = self._get_repository_fields('Subversion', fields={
            'sourceforge_project_name': 'myproj',
        })
        self.assertEqual(fields['path'],
                         'http://myproj.svn.sourceforge.net/svnroot/myproj')
        self.assertEqual(fields['mirror_path'],
                         'https://myproj.svn.sourceforge.net/svnroot/myproj')


class TracTests(ServiceTests):
    """Unit tests for the Trac hosting service."""
    service_name = 'trac'
    fixtures = ['test_scmtools.json']

    def test_service_support(self):
        """Testing the Trac service support capabilities"""
        self.assertTrue(self.service_class.supports_bug_trackers)
        self.assertFalse(self.service_class.supports_repositories)

    def test_bug_tracker_field(self):
        """Testing the Trac bug tracker field value"""
        self.assertFalse(self.service_class.get_bug_tracker_requires_username())
        self.assertEqual(
            self.service_class.get_bug_tracker_field(None, {
                'trac_url': 'http://trac.example.com',
            }),
            'http://trac.example.com/ticket/%s')
