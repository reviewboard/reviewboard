import os
import tempfile

import pytest
from djblets.cache.serials import generate_media_serial


tests_tempdir = None


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(django_db_reset_sequences):
    """Enable database access for all unit tests.

    This is applied to all test functions, ensuring database access isn't
    blocked.
    """
    pass


@pytest.fixture(autouse=True, scope='session')
def setup_siteconfig():
    """Set up the siteconfig for tests.

    This is run at the start of the project-wide test session, putting together
    a suitable test environment for Review Board's test suite.
    """
    from django.conf import settings

    # Default to testing in a non-subdir install.
    settings.SITE_ROOT = '/'

    # Set some defaults for cache serials, in case the tests need them.
    settings.AJAX_SERIAL = 123
    settings.TEMPLATE_SERIAL = 123

    # Set a faster password hasher, for performance.
    settings.PASSWORD_HASHERS = (
        'django.contrib.auth.hashers.SHA1PasswordHasher',
    )

    # Make sure we're using standard static files storage, and not
    # something like Pipeline or S3 (since we don't want to trigger any
    # special behavior). Subclasses are free to override this setting.
    settings.STATICFILES_STORAGE = \
        'django.contrib.staticfiles.storage.StaticFilesStorage'

    # By default, don't look up DMARC records when generating From
    # addresses for e-mails. Just assume we can, since we're not
    # sending anything out. Some unit tests will override
    # this.
    settings.EMAIL_ENABLE_SMART_SPOOFING = False

    # Create a temp directory that tests can rely upon.
    tests_tempdir = tempfile.mkdtemp(prefix='rb-tests-')

    # Configure file paths for static media. This will handle the main
    # static and uploaded media directories, along with extension
    # directories (for projects that need to use them).
    settings.STATIC_URL = settings.SITE_ROOT + 'static/'
    settings.MEDIA_URL = settings.SITE_ROOT + 'media/'
    settings.STATIC_ROOT = os.path.join(tests_tempdir, 'static')
    settings.MEDIA_ROOT = os.path.join(tests_tempdir, 'media')

    settings.SITE_DATA_DIR = os.path.join(tests_tempdir, 'data')
    settings.HAYSTACK_CONNECTIONS['default']['PATH'] = \
        os.path.join(settings.SITE_DATA_DIR, 'search-index')

    required_dirs = [
        settings.SITE_DATA_DIR,
        settings.STATIC_ROOT,
        settings.MEDIA_ROOT,
        os.path.join(settings.MEDIA_ROOT, 'uploaded', 'images'),
        os.path.join(settings.MEDIA_ROOT, 'ext'),
        os.path.join(settings.STATIC_ROOT, 'ext'),
    ]

    for dirname in required_dirs:
        if not os.path.exists(dirname):
            os.makedirs(dirname)

    from django.core import management
    management.call_command('collectstatic',
                            verbosity=0,
                            interactive=False)

    generate_media_serial()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Set up the Django database.

    This is run at the start of the project-wide test session, setting up
    an initial siteconfig in the database.
    """
    with django_db_blocker.unblock():
        from reviewboard.admin.management.sites import init_siteconfig

        siteconfig = init_siteconfig()
        siteconfig.set('mail_from_spoofing', 'never')
        siteconfig.save(update_fields=('settings',))
