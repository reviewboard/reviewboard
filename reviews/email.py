import time
import smtplib, rfc822
import socket
import random
from datetime import datetime

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import SafeMIMEText
from django.template.loader import render_to_string

from reviewboard.reviews.models import ReviewRequest, Review

DNS_NAME = socket.getfqdn()

def send_review_mail(user, review_request, subject, in_reply_to,
                     template_name, context={}):
    """
    Formats and sends an e-mail out with the current domain and review request
    being added to the template context. Returns the resulting message ID.
    """
    current_site = Site.objects.get(pk=settings.SITE_ID)

    if user.get_full_name() == "":
        from_email = user.email
    else:
        from_email = "%s <%s>" % (user.get_full_name(), user.email)

    recipient_list = \
        [u.email for u in review_request.target_people.all()] + \
        [group.mailing_list for group in review_request.target_groups.all()]

    if recipient_list == []:
        return None

    if not user.email in recipient_list:
        recipient_list += [user.email]

    context['domain'] = current_site.domain
    context['review_request'] = review_request
    body = render_to_string(template_name, context)

    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        server.login(settings.EMAIL_HOST_USER,
                     settings.EMAIL_HOST_PASSWORD)

    msg = SafeMIMEText(body, 'plain', settings.DEFAULT_CHARSET)
    msg['Subject'] = subject.strip()
    msg['From'] = from_email
    msg['To'] = ', '.join(recipient_list)
    msg['Date'] = rfc822.formatdate()

    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
        msg['References'] = in_reply_to

    try:
        random_bits = str(random.getrandbits(64))
    except AttributeError: # Python 2.3 doesn't have random.getrandbits()
        random_bits = ''.join([random.choice('1234567890') for i in range(19)])

    msg['Message-ID'] = "<%d.%s@%s>" % (time.time(), random_bits, DNS_NAME)

    server.sendmail(from_email, recipient_list, msg.as_string())

    return msg['Message-ID']


def mail_review_request(user, review_request):
    """
    Sends an e-mail representing the supplied review request.
    """
    if not review_request.public:
        return

    subject = "Review Request: %s" % review_request.summary
    reply_message_id = None

    if review_request.email_message_id:
        subject = "Re: " + subject
        reply_message_id = review_request.email_message_id

    review_request.time_emailed = datetime.now()
    review_request.email_message_id = \
        send_review_mail(user, review_request, subject, reply_message_id,
                         'reviews/review_request_email.txt')
    review_request.save()


def mail_diff_update(user, review_request):
    """
    Sends an e-mail informing users that the diff has been updated.
    """
    if not review_request.public:
        return

    send_review_mail(user, review_request,
                     "Re: Review Request: %s" % review_request.summary,
                     review_request.email_message_id,
                     'reviews/diff_update.txt')
    review_request.save()


def mail_review(user, review):
    """
    Sends an e-mail representing the supplied review.
    """
    if not review.review_request.public:
        return

    review.email_message_id = \
        send_review_mail(user,
                         review.review_request,
                         "Re: Review Request: %s" %
                         review.review_request.summary,
                         review.review_request.email_message_id,
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
                         'reviews/reply_email.txt',
                         {'review': review,
                          'reply': reply})
    reply.time_emailed = datetime.now()
    reply.save()
