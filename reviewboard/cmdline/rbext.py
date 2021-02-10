"""Command line tool for helping develop extensions.

This tool, :command:`rbext`, currently provides the ability to easily run
extension-provided unit tests. In the future, it'll also help with other
development tasks, and with updating the Package Store with the latest versions
of an extension.
"""

from __future__ import print_function, unicode_literals

import argparse
import logging
import os
import re
import sys
from importlib import import_module
from textwrap import dedent

os.environ.setdefault(str('DJANGO_SETTINGS_MODULE'),
                      str('reviewboard.settings'))

rbext_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(rbext_dir, 'conf', 'rbext'))

import pkg_resources
from django.utils.encoding import force_str

from reviewboard import get_manual_url
from reviewboard.cmdline.utils.argparsing import (HelpFormatter,
                                                  RBProgVersionAction)
from reviewboard.cmdline.utils.console import init_console


# NOTE: We want to include Django-based modules as late as possible, in order
#       to allow extension-provided settings to apply.


MANUAL_URL = get_manual_url()
EXTENSION_MANUAL_URL = '%sextending/' % MANUAL_URL

console = None


class BaseCommand(object):
    """Base class for a command."""

    #: The name of a command.
    #:
    #: This is what the user will type on the command line after ``rbext``.
    name = None

    #: The summary of the command.
    #:
    #: This will be shown in the help output.
    help_summary = 'Run unit tests for an extension.'

    #: A description of the command, when displaying the command's own help.
    description_text = None

    def add_options(self, parser):
        """Add any command-specific options to the parser.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser.
        """
        pass

    def run(self, options):
        """Run the command.

        This will perform common setup work and then hand things off to
        :py:meth:`main`.

        Args:
            options (argparse.Namespace):
                Options set from the arguments.
        """
        if options.settings_file:
            sys.path.insert(
                0,
                os.path.abspath(os.path.dirname(options.settings_file)))

        return self.main(options)

    def main(self, options):
        """Perform the main operations for the command.

        Args:
            options (argparse.Namespace):
                Options set from the arguments.

        Returns:
            int:
            The command's exit code.
        """
        raise NotImplementedError

    def error(self, msg):
        """Display a fatal error to the user and exit.

        Args:
            msg (unicode):
                The message to display.

        Raises:
            django.core.management.CommandError:
            The resulting error.
        """
        from django.core.management import CommandError

        raise CommandError(msg)


class TestCommand(BaseCommand):
    """A command that runs an extension's test suite."""

    name = 'test'
    help_summary = 'Run unit tests for an extension.'
    description_text = (
        'Runs the unit tests for your extension, looking for any tests.py '
        'or tests/*.py files.\n'
        '\n'
        'For simple extensions, you can just provide -m <modulename>.\n'
        '\n'
        'For more advanced extensions with many apps, you may need to '
        'define a custom settings_local.py file in your tree based on your '
        'Review Board development environment, RB_EXTRA_APPS to a list of '
        'Django app names required by the extension.\n'
        '\n'
        'This will wrap the "nose" test runner, which provides many '
        'additional options for running your tests. To see all available '
        'options, run:\n'
        '\n'
        '  nosetests --help\n'
        '\n'
        'To use any additional "nose" options, run this command with a '
        '"--" before the arguments and test names:\n'
        '\n'
        '  rbext test <options> -- <nose-options> <tests>'
    )

    def add_options(self, parser):
        """Add command line arguments for running tests.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser.
        """
        parser.add_argument(
            '--app',
            metavar='APP_LABEL',
            action='append',
            dest='app_names',
            help='A Django app label to add to the list of installed apps. '
                 'This is only required for tests that use apps not '
                 'enabled by extensions.')
        parser.add_argument(
            '-e',
            '--extension',
            metavar='EXTENSION_CLASS',
            dest='extension_class',
            help='The full module and class path to the extension to test.')
        parser.add_argument(
            '-m',
            '--module',
            action='append',
            metavar='MODULE_NAME',
            dest='module_names',
            help='The name(s) of the extension module(s) to test. For '
                 'example, if your tests are in "myextension.tests", you '
                 'might want to use "myextension". This may require '
                 'specifying multiple modules in the extension, and any '
                 'dependencies. You may want to use --extension instead.')
        parser.add_argument(
            '--pdb',
            action='append_const',
            dest='test_options',
            const='--pdb',
            help='Drop into a debugger on any failures or errors.')
        parser.add_argument(
            '--tree-root',
            metavar='PATH',
            default=os.getcwd(),
            help='The path to the root of the source tree.')
        parser.add_argument(
            '--with-coverage',
            action='append_const',
            dest='test_options',
            const='--with-coverage',
            help='Display a report on code covered or missed by tests.')
        parser.add_argument(
            '-x',
            '--stop',
            action='append_const',
            dest='test_options',
            const='-x',
            help='Stop running tests after the first failure.')
        parser.add_argument(
            'tests',
            metavar='TEST',
            nargs='*',
            help='Specific tests to run. This can be in the form of '
                 'mypackage.mymodule, mypackage.mymodule:TestsClass, or '
                 'mypackage.mymodule:TestsClass.test_method.')

    def main(self, options):
        """Main function for running unit tests for the extension.

        Args:
            options (argparse.Namespace):
                Options set from the arguments.

        Returns:
            int:
            The command's exit code.
        """
        module_names = options.module_names or []

        os.environ[str('RB_TEST_MODULES')] = force_str(','.join(module_names))

        os.chdir(options.tree_root)
        os.environ[str('RB_RUNNING_TESTS')] = str('1')

        from django import setup
        from django.apps import apps
        from django.conf import settings

        if not apps.ready:
            setup()

        installed_apps = list(settings.INSTALLED_APPS)

        # If an explicit extension is specified, then we'll want to grab its
        # list of apps.
        extension_class_name = options.extension_class

        if extension_class_name:
            module_name, class_name = extension_class_name.rsplit('.', 1)

            try:
                extension_class = getattr(import_module(module_name),
                                          class_name)
            except AttributeError:
                console.error('The provided extension class "%s" could not be '
                              'found in %s'
                              % (class_name, module_name))
                return 1
            except ImportError:
                console.error('The provided extension class module "%s" '
                              'could not be found'
                              % module_name)
                return 1

            installed_apps += (extension_class.apps or
                               [module_name.rsplit('.', 1)[0]])

        if options.app_names:
            installed_apps += options.app_names

        if installed_apps != list(settings.INSTALLED_APPS):
            settings.INSTALLED_APPS = installed_apps
            apps.set_installed_apps(installed_apps)

        from reviewboard.test import RBTestRunner

        test_runner = RBTestRunner(test_packages=module_names,
                                   cover_packages=module_names,
                                   verbosity=1,
                                   needs_collect_static=False)

        # Don't use +=, as we don't want to modify the list on the class.
        # We want to create a new one on the instance.
        test_runner.nose_options = \
            test_runner.nose_options + (options.test_options or [])

        failures = test_runner.run_tests(options.tests)

        if failures:
            return 1
        else:
            return 0


class CreateCommand(BaseCommand):
    """A command for creating a new extension package."""

    name = 'create'
    help_summary = 'Create a new extension source tree.'
    description_text = (
        'This takes care of creating a boilerplate extension and source '
        'tree, giving you a starting point for developing a new extension.\n'
        '\n'
        'See the documentation for creating extensions:\n'
        '\n'
        '%(extension_manual_url)s'
        % {
            'extension_manual_url': EXTENSION_MANUAL_URL,
        }
    )

    def add_options(self, parser):
        """Add command line arguments for creating an extension.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser.
        """
        parser.add_argument(
            '--name',
            required=True,
            help='The human-readable name for the extension. This is '
                 'required.')
        parser.add_argument(
            '--class-name',
            default=None,
            help='The class name for the extension (generally in CamelCase '
                 'form, without spaces). If not provided, this will be '
                 'based on the extension name.')
        parser.add_argument(
            '--package-name',
            default=None,
            help='The name of the package (using alphanumeric  ). '
                 'If not provided, this will be based on the exension '
                 'name.')
        parser.add_argument(
            '--package-version',
            default='1.0',
            help='The version for your extension and package.')
        parser.add_argument(
            '--summary',
            default=None,
            help='A one-line summary of the extension.')
        parser.add_argument(
            '--description',
            default=None,
            help='A short description of the extension.')
        parser.add_argument(
            '--author-name',
            default=None,
            help='The name of the author for the package and extension '
                 'metadata. This can be a company name.')
        parser.add_argument(
            '--author-email',
            default=None,
            help='The e-mail address of the author for the package and '
                 'extension metadata.')
        parser.add_argument(
            '--enable-configuration',
            action='store_true',
            default=False,
            help='Whether to enable a Configure button and view for the '
                 'extension.')
        parser.add_argument(
            '--enable-static-media',
            action='store_true',
            default=False,
            help='Whether to enable static media files for the package.')

    def main(self, options):
        """Main function for creating an extension.

        Args:
            options (argparse.Namesapce):
                Options set from the arguments.

        Returns:
            int:
            The comamnd's exit code.
        """
        self._process_options(options)

        name = options.name
        package_name = options.package_name
        summary = options.summary
        description = options.description
        class_name = options.class_name
        configurable = options.enable_configuration
        enable_static_media = options.enable_static_media

        # Create the directory hierarchy.
        root_dir = package_name

        if os.path.exists(root_dir):
            self.error(
                'There\'s already a directory named "%s". You must '
                'remove it before you can create a new extension '
                'there.'
                % root_dir)

        ext_dir = os.path.join(root_dir, package_name)
        static_dir = os.path.join(ext_dir, 'static')
        templates_dir = os.path.join(ext_dir, 'templates')

        for path in (root_dir, ext_dir):
            os.mkdir(path, 0o755)

        if enable_static_media:
            os.mkdir(static_dir, 0o755)

            for path in ('css', 'js', 'images'):
                os.mkdir(os.path.join(static_dir, path))

        # Create the packaging files.
        self._write_file(
            os.path.join(root_dir, 'README.rst'),
            self._create_readme(name=name,
                                summary=summary,
                                description=description))

        self._write_file(
            os.path.join(root_dir, 'MANIFEST.in'),
            self._create_manifest(static_dir=static_dir,
                                  templates_dir=templates_dir))

        self._write_file(
            os.path.join(root_dir, 'setup.py'),
            self._create_setup_py(package_name=package_name,
                                  version=options.package_version,
                                  summary=summary,
                                  author=options.author_name,
                                  author_email=options.author_email,
                                  class_name=class_name),
            mode=0o755)

        # Create the extension source files.
        self._write_file(os.path.join(ext_dir, '__init__.py'), '')

        self._write_file(
            os.path.join(ext_dir, 'extension.py'),
            self._create_extension_py(
                name=name,
                package_name=package_name,
                class_name=class_name,
                summary=summary,
                configurable=configurable,
                has_static_media=enable_static_media))

        if configurable:
            form_class_name = '%sForm' % class_name

            self._write_file(
                os.path.join(ext_dir, 'admin_urls.py'),
                self._create_admin_urls_py(
                    package_name=package_name,
                    class_name=class_name,
                    form_class_name=form_class_name))

            self._write_file(
                os.path.join(ext_dir, 'forms.py'),
                self._create_forms_py(form_class_name=form_class_name))

        # We're done!
        console.print('Generated a new extension in %s'
                      % os.path.abspath(root_dir))
        console.print()
        console.print('For information on writing your extension, see')
        console.print(EXTENSION_MANUAL_URL)

        return 0

    def _process_options(self, options):
        """Process and normalize any provided options.

        This will attempt to provide suitable defaults for missing parameters,
        adn to check that others are valid.

        Args:
            options (argparse.Namesapce):
                Options set from the arguments.
        """
        name = options.name.strip()
        package_name = options.package_name
        class_name = options.class_name

        if not package_name:
            package_name = self._normalize_package_name(name)
            console.print('Using "%s" as the package name.' % package_name)
        else:
            package_name = package_name.strip()

            if not re.match(r'[A-Za-z][A-Za-z0-9._-]*', package_name):
                self.error(
                    '"%s" is not a valid package name. Try --package-name="%s"'
                    % (package_name,
                       self._normalize_package_name(package_name)))

        if not class_name:
            class_name = self._normalize_class_name(name)
            console.print('Using "%s" as the extension class name.'
                          % class_name)
        else:
            class_name = class_name.strip()

            if not re.match(r'[A-Za-z][A-Za-z0-9_]+Extension$', class_name):
                self.error(
                    '"%s" is not a valid class name. Try --class-name="%s"'
                    % (package_name,
                       self._normalize_class_name(class_name)))

        options.name = name
        options.package_name = package_name
        options.class_name = class_name

    def _normalize_package_name(self, name):
        """Normalize a package name.

        This will ensure the package name is in a suitable format, replacing
        any invalid characters or dashes with ``_``, and converting it to
        lowercase.

        Args:
            name (unicode):
                The name of the package to normalize.

        Returns:
            unicode:
            The normalized name.
        """
        return pkg_resources.safe_name(name).replace('-', '_').lower()

    def _normalize_class_name(self, name):
        """Normalize a class name.

        This will ensure the class name is in a suitable format, converting it
        to CamelCase and adding an "Extension" at the end if needed.

        Args:
            name (unicode):
                The name of the class to normalize.

        Returns:
            unicode:
            The normalized class name.
        """
        class_name = ''.join(
            word.capitalize()
            for word in re.sub('[^A-Za-z0-9]+', ' ', name).split()
        )

        if not class_name.endswith('Extension'):
            class_name += 'Extension'

        return class_name

    def _write_file(self, filename, content, mode=None):
        """Write content to a file.

        This will create the file and write the provided content. The content
        will be stripped and dedented, with a trailing newline added, allowing
        the generation code to make use of multi-line strings.

        Args:
            path (unicode):
                The path of the file to write.

            content (unicode):
                The content to write.

            mode (int):
                The optional permissions mode to set for the file.
        """
        with open(filename, 'w') as fp:
            fp.write(dedent(content).strip())
            fp.write('\n')

        if mode is not None:
            os.chmod(filename, mode)

    def _create_readme(self, name, summary, description):
        """Create the content for a README.rst file.

        Args:
            name (unicode):
                The extension's name.

            summary (unicode):
                The extension's summary.

            description (unicode):
                A description of the extension.

        Returns:
            unicode:
            The resulting content for the file.
        """
        return """
            %(header_bar)s
            %(header)s
            %(header_bar)s

            %(content)s
        """ % {
            'header': name,
            'header_bar': '=' * len(name),
            'content': '\n\n'.join(
                content
                for content in (summary, description)
                if content
            ) or 'Describe your extension.',
        }

    def _create_manifest(self, templates_dir, static_dir):
        """Create the content for a MANIFEST.in file.

        Args:
            templates_dir (unicode):
                The relative path to the templates directory.

            static_dir (unicode):
                The relative path to the static media directory.

        Returns:
            unicode:
            The resulting content for the file.
        """
        return """
            graft %(templates_dir)s
            graft %(static_dir)s

            include COPYING
            include INSTALL
            include README.md
            include *-requirements.txt

            global-exclude .*.sw[op] *.py[co] __pycache__ .DS_Store .noseids
        """ % {
            'templates_dir': templates_dir,
            'static_dir': static_dir,
        }

    def _create_setup_py(self, package_name, version, summary, author,
                         author_email, class_name):
        """Create the content for a setup.py file.

        Args:
            package_name (unicode):
                The name of the package.

            version (unicode):
                The version of the package.

            summary (unicode):
                A summary of the package.

            author (unicode):
                The name of the author of the extension.

            author_email (unicode):
                The e-mail address of the author of the extension.

            class_name (unicode):
                The name of the extension class.

        Returns:
            unicode:
            The resulting content for the file.
        """
        return """
            #!/usr/bin/env python

            from __future__ import unicode_literals

            from reviewboard.extensions.packaging import setup
            from setuptools import find_packages


            setup(
                name='%(package_name)s',
                version='%(version)s',
                description=%(description)s,
                author=%(author)s,
                author_email=%(author_email)s,
                packages=find_packages(),
                install_requires=[
                    # Your package dependencies go here.
                    # Don't include "ReviewBoard" in this list.
                ],
                entry_points={
                    'reviewboard.extensions': [
                        '%(package_name)s = %(ext_class_path)s',
                    ],
                },
                classifiers=[
                    # For a full list of package classifiers, see
                    # %(classifiers_url)s

                    'Development Status :: 3 - Alpha',
                    'Environment :: Web Framework',
                    'Framework :: Review Board',
                    'Operating System :: OS Independent',
                    'Programming Language :: Python',
                ],
            )
        """ % {
            'author': self._sanitize_string_for_python(author or
                                                       '<REPLACE ME>'),
            'author_email': self._sanitize_string_for_python(author_email or
                                                             '<REPLACE ME>'),
            'classifiers_url':
                'https://pypi.python.org/pypi?%3Aaction=list_classifiers',
            'description': self._sanitize_string_for_python(summary or
                                                            '<REPLACE ME>'),
            'ext_class_path': '%s.extension:%s' % (package_name, class_name),
            'package_name': package_name,
            'version': version,
        }

    def _create_extension_py(self, name, package_name, class_name, summary,
                             configurable, has_static_media):
        """Create the content for an extension.py file.

        Args:
            name (unicode):
                The name of the extension.

            package_name (unicode):
                The name of the package.

            class_name (unicode):
                The name of the extension class.

            summary (unicode):
                A summary of the extension.

            configurable (bool):
                Whether the package is set to be configurable.

            has_static_media (bool):
                Whether the package is set to have static media files.

        Returns:
            unicode:
            The resulting content for the file.
        """
        extension_docs_url = '%sextensions/' % EXTENSION_MANUAL_URL

        static_media_content = """
                # You can create a list of CSS bundles to compile and ship
                # with your extension. These can include both *.css and
                # *.less (http://lesscss.org/) files. See
                # %(static_docs_url)s
                css_bundles = {
                    'my-bundle-name': {
                        'source_filenames': [
                            'css/style.less',
                        ],
                        'apply_to': ['my-view-url-name'],
                    },
                }

                # JavaScript bundles are also supported. These support
                # standard *.js files and *.es6.js files (which allow for
                # writing and transpiling ES6 JavaScript).
                js_bundles = {
                    'my-bundle-name': {
                        'source_filenames': [
                            'js/script.es6.js',
                            'js/another-script.js',
                        ],
                    },
                }
        """ % {
            'static_docs_url': '%sstatic-files/' % extension_docs_url,
        }

        configuration_content = """
                # Default values for any configuration settings for your
                # extension.
                default_settings = {
                    'my_field_1': 'my default value',
                    'my_field_2': False,
                }

                # Set is_configurable and define an admin_urls.py to add
                # a standard configuration page for your extension.
                # See %(configure_docs_url)s
                is_configurable = True
        """ % {
            'configure_docs_url': '%sconfiguration/' % extension_docs_url,
        }

        return '''
            """%(name)s for Review Board."""

            from __future__ import unicode_literals

            from django.utils.translation import ugettext_lazy as _
            from reviewboard.extensions.base import Extension
            from reviewboard.extensions.hooks import TemplateHook


            class %(class_name)s(Extension):
                """Internal description for your extension here."""

                metadata = {
                    'Name': _(%(metadata_name)s),
                    'Summary': _(%(metadata_summary)s),
                }
            %(extra_class_content)s
                def initialize(self):
                    """Initialize the extension."""
                    # Set up any hooks your extension needs here. See
                    # %(hooks_docs_url)s
                    TemplateHook(self,
                                 'before-login-form',
                                 '%(package_name)s/before-login-form.html')
        ''' % {
            'class_name': class_name,
            'extra_class_content': ''.join(
                extra_content
                for extra_content, should_add in (
                    (configuration_content, configurable),
                    (static_media_content, has_static_media))
                if should_add
            ),
            'hooks_docs_url': '%s#python-extension-hooks' % extension_docs_url,
            'metadata_name': self._sanitize_string_for_python(name),
            'metadata_summary': self._sanitize_string_for_python(
                summary or 'REPLACE ME'),
            'name': name,
            'package_name': package_name,
        }

    def _create_admin_urls_py(self, package_name, class_name, form_class_name):
        """Create the content for an admin_urls.py file.

        Args:
            package_name (unicode):
                The name of the package.

            class_name (unicode):
                The name of the extension class.

            form_class_name (unicode):
                The name of the extension settings form class.

        Returns:
            unicode:
            The resulting content for the file.
        """
        return '''
            """Administration and configuration URLs for the extension."""

            from __future__ import unicode_literals

            from django.conf.urls import url
            from reviewboard.extensions.views import configure_extension

            from %(package_name)s.extension import %(class_name)s
            from %(package_name)s.forms import %(form_class_name)s


            urlpatterns = [
                url(r'^$',
                    configure_extension,
                    {
                        'ext_class': %(class_name)s,
                        'form_class': %(form_class_name)s,
                    }),
            ]
        ''' % {
            'class_name': class_name,
            'form_class_name': form_class_name,
            'package_name': package_name,
        }

    def _create_forms_py(self, form_class_name):
        """Create the content for a forms.py file.

        Args:
            form_class_name (unicode):
                The name of the extension settings form class.

        Returns:
            unicode:
            The resulting content for the file.
        """
        return '''
            """Configuration forms for the extension."""

            from __future__ import unicode_literals

            from django import forms
            from djblets.extensions.forms import SettingsForm


            class %(form_class_name)s(SettingsForm):
                my_field_1 = forms.CharField()
                my_field_2 = forms.BooleanField()
        ''' % {
            'form_class_name': form_class_name,
        }

    def _sanitize_string_for_python(self, s):
        """Sanitize a string for inclusion in a Python source file.

        This will return a string representation without any leading ``u``
        (when run on Python 2.x).

        Args:
            s (unicode):
                The string to sanitize.

        Returns:
            unicode:
            The sanitized string.
        """
        s = repr(s)

        if s.startswith('u'):
            s = s[1:]

        return s


class RBExt(object):
    """Command line tool for helping develop Review Board extensions.

    This tool provides subcommands useful for extension developers. It
    currently provides:

    * ``test``: Runs an extension's test suite.
    """

    COMMANDS = [
        CreateCommand(),
        TestCommand(),
    ]

    def run(self, argv):
        """Run an rbext command with the provided arguments.

        During the duration of the run, :py:data:`sys.argv` will be set to
        the provided arguments.

        Args:
            argv (list of unicode):
                The command line arguments passed to the command. This should
                not include the executable name as the first element.

        Returns:
            int:
            The command's exit code.
        """
        global console

        console = init_console()

        command, options = self.parse_options(argv)

        # We call out to things like the test runner, which expect to operate
        # off of sys.argv. We want to simulate that now that we've parsed
        # options. We'll restore sys.argv after the command finishes.
        old_argv = sys.argv
        sys.argv = argv

        try:
            return command.run(options)
        except Exception as e:
            logging.exception('Unexpected exception when running command '
                              '"%s": %s',
                              command.name, e)
            return 1
        finally:
            sys.argv = old_argv

    def parse_options(self, argv):
        """Parse arguments for the command.

        Args:
            argv (list of unicode):
                The arguments provided on the command line.

        Returns:
            unicode:
            The name of the command to run.
        """
        parser = argparse.ArgumentParser(
            prog='rbext',
            usage='%(prog)s <command>',
            formatter_class=HelpFormatter,
            description=(
                'rbext helps create initial source code trees for extensions '
                'and helps run extension test suites within a '
                'pre-established Review Board development environment.\n'
                '\n'
                'To get help on an individual command, run:\n'
                '\n'
                '  rbext <command> --help'
            ))
        parser.add_argument(
            '--version',
            action=RBProgVersionAction)

        subparsers = parser.add_subparsers(
            title='Commands',
            dest='command',
            description=(
                'To get additional help for these commands, run: '
                'rb-site <command> --help'
            ))

        commands = sorted(self.COMMANDS, key=lambda cmd: cmd.name)
        command_map = {}

        for command in commands:
            command_map[command.name] = command

            subparser = subparsers.add_parser(
                command.name,
                formatter_class=HelpFormatter,
                prog='%s %s' % (parser.prog, command.name),
                description=command.description_text,
                help=command.help_summary)

            subparser.add_argument(
                '-d',
                '--debug',
                action='store_true',
                dest='debug',
                default=False,
                help='Display debug output.')
            subparser.add_argument(
                '-s',
                '--settings-file',
                dest='settings_file',
                default=None,
                help='test_settings.py file to use for any custom settings.')

            command.add_options(subparser)

        # Prevent the '--' and anything after it from being parsed, so the
        # command can work with it.
        try:
            i = argv.index('--')
            argv = argv[:i]
        except ValueError:
            # The "--" isn't in the list anywhere.
            pass

        options = parser.parse_args(argv)

        return command_map[options.command], options


def main():
    """Run rbext.

    This is used by the Python EntryPoint to run rbext. It will pass in any
    arguments found on the command line and exit with the correct error code.
    """
    sys.exit(RBExt().run(sys.argv[1:]))
