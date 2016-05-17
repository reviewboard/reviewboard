from __future__ import absolute_import, unicode_literals

import email
import logging
from email.utils import formataddr
from collections import defaultdict

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.db.models.signals import post_delete, post_save
from django.template.loader import render_to_string
from django.utils import six, timezone
from django.utils.datastructures import MultiValueDict
from django.utils.six.moves.urllib.parse import urljoin
from djblets.siteconfig.models import SiteConfiguration
from djblets.auth.signals import user_registered

from reviewboard.accounts.models import ReviewRequestVisit
from reviewboard.admin.server import get_server_url
from reviewboard.reviews.models import Group, ReviewRequest, Review
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.reviews.views import build_diff_comment_fragments
from reviewboard.webapi.models import WebAPIToken


# A mapping of signals to EmailHooks.
_hooks = defaultdict(set)


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


def register_email_hook(signal, handler):
    """Register an e-mail hook.

    Args:
        signal (django.dispatch.Signal):
            The signal that will trigger the e-mail to be sent. This is one of
            :py:data:`~reviewboard.reviews.signals.review_request_published`,
            :py:data:`~reviewboard.reviews.signals.review_request_closed`,
            :py:data:`~reviewboard.reviews.signals.review_published`, or
            :py:data:`~reviewboard.reviews.signals.reply_published`.

        handler (reviewboard.extensions.hooks.EmailHook):
            The ``EmailHook`` that will be triggered when an e-mail of the
            chosen type is about to be sent.
    """
    assert signal in (review_request_published, review_request_closed,
                      review_published, reply_published), (
        'Invalid signal %r' % signal)

    _hooks[signal].add(handler)


def unregister_email_hook(signal, handler):
    """Unregister an e-mail hook.

    Args:
        signal (django.dispatch.Signal):
            The signal that will trigger the e-mail to be sent. This is one of
            :py:data:`~reviewboard.reviews.signals.review_request_published`,
            :py:data:`~reviewboard.reviews.signals.review_request_closed`,
            :py:data:`~reviewboard.reviews.signals.review_published`, or
            :py:data:`~reviewboard.reviews.signals.reply_published`.

        handler (reviewboard.extensions.hooks.EmailHook):
            The ``EmailHook`` that will be triggered when an e-mail of the
            chosen type is about to be sent.
    """
    assert signal in (review_request_published, review_request_closed,
                      review_published, reply_published), (
        'Invalid signal %r' % signal)

    _hooks[signal].discard(handler)


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


def review_published_cb(sender, user, review, **kwargs):
    """Send e-mail when a review is published.

    Listens to the :py:data:`~reviewboard.reviews.signals.review_published`
    signal and sends e-mail if this type of notification is enabled through the
    ``mail_send_review_mail`` site configuration setting).
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if siteconfig.get('mail_send_review_mail'):
        mail_review(review, user)


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


def connect_signals():
    """Connect e-mail callbacks to signals."""
    review_request_published.connect(review_request_published_cb,
                                     sender=ReviewRequest)
    review_published.connect(review_published_cb, sender=Review)
    reply_published.connect(reply_published_cb, sender=Review)
    review_request_closed.connect(review_request_closed_cb,
                                  sender=ReviewRequest)
    user_registered.connect(user_registered_cb)
    post_save.connect(webapi_token_saved_cb, sender=WebAPIToken)
    post_delete.connect(webapi_token_deleted_cb, sender=WebAPIToken)


def build_email_address(fullname, email):
    """Build an e-mail address for the name and e-mail address.

    Args:
        fullname (unicode):
            The full name associated with the e-mail address (or ``None``).

        email (unicode):
            The e-mail address.

    Returns:
        unicode: A properly formatted e-mail address.
    """
    return formataddr((fullname, email))


def get_email_address_for_user(user):
    """Build an e-mail address for the given user.

    Args:
        user (django.contrib.auth.models.User):
            The user.

    Returns:
        unicode: A properly formatted e-mail address for the user.
    """
    return build_email_address(user.get_full_name(), user.email)


def get_email_addresses_for_group(group, review_request_id=None):
    """Build a list of e-mail addresses for the group.

    Args:
        group (reviewboard.reviews.models.Group):
            The review group to build the e-mail addresses for.

    Returns:
        list: A list of properly formatted e-mail addresses for all users in
        the review group.
    """
    addresses = []

    if group.mailing_list:
        if ',' not in group.mailing_list:
            # The mailing list field has only one e-mail address in it,
            # so we can just use that and the group's display name.
            addresses =  [build_email_address(group.display_name,
                                              group.mailing_list)]
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
            get_email_address_for_user(u)
            for u in users
            if (u.should_send_email() and
                (not review_request_id or
                 u.visibility != ReviewRequestVisit.MUTED))
        ])

    return addresses


class SpiffyEmailMessage(EmailMultiAlternatives):
    """An EmailMessage subclass with improved header and message ID support.

    This also knows about several headers (standard and variations),
    including ``Sender``/``X-Sender``, ``In-Reply-To``/``References``, and
    ``Reply-To``.

    The generated ``Message-ID`` header from the e-mail can be accessed
    through the :py:attr:`message_id` attribute after the e-mail is sent.

    This class also supports repeated headers.
    """

    def __init__(self, subject, text_body, html_body, from_email, sender,
                 to, cc=None, in_reply_to=None, headers=None):
        siteconfig = SiteConfiguration.objects.get_current()

        headers = headers or MultiValueDict()

        if (isinstance(headers, dict) and
            not isinstance(headers, MultiValueDict)):
            # Instantiating a MultiValueDict from a dict does not ensure that
            # the values are lists, so we have to do that ourselves.
            headers = MultiValueDict(dict(
                (key, [value])
                for key, value in six.iteritems(headers)
            ))

        if sender:
            headers['Sender'] = sender
            headers['X-Sender'] = sender

        if in_reply_to:
            headers['In-Reply-To'] = in_reply_to
            headers['References'] = in_reply_to

        headers['Reply-To'] = from_email

        # If enabled (through 'mail_enable_autogenerated_header' site
        # configuration), mark the mail as 'auto-generated' (according to
        # RFC 3834) to hopefully avoid auto replies.
        if siteconfig.get("mail_enable_autogenerated_header"):
            headers['Auto-Submitted'] = 'auto-generated'

        # Prevent Exchange from sending auto-replies for delivery reports,
        # read receipts, Out of Office e-mails, and other general auto-replies.
        headers['X-Auto-Response-Suppress'] = 'DR, RN, OOF, AutoReply'

        super(SpiffyEmailMessage, self).__init__(
            subject, text_body, settings.DEFAULT_FROM_EMAIL, to,
            headers={
                'From': from_email,
            })

        self.cc = cc or []
        self.message_id = None

        # We don't want to use the regular extra_headers attribute because
        # it will be treated as a plain dict by Django. Instead, since we're
        # using a MultiValueDict, we store it in a separate attribute
        # attribute and handle adding our headers in the message method.
        self.rb_headers = headers

        self.attach_alternative(html_body, "text/html")

    def message(self):
        msg = super(SpiffyEmailMessage, self).message()
        self.message_id = msg['Message-ID']

        for name, value_list in self.rb_headers.iterlists():
            for value in value_list:
                msg.add_header(six.binary_type(name), value)

        return msg

    def recipients(self):
        """Returns a list of all recipients of the e-mail. """
        return self.to + self.bcc + self.cc


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
        tuple: A 2-tuple of the To field and the CC field, as sets of
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
                for recipient in filtered_users.select_related('Profile')
                if recipient.should_send_email()
            )

    if limit_recipients_to is not None:
        _filter_recipients(limit_recipients_to)
    else:
        _filter_recipients(extra_recipients)

        target_people = target_people.filter(is_active=True)

        to_field.update(
            recipient
            for recipient in target_people.select_related('Profile')
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
            addresses.add(get_email_address_for_user(recipient))
        else:
            addresses.update(get_email_addresses_for_group(recipient,
                                                           review_request_id))

    return addresses


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
    current_site = Site.objects.get_current()
    local_site = review_request.local_site
    from_email = get_email_address_for_user(user)

    to_field = recipients_to_addresses(to_field, review_request.id)
    cc_field = recipients_to_addresses(cc_field, review_request.id) - to_field

    if not user.should_send_own_updates():
        user_email = get_email_address_for_user(user)
        to_field.discard(user_email)
        cc_field.discard(user_email)

    if not to_field and not cc_field:
        # Nothing to send.
        return

    siteconfig = current_site.config.get()
    domain_method = siteconfig.get("site_domain_method")

    if not context:
        context = {}

    context['user'] = user
    context['domain'] = current_site.domain
    context['domain_method'] = domain_method
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

    sender = None

    if settings.DEFAULT_FROM_EMAIL:
        sender = build_email_address(user.get_full_name(),
                                     settings.DEFAULT_FROM_EMAIL)

        if sender == from_email:
            # RFC 2822 states that we should only include Sender if the
            # two are not equal.
            sender = None

    message = SpiffyEmailMessage(subject.strip(),
                                 text_body.encode('utf-8'),
                                 html_body.encode('utf-8'),
                                 from_email, sender,
                                 list(to_field), list(cc_field),
                                 in_reply_to, headers)
    try:
        message.send()
    except Exception:
        logging.exception("Error sending e-mail notification with subject "
                          "'%s' on behalf of '%s' to '%s'",
                          subject.strip(),
                          from_email,
                          ','.join(list(to_field) + list(cc_field)))

    return message.message_id


def mail_review_request(review_request, user, changedesc=None,
                        close_type=None):
    """Send an e-mail representing the supplied review request.

    Args:
        review_request (reviewboard.reviews.models.ReviewRequest):
            The review request to send an e-mail about.

        user (django.contrib.auth.models.User):
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
    # review requests
    if (not review_request.public or
        (not close_type and review_request.status == 'D')):
        return

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

    submitter = review_request.submitter

    to_field, cc_field = build_recipients(submitter, review_request,
                                          extra_recipients,
                                          limit_recipients_to)

    extra_filter_kwargs = {}

    if close_type:
        signal = review_request_closed
        extra_filter_kwargs['close_type'] = close_type
    else:
        signal = review_request_published

    to_field, cc_field = filter_email_recipients_from_hooks(
        to_field, cc_field, signal, review_request=review_request, user=user,
        **extra_filter_kwargs)

    review_request.time_emailed = timezone.now()
    review_request.email_message_id = \
        send_review_mail(review_request.submitter, review_request, subject,
                         reply_message_id, to_field, cc_field,
                         'notifications/review_request_email.txt',
                         'notifications/review_request_email.html',
                         extra_context)
    review_request.save()


def mail_review(review, user):
    """Send an e-mail representing the supplied review.

    Args:
        review (reviewboard.reviews.models.Review):
            The review to send an e-mail about.
    """
    review_request = review.review_request

    if not review_request.public:
        return

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    has_issues = (
        review.comments.filter(issue_opened=True).exists() or
        review.file_attachment_comments.filter(issue_opened=True).exists() or
        review.screenshot_comments.filter(issue_opened=True).exists()
    )

    extra_context = {
        'user': review.user,
        'review': review,
        'has_issues': has_issues,
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

    to_field, cc_field = build_recipients(reviewer, review_request, None)

    to_field, cc_field = filter_email_recipients_from_hooks(
        to_field, cc_field, review_published, review=review, user=user,
        review_request=review_request)

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
    current_site = Site.objects.get_current()
    siteconfig = SiteConfiguration.objects.get_current()
    domain_method = siteconfig.get("site_domain_method")
    subject = "New Review Board user registration for %s" % user.username
    from_email = get_email_address_for_user(user)

    context = {
        'domain': current_site.domain,
        'domain_method': domain_method,
        'user': user,
        'user_url': reverse('admin:auth_user_change', args=(user.id,))
    }

    text_message = render_to_string('notifications/new_user_email.txt',
                                    context)
    html_message = render_to_string('notifications/new_user_email.html',
                                    context)

    message = SpiffyEmailMessage(subject.strip(), text_message, html_message,
                                 settings.SERVER_EMAIL, settings.SERVER_EMAIL,
                                 [build_email_address(*a)
                                  for a in settings.ADMINS], None, None)

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

    current_site = Site.objects.get_current()
    siteconfig = SiteConfiguration.objects.get_current()
    domain_method = siteconfig.get('site_domain_method')
    user = webapi_token.user
    user_email = get_email_address_for_user(user)

    context = {
        'api_token': webapi_token,
        'domain': current_site.domain,
        'domain_method': domain_method,
        'partial_token': '%s...' % webapi_token.token[:10],
        'user': user,
    }

    text_message = render_to_string('%s.txt' % template_name, context)
    html_message = render_to_string('%s.html' % template_name, context)

    message = SpiffyEmailMessage(
        subject,
        text_message,
        html_message,
        settings.SERVER_EMAIL,
        settings.SERVER_EMAIL,
        [user_email])

    try:
        message.send()
    except Exception as e:
        logging.exception("Error sending API Token e-mail with subject '%s' "
                          "from '%s' to '%s': %s",
                          subject, settings.SERVER_EMAIL, user_email, e)


def filter_email_recipients_from_hooks(to_field, cc_field, signal, **kwargs):
    """Filter the e-mail recipients through configured e-mail hooks.

    Args:
        to_field (set):
            The original To field of the e-mail, as a set of
            :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>`.

        cc_field (set):
            The original CC field of the e-mail, as a set of
            :py:class:`Users <django.contrib.auth.models.User>` and
            :py:class:`Groups <reviewboard.reviews.models.Group>`.

        signal (django.dispatch.Signal):
            The signal that triggered the e-mail.

        **kwargs (dict):
            Extra keyword arguments to pass to the e-mail hook.

    Returns:
        tuple: A 2-tuple of the To field and the CC field, as sets
        of :py:class:`Users <django.contrib.auth.models.User>` and
        :py:class:`Groups <reviewboard.reviews.models.Group>`.
    """
    if signal in _hooks:
        for hook in _hooks[signal]:
            to_field = hook.get_to_field(to_field, **kwargs)
            cc_field = hook.get_cc_field(cc_field, **kwargs)

    return to_field, cc_field


# Fixes bug #3613
_old_header_init = email.header.Header.__init__


def _unified_header_init(self, *args, **kwargs):
    kwargs['continuation_ws'] = b' '

    _old_header_init(self, *args, **kwargs)

email.header.Header.__init__ = _unified_header_init
