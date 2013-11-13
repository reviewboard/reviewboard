from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.signals import user_registered
from reviewboard.reviews.models import ReviewRequest, Review
from reviewboard.reviews.signals import (review_request_published,
                                         review_published, reply_published,
                                         review_request_closed)
from reviewboard.reviews.views import build_diff_comment_fragments


def review_request_closed_cb(sender, user, review_request, **kwargs):
    """Sends e-mail when a review request is closed.

    Listens to the ``review_request_closed`` signal and sends an
    email if this type of notification is enabled (through
    ``mail_send_review_close_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()
    if siteconfig.get("mail_send_review_close_mail"):
        mail_review_request(review_request, on_close=True)


def review_request_published_cb(sender, user, review_request, changedesc,
                                **kwargs):
    """
    Listens to the ``review_request_published`` signal and sends an
    email if this type of notification is enabled (through
    ``mail_send_review_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()
    if siteconfig.get("mail_send_review_mail"):
        mail_review_request(review_request, changedesc)


def review_published_cb(sender, user, review, **kwargs):
    """
    Listens to the ``review_published`` signal and sends an email if
    this type of notification is enabled (through
    ``mail_send_review_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()
    if siteconfig.get("mail_send_review_mail"):
        mail_review(review)


def reply_published_cb(sender, user, reply, **kwargs):
    """
    Listens to the ``reply_published`` signal and sends an email if
    this type of notification is enabled (through
    ``mail_send_review_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()
    if siteconfig.get("mail_send_review_mail"):
        mail_reply(reply)


def user_registered_cb(user, **kwargs):
    """
    Listens for new user registrations and sends a new user registration
    e-mail to administrators, if enabled.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if siteconfig.get("mail_send_new_user_mail"):
        mail_new_user(user)


def connect_signals():
    review_request_published.connect(review_request_published_cb,
                                     sender=ReviewRequest)
    review_published.connect(review_published_cb, sender=Review)
    reply_published.connect(reply_published_cb, sender=Review)
    review_request_closed.connect(review_request_closed_cb,
                                  sender=ReviewRequest)
    user_registered.connect(user_registered_cb)


def build_email_address(fullname, email):
    if not fullname:
        return email
    else:
        return '"%s" <%s>' % (fullname, email)


def get_email_address_for_user(u):
    return build_email_address(u.get_full_name(), u.email)


def get_email_addresses_for_group(g):
    if g.mailing_list:
        if g.mailing_list.find(",") == -1:
            # The mailing list field has only one e-mail address in it,
            # so we can just use that and the group's display name.
            return ['"%s" <%s>' % (g.display_name, g.mailing_list)]
        else:
            # The mailing list field has multiple e-mail addresses in it.
            # We don't know which one should have the group's display name
            # attached to it, so just return their custom list as-is.
            return g.mailing_list.split(',')
    else:
        return [get_email_address_for_user(u)
                for u in g.users.filter(is_active=True)]


class SpiffyEmailMessage(EmailMultiAlternatives):
    """An EmailMessage subclass with improved header and message ID support.

    This also knows about several headers (standard and variations),
    including Sender/X-Sender, In-Reply-To/References, and Reply-To.

    The generated Message-ID header from the e-mail can be accessed
    through the :py:attr:`message_id` attribute after the e-mail is sent.
    """
    def __init__(self, subject, text_body, html_body, from_email, sender,
                 to, cc, in_reply_to, headers={}):
        headers = headers.copy()

        if sender:
            headers['Sender'] = sender
            headers['X-Sender'] = sender

        if in_reply_to:
            headers['In-Reply-To'] = in_reply_to
            headers['References'] = in_reply_to

        headers['Reply-To'] = from_email

        # Mark the mail as 'auto-generated' (according to RFC 3834) to
        # hopefully avoid auto replies.
        headers['Auto-Submitted'] = 'auto-generated'
        headers['From'] = from_email

        super(SpiffyEmailMessage, self).__init__(subject, text_body,
                                                 settings.DEFAULT_FROM_EMAIL,
                                                 to, headers=headers)

        self.cc = cc or []
        self.message_id = None

        self.attach_alternative(html_body, "text/html")

    def message(self):
        msg = super(SpiffyEmailMessage, self).message()
        self.message_id = msg['Message-ID']
        return msg

    def recipients(self):
        """Returns a list of all recipients of the e-mail. """
        return self.to + self.bcc + self.cc


def send_review_mail(user, review_request, subject, in_reply_to,
                     extra_recipients, text_template_name,
                     html_template_name, context={}):
    """
    Formats and sends an e-mail out with the current domain and review request
    being added to the template context. Returns the resulting message ID.
    """
    current_site = Site.objects.get_current()

    from_email = get_email_address_for_user(user)

    recipients = set()
    to_field = set()

    if from_email:
        recipients.add(from_email)

    if review_request.submitter.is_active:
        recipients.add(get_email_address_for_user(review_request.submitter))

    for u in review_request.target_people.filter(is_active=True):
        recipients.add(get_email_address_for_user(u))
        to_field.add(get_email_address_for_user(u))

    for group in review_request.target_groups.all():
        for address in get_email_addresses_for_group(group):
            recipients.add(address)

    for profile in review_request.starred_by.all():
        if profile.user.is_active:
            recipients.add(get_email_address_for_user(profile.user))

    if extra_recipients:
        for recipient in extra_recipients:
            if recipient.is_active:
                recipients.add(get_email_address_for_user(recipient))

    siteconfig = current_site.config.get()
    domain_method = siteconfig.get("site_domain_method")

    context['user'] = user
    context['domain'] = current_site.domain
    context['domain_method'] = domain_method
    context['review_request'] = review_request

    if review_request.local_site:
        context['local_site_name'] = review_request.local_site.name

    text_body = render_to_string(text_template_name, context)
    html_body = render_to_string(html_template_name, context)

    # Set the cc field only when the to field (i.e People) are mentioned,
    # so that to field consists of Reviewers and cc consists of all the
    # other members of the group
    if to_field:
        cc_field = recipients.symmetric_difference(to_field)
    else:
        to_field = recipients
        cc_field = set()

    base_url = '%s://%s' % (domain_method, current_site.domain)

    headers = {
        'X-ReviewBoard-URL': base_url,
        'X-ReviewRequest-URL': base_url + review_request.get_absolute_url(),
        'X-ReviewGroup': ', '.join(group.name for group in
                                   review_request.target_groups.all()),
    }

    if review_request.repository:
        headers['X-ReviewRequest-Repository'] = review_request.repository.name

    sender = None

    if settings.DEFAULT_FROM_EMAIL:
        sender = build_email_address(user.get_full_name(),
                                     settings.DEFAULT_FROM_EMAIL)

        if sender == from_email:
            # RFC 2822 states that we should only include Sender if the
            # two are not equal.
            sender = None

    message = SpiffyEmailMessage(subject.strip(), text_body, html_body,
                                 from_email, sender, list(to_field),
                                 list(cc_field), in_reply_to, headers)
    try:
        message.send()
    except Exception as e:
        logging.error("Error sending e-mail notification with subject '%s' on "
                      "behalf of '%s' to '%s': %s",
                      subject.strip(),
                      from_email,
                      ','.join(list(to_field) + list(cc_field)),
                      e,
                      exc_info=1)

    return message.message_id


def mail_review_request(review_request, changedesc=None, on_close=False):
    """
    Send an e-mail representing the supplied review request.

    The "changedesc" argument is an optional ChangeDescription showing
    what changed in a review request, possibly with explanatory text from
    the submitter. This is created when saving a draft on a public review
    request, and will be None when publishing initially.  This is used by
    the template to add contextual (updated) flags to inform people what
    changed.

    The "on_close" argument indicates whether review request emails should
    be sent on closing (SUBMITTED,DISCARDED) review requests.
    """
    # If the review request is not yet public or has been discarded, don't send
    # any mail. Relax the "discarded" rule when emails are sent on closing
    # review requests
    if (   not review_request.public
        or (not on_close and review_request.status == 'D')):
        return

    subject = "Review Request %d: %s" % (review_request.display_id,
                                         review_request.summary)
    reply_message_id = None

    if review_request.email_message_id:
        # Fancy quoted "replies"
        subject = "Re: " + subject
        reply_message_id = review_request.email_message_id
        extra_recipients = review_request.participants
    else:
        extra_recipients = None

    extra_context = {}

    if on_close:
        changedesc = review_request.changedescs.filter(public=True).latest()

    if changedesc:
        extra_context['change_text'] = changedesc.text
        extra_context['changes'] = changedesc.fields_changed

    review_request.time_emailed = timezone.now()
    review_request.email_message_id = \
        send_review_mail(review_request.submitter, review_request, subject,
                         reply_message_id, extra_recipients,
                         'notifications/review_request_email.txt',
                         'notifications/review_request_email.html',
                         extra_context)
    review_request.save()


def mail_review(review):
    """Sends an e-mail representing the supplied review."""
    review_request = review.review_request

    if not review_request.public:
        return

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    extra_context = {
        'user': review.user,
        'review': review,
    }

    has_error, extra_context['comment_entries'] = \
        build_diff_comment_fragments(
            review.ordered_comments, extra_context,
            "notifications/email_diff_comment_fragment.html")

    review.email_message_id = \
        send_review_mail(review.user,
                         review_request,
                         "Re: Review Request %d: %s" % (
                             review_request.display_id,
                             review_request.summary),
                         review_request.email_message_id,
                         None,
                         'notifications/review_email.txt',
                         'notifications/review_email.html',
                         extra_context)
    review.time_emailed = timezone.now()
    review.save()


def mail_reply(reply):
    """
    Sends an e-mail representing the supplied reply to a review.
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

    reply.email_message_id = \
        send_review_mail(reply.user,
                         review_request,
                         "Re: Review Request %d: %s" % (
                             review_request.display_id,
                             review_request.summary),
                         review.email_message_id,
                         review.participants,
                         'notifications/reply_email.txt',
                         'notifications/reply_email.html',
                         extra_context)
    reply.time_emailed = timezone.now()
    reply.save()


def mail_new_user(user):
    """Sends an e-mail to administrators for newly registered users."""
    current_site = Site.objects.get_current()
    siteconfig = current_site.config.get_current()
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
