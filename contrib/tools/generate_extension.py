#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import re
from optparse import OptionParser

from django.utils.six.moves import input
from jinja2 import Environment, FileSystemLoader

from reviewboard import get_version_string


env = Environment(
    loader=FileSystemLoader(os.path.join(
        os.path.dirname(__file__), 'templates', 'extensions')))

options = None


def get_confirmation(question):
    """
    Will pose the question to the user and keep asking them until they
    provide an answer that starts with either a 'y' or an 'n', at which
    point it will return True if it was a 'y'.
    """
    while True:
        response = input("%s (y/n): " % question).lower()
        if re.match(r'^[yn]', response) is not None:
            break
        print("Incorrect option '%s'" % response)

    return response[0] == 'y'


class NamingConvention(object):
    """
    Provides functionality for testing adherence to a naming convention
    and a method for converting a string to the convention.
    """
    ILLEGAL_CHARACTERS = re.compile(r'[^A-Za-z0-9 ]')

    def formatted(self, string):
        return False

    def convert(self, string):
        return string


class CamelCase(NamingConvention):
    """
    This represents the camel case naming convention and is typically used for
    class names. All tokens are one of the following:
        1) Alphabetic and starting with a capital
        2) Numeric
        3) Alphanumeric and starting with a capital letter
    There must be at least one token, and the first character must be a
    capital letter.
    """
    REGEX = re.compile(r'^[A-Z][a-z0-9]*(([0-9]+)|([A-Z][a-z0-9]*))*$')

    def formatted(self, string):
        return re.match(self.REGEX, string) is not None

    def convert(self, string):
        string = re.sub(self.ILLEGAL_CHARACTERS, " ", string)
        string = re.sub(r'([0-9a-zA-Z])([A-Z])', r'\1 \2', string)
        return ''.join([word.capitalize() for word in string.split()])


class LowerCaseWithUnderscores(NamingConvention):
    """
    This represents the case typically used for module/package names (and
    perhaps functions). All tokens are one of the following separated by
    an underscore:
        1) Alphabetic lower case
        2) Numeric
        3) Alphanumeric lower case and starting with a letter
    There must be at least one token, and the first character must be a letter.
    """
    REGEX = re.compile(r'^[a-z][a-z0-9]*(_+(([0-9]+)|([a-z][a-z0-9]*)))*_*$')

    def formatted(self, string):
        return re.match(self.REGEX, string) is not None

    def convert(self, string):
        string = re.sub(self.ILLEGAL_CHARACTERS, " ", string)
        string = re.sub(r'([0-9a-zA-Z])([A-Z])', r'\1 \2', string)
        return '_'.join(string.lower().split())


def get_formatted_string(string_type, string, fallback, case):
    """
    Given the name of the type of string, the string itself, and the fallback
    from which a string will be auto-generated in the given case if the given
    string does not conform to the case.
    """
    if string is not None:
        if case.formatted(string):
            return string
    else:
        string = case.convert(fallback)
        question = "Do you wish to use %s as the %s?" % \
                   (string, string_type)
        if not get_confirmation(question):
            string = input("Please input a %s: " % string_type)

    while not case.formatted(string):
        print("'%s' is not a valid %s." % (string, string_type))
        string = input("Please input a valid %s: " % string_type)

    return string


def parse_options():
    """
    Parses the options and stores them in the global options variable.
    """
    parser = OptionParser(usage="%prog name [options]",
                          version="Review Board " + get_version_string())
    parser.add_option("--class-name",
                      dest="class_name", default=None,
                      help="class name of extension (capitalized no spaces)")
    parser.add_option("--package-name",
                      dest="package_name", default=None,
                      help="package name of extension (lower case with "
                           "underscores)")
    parser.add_option("--description",
                      dest="description", default=None,
                      help="description of extension")
    parser.add_option("--author",
                      dest="author", default=None,
                      help="author of the extension")
    parser.add_option("--is-configurable",
                      dest="is_configurable", action="store_true",
                      default=False,
                      help="whether this extension is configurable")
    (globals()["options"], args) = parser.parse_args()

    if len(args) != 1:
        print("Error: incorrect number of arguments")
        parser.print_help()
        exit(-1)
    options.extension_name = args[0]

    autofill_unprovided_options()


def autofill_unprovided_options():
    """
    This will autofill all the empty 'necessary' options that can be auto-
    generated from the necessary fields.
    """
    options.package_name = get_formatted_string("package name",
                                                options.package_name,
                                                options.extension_name,
                                                LowerCaseWithUnderscores())
    options.class_name = get_formatted_string("class name",
                                              options.class_name,
                                              options.extension_name,
                                              CamelCase())

    if options.description is None:
        options.description = "Extension %s" % options.extension_name


class TemplateBuilder(object):
    """
    A builder that handles the creation of directories for the registed
    template files in addition to creating the output files by filling
    in the templates with the values from options.
    """
    def __init__(self, package_name, options):
        self.package_name = package_name
        self.options = vars(options)
        self.templates = {}
        self.directories = set()

    def add_template(self, template, target):
        target = re.sub("\{\{PACKAGE\}\}", self.package_name, target)
        self.templates[template] = target
        directory = os.path.dirname(target)
        self.add_directory(os.path.join(self.package_name, directory))

    def add_directory(self, dir_name):
        self.directories.add(dir_name)

    def build(self):
        self._build_directories()
        self._fill_templates()

    def _build_directories(self):
        if os.path.exists(self.package_name):
            question = "Directory '%s' already exists. " \
                       "Do you wish to continue?" \
                       % self.package_name
            if not get_confirmation(question):
                print("Exiting...")
                exit(-1)

        for directory in self.directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def _fill_templates(self):
        for template, target in self.templates.iteritems():
            self._write_file(template, target, self.options)

    def _write_file(self, template, target, file_opts):
        filepath = os.path.join(self.package_name, target)
        f = open(filepath, "w")
        template = env.get_template(template)
        f.writelines(template.render(file_opts))
        f.close()


def main():
    parse_options()
    builder = TemplateBuilder(options.package_name, options)
    builder.add_template("setup.py", "setup.py")
    builder.add_template("extension/extension.py",
                         "{{PACKAGE}}/extension.py")
    builder.add_template("extension/__init__.py",
                         "{{PACKAGE}}/__init__.py")
    builder.add_template("extension/admin_urls.py",
                         "{{PACKAGE}}/admin_urls.py")

    if options.is_configurable:
        builder.add_template("extension/templates/extension/configure.html",
                             "{{PACKAGE}}/templates/{{PACKAGE}}/configure.html"
                             )
        builder.add_template("extension/views.py",
                             "{{PACKAGE}}/views.py")

    builder.build()


if __name__ == "__main__":
    main()
