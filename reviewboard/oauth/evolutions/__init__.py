from __future__ import unicode_literals


# The oauth2_provider module expects that the app specified in
# settings.OAUTH2_PROVIDER['APPLICATION_MODULE'] has already been added in the
# database. We need to specify this dependency to ensure this app is processed
# first, to fulfill that requirement.
BEFORE_MIGRATIONS = [
    ('oauth2_provider', '0001_initial'),
]


# We also need to ensure that we've installed reviewboard.site first, since
# otherwise it would apply after oauth2_provider.
AFTER_EVOLUTIONS = [
    'site',
]


SEQUENCE = [
    'disabled_for_security',
]
