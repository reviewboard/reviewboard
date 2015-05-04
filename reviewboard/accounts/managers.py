from __future__ import unicode_literals

import logging

from django.db.models import Manager
from django.utils import six
from djblets.db.managers import ConcurrencyManager

from reviewboard.accounts.trophies import get_registered_trophy_types


class ProfileManager(Manager):
    """Manager for user profiles."""

    def get_or_create(self, user, *args, **kwargs):
        """Return the profile for the user.

        This will create the profile if one does not exist.
        """
        if hasattr(user, '_profile'):
            return user._profile, False

        profile, is_new = \
            super(ProfileManager, self).get_or_create(user=user, *args,
                                                      **kwargs)
        user._profile = profile

        return profile, is_new


class ReviewRequestVisitManager(ConcurrencyManager):
    """Manager for review request visits.

    Unarchives a specified review request for all users that have archived it.
    """

    def unarchive_all(self, review_request):
        """ Unarchives review request for all users.

        Unarchives the given review request for all users by changing all
        review request visit database entries for this review request from
        archived to visible.
        """
        queryset = self.filter(review_request=review_request,
                               visibility=self.model.ARCHIVED)
        queryset.update(visibility=self.model.VISIBLE)


class TrophyManager(Manager):
    """Manager for trophies.

    Creates new trophies, updates the database and fetches trophies from the
    database.
    """

    def compute_trophies(self, review_request):
        """Compute and return trophies for a review request.

        Computes trophies for a given review request by looping through all
        registered trophy types and seeing if any apply to the review request.

        If trophies are to be awarded, they are saved in the database and
        returned. If no trophies are to be awarded, an empty list is returned.
        """
        if 'calculated_trophies' in review_request.extra_data:
            return list(self.filter(review_request=review_request))

        calculated_trophy_types = []

        registered_trophy_types = get_registered_trophy_types()
        for registered_trophy_type in six.itervalues(registered_trophy_types):
            try:
                instance = registered_trophy_type()
            except Exception as e:
                logging.error('Error instantiating trophy type %r: %s',
                              registered_trophy_type, e, exc_info=1)
                continue

            try:
                if instance.qualifies(review_request):
                    calculated_trophy_types.append(instance)
            except Exception as e:
                logging.error('Error when running %r.instance_qualifies: %s',
                              registered_trophy_type, e, exc_info=1)

        trophies = [
            self.model.objects.create(category=trophy_type.category,
                                      review_request=review_request,
                                      local_site=review_request.local_site,
                                      user=review_request.submitter)
            for trophy_type in calculated_trophy_types
        ]

        review_request.extra_data['calculated_trophies'] = True
        review_request.save(update_fields=['extra_data'])

        return trophies

    def get_trophies(self, review_request):
        """Get all the trophies for a given review request."""
        return self.compute_trophies(review_request)
