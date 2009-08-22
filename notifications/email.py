from datetime import datetime

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.reviews.signals import review_request_published, \
                                        review_published, reply_published
from reviewboard.reviews.views import build_diff_comment_fragments


def review_request_published_cb(sender, user, review_request, changedesc,
                                **kwargs):
    """
    Listens to the ``review_request_published`` signal and sends an
    email if this type of notification is enabled (through
    ``mail_send_review_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()
    if siteconfig.get("mail_send_review_mail"):
        mail_review_request(user, review_request, changedesc)

review_request_published.connect(review_request_published_cb)


def review_published_cb(sender, user, review, **kwargs):
    """
    Listens to the ``review_published`` signal and sends an email if
    this type of notification is enabled (through
    ``mail_send_review_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()
    if siteconfig.get("mail_send_review_mail"):
        mail_review(user, review)

review_published.connect(review_published_cb)


def reply_published_cb(sender, user, reply, **kwargs):
    """
    Listens to the ``reply_published`` signal and sends an email if
    this type of notification is enabled (through
    ``mail_send_review_mail`` site configuration).
    """
    siteconfig = SiteConfiguration.objects.get_current()
    if siteconfig.get("mail_send_review_mail"):
        mail_reply(user, reply)

reply_published.connect(reply_published_cb)


def get_email_address_for_user(u):
    if not u.get_full_name():
        return u.email
    else:
        return u'"%s" <%s>' % (u.get_full_name(), u.email)


def get_email_addresses_for_group(g):
    if g.mailing_list:
        if g.mailing_list.find(",") == -1:
            # The mailing list field has only one e-mail address in it,
            # so we can just use that and the group's display name.
            return [u'"%s" <%s>' % (g.display_name, g.mailing_list)]
        else:
            # The mailing list field has multiple e-mail addresses in it.
            # We don't know which one should have the group's display name
            # attached to it, so just return their custom list as-is.
            return g.mailing_list
    else:
        return [get_email_address_for_user(u)
                for u in g.users.filter(is_active=True)]


class SpiffyEmailMessage(EmailMultiAlternatives):
    def __init__(self, subject, text_body, html_body, from_email, to, cc,
                 in_reply_to, headers={}):
        EmailMultiAlternatives.__init__(self, subject, text_body,
                                        from_email, to, headers=headers)

        self.cc = cc or []

        self.in_reply_to = in_reply_to
        self.message_id = None

        self.attach_alternative(html_body, "text/html")

    def message(self):
        msg = super(SpiffyEmailMessage, self).message()

        if self.cc:
            msg['Cc'] = ','.join(self.cc)

        if self.in_reply_to:
            msg['In-Reply-To'] = self.in_reply_to
            msg['References'] = self.in_reply_to

        self.message_id = msg['Message-ID']

        return msg

    def recipients(self):
        """
        Returns a list of all recipients of the e-mail.
        """
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

    recipients = set([from_email])
    to_field = set()

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
    }

    message = SpiffyEmailMessage(subject.strip(), text_body, html_body,
                                 from_email, list(to_field), list(cc_field),
                                 in_reply_to, headers)
    message.send()

    return message.message_id


def harvest_people_from_review(review):
    """
    Returns a list of all people who have been involved in the discussion on
    a review.
    """

    # This list comprehension gives us every user in every reply, recursively.
    # It looks strange and perhaps backwards, but works. We do it this way
    # because harvest_people_from_review gives us a list back, which we can't
    # stick in as the result for a standard list comprehension. We could
    # opt for a simple for loop and concetenate the list, but this is more
    # fun.
    return [review.user] + \
           [u for reply in review.replies.all()
              for u in harvest_people_from_review(reply)]


def harvest_people_from_review_request(review_request):
    """
    Returns a list of all people who have been involved in a discussion on
    a review request.
    """
    # See the comment in harvest_people_from_review for this list
    # comprehension.
    return [u for review in review_request.reviews.all()
              for u in harvest_people_from_review(review)]


def mail_review_request(user, review_request, changedesc=None):
    """
    Send an e-mail representing the supplied review request.

    The "changedesc" argument is an optional ChangeDescription showing
    what changed in a review request, possibly with explanatory text from
    the submitter. This is created when saving a draft on a public review
    request, and will be None when publishing initially.  This is used by
    the template to add contextual (updated) flags to inform people what
    changed.
    """
    # If the review request is not yet public or has been discarded, don't send
    # any mail.
    if not review_request.public or review_request.status == 'D':
        return

    subject = u"Review Request: %s" % review_request.summary
    reply_message_id = None

    if review_request.email_message_id:
        # Fancy quoted "replies"
        subject = "Re: " + subject
        reply_message_id = review_request.email_message_id
        extra_recipients = harvest_people_from_review_request(review_request)
    else:
        extra_recipients = None

    extra_context = {}

    if changedesc:
        extra_context['change_text'] = changedesc.text
        extra_context['changes'] = changedesc.fields_changed

    review_request.time_emailed = datetime.now()
    review_request.email_message_id = \
        send_review_mail(user, review_request, subject, reply_message_id,
                         extra_recipients,
                         'notifications/review_request_email.txt',
                         'notifications/review_request_email.html',
                         extra_context)
    review_request.save()


def mail_review(user, review):
    """Sends an e-mail representing the supplied review."""
    review_request = review.review_request

    if not review_request.public:
        return

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    extra_context = {
        'user': user,
        'review': review,
    }

    has_error, extra_context['comment_entries'] = \
        build_diff_comment_fragments(
            review.ordered_comments, extra_context,
            "notifications/email_diff_comment_fragment.html")

    review.email_message_id = \
        send_review_mail(user,
                         review_request,
                         u"Re: Review Request: %s" % review_request.summary,
                         review_request.email_message_id,
                         None,
                         'notifications/review_email.txt',
                         'notifications/review_email.html',
                         extra_context)
    review.time_emailed = datetime.now()
    review.save()


def mail_reply(user, reply):
    """
    Sends an e-mail representing the supplied reply to a review.
    """
    review = reply.base_reply_to
    review_request = review.review_request

    if not review_request.public:
        return

    extra_context = {
        'user': user,
        'review': review,
        'reply': reply,
    }

    has_error, extra_context['comment_entries'] = \
        build_diff_comment_fragments(
            reply.comments.order_by('filediff', 'first_line'),
            extra_context,
            "notifications/email_diff_comment_fragment.html")

    reply.email_message_id = \
        send_review_mail(user,
                         review_request,
                         u"Re: Review Request: %s" % review_request.summary,
                         review.email_message_id,
                         harvest_people_from_review(review),
                         'notifications/reply_email.txt',
                         'notifications/reply_email.html',
                         extra_context)
    reply.time_emailed = datetime.now()
    reply.save()
