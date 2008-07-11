from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


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


class SpiffyEmailMessage(EmailMessage):
    def __init__(self, subject, body, from_email, to, in_reply_to):
        EmailMessage.__init__(self, subject, body, from_email, to)
        self.in_reply_to = in_reply_to
        self.message_id = None

    def message(self):
        msg = super(SpiffyEmailMessage, self).message()

        if self.in_reply_to:
            msg['In-Reply-To'] = self.in_reply_to
            msg['References'] = self.in_reply_to

        self.message_id = msg['Message-ID']

        return msg


def send_review_mail(user, review_request, subject, in_reply_to,
                     extra_recipients, template_name, context={}):
    """
    Formats and sends an e-mail out with the current domain and review request
    being added to the template context. Returns the resulting message ID.
    """
    current_site = Site.objects.get(pk=settings.SITE_ID)

    from_email = get_email_address_for_user(user)

    recipients = set([from_email])

    if review_request.submitter.is_active:
        recipients.add(get_email_address_for_user(review_request.submitter))

    for u in review_request.target_people.filter(is_active=True):
        recipients.add(get_email_address_for_user(u))

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

    context['user'] = user
    context['domain'] = current_site.domain
    context['domain_method'] = settings.DOMAIN_METHOD
    context['review_request'] = review_request
    body = render_to_string(template_name, context)

    message = SpiffyEmailMessage(subject.strip(), body, from_email,
                                 list(recipients), in_reply_to)
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


def mail_review_request(user, review_request, changes=None):
    """Send an e-mail representing the supplied review request.

    The "changes" argument is an optional list of strings which refer to fields
    within the review request which have been updated.  This is created when
    saving a draft on a public review request, and will be None when publishing
    initially.  This is used by the template to add contextual (updated) flags
    to inform people what changed.

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

    review_request.time_emailed = datetime.now()
    review_request.email_message_id = \
        send_review_mail(user, review_request, subject, reply_message_id,
                         extra_recipients, 'reviews/review_request_email.txt',
                         {'changes': changes})
    review_request.save()


def mail_review(user, review):
    """Sends an e-mail representing the supplied review."""
    review_request = review.review_request

    if not review_request.public:
        return

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    review.email_message_id = \
        send_review_mail(user,
                         review_request,
                         u"Re: Review Request: %s" % review_request.summary,
                         review_request.email_message_id,
                         None,
                         'reviews/review_email.txt',
                         {'review': review})
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

    reply.email_message_id = \
        send_review_mail(user,
                         review_request,
                         u"Re: Review Request: %s" % review_request.summary,
                         review.email_message_id,
                         harvest_people_from_review(review),
                         'reviews/reply_email.txt',
                         {'review': review,
                          'reply': reply})
    reply.time_emailed = datetime.now()
    reply.save()
