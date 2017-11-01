"""E-mail notification callbacks."""

from __future__ import unicode_literals

from django.utils import timezone
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.notifications.email.message import (
    prepare_password_changed_mail,
    prepare_reply_published_mail,
    prepare_review_published_mail,
    prepare_review_request_mail,
    prepare_user_registered_mail,
    prepare_webapi_token_mail)
from reviewboard.notifications.email.utils import send_email
from reviewboard.reviews.models import ReviewRequest


def _update_email_info(obj, message_id):
    """Update the e-mail message information on the object.

    The ``email_message_id`` and ``time_emailed`` fields of the model will be
    updated.

    Args:
        obj (reviewboard.reviews.models.review.Review or
             reviewboard.reviews.models.review_request.ReviewRequest):
            The object for whiche-mail information will be updated.

        message_id (unicode):
            The new e-mail message ID.
    """
    obj.email_message_id = message_id
    obj.time_emailed = timezone.now()
    obj.save(update_fields=('email_message_id', 'time_emailed'))


def send_password_changed_mail(user):
    """Send an e-mail when a user's password changes.

    The e-mail will only be sent when the ``mail_send_password_changed_mail``
    :py:class:`~djblets.siteconfig.models.SiteConfiguration` setting is
    enabled.

    Args:
        user (django.contrib.auth.model.User):
            The user whose password changed.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if siteconfig.get('mail_send_password_changed_mail'):
        send_email(prepare_password_changed_mail, user=user)


def send_reply_published_mail(user, reply, trivial, **kwargs):
    """Send e-mail when a review reply is published.

    Listens to the :py:data:`~reviewboard.reviews.signals.reply_published`
    signal and sends an e-mail if this type of notification is enabled (through
    ``mail_send_review_mail`` site configuration).

    Args:
        user (django.contrib.auth.models.User):
            The user who published the reply.

        reply (reviewboard.reviews.models.Review):
            The reply that was published.

        trivial (bool):
            Whether or not the reply was marked as trivial when it was
            published. If ``True``, the e-mail will not be sent.

        **kwargs (dict):
            Unused keyword arguments from the signal.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if trivial or not siteconfig.get('mail_send_review_mail'):
        return

    review_request = reply.review_request

    if not review_request.public:
        return

    review = reply.base_reply_to

    message, sent = send_email(prepare_reply_published_mail,
                               user=user,
                               reply=reply,
                               review=review,
                               review_request=review_request)

    if sent:
        _update_email_info(reply, message.message_id)


def send_review_published_mail(user, review, request, to_owner_only,
                               **kwargs):
    """Send e-mail when a review is published.

    Listens to the :py:data:`~reviewboard.reviews.signals.review_published`
    signal and sends e-mail if this type of notification is enabled (through
    the ``mail_send_review_mail`` site configuration setting).

    Args:
        user (django.contrib.auth.models.User):
            The user that published the review.

        review (reviewboard.reviews.models.review.Review):
            The review that was published.

        to_owner_only (bool):
            Whether or not the mail should only be sent to the review request
            submitter.

        request (django.http.HttpRequest):
            The HTTP request that triggered this e-mail.

        **kwargs (dict):
            Additional keyword arguments.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if not siteconfig.get('mail_send_review_mail'):
        return

    review_request = review.review_request

    if not review_request.public:
        return

    message, sent = send_email(prepare_review_published_mail,
                               user=user,
                               review=review,
                               review_request=review_request,
                               request=request,
                               to_owner_only=to_owner_only)

    if sent:
        _update_email_info(review, message.message_id)


def send_review_request_closed_mail(user, review_request, close_type,
                                    **kwargs):
    """Send e-mail when a review request is closed.

    Listens to the
    :py:data:`~reviewboard.reviews.signals.review_request_closed` signal and
    sends an e-mail if this type of notification is enabled (through the
    ``mail_send_review_close_mail`` site configuration setting).

    Args:
        user (django.contrib.auth.models.User):
            The user who closed the review request.

        review_request (reviewboard.reviews.models.review_request.ReviewRequest):
            The review request that was closed.

        close_type (unicode):
            How the review request was closed.

        **kwargs (dict):
            Unused keyword arguments from the signal.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if not (siteconfig.get('mail_send_review_close_mail') and
            review_request.public):
        return

    message, sent = send_email(prepare_review_request_mail,
                               user=user,
                               review_request=review_request,
                               close_type=close_type)

    if sent:
        _update_email_info(review_request, message.message_id)


def send_review_request_published_mail(user, review_request, trivial,
                                       changedesc, **kwargs):
    """Send e-mail when a review request is published.

    Listens to the
    :py:data:`~reviewboard.reviews.signals.review_request_published` signal and
    sends an e-mail if this type of notification is enabled (through the
    ``mail_send_review_mail`` site configuration setting).

    If the review request publish was marked as trivial, the e-mail will not be
    sent.

    Args:
        user (django.contrib.auth.models.User):
            The user who published the review request.

        review_request (reviewboard.reviews.models.review_request.ReviewRequest):
            The review request that was published.

        trivial (bool):
            Whether or not the publish was marked as trivial.

        changedesc (reviewboard.changedescs.models.ChangeDescription, optional):
            The change description associated with the publish, if any.

        **kwargs (dict):
            Ignored keyword arguments from the signal.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if trivial or not siteconfig.get('mail_send_review_mail'):
        return

    if (not review_request.public or
        review_request.status == ReviewRequest.DISCARDED):
        return

    message, sent = send_email(prepare_review_request_mail,
                               user=user,
                               review_request=review_request,
                               changedesc=changedesc)

    if sent:
        _update_email_info(review_request, message.message_id)


def send_user_registered_mail(user, **kwargs):
    """Send e-mail when a user is registered.

    Listens for new user registrations and sends a new user registration
    e-mail to administrators, if this type of notification is enabled (through
    ``mail_send_new_user_mail`` site configuration).

    Args:
        user (django.contrib.auth.models.User):
            The user that registered.

        **kwargs (dict):
            Unused keyword arguments from the signal.
    """
    siteconfig = SiteConfiguration.objects.get_current()

    if not siteconfig.get('mail_send_new_user_mail'):
        return

    send_email(prepare_user_registered_mail,
               user=user)


def send_webapi_token_created_mail(instance, auto_generated=False, **kwargs):
    """Send e-mail when an API token is created.

    Args:
        instance (reviewboard.webapi.models.WebAPIToken):
            The token that has been created.

        should_send_email (bool, optional):
            Whether or not an e-mail should be sent.

        **kwargs (dict):
            Unused keyword arguments provided by the signal.
    """
    if not auto_generated:
        send_email(prepare_webapi_token_mail,
                   webapi_token=instance,
                   op='created')


def send_webapi_token_updated_mail(instance, **kwargs):
    """Send e-mail when an API token is updated.

    Args:
        instance (reviewboard.webapi.models.WebAPIToken):
            The token that was updated.

        **kwargs (dict):
            Unused keyword arguments provided by the signal.
    """
    send_email(prepare_webapi_token_mail,
               webapi_token=instance,
               op='updated')


def send_webapi_token_deleted_mail(instance, **kwargs):
    """Send e-mail when an API token is deleted.

    Args:
        instance (reviewboard.webapi.models.WebAPIToken):
            The token that has been created or updated.

        **kwargs (dict):
            Unused keyword arguments provided by the signal.
    """
    send_email(prepare_webapi_token_mail,
               webapi_token=instance,
               op='deleted')
