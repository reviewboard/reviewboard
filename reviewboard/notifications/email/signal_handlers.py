"""E-mail notification callbacks."""

from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils import six, timezone
from django.utils.datastructures import MultiValueDict
from django.utils.six.moves.urllib.parse import urljoin
from djblets.mail.utils import (build_email_address,
                                build_email_address_for_user)
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin.server import build_server_url, get_server_url
from reviewboard.notifications.email.hooks import \
    filter_email_recipients_from_hooks
from reviewboard.notifications.email.message import EmailMessage
from reviewboard.notifications.email.utils import (build_recipients,
                                                   recipients_to_addresses)
from reviewboard.reviews.models import Group
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.reviews.views import build_diff_comment_fragments


def _ensure_unicode(text):
    """Return a unicode object for the given text.

    Args:
        text (bytes or unicode):
            The text to decode.

    Returns:
        unicode: The decoded text.
    """
    if isinstance(text, bytes):
        text = text.decode('utf-8')

    return text


def review_request_closed_cb(sender, user, review_request, type, **kwargs):
    """Send e-mail when a review request is closed.

    Listens to the
    :py:data:`~reviewboard.reviews.signals.review_request_closed` signal and
    sends an e-mail if this type of notification is enabled (through the
    ``mail_send_review_close_mail`` site configuration setting).
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if siteconfig.get('mail_send_review_close_mail'):
        mail_review_request(review_request, user, close_type=type)


def review_request_published_cb(sender, user, review_request, trivial,
                                changedesc, **kwargs):
    """Send e-mail when a review request is published.

    Listens to the
    :py:data:`~reviewboard.reviews.signals.review_request_published` signal and
    sends an e-mail if this type of notification is enabled through the
    ``mail_send_review_mail`` site configuration setting).
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if siteconfig.get('mail_send_review_mail') and not trivial:
        mail_review_request(review_request, user, changedesc)


def review_published_cb(sender, user, review, to_submitter_only, request,
                        **kwargs):
    """Send e-mail when a review is published.

    Listens to the :py:data:`~reviewboard.reviews.signals.review_published`
    signal and sends e-mail if this type of notification is enabled through the
    ``mail_send_review_mail`` site configuration setting).
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if siteconfig.get('mail_send_review_mail'):
        mail_review(review, user, to_submitter_only, request)


def reply_published_cb(sender, user, reply, trivial, **kwargs):
    """Send e-mail when a review reply is published.

    Listens to the :py:data:`~reviewboard.reviews.signals.reply_published`
    signal and sends an e-mail if this type of notification is enabled (through
    ``mail_send_review_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if siteconfig.get('mail_send_review_mail') and not trivial:
        mail_reply(reply, user)


def user_registered_cb(user, **kwargs):
    """Send e-mail when a user is registered.

    Listens for new user registrations and sends a new user registration
    e-mail to administrators, if this type of notification is enabled (through
    ``mail_send_new_user_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if siteconfig.get('mail_send_new_user_mail'):
        mail_new_user(user)


def webapi_token_saved_cb(instance, created, **kwargs):
    """Send e-mail when an API token is created or updated.

    Args:
        instance (reviewboard.webapi.models.WebAPIToken):
            The token that has been created or updated.

        created (bool):
            Whether or not the token is created.

        **kwargs (dict):
            Unused keyword arguments provided by the signal.
    """
    # Unlike the other handlers, we always want to send e-mails for new
    # tokens, as a security measure.
    if created:
        op = 'created'
    else:
        op = 'updated'

    mail_webapi_token(instance, op)


def webapi_token_deleted_cb(instance, **kwargs):
    """Send e-mail when an API token is deleted.

    Args:
        instance (reviewboard.webapi.models.WebAPIToken):
            The token that has been deleted.

        **kwargs (dict):
            Unused keyword arguments provided by the signal.
    """
    # Unlike the other handlers, we always want to send e-mails for new
    # tokens, as a security measure.
    mail_webapi_token(instance, 'deleted')


def send_review_mail(user, review_request, subject, in_reply_to,
                     to_field, cc_field, text_template_name,
                     html_template_name, context=None, extra_headers=None):
    """Format and send an e-mail out.

    Args:
        user (django.contrib.auth.models.User):
            The user who is sending the e-mail.

        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request that the e-mail is about.

        subject (unicode):
            The subject of the e-mail address.

        in_reply_to (unicode):
            The e-mail message ID for threading.

        to_field (list):
            The recipients to send the e-mail to. This should be a list of
            :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>`.

        cc_field (list):
            The addresses to be CC'ed on the e-mail. This should be a list of
            :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>`.

        text_template_name (unicode):
            The name for the text e-mail template.

        html_template_name (unicode):
            The name for the HTML e-mail template.

        context (dict):
            Optional extra context to provide to the template.

        extra_headers (dict):
            Either a dict or
            :py:class:`~django.utils.datastructures.MultiValueDict` providing
            additional headers to send with the e-mail.

    Returns:
        unicode: The resulting e-mail message ID.
    """
    local_site = review_request.local_site
    from_email = build_email_address_for_user(user)

    to_field = recipients_to_addresses(to_field, review_request.id)
    cc_field = recipients_to_addresses(cc_field, review_request.id) - to_field

    if not user.should_send_own_updates():
        user_email = build_email_address_for_user(user)
        to_field.discard(user_email)
        cc_field.discard(user_email)

    if not to_field and not cc_field:
        # Nothing to send.
        return

    if not context:
        context = {}

    context['user'] = user
    context['site_url'] = get_server_url()
    context['review_request'] = review_request

    if review_request.local_site:
        context['local_site_name'] = review_request.local_site.name

    text_body = render_to_string(text_template_name, context)
    html_body = render_to_string(html_template_name, context)

    base_url = get_server_url(local_site=local_site)

    headers = MultiValueDict({
        'X-ReviewBoard-URL': [base_url],
        'X-ReviewRequest-URL': [urljoin(base_url,
                                        review_request.get_absolute_url())],
        'X-ReviewGroup': [', '.join(group.name for group in
                                    review_request.target_groups.all())],
    })

    if extra_headers:
        if not isinstance(extra_headers, MultiValueDict):
            extra_headers = MultiValueDict(
                (key, [value])
                for (key, value) in six.iteritems(extra_headers)
            )

        headers.update(extra_headers)

    if review_request.repository:
        headers['X-ReviewRequest-Repository'] = review_request.repository.name

    latest_diffset = review_request.get_latest_diffset()

    if latest_diffset:
        modified_files = set()

        for filediff in latest_diffset.files.all():
            if filediff.deleted or filediff.copied or filediff.moved:
                modified_files.add(filediff.source_file)

            if filediff.is_new or filediff.copied or filediff.moved:
                modified_files.add(filediff.dest_file)

        for filename in modified_files:
            headers.appendlist('X-ReviewBoard-Diff-For', filename)

    subject = subject.strip()
    to_field = list(to_field)
    cc_field = list(cc_field)

    if settings.DEFAULT_FROM_EMAIL:
        sender = build_email_address(full_name=user.get_full_name(),
                                     email=settings.DEFAULT_FROM_EMAIL)
    else:
        sender = None

    message = EmailMessage(subject=subject,
                           text_body=text_body.encode('utf-8'),
                           html_body=html_body.encode('utf-8'),
                           from_email=from_email,
                           sender=sender,
                           to=to_field,
                           cc=cc_field,
                           in_reply_to=in_reply_to,
                           headers=headers)

    try:
        message.send()
    except Exception:
        logging.exception("Error sending e-mail notification with subject "
                          "'%s' on behalf of '%s' to '%s'",
                          subject,
                          from_email,
                          ','.join(to_field + cc_field))

    return message.message_id


def mail_review_request(review_request, from_user=None, changedesc=None,
                        close_type=None):
    """Send an e-mail representing the supplied review request.

    Args:
        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request to send an e-mail about.

        from_user (django.contrib.auth.models.User):
            The user who triggered the e-mail (i.e., they published or closed
            the review request).

        changedesc (reviewboard.changedescs.models.ChangeDescription):
            An optional change description showing what has changed in the
            review request, possibly with explanatory text from the submitter.
            This is created when saving a draft on a public review request and
            will be ``None`` when publishing initially. This is used by the
            template to add contextual (updated) flags to inform people what
            has changed.

        close_type (unicode):
            How the review request was closed or ``None`` if it was published.
            If this is not ``None`` it must be one of
            :py:attr:`~reviewboard.reviews.models.ReviewRequest.SUBMITTED` or
            :py:attr:`~reviewboard.reviews.models.ReviewRequest.DISCARDED`.
    """
    # If the review request is not yet public or has been discarded, don't send
    # any mail. Relax the "discarded" rule when e-mails are sent on closing
    # review requests.
    if (not review_request.public or
        (not close_type and review_request.status == 'D')):
        return

    if not from_user:
        from_user = review_request.submitter

    summary = _ensure_unicode(review_request.summary)
    subject = "Review Request %d: %s" % (review_request.display_id,
                                         summary)
    reply_message_id = None

    if review_request.email_message_id:
        # Fancy quoted "replies"
        subject = "Re: " + subject
        reply_message_id = review_request.email_message_id
        extra_recipients = review_request.participants
    else:
        extra_recipients = None

    extra_context = {}

    if close_type:
        changedesc = review_request.changedescs.filter(public=True).latest()

    limit_recipients_to = None

    if changedesc:
        extra_context['change_text'] = changedesc.text
        extra_context['change_rich_text'] = changedesc.rich_text
        extra_context['changes'] = changedesc.fields_changed

        fields_changed = changedesc.fields_changed
        changed_field_names = set(fields_changed.keys())

        if (changed_field_names and
            changed_field_names.issubset(['target_people', 'target_groups'])):
            # If the only changes are to the target reviewers, try to send a
            # much more targeted e-mail (rather than sending it out to
            # everyone, only send it to new people).
            limit_recipients_to = set()

            if 'target_people' in changed_field_names:
                user_pks = [
                    item[2]
                    for item in fields_changed['target_people']['added']
                ]

                limit_recipients_to.update(User.objects.filter(
                    pk__in=user_pks))

            if 'target_groups' in changed_field_names:
                group_pks = [
                    item[2]
                    for item in fields_changed['target_groups']['added']
                ]

                limit_recipients_to.update(Group.objects.filter(
                    pk__in=group_pks))

    to_field, cc_field = build_recipients(from_user, review_request,
                                          extra_recipients,
                                          limit_recipients_to)

    extra_filter_kwargs = {}

    if close_type:
        signal = review_request_closed
        extra_filter_kwargs['close_type'] = close_type
    else:
        signal = review_request_published

    to_field, cc_field = filter_email_recipients_from_hooks(
        to_field, cc_field, signal, review_request=review_request,
        user=from_user, **extra_filter_kwargs)

    review_request.time_emailed = timezone.now()
    review_request.email_message_id = \
        send_review_mail(from_user, review_request, subject,
                         reply_message_id, to_field, cc_field,
                         'notifications/review_request_email.txt',
                         'notifications/review_request_email.html',
                         extra_context)
    review_request.save()


def mail_review(review, user, to_submitter_only, request):
    """Send an e-mail representing the supplied review.

    Args:
        review (reviewboard.reviews.models.Review):
            The review to send an e-mail about.

        user (django.contrib.auth.models.User):
            The user who published the review.

        to_submitter_only (bool):
            Determines if the review is to the submitter only or not.

        request (django.http.HttpRequest):
            The request object if the review was published from an HTTP
            request.
    """
    review_request = review.review_request

    if not review_request.public:
        return

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    has_issues = (review.ship_it and
                  review.has_comments(only_issues=True))

    extra_context = {
        'user': review.user,
        'review': review,
        'has_issues': has_issues,
        'request': request,
    }

    extra_headers = {}

    if review.ship_it:
        extra_headers['X-ReviewBoard-ShipIt'] = '1'

        if review.ship_it_only:
            extra_headers['X-ReviewBoard-ShipIt-Only'] = '1'

    has_error, extra_context['comment_entries'] = \
        build_diff_comment_fragments(
            review.ordered_comments, extra_context,
            "notifications/email_diff_comment_fragment.html")

    reviewer = review.user

    limit_to = None

    if to_submitter_only:
        limit_to = set([review_request.submitter, review.user])

    to_field, cc_field = build_recipients(reviewer, review_request,
                                          limit_recipients_to=limit_to)

    to_field, cc_field = filter_email_recipients_from_hooks(
        to_field, cc_field, review_published, review=review, user=user,
        review_request=review_request, to_submitter_only=to_submitter_only)

    summary = _ensure_unicode(review_request.summary)

    review.email_message_id = send_review_mail(
        reviewer,
        review_request,
        ('Re: Review Request %d: %s'
         % (review_request.display_id, summary)),
        review_request.email_message_id,
        to_field,
        cc_field,
        'notifications/review_email.txt',
        'notifications/review_email.html',
        extra_context,
        extra_headers=extra_headers)

    review.time_emailed = timezone.now()
    review.save()


def mail_reply(reply, user):
    """Send an e-mail representing the supplied reply to a review.

    Args:
        reply (reviewboard.reviews.models.Review):
            The review reply to send an e-mail about.
    """
    review = reply.base_reply_to
    review_request = review.review_request

    if not review_request.public:
        return

    extra_context = {
        'user': reply.user,
        'review': review,
        'reply': reply,
    }

    has_error, extra_context['comment_entries'] = \
        build_diff_comment_fragments(
            reply.comments.order_by('filediff', 'first_line'),
            extra_context,
            "notifications/email_diff_comment_fragment.html")

    reviewer = reply.user

    to_field, cc_field = build_recipients(reviewer, review_request,
                                          review_request.participants)

    to_field, cc_field = filter_email_recipients_from_hooks(
        to_field, cc_field, reply_published, reply=reply, user=user,
        review=review, review_request=review_request)

    summary = _ensure_unicode(review_request.summary)

    reply.email_message_id = send_review_mail(
        user,
        review_request,
        ('Re: Review Request %d: %s'
         % (review_request.display_id, summary)),
        review.email_message_id,
        to_field,
        cc_field,
        'notifications/reply_email.txt',
        'notifications/reply_email.html',
        extra_context)

    reply.time_emailed = timezone.now()
    reply.save()


def mail_new_user(user):
    """Send an e-mail to administrators for newly registered users.

    Args:
        user (django.contrib.auth.models.User):
            The user to send an e-mail about.
    """
    subject = "New Review Board user registration for %s" % user.username
    from_email = build_email_address_for_user(user)

    context = {
        'site_url': get_server_url(),
        'user': user,
        'user_url': reverse('admin:auth_user_change', args=(user.id,))
    }

    text_message = render_to_string('notifications/new_user_email.txt',
                                    context)
    html_message = render_to_string('notifications/new_user_email.html',
                                    context)

    message = EmailMessage(
        subject=subject.strip(),
        text_body=text_message,
        html_body=html_message,
        from_email=settings.SERVER_EMAIL,
        sender=settings.SERVER_EMAIL,
        to=[
            build_email_address(full_name=admin[0],
                                email=admin[1])
            for admin in settings.ADMINS
        ])

    try:
        message.send()
    except Exception as e:
        logging.error("Error sending e-mail notification with subject '%s' on "
                      "behalf of '%s' to admin: %s",
                      subject.strip(), from_email, e, exc_info=1)


def mail_webapi_token(webapi_token, op):
    """Send an e-mail about an API token update.

    This will inform the user about a newly-created, updated, or deleted
    token.

    Args:
        webapi_token (reviewboard.webapi.models.WebAPIToken):
            The API token the e-mail is about.

        op (unicode):
            The operation the email is about. This is one of
            ``created``, ``updated``, or ``deleted``.

    Raises:
        ValueError:
            The provided ``op`` argument was invalid.
    """
    if op == 'created':
        subject = 'New Review Board API token created'
        template_name = 'notifications/api_token_created'
    elif op == 'updated':
        subject = 'Review Board API token updated'
        template_name = 'notifications/api_token_updated'
    elif op == 'deleted':
        subject = 'Review Board API token deleted'
        template_name = 'notifications/api_token_deleted'
    else:
        raise ValueError('Unexpected op "%s" passed to mail_webapi_token.'
                         % op)

    user = webapi_token.user
    user_email = build_email_address_for_user(user)

    context = {
        'api_token': webapi_token,
        'site_url': get_server_url(),
        'api_token_url': '%s#api-tokens'
                         % build_server_url(reverse('user-preferences')),
        'partial_token': '%s...' % webapi_token.token[:10],
        'user': user,
    }

    text_message = render_to_string('%s.txt' % template_name, context)
    html_message = render_to_string('%s.html' % template_name, context)

    message = EmailMessage(
        subject=subject,
        text_body=text_message,
        html_body=html_message,
        from_email=settings.SERVER_EMAIL,
        sender=settings.SERVER_EMAIL,
        to=[user_email])

    try:
        message.send()
    except Exception as e:
        logging.exception("Error sending API Token e-mail with subject '%s' "
                          "from '%s' to '%s': %s",
                          subject, settings.SERVER_EMAIL, user_email, e)


def mail_password_changed(user):
    """Send an e-mail when a user's password changes.

    Args:
        user (django.contrib.auth.model.User):
            The user whose password changed.
    """
    api_token_url = (
        '%s#api-tokens'
        % build_server_url(reverse('user-preferences'))
    )
    server_url = get_server_url()

    context = {
        'api_token_url': api_token_url,
        'has_api_tokens': user.webapi_tokens.exists(),
        'server_url': server_url,
        'user': user,
    }

    user_email = build_email_address_for_user(user)
    text_body = render_to_string('notifications/password_changed.txt', context)
    html_body = render_to_string('notifications/password_changed.html',
                                 context)

    message = EmailMessage(
        subject='Password changed for user "%s" on %s' % server_url,
        text_body=text_body,
        html_body=html_body,
        from_email=settings.SERVER_EMAIL,
        sender=settings.SERVER_EMAIL,
        to=user_email,
    )

    try:
        message.send()
    except Exception as e:
        logging.exception('Failed to send password changed email to %s: %s',
                          user.username, e)
