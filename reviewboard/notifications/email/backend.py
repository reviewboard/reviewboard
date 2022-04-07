"""E-mail backend for Review Board.

Version Added:
    4.0.4
"""

import re
import smtplib

from django.core.mail.backends import smtp
from django.utils.functional import cached_property


class SMTPConnectionMixin(object):
    """Mixin for tracking last replies when sending e-mail over SMTP.

    Version Added:
        4.0.4

    Attributes:
        rb_last_reply (tuple):
            The last reply object. This contains the status code and reply
            details string.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the mixin.

        Args:
            *args (tuple):
                Positional arguments for the SMTP backend.

            **kwargs (dict):
                Keyword arguments for the SMTP backend.
        """
        self.rb_last_reply = None

        super(SMTPConnectionMixin, self).__init__(*args, **kwargs)

    def data(self, *args, **kwargs):
        """Send message data over SMTP.

        This will use the backend to send the data, and then store the
        last reply for further processing by :py:class:`EmailBackend`.

        Args:
            *args (tuple):
                Positional arguments for the underlying method.

            **kwargs (dict):
                Keyword arguments for the underlying method.

        Returns:
            tuple:
            The reply object. See :py:attr:`rb_last_reply`.
        """
        reply = super(SMTPConnectionMixin, self).data(*args, **kwargs)

        self.rb_last_reply = reply

        return reply


class SMTPConnection(SMTPConnectionMixin, smtplib.SMTP):
    """SMTP connection with last-response tracking.

    Version Added:
        4.0.4
    """


class SMTPSSLConnection(SMTPConnectionMixin, smtplib.SMTP_SSL):
    """SMTP SSL connection with last-response tracking.

    Version Added:
        4.0.4
    """


class EmailBackend(smtp.EmailBackend):
    """Standard Review Board e-mail backend.

    This is a specialization of Django's e-mail backend that has enhanced
    support for mail services, Amazon SES in particular.

    Amazon SES does not allow for custom Message IDs, and will return a
    generated Message ID as part of a ``205 Ok`` responses (which is not
    a standard part of the SMTP specifications). This backend has the
    ability to capture that Message ID and reassign it back to the message
    being sent for storage.

    Otherwise, the backend works exactly like the standard Django e-mail
    backend.

    Version Added:
        4.0.4
    """

    SES_HOST_RE = re.compile(r'email-smtp(?:-fips)?\.([^.]+)\.amazonaws\.com')

    def __init__(self, *args, **kwargs):
        """Initialize the e-mail backend.

        Args:
            *args (tuple):
                Positional arguments for the backend class.

            **kwargs (dict):
                Keyword arguments for the backend class.
        """
        super(EmailBackend, self).__init__(*args, **kwargs)

        self._ses_region = None

    @property
    def connection_class(self):
        """The SMTP connection class to use for communication.

        This will be a version with last-response tracking enabled.

        Type:
            type
        """
        if self.use_ssl:
            return SMTPSSLConnection
        else:
            return SMTPConnection

    @cached_property
    def is_ses(self):
        """Whether e-mail is being sent via Amazon SES.

        Type:
            bool
        """
        m = self.SES_HOST_RE.match(self.host)

        if m:
            self._ses_region = m.group(1)

            return True

        return False

    @cached_property
    def ses_message_id_domain(self):
        """The Amazon SES domain to use for a Message ID.

        This cannot be called if :py:attr:`is_ses` is not ``True``.

        Type:
            unicode
        """
        assert self.is_ses

        # Note that we're making some assumptions that us-east-1 is the only
        # region using "email.amazonses.com". There is no official
        # documentation on this.
        if self._ses_region == 'us-east-1':
            return 'email.amazonses.com'
        else:
            return '%s.amazonses.com' % self._ses_region

    def _send(self, email_message, *args, **kwargs):
        """Send an e-mail message.

        This wraps Django's main e-mail sending logic, processing the
        result and extracting an Amazon SES Message ID, if available and if
        using SES.

        Args:
            email_message (django.core.mail.message.EmailMessage):
                The e-mail message to send.

            *args (tuple):
                Additional positional arguments to pass to the parent method.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent method.

        Returns:
            object:
            The result of the parent method.

        Raises:
            Exception:
                An error raised by the parent method.
        """
        result = super(EmailBackend, self)._send(email_message, *args,
                                                 **kwargs)

        last_reply = self.connection.rb_last_reply

        if last_reply:
            # Don't leak this result. Clear it out before anything can go
            # wrong.
            self.connection.rb_last_reply = None

            code, response = last_reply

            # If we're talking to Amazon SES, then a successful send should
            # come with a rewritten Message-ID. This is non-standard, though
            # it's conceivable that some other service may adopt this pattern
            # in the future, in which case we'll need to specialize this for
            # them.
            #
            # Check to see if we got a 250 Ok with extra content (which by
            # itself means nothing), and whether this is SES (in which case
            # there's probably a new Message-ID).
            if self.is_ses and code == 250 and response.startswith(b'Ok '):
                parts = response.split(b' ')

                if len(parts) == 2:
                    # This should be a Message ID.
                    #
                    # Annoyingly, the Message-ID does not contain the domain.
                    # We have to infer that.
                    #
                    # As of this comment (July 8, 2021), the domain will be
                    # "<region>.amazonses.com" for all regions but us-east-1.
                    # That region just uses "email.amazonses.com". This could
                    # always change in the future, but has remained stable for
                    # the last several years.
                    email_message.message_id = (
                        '<%s@%s>'
                        % (parts[1].decode('utf-8'),
                           self.ses_message_id_domain))

        return result
