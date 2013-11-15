from __future__ import unicode_literals

import os

from djblets.extensions.packaging import (
    BuildStaticFiles as DjbletsBuildStaticFiles,
    build_extension_cmdclass)
from setuptools import setup as setuptools_setup

from reviewboard import VERSION


class BuildStaticFiles(DjbletsBuildStaticFiles):
    extension_entrypoint_group = 'reviewboard.extensions'
    django_settings_module = 'reviewboard.settings'

    def get_lessc_global_vars(self):
        # NOTE: Command (the base class) is not a new-style object, so
        #       we can't use super().
        global_vars = DjbletsBuildStaticFiles.get_lessc_global_vars(self)
        global_vars.update({
            'RB_MAJOR_VERSION': VERSION[0],
            'RB_MINOR_VERSION': VERSION[1],
            'RB_MICRO_VERSION': VERSION[2],
            'RB_PATCH_VERSION': VERSION[3],
            'RB_IS_RELEASED': VERSION[5],
        })

        return global_vars


def setup(**setup_kwargs):
    os.environ['FORCE_BUILD_MEDIA'] = '1'

    setup_kwargs.update({
        'zip_safe': False,
        'include_package_data': True,
        'cmdclass': dict(build_extension_cmdclass(BuildStaticFiles),
                         **setup_kwargs.get('cmdclass', {})),
    })

    setuptools_setup(**setup_kwargs)
