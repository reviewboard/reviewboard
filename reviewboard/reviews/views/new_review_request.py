"""View for the New Review Request page."""

import logging
from typing import Any, Dict

from django.views.generic.base import TemplateView

from reviewboard.accounts.mixins import (LoginRequiredViewMixin,
                                         UserProfileRequiredViewMixin)
from reviewboard.admin.mixins import CheckReadOnlyViewMixin
from reviewboard.scmtools.models import Repository
from reviewboard.site.mixins import CheckLocalSiteAccessViewMixin


logger = logging.getLogger(__name__)


class NewReviewRequestView(LoginRequiredViewMixin,
                           CheckLocalSiteAccessViewMixin,
                           UserProfileRequiredViewMixin,
                           CheckReadOnlyViewMixin,
                           TemplateView):
    """View for the New Review Request page.

    This provides the user with a UI consisting of all their repositories,
    allowing them to manually upload a diff against the repository or,
    depending on the repository's capabilities, to browse for an existing
    commit to post.
    """

    template_name = 'reviews/new_review_request.html'

    def get_context_data(
        self,
        **kwargs,
    ) -> Dict[str, Any]:
        """Return data for the template.

        This will return information on each repository shown on the page.

        Args:
            **kwargs (dict):
                Additional keyword arguments passed to the view.

        Returns:
            dict:
            Context data for the template.
        """
        local_site = self.local_site

        if local_site:
            local_site_prefix = 's/%s/' % local_site.name
        else:
            local_site_prefix = ''

        valid_repos = []

        repos = Repository.objects.accessible(self.request.user,
                                              local_site=local_site)

        for repo in repos.order_by('name')[:25]:
            try:
                valid_repos.append({
                    'id': repo.pk,
                    'name': repo.name,
                    'scmtoolName': repo.scmtool_class.name,
                    'localSitePrefix': local_site_prefix,
                    'supportsPostCommit': repo.supports_post_commit,
                    'requiresChangeNumber': repo.supports_pending_changesets,
                    'requiresBasedir': not repo.diffs_use_absolute_paths,
                    'filesOnly': False,
                })
            except Exception:
                logger.exception(
                    'Error loading information for repository "%s" (ID %d) '
                    'for the New Review Request page.',
                    repo.name, repo.pk)

        return {
            'page_model_attrs': {
                'repositories': valid_repos,
                'localSitePrefix': local_site_prefix,
            }
        }
