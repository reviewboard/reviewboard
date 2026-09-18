"""Managers for the hostingsvcs app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Manager, Q

from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.contrib.auth.models import User
    from django.db.models import QuerySet
    from django.http import HttpRequest

    from reviewboard.hostingsvcs.models import (
        ConfiguredBugTracker,
        HostingServiceAccount,
    )
    from reviewboard.reviews.models import ReviewRequest
    from reviewboard.reviews.models.base_review_request_details import (
        BaseReviewRequestDetails,
    )
    from reviewboard.site.models import AnyOrAllLocalSites


class HostingServiceAccountManager(Manager['HostingServiceAccount']):
    """A manager for HostingServiceAccount models."""

    def accessible(
        self,
        visible_only: bool = True,
        local_site: (AnyOrAllLocalSites | None) = None,
    ) -> QuerySet[HostingServiceAccount]:
        """Return hosting service accounts that are accessible.

        These will include all visible accounts that are compatible with the
        specified :term:`Local Site`.

        Version Changed:
            6.0:
            Removed the ``filter_local_site`` argument.

        Version Changed:
            5.0:
            Deprecated ``filter_local_site`` and added support for
            setting ``local_site`` to :py:class:`LocalSite.ALL
            <reviewboard.site.models.LocalSite.ALL>`.

        Args:
            visible_only (bool, optional):
                Whether to only include visible accounts in the results.

            local_site (reviewboard.site.models.AnyOrAllLocalSites, optional):
                A :term:`Local Site` that the accounts must be associated with.
                If not specified, returned accounts won't be bound to a
                Local Site.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

                Version Changed:
                    5.0:
                    Added support for :py:attr:`LocalSite.ALL
                    <reviewboard.site.models.LocalSite.ALL>`.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        q = LocalSite.objects.build_q(local_site=local_site)

        if visible_only:
            q &= Q(visible=True)

        return self.filter(q)

    def can_create(
        self,
        user: User,
        local_site: (AnyOrAllLocalSites | None) = None,
    ) -> bool:
        """Return whether the user can create a hosting service account.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

            local_site (reviewboard.site.models.AnyOrAllLocalSites, optional):
                A :term:`Local Site` to create hosting service accounts on.

                This may be :py:attr:`LocalSite.ALL
                <reviewboard.site.models.LocalSite.ALL>`.

        Returns:
            bool:
            True if the user can create hosting service accounts.
        """
        return user.has_perm('hostingsvcs.create_hostingserviceaccount',
                             local_site)


class ConfiguredBugTrackerManager(Manager['ConfiguredBugTracker']):
    """A manager for ConfiguredBugTracker models.

    Version Added:
        9.0
    """

    def accessible(
        self,
        local_site: (AnyOrAllLocalSites | None) = None,
    ) -> QuerySet[ConfiguredBugTracker]:
        """Return bug trackers for admin and API listings.

        This includes disabled trackers (so they can be re-enabled), but
        never the sentinel tracker.

        Args:
            local_site (reviewboard.site.models.AnyOrAllLocalSites, optional):
                A :term:`Local Site` that the trackers must be associated
                with. If not specified, returned trackers won't be bound
                to a Local Site.

        Returns:
            django.db.models.query.QuerySet:
            The resulting queryset.
        """
        from reviewboard.hostingsvcs.models import \
            SENTINEL_BUG_TRACKER_SERVICE_NAME

        q = LocalSite.objects.build_q(local_site=local_site)

        return (
            self.filter(q)
            .exclude(service_name=SENTINEL_BUG_TRACKER_SERVICE_NAME)
            .order_by('name')
        )

    def for_review_request(
        self,
        review_request: ReviewRequest,
        *,
        user: User,
        request: (HttpRequest | None) = None,
    ) -> Sequence[ConfiguredBugTracker]:
        """Return the bug trackers available for a review request and user.

        This is the availability API for bug trackers. It returns every
        enabled tracker whose repository scoping matches the review
        request, unioned with the repository's default bug tracker, and
        then filtered by each tracker's user conditions.

        Results are cached on ``request`` when one is provided.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request to look up trackers for.

            user (django.contrib.auth.models.User):
                The acting user.

            request (django.http.HttpRequest, optional):
                The HTTP request, used for caching.

        Returns:
            list of reviewboard.hostingsvcs.models.ConfiguredBugTracker:
            The bug trackers usable by the user on this review request.
        """
        cache_key = (review_request.pk, user.pk)
        cache: (dict[tuple[int, int], Sequence[ConfiguredBugTracker]] |
                None) = None

        if request is not None:
            try:
                cache = request._bug_trackers_for_review_request  # type:ignore
            except AttributeError:
                cache = {}
                request._bug_trackers_for_review_request = cache  # type:ignore

            assert cache is not None

            try:
                return cache[cache_key]
            except KeyError:
                pass

        model = self.model
        repository = review_request.repository

        if repository is not None:
            scope_q = (
                Q(apply_to=model.APPLY_TO_ALL) |
                (Q(apply_to=model.APPLY_TO_SELECTED_REPOS) &
                 Q(repositories=repository))
            )

            if repository.default_bug_tracker_id is not None:
                scope_q |= Q(pk=repository.default_bug_tracker_id)
        else:
            scope_q = Q(apply_to__in=[model.APPLY_TO_ALL,
                                      model.APPLY_TO_NO_REPOS])

        queryset = (
            self.filter(
                Q(enabled=True) &
                Q(local_site=review_request.local_site_id) &
                scope_q)
            .distinct()
            .order_by('pk')
        )

        trackers = [
            tracker
            for tracker in queryset
            if tracker.is_usable_by(user, request=request)
        ]

        if cache is not None:
            cache[cache_key] = trackers

        return trackers

    def get_sentinel(self) -> ConfiguredBugTracker:
        """Return the sentinel bug tracker, creating it if needed.

        The sentinel is a hidden, disabled tracker that unattributed
        :py:class:`~reviewboard.reviews.models.bug.Bug` rows point at.
        It carries no settings, no access control, and is excluded from
        all listings.

        There is no unique constraint backing the sentinel. If concurrent
        callers race to create it, the row with the lowest ID wins
        deterministically and any extra rows are inert.

        Returns:
            reviewboard.hostingsvcs.models.ConfiguredBugTracker:
            The sentinel bug tracker.
        """
        from reviewboard.hostingsvcs.models import \
            SENTINEL_BUG_TRACKER_SERVICE_NAME

        base_queryset = (
            self.filter(service_name=SENTINEL_BUG_TRACKER_SERVICE_NAME,
                        local_site=None)
            .order_by('pk')
        )

        sentinel = base_queryset.first()

        if sentinel is None:
            self.create(
                name='Unattributed Bugs',
                service_name=SENTINEL_BUG_TRACKER_SERVICE_NAME,
                enabled=False,
                apply_to=self.model.APPLY_TO_NO_REPOS)

            sentinel = base_queryset.first()
            assert sentinel is not None

        return sentinel

    def with_linked_bugs(
        self,
        review_request_details: BaseReviewRequestDetails,
        *,
        request: (HttpRequest | None) = None,
    ) -> Sequence[ConfiguredBugTracker]:
        """Return the trackers with bugs linked to a review request or draft.

        The sentinel tracker is never included. Unattributed bugs have no
        tracker of their own to render.

        Results are cached on ``request`` when one is provided. Callers
        must not use this across a change to the linked bugs.

        Version Added:
            9.0

        Args:
            review_request_details (reviewboard.reviews.models.
                                    base_review_request_details.
                                    BaseReviewRequestDetails):
                The review request or draft to look up trackers for.

            request (django.http.HttpRequest, optional):
                The HTTP request, used for caching.

        Returns:
            list of reviewboard.hostingsvcs.models.ConfiguredBugTracker:
            The bug trackers with bugs linked to the review request or
            draft.
        """
        from reviewboard.hostingsvcs.models import \
            SENTINEL_BUG_TRACKER_SERVICE_NAME

        details = review_request_details
        cache_key = (details._meta.label, details.pk)
        cache: (dict[tuple[str, int], Sequence[ConfiguredBugTracker]] |
                None) = None

        if request is not None:
            try:
                cache = request._bug_trackers_with_linked_bugs  # type:ignore
            except AttributeError:
                cache = {}
                request._bug_trackers_with_linked_bugs = cache  # type:ignore

            assert cache is not None

            try:
                return cache[cache_key]
            except KeyError:
                pass

        trackers = list(
            self.filter(bugs__in=details.bugs.all())
            .exclude(service_name=SENTINEL_BUG_TRACKER_SERVICE_NAME)
            .distinct()
        )

        if cache is not None:
            cache[cache_key] = trackers

        return trackers
