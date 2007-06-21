from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string


def get_email_address_for_user(u):
    if not u.get_full_name():
        return u.email
    else:
        return '%s <%s>' % (u.get_full_name(), u.email)


def get_email_address_for_group(g):
    return '%s <%s>' % (g.display_name, g.mailing_list)


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

    recipient_table = {
        from_email: 1,
        get_email_address_for_user(review_request.submitter): 1,
    }

    for u in review_request.target_people.all():
        recipient_table[get_email_address_for_user(u)] = 1

    for group in review_request.target_groups.all():
        recipient_table[get_email_address_for_group(group)] = 1

    if extra_recipients:
        for recipient in extra_recipients:
            recipient_table[get_email_address_for_user(recipient)] = 1

    recipient_list = [recipient for recipient in recipient_table]

    context['domain'] = current_site.domain
    context['review_request'] = review_request
    body = render_to_string(template_name, context)

    message = SpiffyEmailMessage(subject.strip(), body, from_email,
                                 recipient_list, in_reply_to)
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
    return [u for review in review_request.review_set.all()
              for u in harvest_people_from_review(review)]


def mail_review_request(user, review_request):
    """
    Sends an e-mail representing the supplied review request.
    """
    if not review_request.public or review_request.status == 'D':
        return

    subject = "Review Request: %s" % review_request.summary
    reply_message_id = None

    if review_request.email_message_id:
        subject = "Re: " + subject
        reply_message_id = review_request.email_message_id
        extra_recipients = harvest_people_from_review_request(review_request)
    else:
        extra_recipients = None

    review_request.time_emailed = datetime.now()
    review_request.email_message_id = \
        send_review_mail(user, review_request, subject, reply_message_id,
                         extra_recipients, 'reviews/review_request_email.txt')
    review_request.save()


def mail_diff_update(user, review_request):
    """
    Sends an e-mail informing users that the diff has been updated.
    """
    if not review_request.public or review_request.status == 'D':
        return

    send_review_mail(user, review_request,
                     "Re: Review Request: %s" % review_request.summary,
                     review_request.email_message_id,
                     harvest_people_from_review_request(review_request),
                     'reviews/diff_update.txt')
    review_request.save()


def mail_review(user, review):
    """
    Sends an e-mail representing the supplied review.
    """
    if not review.review_request.public:
        return

    review.ordered_comments = \
        review.comments.order_by('filediff', 'first_line')

    review.email_message_id = \
        send_review_mail(user,
                         review.review_request,
                         "Re: Review Request: %s" %
                         review.review_request.summary,
                         review.review_request.email_message_id,
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

    if not review.review_request.public:
        return

    reply.email_message_id = \
        send_review_mail(user,
                         review.review_request,
                         "Re: Review Request: %s" %
                         review.review_request.summary,
                         review.email_message_id,
                         harvest_people_from_review(review),
                         'reviews/reply_email.txt',
                         {'review': review,
                          'reply': reply})
    reply.time_emailed = datetime.now()
    reply.save()
