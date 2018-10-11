"""Utilities for sending e-mail messages."""

from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.db.models import Q
from djblets.mail.utils import (build_email_address,
                                build_email_address_for_user)

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.reviews.models import Group


def build_recipients(user, review_request, extra_recipients=None,
                     limit_recipients_to=None):
    """Build the recipient sets for an e-mail.

    By default, the user sending the e-mail, the review request submitter (if
    they are active), all active reviewers, and all active members of review
    groups will be recipients of the e-mail.

    If the ``limit_recipients_to`` parameter is provided, the given ``user``
    and the review request submitter (if active) will still be recipients of
    the e-mail, but all reviewers and members of review groups will not.
    Instead, the recipients given in ``limit_recipients_to`` will be used.

    Args:
        user (django.contrib.auth.models.User):
            The user sending the e-mail.

        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request the e-mail corresponds to.

        extra_recipients (list):
            An optional list of extra recipients as
            :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>` that will
            receive the e-mail.

        limit_recipients_to (list):
            An optional list of recipients as
            :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>` who will
            receive the e-mail in place of the normal recipients.

    Returns:
        tuple:
        A 2-tuple of the To field and the CC field, as sets of
        :py:class:`Users <django.contrib.auth.models.User>` and
        :py:class:`Groups <reviewboard.reviews.models.Group>`.
    """
    recipients = set()
    to_field = set()

    local_site = review_request.local_site_id
    submitter = review_request.submitter

    target_people = review_request.target_people.filter(is_active=True).extra(
        select={
            'visibility': """
                SELECT accounts_reviewrequestvisit.visibility
                  FROM accounts_reviewrequestvisit
                 WHERE accounts_reviewrequestvisit.review_request_id =
                       reviews_reviewrequest_target_people.reviewrequest_id
                   AND accounts_reviewrequestvisit.user_id =
                       reviews_reviewrequest_target_people.user_id
            """
        })

    starred_users = User.objects.filter(
        is_active=True,
        profile__starred_review_requests=review_request,
        profile__should_send_email=True)

    local_site_q = Q()

    if local_site:
        # Filter out users who are on the reviewer list in some form or have
        # starred the review request but are no longer part of the LocalSite.
        local_site_q = (Q(local_site=local_site) |
                        Q(local_site_admins=local_site))

        target_people = target_people.filter(local_site_q)

        starred_users = starred_users.filter(local_site_q)

    if not extra_recipients:
        extra_recipients = User.objects.none()

    if user.should_send_email():
        recipients.add(user)

    try:
        changedesc = review_request.changedescs.latest()
    except ChangeDescription.DoesNotExist:
        pass
    else:
        # If the submitter has changed and the person sending this e-mail is
        # not the original submitter, then we should include them in the list
        # of recipients.
        if changedesc.fields_changed:
            submitter_info = changedesc.fields_changed.get('submitter')

            if submitter_info:
                prev_submitter_pk = submitter_info['old'][0][2]
                prev_submitter = User.objects.get(pk=prev_submitter_pk)

                if (prev_submitter.is_active and
                    prev_submitter.should_send_email()):
                    recipients.add(prev_submitter)

    if submitter.is_active and submitter.should_send_email():
        recipients.add(submitter)

    recipients.update(starred_users)

    def _filter_recipients(to_filter):
        """Filter the given recipients.

        All groups will be added to the resulting recipients. Only users with a
        matching local site will be added to the resulting recipients.

        Args:
            to_filter (list):
                A list of recipients as
                :py:class:`Users <django.contrib.auth.models.User>` and
                :py:class:`Groups <reviewboard.reviews.models.Group>`.
        """
        pks = set()

        for recipient in to_filter:
            if isinstance(recipient, User):
                pks.add(recipient.pk)
            elif isinstance(recipient, Group):
                recipients.add(recipient)
            else:
                logging.error(
                    'Unexpected e-mail recipient %r; expected '
                    'django.contrib.auth.models.User or '
                    'reviewboard.reviews.models.Group.',
                    recipient)
        if pks:
            filtered_users = User.objects.filter(
                Q(is_active=True, pk__in=pks),
                local_site_q)

            recipients.update(
                recipient
                for recipient in filtered_users.select_related('profile')
                if recipient.should_send_email()
            )

    if limit_recipients_to is not None:
        _filter_recipients(limit_recipients_to)
    else:
        _filter_recipients(extra_recipients)

        to_field.update(
            recipient
            for recipient in target_people.select_related('profile')
            if (recipient.should_send_email() and
                recipient.visibility != ReviewRequestVisit.MUTED)
        )

        recipients.update(to_field)
        recipients.update(review_request.target_groups.all())

    if not user.should_send_own_updates():
        recipients.discard(user)
        to_field.discard(user)

    if to_field:
        cc_field = recipients.symmetric_difference(to_field)
    else:
        to_field = recipients
        cc_field = set()

    return to_field, cc_field


def get_email_addresses_for_group(group, review_request_id=None):
    """Build a list of e-mail addresses for the group.

    Args:
        group (reviewboard.reviews.models.Group):
            The review group to build the e-mail addresses for.

        review_request_id (int, optional):


    Returns:
        list of unicode:
        A list of properly formatted e-mail addresses for all users in the
        review group.
    """
    addresses = []

    if group.mailing_list:
        if ',' not in group.mailing_list:
            # The mailing list field has only one e-mail address in it,
            # so we can just use that and the group's display name.
            addresses = [build_email_address(full_name=group.display_name,
                                             email=group.mailing_list)]
        else:
            # The mailing list field has multiple e-mail addresses in it.
            # We don't know which one should have the group's display name
            # attached to it, so just return their custom list as-is.
            addresses = group.mailing_list.split(',')

    if not (group.mailing_list and group.email_list_only):
        users_q = Q(is_active=True)

        local_site = group.local_site

        if local_site:
            users_q = users_q & (Q(local_site=local_site) |
                                 Q(local_site_admins=local_site))

        users = group.users.filter(users_q).select_related('profile')

        if review_request_id:
            users = users.extra(select={
                'visibility': """
                    SELECT accounts_reviewrequestvisit.visibility
                      FROM accounts_reviewrequestvisit
                     WHERE accounts_reviewrequestvisit.review_request_id =
                           %s
                       AND accounts_reviewrequestvisit.user_id =
                           reviews_group_users.user_id
                """ % review_request_id
            })

        addresses.extend([
            build_email_address_for_user(u)
            for u in users
            if (u.should_send_email() and
                (not review_request_id or
                 u.visibility != ReviewRequestVisit.MUTED))
        ])

    return addresses


def recipients_to_addresses(recipients, review_request_id=None):
    """Return the set of e-mail addresses for the recipients.

    Args:
        recipients (list):
            A list of :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>`.

    Returns:
        set: The e-mail addresses for all recipients.
    """
    addresses = set()

    for recipient in recipients:
        assert isinstance(recipient, User) or isinstance(recipient, Group)

        if isinstance(recipient, User):
            addresses.add(build_email_address_for_user(recipient))
        else:
            addresses.update(get_email_addresses_for_group(recipient,
                                                           review_request_id))

    return addresses


def send_email(email_builder, **kwargs):
    """Attempt to send an e-mail, logging any exceptions that occur.

    Args:
        email_builder (callable):
            A function that generates an :py:class:`EmailMessage`.

        **kwargs (dict):
            Keyword arguments to provide to ``email_builder``.

    Returns:
        tuple:
        A tuple of:

        * The message that was generated (:py:class`EmailMessage`).
        * Whether or not the message was sent successfully (:py:class:`bool`).
    """
    message = email_builder(**kwargs)

    if message is None:
        return None, False

    try:
        message.send()
    except Exception:
        logging.exception(
            'Could not send e-mail message with subject "%s" from "%s" to '
            '"%s"',
            message.subject,
            message.from_email,
            message.to + (message.cc or []))

        return message, False

    return message, True
