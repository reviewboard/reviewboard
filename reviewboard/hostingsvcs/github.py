import urllib2

from django import forms
from django.contrib.sites.models import Site
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.hostingsvcs.errors import AuthorizationError
from reviewboard.hostingsvcs.forms import HostingServiceForm
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.site.urlresolvers import local_site_reverse


class GitHubPublicForm(HostingServiceForm):
    github_public_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class GitHubPrivateForm(HostingServiceForm):
    github_private_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class GitHubPublicOrgForm(HostingServiceForm):
    github_public_org_name = forms.CharField(
        label=_('Organization name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))

    github_public_org_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class GitHubPrivateOrgForm(HostingServiceForm):
    github_private_org_name = forms.CharField(
        label=_('Organization name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))

    github_private_org_repo_name = forms.CharField(
        label=_('Repository name'),
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={'size': '60'}))


class GitHub(HostingService):
    name = _('GitHub')
    repository_plans = [
        ('public', {
            'name': _('Public'),
            'repository_form': GitHubPublicForm,
            'repository_fields': {
                'Git': {
                    'path': 'git://github.com/%(hosting_account_username)s/'
                            '%(github_public_repo_name)s.git',
                    'mirror_path': 'git@github.com:'
                                   '%(hosting_account_username)s/'
                                   '%(github_public_repo_name)s.git',
                }
            },
        }),
        ('public-org', {
            'name': _('Public Organization'),
            'repository_form': GitHubPublicOrgForm,
            'repository_fields': {
                'Git': {
                    'path': 'git://github.com/%(github_org_name)s/'
                            '%(github_public_org_repo_name)s.git',
                    'mirror_path': 'git@github.com:%(github_org_name)s/'
                                   '%(github_public_org_repo_name)s.git',
                }
            },
        }),
        ('private', {
            'name': _('Private'),
            'repository_form': GitHubPrivateForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@github.com:%(hosting_account_username)s/'
                            '%(github_private_repo_name)s.git',
                    'mirror_path': '',
                },
            },
        }),
        ('private-org', {
            'name': _('Private Organization'),
            'repository_form': GitHubPrivateOrgForm,
            'repository_fields': {
                'Git': {
                    'path': 'git@github.com:%(github_org_name)s/'
                            '%(github_private_org_repo_name)s.git',
                    'mirror_path': '',
                },
            },
        }),
    ]

    needs_authorization = True
    supported_scmtools = ['Git']

    API_URL = 'https://api.github.com/'
    RAW_MIMETYPE = 'application/vnd.github.v3.raw'

    def authorize(self, username, password, local_site_name=None,
                  *args, **kwargs):
        site = Site.objects.get_current()
        siteconfig = SiteConfiguration.objects.get_current()

        site_url = '%s://%s%s' % (
            siteconfig.get('site_domain_method'),
            site.domain,
            local_site_reverse('root', local_site_name=local_site_name))

        try:
            rsp = self._json_post(
                self.API_URL + 'authorizations',
                username=username,
                password=password,
                body=simplejson.dumps({
                    'scopes': [
                        'user',
                        'repo',
                    ],
                    'note': 'Access for Review Board',
                    'note_url': site_url,
                }))
        except (urllib2.HTTPError, urllib2.URLError), e:
            data = e.read()

            try:
                rsp = simplejson.loads(data)
            except:
                rsp = None

            if rsp and 'message' in rsp:
                raise AuthorizationError(rsp['message'])
            else:
                raise AuthorizationError(str(e))

        self.account.data['authorization'] = rsp
        self.account.save()

    def is_authorized(self):
        return ('authorization' in self.account.data and
                'token' in self.account.data['authorization'])

    def get_file(self, repository, path, revision, *args, **kwargs):
        url = '%sgit/blobs/%s' % (self._get_repo_api_url(repository), revision)

        try:
            return self._http_get(url, headers={
                'Accept': self.RAW_MIMETYPE,
            })
        except (urllib2.URLError, urllib2.HTTPError), e:
            raise FileNotFoundError(str(e))

    def get_file_exists(self, repository, path, revision, *args, **kwargs):
        url = '%sgit/blobs/%s' % (self._get_repo_api_url(repository), revision)

        try:
            self._http_get(url, headers={
                'Accept': self.RAW_MIMETYPE,
            })

            return True
        except (urllib2.URLError, urllib2.HTTPError), e:
            return False

    def _get_repo_api_url(self, repository):
        url = self.API_URL

        plan = repository.extra_data['repository_plan']

        if plan == 'public':
            repo_name = repository.extra_data['github_public_repo_name']
            owner = self.account.username
        elif plan == 'private':
            repo_name = repository.extra_data['github_private_repo_name']
            owner = self.account.username
        elif plan == 'public-org':
            repo_name = repository.extra_data['github_public_org_repo_name']
            owner = repository.extra_data['github_public_org_name']
        elif plan == 'private-org':
            repo_name = repository.extra_data['github_private_org_repo_name']
            owner = repository.extra_data['github_private_org_name']

        return '%srepos/%s/%s/' % (self.API_URL, owner, repo_name)
