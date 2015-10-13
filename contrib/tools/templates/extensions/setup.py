from __future__ import unicode_literals

from reviewboard.extensions.packaging import setup


PACKAGE = "{{extension_name}}"
VERSION = "0.1"

setup(
    name=PACKAGE,
    version=VERSION,
    description="{{description}}",
    author="{{author}}",
    packages=["{{package_name}}"],
    entry_points={
        'reviewboard.extensions':
            '%s = {{package_name}}.extension:{{class_name}}' % PACKAGE,
    },
    package_data={
        b'{{package_name}}': [
            'templates/{{package_name}}/*.txt',
            'templates/{{package_name}}/*.html',
        ],
    }
)
