from __future__ import unicode_literals

import os

from django.contrib.staticfiles.finders import get_finders
from django.contrib.staticfiles.storage import staticfiles_storage

from pipeline.conf import settings

from manifesto import Manifest

from pipeline.packager import Packager


class PipelineManifest(Manifest):
    def __init__(self):
        self.packager = Packager()
        self.packages = self.collect_packages()
        self.finders = get_finders()
        self.package_files = []

    def collect_packages(self):
        packages = []
        for package_name in self.packager.packages['css']:
            package = self.packager.package_for('css', package_name)
            if package.manifest:
                packages.append(package)
        for package_name in self.packager.packages['js']:
            package = self.packager.package_for('js', package_name)
            if package.manifest:
                packages.append(package)
        return packages

    def cache(self):
        ignore_patterns = getattr(settings, "STATICFILES_IGNORE_PATTERNS", None)

        if settings.PIPELINE_ENABLED:
            for package in self.packages:
                path = package.output_filename
                self.package_files.append(path)
                yield staticfiles_storage.url(path)
        else:
            for package in self.packages:
                for path in self.packager.compile(package.paths):
                    self.package_files.append(path)
                    yield staticfiles_storage.url(path)

        for finder in self.finders:
            for path, storage in finder.list(ignore_patterns):
                # Prefix the relative path if the source storage contains it
                if getattr(storage, 'prefix', None):
                    prefixed_path = os.path.join(storage.prefix, path)
                else:
                    prefixed_path = path

                # Dont add any doubles
                if prefixed_path not in self.package_files:
                    self.package_files.append(prefixed_path)
                    yield staticfiles_storage.url(prefixed_path)
