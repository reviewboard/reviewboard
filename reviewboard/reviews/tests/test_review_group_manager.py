"""Unit tests for reviewboard.reviews.manager.ReviewGroupManager."""

from __future__ import annotations

from itertools import chain
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING, Tuple, Union

from django.contrib.auth.models import AnonymousUser, User
from djblets.testing.decorators import add_fixtures

from reviewboard.reviews.models import Group
from reviewboard.reviews.testing.queries.review_groups import (
    get_review_groups_accessible_equeries,
    get_review_groups_accessible_ids_equeries)
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from djblets.util.typing import KwargsDict

    from reviewboard.site.models import AnyOrAllLocalSites

    _MixinParent = TestCase
else:
    _MixinParent = object


class AccessibleTestsMixin(_MixinParent):
    """Mixins for review group accessibility unit tests.

    Version Added:
        5.0.7
    """

    def _create_accessible_review_group_data(
        self,
        *,
        user: Union[AnonymousUser, User],
        with_local_sites: bool = False,
        with_member: bool = False,
        group_kwargs: KwargsDict = {},
    ) -> Tuple[Sequence[Group], Optional[LocalSite]]:
        """Create test review group data for accessibility checks.

        This will create review groups on the global site and, optionally,
        two Local Sites. The provided user may optionally be granted membership
        directly.

        Args:
            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to associate with any membership lists.

            with_local_sites (bool, optional):
                Whether to create Local Sites.

            with_member (bool, optional):
                Whether to make the user a member of the review group.

        Returns:
            tuple:
            A 2-tuple of:

            Tuple:
                0 (list of reviewboard.reviews.models.group.Group):
                    The list of created review groups, in order.

                1 (reviewboard.site.models.LocalSite):
                    The first Local Site created, or ``None`` if not creating
                    Local Sites.
        """
        groups_by_site: Dict[Optional[LocalSite], List[Group]] = {}
        local_sites: List[Optional[LocalSite]] = []
        local_site_kwargs: KwargsDict = {}
        group_i = 1

        if user.is_authenticated:
            # Satisfy the type checker.
            assert isinstance(user, User)

            local_site_kwargs['users'] = [user]

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
            groups_by_site[local_site] = [
                self.create_review_group(local_site=local_site,
                                         name=f'repo{group_i:02}',
                                         invite_only=False,
                                         visible=True),
                self.create_review_group(local_site=local_site,
                                         name=f'repo{group_i + 1:02}',
                                         invite_only=False,
                                         visible=False),
                self.create_review_group(local_site=local_site,
                                         name=f'repo{group_i + 2:02}',
                                         invite_only=True,
                                         visible=True),
                self.create_review_group(local_site=local_site,
                                         name=f'repo{group_i + 3:02}',
                                         invite_only=True,
                                         visible=False),
            ]
            group_i += 4

        if with_member and user.is_authenticated:
            # Satisfy the type checker.
            assert isinstance(user, User)

            for local_site in local_sites:
                user.review_groups.add(*groups_by_site[local_site])

        return (
            list(chain.from_iterable(groups_by_site.values())),
            local_sites[0],
        )


class AccessibleTests(AccessibleTestsMixin, TestCase):
    """Unit tests for ReviewGroupManager.accessible()."""

    def test_with_anonymous(self) -> None:
        """Testing Group.objects.accessible with anonymous and
        visible_only=False
        """
        user = AnonymousUser()
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible(
            groups=[
                groups[0],
                groups[1],
            ],
            user=user,
            visible_only=False)

    def test_with_anonymous_visible_only(self) -> None:
        """Testing Group.objects.accessible with anonymous and
        visible_only=True
        """
        user = AnonymousUser()
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible(
            groups=[groups[0]],
            user=user,
            visible_only=True)

    #
    # Superuser tests
    #

    def test_with_superuser(self) -> None:
        """Testing Group.objects.accessible with superuser and
        visible_only=False
        """
        user = self.create_user(is_superuser=True)
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible(
            groups=groups,
            user=user,
            visible_only=False)

    def test_with_superuser_visible_only(self) -> None:
        """Testing Group.objects.accessible with superuser and
        visible_only=True
        """
        user = self.create_user(is_superuser=True)
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible(
            groups=[
                groups[0],
                groups[2],
            ],
            user=user,
            visible_only=True)

    def test_with_superuser_local_site(self) -> None:
        """Testing Group.objects.accessible with superuser, Local Site,
        and visible_only=False
        """
        user = self.create_user(is_superuser=True)
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            groups=groups[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    def test_with_superuser_local_site_visible_only(self) -> None:
        """Testing Group.objects.accessible with superuser, Local Site,
        and visible_only=True
        """
        user = self.create_user(is_superuser=True)
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            groups=[
                groups[0],
                groups[2],
            ],
            user=user,
            local_site=local_site,
            visible_only=True)

    def test_with_superuser_local_site_all(self) -> None:
        """Testing Group.objects.accessible with superuser, all Local
        Sites, and visible_only=False
        """
        user = self.create_user(is_superuser=True)
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            groups=groups,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    def test_with_superuser_local_site_all_visible_only(self) -> None:
        """Testing Group.objects.accessible with superuser, all Local
        Sites, and visible_only=True
        """
        user = self.create_user(is_superuser=True)
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            groups=[
                groups[0],
                groups[2],
                groups[4],
                groups[6],
                groups[8],
                groups[10],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Non-member tests
    #

    def test_with_non_member(self) -> None:
        """Testing Group.objects.accessible with non-member and
        visible_only=False
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible(
            groups=[
                groups[0],
                groups[1],
            ],
            user=user,
            visible_only=False)

    def test_with_non_member_visible_only(self) -> None:
        """Testing Group.objects.accessible with non-member and
        visible_only=True
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible(
            groups=[groups[0]],
            user=user,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_non_member_local_site(self) -> None:
        """Testing Group.objects.accessible with non-member, Local Site,
        and visible_only=False
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            groups=[
                groups[0],
                groups[1],
            ],
            user=user,
            local_site=local_site,
            visible_only=False)

    def test_with_non_member_local_site_visible_only(self) -> None:
        """Testing Group.objects.accessible with non-member, Local Site,
        and visible_only=True
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            groups=[groups[0]],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_non_member_local_site_all(self) -> None:
        """Testing Group.objects.accessible with non-member, all Local
        Sites, and visible_only=False
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            groups=[
                groups[0],
                groups[1],
                groups[4],
                groups[5],
                groups[8],
                groups[9],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    def test_with_non_member_local_site_all_visible_only(self) -> None:
        """Testing Group.objects.accessible with non-member, all Local
        Sites, and visible_only=True
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible(
            groups=[
                groups[0],
                groups[4],
                groups[8],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Member tests
    #

    def test_with_member(self) -> None:
        """Testing Group.objects.accessible with member and
        visible_only=False
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(
            user=user,
            with_member=True)[0]

        self._test_accessible(
            groups=groups[:4],
            user=user,
            visible_only=False)

    def test_with_member_visible_only(self) -> None:
        """Testing Group.objects.accessible with member and
        visible_only=True
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(
            user=user,
            with_member=True)[0]

        # Note that members can see hidden review groups. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            groups=groups,
            user=user,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_member_local_site(self) -> None:
        """Testing Group.objects.accessible with member, Local Site,
        and visible_only=False
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        self._test_accessible(
            groups=groups[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    def test_with_member_local_site_visible_only(self) -> None:
        """Testing Group.objects.accessible with member, Local Site,
        and visible_only=True
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        # Note that members can see hidden review groups. This is a legacy
        # piece of intentional logic in Group.objects.accessible().
        self._test_accessible(
            groups=groups[:4],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_member_local_site_all(self) -> None:
        """Testing Group.objects.accessible with member, all Local
        Sites, and visible_only=False
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True,
            with_member=True)[0]

        self._test_accessible(
            groups=groups,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    def test_with_member_local_site_all_visible_only(self) -> None:
        """Testing Group.objects.accessible with member, all Local
        Sites, and visible_only=True
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)[0]

        self._test_accessible(
            groups=[
                groups[0],
                groups[4],
                groups[8],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_show_all_local_sites(self) -> None:
        """Testing Group.objects.accessible with show_all_local_sites=True
        """
        user = self.create_user()

        group = self.create_review_group(with_local_site=True)
        group.local_site.users.add(user)

        self.assertIn(
            group,
            Group.objects.accessible(user, local_site=group.local_site))
        self.assertIn(
            group,
            Group.objects.accessible(user, local_site=LocalSite.ALL))

    def _test_accessible(
        self,
        *,
        groups: Sequence[Group],
        user: Union[AnonymousUser, User],
        visible_only: bool,
        local_site: AnyOrAllLocalSites = None,
        has_view_invite_only_groups_perm: bool = False,
    ) -> None:
        """Test the results of accessible(), using the given settings.

        Version Added:
            5.0.7

        Args:
            groups (list of reviewboard.revies.models.group.Group):
                The review groups to expect in results.

            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to check for access.

            visible_only (bool):
                Whether to check for visible groups only.

            local_site (reviewboard.site.models.LocalSite, optional):
                The optional Local Site to check.

            expect_in (bool, optional):
                Whether to expect the provided group's ID to be in the
                accessible IDs list.

            has_view_invite_only_groups_perm (bool, optional):
                Whether to expect the
                ``reviews.has_view_invite_only_groups_perm`` permission to
                be set.

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

        equeries = get_review_groups_accessible_equeries(
            user=user,
            visible_only=visible_only,
            has_view_invite_only_groups_perm=has_view_invite_only_groups_perm,
            local_site=local_site)

        with self.assertQueries(equeries):
            accessible = list(Group.objects.accessible(
                user,
                visible_only=visible_only,
                local_site=local_site))

        self.assertEqual(accessible, groups)


class AccessibleIDsTests(AccessibleTestsMixin, TestCase):
    """Unit tests for ReviewGroupManager.accessible_ids()."""

    #
    # Anonymous tests
    #

    def test_with_anonymous(self) -> None:
        """Testing Group.objects.accessible_ids with anonymous and
        visible_only=False
        """
        user = AnonymousUser()
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[1],
            ],
            user=user,
            visible_only=False)

    def test_with_anonymous_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with anonymous and
        visible_only=True
        """
        user = AnonymousUser()
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible_ids(
            groups=[groups[0]],
            user=user,
            visible_only=True)

    #
    # Superuser tests
    #

    def test_with_superuser(self) -> None:
        """Testing Group.objects.accessible_ids with superuser and
        visible_only=False
        """
        user = self.create_user(is_superuser=True)
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible_ids(
            groups=groups,
            user=user,
            visible_only=False)

    def test_with_superuser_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with superuser and
        visible_only=True
        """
        user = self.create_user(is_superuser=True)
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[2],
            ],
            user=user,
            visible_only=True)

    def test_with_superuser_local_site(self) -> None:
        """Testing Group.objects.accessible_ids with superuser, Local Site,
        and visible_only=False
        """
        user = self.create_user(is_superuser=True)
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            groups=groups[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    def test_with_superuser_local_site_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with superuser, Local Site,
        and visible_only=True
        """
        user = self.create_user(is_superuser=True)
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[2],
            ],
            user=user,
            local_site=local_site,
            visible_only=True)

    def test_with_superuser_local_site_all(self) -> None:
        """Testing Group.objects.accessible_ids with superuser, all Local
        Sites, and visible_only=False
        """
        user = self.create_user(is_superuser=True)
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            groups=groups,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    def test_with_superuser_local_site_all_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with superuser, all Local
        Sites, and visible_only=True
        """
        user = self.create_user(is_superuser=True)
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[2],
                groups[4],
                groups[6],
                groups[8],
                groups[10],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Non-member tests
    #

    def test_with_non_member(self) -> None:
        """Testing Group.objects.accessible_ids with non-member and
        visible_only=False
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[1],
            ],
            user=user,
            visible_only=False)

    def test_with_non_member_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with non-member and
        visible_only=True
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(user=user)[0]

        self._test_accessible_ids(
            groups=[groups[0]],
            user=user,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_non_member_local_site(self) -> None:
        """Testing Group.objects.accessible_ids with non-member, Local Site,
        and visible_only=False
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[1],
            ],
            user=user,
            local_site=local_site,
            visible_only=False)

    def test_with_non_member_local_site_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with non-member, Local Site,
        and visible_only=True
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            groups=[groups[0]],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_non_member_local_site_all(self) -> None:
        """Testing Group.objects.accessible_ids with non-member, all Local
        Sites, and visible_only=False
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[1],
                groups[4],
                groups[5],
                groups[8],
                groups[9],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    def test_with_non_member_local_site_all_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with non-member, all Local
        Sites, and visible_only=True
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[4],
                groups[8],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    #
    # Member tests
    #

    def test_with_member(self) -> None:
        """Testing Group.objects.accessible_ids with member and
        visible_only=False
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(
            user=user,
            with_member=True)[0]

        self._test_accessible_ids(
            groups=groups[:4],
            user=user,
            visible_only=False)

    def test_with_member_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with member and
        visible_only=True
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(
            user=user,
            with_member=True)[0]

        # Note that members can see hidden review groups. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            groups=groups,
            user=user,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_member_local_site(self) -> None:
        """Testing Group.objects.accessible_ids with member, Local Site,
        and visible_only=False
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        self._test_accessible_ids(
            groups=groups[:4],
            user=user,
            local_site=local_site,
            visible_only=False)

    def test_with_member_local_site_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with member, Local Site,
        and visible_only=True
        """
        user = self.create_user()
        groups, local_site = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True,
            with_member=True)

        # Note that members can see hidden review groups. This is a legacy
        # piece of intentional logic in Group.objects.accessible_ids().
        self._test_accessible_ids(
            groups=groups[:4],
            user=user,
            local_site=local_site,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_member_local_site_all(self) -> None:
        """Testing Group.objects.accessible_ids with member, all Local
        Sites, and visible_only=False
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True,
            with_member=True)[0]

        self._test_accessible_ids(
            groups=groups,
            user=user,
            local_site=LocalSite.ALL,
            visible_only=False)

    def test_with_member_local_site_all_visible_only(self) -> None:
        """Testing Group.objects.accessible_ids with member, all Local
        Sites, and visible_only=True
        """
        user = self.create_user()
        groups = self._create_accessible_review_group_data(
            user=user,
            with_local_sites=True)[0]

        self._test_accessible_ids(
            groups=[
                groups[0],
                groups[4],
                groups[8],
            ],
            user=user,
            local_site=LocalSite.ALL,
            visible_only=True)

    @add_fixtures(['test_users', 'test_site'])
    def test_with_show_all_local_sites(self) -> None:
        """Testing Group.objects.accessible_ids with show_all_local_sites=True
        """
        user = self.create_user()

        group = self.create_review_group(with_local_site=True)
        group.local_site.users.add(user)

        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, local_site=group.local_site))
        self.assertIn(
            group.pk,
            Group.objects.accessible_ids(user, local_site=LocalSite.ALL))

    def _test_accessible_ids(
        self,
        *,
        groups: Sequence[Group],
        user: Union[AnonymousUser, User],
        visible_only: bool,
        local_site: AnyOrAllLocalSites = None,
        has_view_invite_only_groups_perm: bool = False,
    ) -> None:
        """Test the results of accessible_ids(), using the given settings.

        Version Added:
            5.0.7

        Args:
            groups (list of reviewboard.revies.models.group.Group):
                The review groups to expect in results.

            user (django.contrib.auth.models.AnonymousUser or
                  django.contrib.auth.models.User):
                The user to check for access.

            visible_only (bool):
                Whether to check for visible groups only.

            local_site (reviewboard.site.models.LocalSite, optional):
                The optional Local Site to check.

            expect_in (bool, optional):
                Whether to expect the provided group's ID to be in the
                accessible IDs list.

            has_view_invite_only_groups_perm (bool, optional):
                Whether to expect the
                ``reviews.has_view_invite_only_groups_perm`` permission to
                be set.

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

        equeries = get_review_groups_accessible_ids_equeries(
            user=user,
            visible_only=visible_only,
            has_view_invite_only_groups_perm=has_view_invite_only_groups_perm,
            local_site=local_site)

        with self.assertQueries(equeries):
            accessible_ids = Group.objects.accessible_ids(
                user,
                visible_only=visible_only,
                local_site=local_site)

        self.assertEqual(
            accessible_ids,
            [
                group.pk
                for group in groups
            ])
