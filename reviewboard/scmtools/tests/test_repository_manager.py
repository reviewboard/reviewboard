"""Unit tests for reviewboard.scmtools.manager.RepositoryManager."""

from __future__ import annotations

from itertools import chain
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING, Tuple, Union

from django.contrib.auth.models import AnonymousUser, User
from djblets.testing.decorators import add_fixtures

from reviewboard.scmtools.models import Repository
from reviewboard.scmtools.testing.queries import (
    get_repositories_accessible_equeries,
    get_repositories_accessible_ids_equeries)
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from djblets.util.typing import KwargsDict

    from reviewboard.site.models import AnyOrAllLocalSites

    _MixinParent = TestCase
else:
    _MixinParent = object


class AccessibleTestsMixin(_MixinParent):
    """Mixins for repository accessibility unit tests.

    Version Added:
        5.0.7
    """

    def _create_accessible_repository_data(
        self,
        *,
        user: Union[AnonymousUser, User],
        with_local_sites: bool = False,
        with_member: bool = False,
        with_member_by_group: bool = False,
        group_kwargs: KwargsDict = {},
    ) -> Tuple[Sequence[Repository], Optional[LocalSite]]:
        """Create test repository data for accessibility checks.

        This will create repositories on the global site and, optionally,
        two Local Sites. The provided user may optionally be granted membership
        directly or via group.

        Args:
            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to associate with any membership lists.

            with_local_sites (bool, optional):
                Whether to create Local Sites.

            with_member (bool, optional):
                Whether to make the user a member of the repository.

            with_member_by_group (bool, optional):
                Whether to make the user a member of the repository via a
                review group.

            group_kwargs (dict, optional):
                Additional keyword arguments to pass to review group
                construction.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (list of reviewboard.scmtools.models.Repository):
                    The list of created repositories, in order.

                1 (reviewboard.site.models.LocalSite):
                    The first Local Site created, or ``None`` if not creating
                    Local Sites.
        """
        repositories_by_site: Dict[Optional[LocalSite], List[Repository]] = {}
        local_sites: List[Optional[LocalSite]] = []
        local_site_kwargs: KwargsDict = {}
        repository_i = 1

        if user.is_authenticated:
            # Satisfy the type checker.
            assert isinstance(user, User)

            local_site_kwargs['users'] = [user]

            if with_member_by_group:
                group_kwargs['users'] = [user]

        if with_local_sites:
            # Create the Local Sites
            local_sites += [
                self.create_local_site(name='test-site-1',
                                       **local_site_kwargs),
                self.create_local_site(name='test-site-2',
                                       **local_site_kwargs),
            ]

        # Add the global site last.
        local_sites.append(None)

        for local_site in local_sites:
            repositories_by_site[local_site] = [
                self.create_repository(local_site=local_site,
                                       name=f'repo{repository_i}',
                                       public=True,
                                       visible=True),
                self.create_repository(local_site=local_site,
                                       name=f'repo{repository_i + 1}',
                                       public=True,
                                       visible=False),
                self.create_repository(local_site=local_site,
                                       name=f'repo{repository_i + 2}',
                                       public=False,
                                       visible=True),
                self.create_repository(local_site=local_site,
                                       name=f'repo{repository_i + 3}',
                                       public=False,
                                       visible=False),
            ]
            repository_i += 4

        if with_member and user.is_authenticated:
            # Satisfy the type checker.
            assert isinstance(user, User)

            for local_site in local_sites:
                user.repositories.add(*repositories_by_site[local_site])

        if with_member_by_group:
            for local_site in local_sites:
                group = self.create_review_group(local_site=local_site,
                                                 **group_kwargs)
                group.repositories.add(*repositories_by_site[local_site])

        return (
            list(chain.from_iterable(repositories_by_site.values())),
            local_sites[0],
        )


class AccessibleTests(AccessibleTestsMixin, TestCase):
    """Unit tests for RepositoryManager.accessible()."""

    fixtures = ['test_scmtools', 'test_users']

    #
    # Anonymous tests
    #

    def test_with_anonymous(self) -> None:
        """Testing Repository.objects.accessible with anonymous and
        visible_only=False
        """
        user = AnonymousUser()
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible(
            repositories=[
                repositories[0],
                repositories[1],
            ],
            user=user,
            visible_only=False)

    def test_with_anonymous_visible_only(self) -> None:
        """Testing Repository.objects.accessible with anonymous and
        visible_only=True
        """
        user = AnonymousUser()
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible(
            repositories=[repositories[0]],
            user=user,
            visible_only=True)

    #
    # Superuser tests
    #

    def test_with_superuser(self) -> None:
        """Testing Repository.objects.accessible with superuser and
        visible_only=False
        """
        user = self.create_user(is_superuser=True)
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible(
            repositories=repositories,
            user=user,
            visible_only=False)

    def test_with_superuser_visible_only(self) -> None:
        """Testing Repository.objects.accessible with superuser and
        visible_only=True
        """
        user = self.create_user(is_superuser=True)
        repositories = self._create_accessible_repository_data(user=user)[0]

        # Note that, unlike with standard members, superusers won't see
        # hidden repositories in this case. This is a legacy
        # piece of logic in Group.objects.accessible().
        self._test_accessible(
            repositories=[
                repositories[0],
                repositories[2],
            ],
            user=user,
            visible_only=True)

    def test_with_superuser_local_site(self) -> None:
        """Testing Repository.objects.accessible with superuser,
        Local Site, and visible_only=False
        """
        user = self.create_user(is_superuser=True)
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    def test_with_superuser_local_site_visible_only(self) -> None:
        """Testing Repository.objects.accessible with superuser and
        visible_only=True
        """
        user = self.create_user(is_superuser=True)
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        # Note that, unlike with standard members, superusers won't see
        # hidden repositories in this case. This is a legacy
        # piece of logic in Group.objects.accessible().
        self._test_accessible(
            repositories=[
                repositories[0],
                repositories[2],
            ],
            user=user,
            local_site=local_site,
            visible_only=True)

    def test_with_superuser_local_site_all(self) -> None:
        """Testing Repository.objects.accessible with superuser,
        all Local Sites, and visible_only=False
        """
        user = self.create_user(is_superuser=True)
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)[0]

        self._test_accessible(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    def test_with_superuser_local_site_all_visible_only(self) -> None:
        """Testing Repository.objects.accessible with superuser, all
        Local Sites, and visible_only=True
        """
        user = self.create_user(is_superuser=True)
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)[0]

        # Note that, unlike with standard members, superusers won't see
        # hidden repositories in this case. This is a legacy
        # piece of logic in Group.objects.accessible().
        self._test_accessible(
            repositories=[
                repositories[0],
                repositories[2],
                repositories[4],
                repositories[6],
                repositories[8],
                repositories[10],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Non-member tests
    #

    def test_with_non_member(self) -> None:
        """Testing Repository.objects.accessible with non-member and
        visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible(
            repositories=[
                repositories[0],
                repositories[1],
            ],
            user=user,
            visible_only=False)

    def test_with_non_member_visible_only(self) -> None:
        """Testing Repository.objects.accessible with non-member and
        visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible(
            repositories=[repositories[0]],
            user=user,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_non_member_local_site(self) -> None:
        """Testing Repository.objects.accessible with non-member,
        Local Site, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            repositories=[
                repositories[0],
                repositories[1],
            ],
            user=user,
            local_site=local_site,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_non_member_local_site_visible_only(self) -> None:
        """Testing Repository.objects.accessible with non-member,
        Local Site, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            repositories=[repositories[0]],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_non_member_local_site_all(self) -> None:
        """Testing Repository.objects.accessible with non-member,
        all Local Sites, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            repositories=[
                repositories[0],
                repositories[1],
                repositories[4],
                repositories[5],
                repositories[8],
                repositories[9],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_non_member_local_site_all_visible_only(self) -> None:
        """Testing Repository.objects.accessible with non-member,
        all Local Sites, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            repositories=[
                repositories[0],
                repositories[4],
                repositories[8],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Member tests
    #

    def test_with_member(self) -> None:
        """Testing Repository.objects.accessible with member,
        visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member=True)[0]

        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            visible_only=False)

    def test_with_member_visible_only(self) -> None:
        """Testing Repository.objects.accessible with member,
        visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member=True)[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_local_site(self) -> None:
        """Testing Repository.objects.accessible with member, Local Site,
        and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_local_site_visible_only(self) -> None:
        """Testing Repository.objects.accessible with member, Local Site,
        and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_local_site_all(self) -> None:
        """Testing Repository.objects.accessible with member, all
        Local Sites, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        self._test_accessible(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_local_site_all_visible_only(self) -> None:
        """Testing Repository.objects.accessible with member, all
        Local Sites, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Member by public group tests
    #

    def test_with_member_by_group(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        and visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member_by_group=True)[0]

        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            visible_only=False)

    def test_with_member_by_group_visible_only(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        and visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member_by_group=True)[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_by_group_local_site(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        Local Site, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True)

        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_by_group_local_site_visible_only(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        Local Site, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True)

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_by_group_local_site_all(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        all Local Sites, visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True)[0]

        self._test_accessible(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_by_group_local_site_all_visible_only(
        self,
    ) -> None:
        """Testing Repository.objects.accessible with member by group,
        all Local Sites, visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True)[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Member by invite-only group tests
    #

    def test_with_member_by_invite_only_group(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        and visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })[0]

        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            visible_only=False)

    def test_with_member_by_invite_only_group_visible_only(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        and visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_by_invite_only_group_local_site(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        Local Site, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })

        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_by_invite_only_group_local_site_visible_only(
        self,
    ) -> None:
        """Testing Repository.objects.accessible with member by group,
        Local Site, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_by_invite_only_group_local_site_all(self) -> None:
        """Testing Repository.objects.accessible with member by group,
        all Local Sites, visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })[0]

        self._test_accessible(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_by_invite_only_group_local_site_all_visible_only(
        self,
    ) -> None:
        """Testing Repository.objects.accessible with member by group,
        all Local Sites, visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_show_all_local_sites(self) -> None:
        """Testing Group.objects.accessible with show_all_local_sites=True
        """
        user = self.create_user(is_superuser=True)

        repository = self.create_repository(with_local_site=True)
        repository.local_site.users.add(user)

        self.assertIn(
            repository,
            Repository.objects.accessible(user,
                                          local_site=repository.local_site))
        self.assertIn(
            repository,
            Repository.objects.accessible(user,
                                          local_site=LocalSite.ALL))

    def _test_accessible(
        self,
        *,
        repositories: Sequence[Repository],
        user: Union[AnonymousUser, User],
        visible_only: bool,
        local_site: AnyOrAllLocalSites = None,
    ) -> None:
        """Test the results of accessible_ids(), using the given settings.

        Version Added:
            5.0.7

        Args:
            repository (list of reviewboard.scmtools.models.Repository):
                The repositories to expect in results.

            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to check for access.

            visible_only (bool):
                Whether to check for visible repositories only.

            local_site (reviewboard.site.models.LocalSite, optional):
                The optional Local Site to check.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        # Prime the caches.
        if user.is_authenticated:
            user.get_local_site_stats()
            user.get_profile()

            if local_site is not LocalSite.ALL:
                user.get_site_profile(local_site=local_site)

        equeries = get_repositories_accessible_equeries(
            user=user,
            visible_only=visible_only,
            local_site=local_site)

        with self.assertQueries(equeries):
            accessible = list(Repository.objects.accessible(
                user,
                visible_only=visible_only,
                local_site=local_site))

        self.assertEqual(accessible, repositories)


class AccessibleIDsTests(AccessibleTestsMixin, TestCase):
    """Unit tests for RepositoryManager.accessible_ids()."""

    fixtures = ['test_scmtools', 'test_users']

    #
    # Anonymous tests
    #

    def test_with_anonymous(self) -> None:
        """Testing Repository.objects.accessible_ids with anonymous and
        visible_only=False
        """
        user = AnonymousUser()
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible_ids(
            repositories=[
                repositories[0],
                repositories[1],
            ],
            user=user,
            visible_only=False)

    def test_with_anonymous_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with anonymous and
        visible_only=True
        """
        user = AnonymousUser()
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible_ids(
            repositories=[repositories[0]],
            user=user,
            visible_only=True)

    #
    # Superuser tests
    #

    def test_with_superuser(self) -> None:
        """Testing Repository.objects.accessible_ids with superuser and
        visible_only=False
        """
        user = self.create_user(is_superuser=True)
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            visible_only=False)

    def test_with_superuser_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with superuser and
        visible_only=True
        """
        user = self.create_user(is_superuser=True)
        repositories = self._create_accessible_repository_data(user=user)[0]

        # Note that, unlike with standard members, superusers won't see
        # hidden repositories in this case. This is a legacy
        # piece of logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=[
                repositories[0],
                repositories[2],
            ],
            user=user,
            visible_only=True)

    def test_with_superuser_local_site(self) -> None:
        """Testing Repository.objects.accessible_ids with superuser,
        Local Site, and visible_only=False
        """
        user = self.create_user(is_superuser=True)
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    def test_with_superuser_local_site_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with superuser and
        visible_only=True
        """
        user = self.create_user(is_superuser=True)
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        # Note that, unlike with standard members, superusers won't see
        # hidden repositories in this case. This is a legacy
        # piece of logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=[
                repositories[0],
                repositories[2],
            ],
            user=user,
            local_site=local_site,
            visible_only=True)

    def test_with_superuser_local_site_all(self) -> None:
        """Testing Repository.objects.accessible_ids with superuser,
        all Local Sites, and visible_only=False
        """
        user = self.create_user(is_superuser=True)
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)[0]

        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    def test_with_superuser_local_site_all_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with superuser,
        all Local Sites, and visible_only=True
        """
        user = self.create_user(is_superuser=True)
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)[0]

        # Note that, unlike with standard members, superusers won't see
        # hidden repositories in this case. This is a legacy
        # piece of logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=[
                repositories[0],
                repositories[2],
                repositories[4],
                repositories[6],
                repositories[8],
                repositories[10],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Non-member tests
    #

    def test_with_non_member(self) -> None:
        """Testing Repository.objects.accessible_ids with non-member and
        visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible_ids(
            repositories=[
                repositories[0],
                repositories[1],
            ],
            user=user,
            visible_only=False)

    def test_with_non_member_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with non-member and
        visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(user=user)[0]

        self._test_accessible_ids(
            repositories=[repositories[0]],
            user=user,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_non_member_local_site(self) -> None:
        """Testing Repository.objects.accessible_ids with non-member,
        Local Site, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            repositories=[
                repositories[0],
                repositories[1],
            ],
            user=user,
            local_site=local_site,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_non_member_local_site_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with non-member,
        Local Site, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            repositories=[repositories[0]],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_non_member_local_site_all(self) -> None:
        """Testing Repository.objects.accessible_ids with non-member,
        all Local Sites, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            repositories=[
                repositories[0],
                repositories[1],
                repositories[4],
                repositories[5],
                repositories[8],
                repositories[9],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_non_member_local_site_all_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with non-member,
        all Local Sites, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            repositories=[
                repositories[0],
                repositories[4],
                repositories[8],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Member tests
    #

    def test_with_member(self) -> None:
        """Testing Repository.objects.accessible_ids with member,
        visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member=True)[0]

        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            visible_only=False)

    def test_with_member_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with member,
        visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member=True)[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_local_site(self) -> None:
        """Testing Repository.objects.accessible_ids with member, Local Site,
        and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_local_site_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with member, Local Site,
        and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_local_site_all(self) -> None:
        """Testing Repository.objects.accessible_ids with member, all
        Local Sites, and visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member=True)[0]

        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_local_site_all_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with member, all
        Local Sites, and visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member=True)[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Member by public group tests
    #

    def test_with_member_by_group(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        and visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member_by_group=True)[0]

        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            visible_only=False)

    def test_with_member_by_group_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        and visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member_by_group=True)[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_by_group_local_site(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        Local Site, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True)

        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_by_group_local_site_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        Local Site, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True)

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_by_group_local_site_all(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        all Local Sites, visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True)[0]

        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_by_group_local_site_all_visible_only(
        self,
    ) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        all Local Sites, visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True)[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Member by invite-only group tests
    #

    def test_with_member_by_invite_only_group(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        and visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })[0]

        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            visible_only=False)

    def test_with_member_by_invite_only_group_visible_only(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        and visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_by_invite_only_group_local_site(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        Local Site, and visible_only=False
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })

        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_by_invite_only_group_local_site_visible_only(
        self,
    ) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        Local Site, and visible_only=True
        """
        user = self.create_user()
        repositories, local_site = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories[:4],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_site'])
    def test_with_member_by_invite_only_group_local_site_all(self) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        all Local Sites, visible_only=False
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })[0]

        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    @add_fixtures(['test_site'])
    def test_with_member_by_invite_only_group_local_site_all_visible_only(
        self,
    ) -> None:
        """Testing Repository.objects.accessible_ids with member by group,
        all Local Sites, visible_only=True
        """
        user = self.create_user()
        repositories = self._create_accessible_repository_data(
            user=user,
            with_local_sites=True,
            with_member_by_group=True,
            group_kwargs={
                'invite_only': True,
            })[0]

        # Note that members can see hidden repositories. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            repositories=repositories,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_show_all_local_sites(self) -> None:
        """Testing Group.objects.accessible_ids with show_all_local_sites=True
        """
        user = self.create_user(is_superuser=True)

        repository = self.create_repository(with_local_site=True)
        repository.local_site.users.add(user)

        self.assertIn(
            repository.pk,
            Repository.objects.accessible_ids(
                user,
                local_site=repository.local_site))
        self.assertIn(
            repository.pk,
            Repository.objects.accessible_ids(
                user,
                local_site=LocalSite.ALL))

    def _test_accessible_ids(
        self,
        *,
        repositories: Sequence[Repository],
        user: Union[AnonymousUser, User],
        visible_only: bool,
        local_site: AnyOrAllLocalSites = None,
        expect_in: bool = True,
    ) -> None:
        """Test the results of accessible_ids(), using the given settings.

        Version Added:
            5.0.7

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repositories to expect in results.

            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to check for access.

            visible_only (bool):
                Whether to check for visible repositories only.

            local_site (reviewboard.site.models.LocalSite, optional):
                The optional Local Site to check.

            expect_in (bool, optional):
                Whether to expect the provided repository's ID to be in the
                accessible IDs list.

        Raises:
            AssertionError:
                One of the checks failed.
        """
        # Prime the caches.
        if user.is_authenticated:
            user.get_local_site_stats()
            user.get_profile()

            if local_site is not LocalSite.ALL:
                user.get_site_profile(local_site=local_site)

        equeries = get_repositories_accessible_ids_equeries(
            user=user,
            visible_only=visible_only,
            local_site=local_site)

        with self.assertQueries(equeries):
            accessible_ids = Repository.objects.accessible_ids(
                user,
                visible_only=visible_only,
                local_site=local_site)

        self.assertEqual(
            accessible_ids,
            [
                repository.pk
                for repository in repositories
            ])


class GetBestMatchTests(TestCase):
    """Unit tests for RepositoryManager.get_best_match()."""

    fixtures = ['test_scmtools', 'test_users']

    def test_with_pk(self):
        """Testing Repository.objects.get_best_match with repository ID"""
        repository1 = self.create_repository()
        self.create_repository(name=str(repository1.pk))

        self.assertEqual(
            Repository.objects.get_best_match(repository1.pk),
            repository1)

    @add_fixtures(['test_site'])
    def test_with_pk_and_local_site(self):
        """Testing Repository.objects.get_best_match with repository ID and
        local_site=...
        """
        repository1 = self.create_repository(with_local_site=True)
        repository2 = self.create_repository()
        local_site = repository1.local_site

        # This should match.
        self.assertEqual(
            Repository.objects.get_best_match(repository1.pk,
                                              local_site=local_site),
            repository1)

        # These should both fail.
        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository1.pk)

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository2.pk,
                                              local_site=local_site)

    def test_with_name(self):
        """Testing Repository.objects.get_best_match with repository name"""
        repository1 = self.create_repository(name='repo 1')
        self.create_repository(name='repo 2')

        self.assertEqual(
            Repository.objects.get_best_match('repo 1'),
            repository1)

    @add_fixtures(['test_site'])
    def test_with_name_and_local_site(self):
        """Testing Repository.objects.get_best_match with repository name
        and local_site=...
        """
        repository1 = self.create_repository(name='repo 1',
                                             with_local_site=True)
        repository2 = self.create_repository(name='repo 2')
        local_site = repository1.local_site

        # This should match.
        self.assertEqual(
            Repository.objects.get_best_match(repository1.name,
                                              local_site=local_site),
            repository1)

        # These should both fail.
        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository1.name)

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository2.name,
                                              local_site=local_site)

    def test_with_path(self):
        """Testing Repository.objects.get_best_match with repository path"""
        repository1 = self.create_repository(name='repo1',
                                             path='/test-path-1')
        self.create_repository(name='repo2',
                               path='/test-path-2')

        self.assertEqual(
            Repository.objects.get_best_match('/test-path-1'),
            repository1)

    @add_fixtures(['test_site'])
    def test_with_path_and_local_site(self):
        """Testing Repository.objects.get_best_match with repository path
        and local_site=...
        """
        repository1 = self.create_repository(path='/test-path-1',
                                             with_local_site=True)
        repository2 = self.create_repository(path='/test-path-2')
        local_site = repository1.local_site

        # This should match.
        self.assertEqual(
            Repository.objects.get_best_match(repository1.path,
                                              local_site=local_site),
            repository1)

        # These should both fail.
        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository1.path)

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository2.path,
                                              local_site=local_site)

    def test_with_mirror_path(self):
        """Testing Repository.objects.get_best_match with repository
        mirror_path
        """
        repository1 = self.create_repository(name='repo1',
                                             mirror_path='/test-path-1')
        self.create_repository(name='repo2',
                               mirror_path='/test-path-2')

        self.assertEqual(
            Repository.objects.get_best_match('/test-path-1'),
            repository1)

    @add_fixtures(['test_site'])
    def test_with_mirror_path_and_local_site(self):
        """Testing Repository.objects.get_best_match with repository
        mirror_path and local_site=...
        """
        repository1 = self.create_repository(name='repo1',
                                             mirror_path='/test-path-1',
                                             with_local_site=True)
        repository2 = self.create_repository(name='repo2',
                                             mirror_path='/test-path-2')
        local_site = repository1.local_site

        # This should match.
        self.assertEqual(
            Repository.objects.get_best_match(repository1.mirror_path,
                                              local_site=local_site),
            repository1)

        # These should both fail.
        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository1.mirror_path)

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match(repository2.mirror_path,
                                              local_site=local_site)

    def test_with_no_match(self):
        """Testing Repository.objects.get_best_match with no match"""
        self.create_repository(name='repo 1')
        self.create_repository(name='repo 2')

        with self.assertRaises(Repository.DoesNotExist):
            Repository.objects.get_best_match('bad-id')

    def test_with_multiple_prefer_visible(self):
        """Testing Repository.objects.get_best_match with multiple results
        prefers visible over name/path/mirror_path
        """
        repository1 = self.create_repository(
            name='repo1',
            path='/path1',
            mirror_path='mirror')
        repository2 = self.create_repository(
            name='repo2',
            path='/path2',
            mirror_path='mirror')
        repository3 = self.create_repository(
            name='repo3',
            path='/path3',
            mirror_path='mirror')

        # This should fail, since all are visible and they conflict.
        with self.assertRaises(Repository.MultipleObjectsReturned):
            Repository.objects.get_best_match('mirror')

        # It should then work if only one is visible.
        repository2.visible = False
        repository2.save(update_fields=('visible',))

        repository3.visible = False
        repository3.save(update_fields=('visible',))

        self.assertEqual(
            Repository.objects.get_best_match('mirror'),
            repository1)

    def test_with_multiple_prefer_name(self):
        """Testing Repository.objects.get_best_match with multiple results
        prefers name over path/mirror_path
        """
        repository1 = self.create_repository(
            name='repo1',
            path='/path1',
            mirror_path='mirror')
        self.create_repository(
            name='repo2',
            path='/path2',
            mirror_path='mirror')
        self.create_repository(
            name='repo3',
            path='/path3',
            mirror_path='mirror')

        # This should fail, since all are visible and they conflict.
        with self.assertRaises(Repository.MultipleObjectsReturned):
            Repository.objects.get_best_match('mirror')

        # It should then work if only one is visible.
        repository1.name = 'mirror'
        repository1.save(update_fields=('name',))

        self.assertEqual(
            Repository.objects.get_best_match('mirror'),
            repository1)

    def test_with_multiple_prefer_path(self):
        """Testing Repository.objects.get_best_match with multiple results
        prefers path over mirror_path
        """
        repository1 = self.create_repository(
            name='repo1',
            path='/path1',
            mirror_path='mirror')
        self.create_repository(
            name='repo2',
            path='/path2',
            mirror_path='mirror')
        self.create_repository(
            name='repo3',
            path='/path3',
            mirror_path='mirror')

        # This should fail, since all are visible and they conflict.
        with self.assertRaises(Repository.MultipleObjectsReturned):
            Repository.objects.get_best_match('mirror')

        # It should then work if only one is visible.
        repository1.path = 'mirror'
        repository1.save(update_fields=('path',))

        self.assertEqual(
            Repository.objects.get_best_match('mirror'),
            repository1)
