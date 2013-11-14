from __future__ import unicode_literals


class Certificate(object):
    """A representation of an HTTPS certificate."""
    def __init__(self, valid_from='', valid_until='', hostname='', realm='',
                 fingerprint='', issuer='', failures=[]):
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.hostname = hostname
        self.realm = realm
        self.fingerprint = fingerprint
        self.issuer = issuer
        self.failures = failures
