from __future__ import unicode_literals

import inspect
import os
import sys

import pkg_resources
from django.core.management import call_command
from django.utils import six
from setuptools.command.build_py import build_py
from setuptools import Command


class BuildStaticFiles(Command):
    """Builds static files for the extension.

    This will build the static media files used by the extension. JavaScript
    bundles will be minified and versioned. CSS bundles will be processed
    through lesscss (if using .less files), minified and versioned.

    This must be subclassed by the project offering the extension support.
    The subclass must provide the extension_entrypoint_group and
    django_settings_module parameters.

    extension_entrypoint_group is the group name that entry points register
    into.

    django_settings_module is the Python module path for the project's
    settings module, for use in the DJANGO_SETTINGS_MODULE environment
    variable.
    """
    description = 'Build static media files'
    extension_entrypoint_group = None
    django_settings_module = None

    user_options = [
        (b'remove-source-files', None, 'remove source files from the package'),
    ]
    boolean_options = [b'remove-source-files']

    def initialize_options(self):
        self.build_lib = None
        self.remove_source_files = False

    def finalize_options(self):
        self.set_undefined_options('build', ('build_lib', 'build_lib'))

    def get_lessc_global_vars(self):
        """Returns a dictionary of LessCSS global variables and their values.

        This can be implemented by subclasses to provide global variables for
        .less files for processing.

        By default, this defines two variables: ``STATIC_ROOT`` and ``DEBUG``.

        ``STATIC_ROOT`` is set to ``/static/``. Any imports using
        ``@{STATIC_ROOT}`` will effectively look up the requested file in
        ``<import_path>/@{STATIC_ROOT}``. This assumes that the project
        serving the static files keeps them in :file:`static/{appname}/`.

        Projects using less.js for the runtime can then define ``STATIC_ROOT``
        to ``settings.STATIC_URL``, ensuring lookups work for development and
        packaged extensions.

        ``DEBUG`` is set to false. Runtimes using less.js can set this to
        ``settings.DEBUG`` for templates. This can be useful for LessCSS
        guards.

        This requires LessCSS 1.5.1 or higher.
        """
        return {
            'DEBUG': False,
            'STATIC_ROOT': '/static/',
        }

    def get_lessc_include_path(self):
        """Returns the include path for LessCSS imports.

        By default, this will include the parent directory of every path in
        STATICFILES_DIRS, plus the static directory of the extension.
        """
        from django.conf import settings

        less_include = set()

        for staticfile_dir in settings.STATICFILES_DIRS:
            if isinstance(staticfile_dir, tuple):
                staticfile_dir = staticfile_dir[1]

            dirname = os.path.dirname(staticfile_dir)

            if os.path.basename(dirname) == 'static':
                # Static files should be living within a static/ directory,
                # generally-speaking. That's how they'll be referenced when
                # using @{STATIC_ROOT}. If we find a static file dir living
                # inside a static/ directory, strip away the static/ so that
                # lookups will work.
                dirname = os.path.dirname(dirname)

            less_include.add(dirname)

        return less_include

    def run(self):
        from django.conf import settings

        # Prepare to import the project's settings file, and the extension
        # modules that are being shipped, so we can scan for the bundled
        # media.
        old_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
        os.environ['DJANGO_SETTINGS_MODULE'] = self.django_settings_module
        cwd = os.getcwd()
        sys.path = [
            os.path.join(cwd, package_name)
            for package_name in self.distribution.packages
        ] + sys.path

        # Set up the common Django settings for the builds.
        settings.STATICFILES_FINDERS = (
            'djblets.extensions.staticfiles.PackagingFinder',
        )
        settings.STATICFILES_STORAGE = \
            'djblets.extensions.staticfiles.PackagingCachedFilesStorage'
        settings.INSTALLED_APPS = [
            'django.contrib.staticfiles',
        ]
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            },
        }

        # Load the entry points this package is providing, so we'll know
        # which extensions to scan.
        entrypoints = pkg_resources.EntryPoint.parse_map(
            self.distribution.entry_points,
            dist=self.distribution)

        extension_entrypoints = \
            entrypoints.get(self.extension_entrypoint_group)
        assert extension_entrypoints, 'No extension entry points were defined.'

        # Begin building pipeline bundles for each of the bundles defined
        # in the extension.
        for ep_name, entrypoint in six.iteritems(extension_entrypoints):
            try:
                extension = entrypoint.load(require=False)
            except ImportError:
                sys.stderr.write(
                    'Error loading the extension for entry point %s\n'
                    % ep_name)
                raise

            self._build_static_media(extension)

        # Restore the environment, so we don't possibly interfere with
        # anything else.
        if old_settings_module is not None:
            os.environ['DJANGO_SETTINGS_MODULE'] = old_settings_module

        sys.path = sys.path[len(self.distribution.packages):]

    def _build_static_media(self, extension):
        from django.conf import settings

        pipeline_js = {}
        pipeline_css = {}

        self._add_bundle(pipeline_js, extension.js_bundles, 'js', '.js')
        self._add_bundle(pipeline_css, extension.css_bundles, 'css', '.css')

        # Get the location of the static/ directory within the module in the
        # source tree. We're going to use it to look up static files for
        # input, and as a relative path within the module for the output.
        module_dir = os.path.dirname(inspect.getmodule(extension).__file__)
        static_dir = os.path.join(module_dir, 'static')

        if not os.path.exists(static_dir):
            # This extension doesn't define any static files.
            return

        from djblets.extensions.staticfiles import PackagingFinder
        PackagingFinder.extension_static_dir = static_dir

        settings.STATICFILES_DIRS = list(settings.STATICFILES_DIRS) + [
            PackagingFinder.extension_static_dir
        ]

        # Register the include path and any global variables used for
        # building .less files.
        settings.PIPELINE_LESS_ARGUMENTS = ' '.join(
            [
                '--include-path=%s'
                % os.path.pathsep.join(self.get_lessc_include_path())
            ] + [
                '--global-var="%s=%s"'
                % (key, self._serialize_lessc_value(value))
                for key, value in six.iteritems(self.get_lessc_global_vars())
            ]
        )

        settings.PIPELINE_JS = pipeline_js
        settings.PIPELINE_CSS = pipeline_css
        settings.PIPELINE_ENABLED = True
        settings.PIPELINE_STORAGE = \
            'djblets.extensions.staticfiles.PackagingStorage'
        settings.STATIC_ROOT = \
            os.path.join(self.build_lib,
                         os.path.relpath(os.path.join(module_dir, 'static')))

        # Due to how Pipeline copies and stores its settings, we actually
        # have to copy over some of these, as they'll be from the original
        # loaded settings.
        from pipeline.conf import settings as pipeline_settings

        for key in six.iterkeys(pipeline_settings.__dict__):
            if hasattr(settings, key):
                setattr(pipeline_settings, key, getattr(settings, key))

        # Collect and process all static media files.
        call_command('collectstatic', interactive=False, verbosity=2)

        if self.remove_source_files:
            self._remove_source_files(
                pipeline_css, os.path.join(settings.STATIC_ROOT, 'css'))
            self._remove_source_files(
                pipeline_js, os.path.join(settings.STATIC_ROOT, 'js'))

    def _add_bundle(self, pipeline_bundles, extension_bundles, default_dir,
                    ext):
        for name, bundle in six.iteritems(extension_bundles):
            if 'output_filename' not in bundle:
                bundle['output_filename'] = \
                    '%s/%s.min%s' % (default_dir, name, ext)

            pipeline_bundles[name] = bundle

    def _remove_source_files(self, pipeline_bundles, media_build_dir):
        """Removes all source files, leaving only built bundles."""
        for root, dirs, files in os.walk(media_build_dir, topdown=False):
            for name in files:
                # A valid file will be represented as one of:
                #
                #     (bundle_name, 'min', stamp, ext)
                #     (bundle_name, 'min', ext)
                #
                # We keep both the pre-stamped and post-stamped versions so
                # that Django's CachedFilesStorage can generate and cache
                # the stamp from the contents of the non-stamped file.
                name_parts = name.split('.')

                if (len(name_parts) < 3 or
                    name_parts[0] not in pipeline_bundles or
                    name_parts[1] != 'min'):
                    # This doesn't appear to be a file representing a bundle,
                    # so we should get rid of it.
                    os.unlink(os.path.join(root, name))

            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except:
                    # The directory is probably not empty yet.
                    pass

    def _serialize_lessc_value(self, value):
        if isinstance(value, six.text_type):
            return '\\"%s\\"' % value
        elif isinstance(value, bool):
            if value:
                return 'true'
            else:
                return 'false'
        elif isinstance(value, int):
            return '%d' % value
        else:
            raise TypeError('%r is not a valid lessc global variable value'
                            % value)


class BuildPy(build_py):
    def run(self):
        self.run_command('build_static_files')
        build_py.run(self)


def build_extension_cmdclass(build_static_files_cls):
    """Builds a cmdclass to pass to setup.

    This is passed a subclass of BuildStaticFiles, and returns something
    that can be passed to setup().
    """
    return {
        'build_static_files': build_static_files_cls,
        'build_py': BuildPy,
    }
