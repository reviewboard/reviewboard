from __future__ import unicode_literals

import logging

from django.conf import settings

from reviewboard import get_version_string, get_package_version, is_release
from reviewboard.admin.server import get_server_url


_registered_capabilities = {}
_capabilities_defaults = {
    'diffs': {
        'base_commit_ids': True,
        'moved_files': True,
        'validation': {
            'base_commit_ids': True,
        }
    },
    'review_requests': {
        'commit_ids': True,
        'trivial_publish': True,
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


def get_server_info(request=None):
    """Returns server information for use in the API.

    This is used for the root resource and for the deprecated server
    info resource.
    """
    capabilities = _capabilities_defaults.copy()
    capabilities.update(_registered_capabilities)

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
        'capabilities': capabilities
    }


def register_webapi_capabilities(capabilities_id, caps):
    """Registers a set of web API capabilities.

    These capabilities will appear in the dictionary of available
    capabilities with the ID as their key.

    A capabilties_id attribute passed in, and can only be registerd once.
    A KeyError will be thrown if attempting to register a second time.
    """
    if not capabilities_id:
        raise ValueError('The capabilities_id attribute must not be None')

    if capabilities_id in _registered_capabilities:
        raise KeyError('"%s" is already a registered set of capabilities'
                       % capabilities_id)

    if capabilities_id in _capabilities_defaults:
        raise KeyError('"%s" is reserved for the default set of capabilities'
                       % capabilities_id)

    _registered_capabilities[capabilities_id] = caps


def unregister_webapi_capabilities(capabilities_id):
    """Unregisters a previously registered set of web API capabilities."""
    try:
        del _registered_capabilities[capabilities_id]
    except KeyError:
        logging.error('Failed to unregister unknown web API capabilities '
                      '"%s".',
                      capabilities_id)
        raise KeyError('"%s" is not a registered web API capabilities set'
                       % capabilities_id)
