from djblets.extensions.packaging import (
    BuildStaticFiles as DjbletsBuildStaticFiles,
    build_extension_cmdclass)
from setuptools import setup as setuptools_setup


class BuildStaticFiles(DjbletsBuildStaticFiles):
    extension_entrypoint_group = 'reviewboard.extensions'
    django_settings_module = 'reviewboard.settings'


def setup(**setup_kwargs):
    setup_kwargs.update({
        'zip_safe': False,
        'include_package_data': True,
        'cmdclass': dict(build_extension_cmdclass(BuildStaticFiles),
                         **setup_kwargs.get('cmdclass', {})),
    })

    setuptools_setup(**setup_kwargs)
