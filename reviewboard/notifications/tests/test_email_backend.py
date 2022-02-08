"""Unit tests for reviewboard.notifications.email.backend."""

from smtplib import SMTP, SMTPDataError

import kgb
from djblets.mail.message import EmailMessage

from reviewboard.notifications.email.backend import EmailBackend
from reviewboard.testing import TestCase


class EmailBackendTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.notifications.email.backend.EmailBackend."""

    # The list of hostnames is taken from
    # https://docs.aws.amazon.com/general/latest/gr/ses.html
    #
    # Note that we're making some assumptions that us-east-1 is the only
    # region using "email.amazonses.com". There is no official documentation
    # on this.
    SES_HOSTS = {
        'email-smtp.us-east-2.amazonaws.com': {
            'msgid_domain': 'us-east-2.amazonses.com',
        },
        'email-smtp.us-east-1.amazonaws.com': {
            'msgid_domain': 'email.amazonses.com',
        },
        'email-smtp-fips.us-east-1.amazonaws.com': {
            'msgid_domain': 'email.amazonses.com',
        },
        'email-smtp.us-west-1.amazonaws.com': {
            'msgid_domain': 'us-west-1.amazonses.com',
        },
        'email-smtp.us-west-2.amazonaws.com': {
            'msgid_domain': 'us-west-2.amazonses.com',
        },
        'email-smtp-fips.us-west-2.amazonaws.com': {
            'msgid_domain': 'us-west-2.amazonses.com',
        },
        'email-smtp.ap-south-1.amazonaws.com': {
            'msgid_domain': 'ap-south-1.amazonses.com',
        },
        'email-smtp.ap-northeast-2.amazonaws.com': {
            'msgid_domain': 'ap-northeast-2.amazonses.com',
        },
        'email-smtp.ap-southeast-1.amazonaws.com': {
            'msgid_domain': 'ap-southeast-1.amazonses.com',
        },
        'email-smtp.ap-southeast-2.amazonaws.com': {
            'msgid_domain': 'ap-southeast-2.amazonses.com',
        },
        'email-smtp.ap-northeast-1.amazonaws.com': {
            'msgid_domain': 'ap-northeast-1.amazonses.com',
        },
        'email-smtp.ca-central-1.amazonaws.com': {
            'msgid_domain': 'ca-central-1.amazonses.com',
        },
        'email-smtp.eu-central-1.amazonaws.com': {
            'msgid_domain': 'eu-central-1.amazonses.com',
        },
        'email-smtp.eu-west-1.amazonaws.com': {
            'msgid_domain': 'eu-west-1.amazonses.com',
        },
        'email-smtp.eu-west-2.amazonaws.com': {
            'msgid_domain': 'eu-west-2.amazonses.com',
        },
        'email-smtp.eu-west-3.amazonaws.com': {
            'msgid_domain': 'eu-west-3.amazonses.com',
        },
        'email-smtp.eu-north-1.amazonaws.com': {
            'msgid_domain': 'eu-north-1.amazonses.com',
        },
        'email-smtp.sa-east-1.amazonaws.com': {
            'msgid_domain': 'sa-east-1.amazonses.com',
        },
        'email-smtp.us-gov-west-1.amazonaws.com': {
            'msgid_domain': 'us-gov-west-1.amazonses.com',
        },
        'email-smtp-fips.us-gov-west-1.amazonaws.com': {
            'msgid_domain': 'us-gov-west-1.amazonses.com',
        },
    }

    def test_is_ses_with_ses(self):
        """Testing EmailBackend.is_ses with Amazon SES SMTP hostname"""
        for host in self.SES_HOSTS.keys():
            backend = EmailBackend(host=host)
            self.assertTrue(backend.is_ses,
                            msg='EmailBackend.is_ses failed for %s' % host)

    def test_is_ses_without_ses(self):
        """Testing EmailBackend.is_ses without Amazon SES SMTP hostname"""
        backend = EmailBackend(host='mail.example.com')
        self.assertFalse(backend.is_ses)

    def test_ses_message_id_domain(self):
        """Testing EmailBackend.ses_message_id_domain"""
        for mail_host, mail_info in self.SES_HOSTS.items():
            backend = EmailBackend(host=mail_host)
            self.assertEqual(backend.ses_message_id_domain,
                             mail_info['msgid_domain'])

    def test_send_messages_with_ses_and_250_ok(self):
        """Testing EmailBackend.send_messages with Amazon SES and 250 Ok with
        message ID
        """
        message_uuid = \
            '1234567abcd12345-6789abcd-1234-a1b2-c3d4-012345abcdef-000000'

        self._spy_on_smtp((250, b'Ok %s' % message_uuid.encode('utf-8')))

        # We're going to run this test for every region, to ensure that
        # there aren't any issues with the differences between regions.
        for mail_host, mail_info in self.SES_HOSTS.items():
            backend = EmailBackend(host=mail_host)
            self.assertTrue(backend.is_ses)

            message = self._create_message()
            backend.send_messages([message])

            self.assertEqual(
                message.message_id,
                '<%s@%s>' % (message_uuid, mail_info['msgid_domain']))

    def test_send_messages_with_ses_and_250_ok_no_msgid(self):
        """Testing EmailBackend.send_messages with Amazon SES and 250 Ok
        without a message ID
        """
        self._spy_on_smtp((250, b'Ok'))

        backend = EmailBackend(host='email-smtp.us-east-1.amazonaws.com')
        self.assertTrue(backend.is_ses)

        message = self._create_message()
        backend.send_messages([message])

        self.assertEqual(message.message_id, '<1234@example.com>')

    def test_send_messages_with_ses_and_250_ok_too_long(self):
        """Testing EmailBackend.send_messages with Amazon SES and 250 Ok
        with too many trailing values
        """
        self._spy_on_smtp((250, b'Ok something something'))

        backend = EmailBackend(host='email-smtp.us-east-1.amazonaws.com')
        self.assertTrue(backend.is_ses)

        message = self._create_message()
        backend.send_messages([message])

        self.assertEqual(message.message_id, '<1234@example.com>')

    def test_send_messages_with_ses_and_no_250(self):
        """Testing EmailBackend.send_messages with Amazon SES and no 250 Ok"""
        self._spy_on_smtp((451, b'Oh no'))

        backend = EmailBackend(host='email-smtp.us-east-1.amazonaws.com')
        self.assertTrue(backend.is_ses)

        message = self._create_message()

        with self.assertRaises(SMTPDataError):
            backend.send_messages([message])

        self.assertEqual(message.message_id, '<1234@example.com>')

    def test_send_messages_without_ses(self):
        """Testing EmailBackend.send_messages without Amazon SES"""
        self._spy_on_smtp((250, b'Ok something'))

        backend = EmailBackend(host='mail.example.com')
        self.assertFalse(backend.is_ses)

        message = self._create_message()
        backend.send_messages([message])

        self.assertEqual(message.message_id, '<1234@example.com>')

    def _create_message(self):
        """Return a new EmailMessage for testing.

        This will contain a sample recipient and initial
        :mailheader:`Message-ID`.

        Returns:
            djblets.mail.message.EmailMessage:
            The resulting message.
        """
        message = EmailMessage(to=['test@example.com'])
        message.extra_headers['Message-ID'] = '<1234@example.com>'

        return message

    def _spy_on_smtp(self, data_result=None):
        """Spy on the SMTP connection process and fake a result.

        Args:
            data_result (tuple):
                The value to fake from the final data request. This will be
                what's stored and processed by our e-mail backend.
        """
        # We want to simulate as much of the SMTP flow as possible, since
        # we're trying to ensure that the final response is caught in our
        # subclass. To do this, we need to stub out much of the communication.
        #
        # We'll simulate connection management (connect() and quit()), stub
        # out responses for the mail sending process (ehlo_or_helo_if_needed(),
        # rcpt(), mail(), and data()), and raise exceptions if we somehow get
        # to any actual socket communication code (putcmd() and getreply()).
        #
        # We're explicitly spying on the base class, so we don't turn off our
        # subclass's overridden behavior.
        self.spy_on(SMTP.connect,
                    owner=SMTP,
                    op=kgb.SpyOpReturn((220, b'')))
        self.spy_on(SMTP.quit,
                    owner=SMTP,
                    op=kgb.SpyOpReturn((221, b'')))
        self.spy_on(SMTP.rset,
                    owner=SMTP,
                    call_original=False)

        self.spy_on(SMTP.putcmd,
                    owner=SMTP,
                    op=kgb.SpyOpRaise(Exception('not reached')))
        self.spy_on(SMTP.getreply,
                    owner=SMTP,
                    op=kgb.SpyOpRaise(Exception('not reached')))

        self.spy_on(SMTP.ehlo_or_helo_if_needed,
                    owner=SMTP,
                    call_original=False)
        self.spy_on(SMTP.rcpt,
                    owner=SMTP,
                    op=kgb.SpyOpReturn((250, b'')))
        self.spy_on(SMTP.mail,
                    owner=SMTP,
                    op=kgb.SpyOpReturn((250, b'')))
        self.spy_on(SMTP.data,
                    owner=SMTP,
                    op=kgb.SpyOpReturn(data_result))
