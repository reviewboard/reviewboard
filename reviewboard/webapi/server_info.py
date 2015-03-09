from __future__ import unicode_literals

from django.conf import settings

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.admin.server import get_server_url


def get_server_info(request=None):
    """Returns server information for use in the API.

    This is used for the root resource and for the deprecated server
    info resource.
    """
    return {
        'product': {
            'name': 'Review Board',
            'version': get_version_string(),
            'package_version': get_package_version(),
            'is_release': is_release(),
        },
        'site': {
            'url': get_server_url(request=request),
            'administrators': [
                {
                    'name': name,
                    'email': email,
                }
                for name, email in settings.ADMINS
            ],
            'time_zone': settings.TIME_ZONE,
        },
        'capabilities': {
            'diffs': {
                'base_commit_ids': True,
                'moved_files': True,
                'validation': {
                    'base_commit_ids': True,
                }
            },
            'review_requests': {
                'commit_ids': True,
            },
            'scmtools': {
                'git': {
                    'empty_files': True,
                },
                'mercurial': {
                    'empty_files': True,
                },
                'perforce': {
                    'moved_files': True,
                    'empty_files': True,
                },
                'svn': {
                    'empty_files': True,
                },
            },
            'text': {
                'markdown': True,
                'per_field_text_types': True,
                'can_include_raw_values': True,
            },
        }
    }
