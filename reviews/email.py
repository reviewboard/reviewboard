import time
import smtplib, rfc822
import socket
import random

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
    from_email = user.email
    recipient_list =
        [user.email for user in review_request.target_users.all()] +
        [group.mailing_list for group in review_request.target_groups.all()]

    context['domain'] = current_site.domain
    context['review_request'] = review_request
    context['user'] = user
    body = render_to_string(template_name, context)

    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        server.login(settings.EMAIL_HOST_USER,
                     settings.EMAIL_HOST_PASSWORD)

    msg = SafeMIMEText(body, 'plain', settings.DEFAULT_CHARSET)
    msg['Subject'] = subject
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
    review_request.email_message_id = \
        send_review_mail(user, review_request,
                         "Review Request: %s" % review_request.summary, None,
                         'reviews/review_request_email.html')
    review_request.save()


def mail_review(user, review):
    """
    Sends an e-mail representing the supplied review or reply to a review.
    """
    review.email_message_id = \
        send_review_mail(user,
                         review.review_request,
                         "Re: Review Request: %s" %
                         review.review_request.summary,
                         review.review_request.email_message_id, # XXX
                         'reviews/review_email.html',
                         {'review': review});
    review.save()
