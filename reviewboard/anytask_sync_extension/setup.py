from __future__ import unicode_literals

from reviewboard.extensions.packaging import setup


PACKAGE = "anytask_sync_extension"
VERSION = "0.1"

setup(
    name=PACKAGE,
    version=VERSION,
    description="Extension description=extension uses to sync review_request with anytask",
    author="gebetix@yandex-team.ru",
    packages=["anytask_sync_extension"],
    entry_points={
        'reviewboard.extensions':
            '%s = anytask_sync_extension.extension:AnytaskSyncExtension' % PACKAGE,
    },
    package_data={
        b'anytask_sync_extension': [
            'templates/anytask_sync_extension/*.txt',
            'templates/anytask_sync_extension/*.html',
        ],
    }
)
