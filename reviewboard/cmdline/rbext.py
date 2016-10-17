"""Command line tool for helping develop extensions.

This tool, :command:`rbext`, currently provides the ability to easily run
extension-provided unit tests. In the future, it'll also help with other
development tasks, and with updating the Package Store with the latest versions
of an extension.
"""

from __future__ import unicode_literals

import argparse
import logging
import os
import sys

os.environ.setdefault(b'DJANGO_SETTINGS_MODULE', b'reviewboard.settings')

rbext_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(rbext_dir, 'conf', 'rbext'))

# NOTE: We want to include Django-based modules as late as possible, in order
#       to allow extension-provided settings to apply.


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


class TestCommand(BaseCommand):
    """A command that runs an extension's test suite."""

    name = 'test'
    help_summary = 'Run unit tests for an extension.'

    def add_options(self, parser):
        """Add command line arguments for running tests.

        Args:
            parser (argparse.ArgumentParser):
                The argument parser.
        """
        parser.add_argument(
            '--tree-root',
            metavar='PATH',
            default=os.getcwd(),
            help='The path to the root of the source tree.')
        parser.add_argument(
            '-m',
            '--module',
            action='append',
            metavar='MODULE_NAME',
            dest='module_names',
            required=True,
            help='The name(s) of the extension module(s) to test. For '
                 'example, if your tests are in "myextension.tests", you '
                 'might want to use "myextension".')

        # Note that we never actually handle this argument anywhere here.
        # This is really just to satisfy the parser. The test runner itself
        # handles it directly.
        parser.add_argument(
            '--with-coverage',
            action='store_true',
            default=False,
            help='Generate a code coverage report for the tests.')

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
        os.environ[b'RB_TEST_MODULES'] = b','.join(
            module_name.encode('utf-8')
            for module_name in options.module_names
        )

        os.chdir(options.tree_root)
        os.environ[b'RB_RUNNING_TESTS'] = b'1'

        from reviewboard.test import RBTestRunner

        test_runner = RBTestRunner(test_packages=options.module_names,
                                   cover_packages=options.module_names,
                                   verbosity=1)
        failures = test_runner.run_tests(options.tests)

        if failures:
            return 1
        else:
            return 0


class RBExt(object):
    """Command line tool for helping develop Review Board extensions.

    This tool provides subcommands useful for extension developers. It
    currently provides:

    * ``test``: Runs an extension's test suite.
    """

    COMMANDS = [
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
        parser = argparse.ArgumentParser(prog='rbext',
                                         usage='%(prog)s <command>')

        subparsers = parser.add_subparsers(
            title='Commands',
            dest='command')

        commands = sorted(self.COMMANDS, key=lambda cmd: cmd.name)
        command_map = {}

        for command in commands:
            command_map[command.name] = command

            subparser = subparsers.add_parser(
                command.name,
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
