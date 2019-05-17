from __future__ import unicode_literals

from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.testing import TestCase


class InterestingLinesTest(TestCase):
    """Unit tests for interesting lines scanner in differ."""

    def test_csharp(self):
        """Testing interesting lines scanner with a C# file"""
        a = ('public class HelloWorld {\n'
             '    public static void Main() {\n'
             '        System.Console.WriteLine("Hello world!");\n'
             '    }\n'
             '}\n')

        b = ('/*\n'
             ' * The Hello World class.\n'
             ' */\n'
             'public class HelloWorld\n'
             '{\n'
             '    /*\n'
             '     * The main function in this class.\n'
             '     */\n'
             '    public static void Main()\n'
             '    {\n'
             '        /*\n'
             '         * Print "Hello world!" to the screen.\n'
             '         */\n'
             '        System.Console.WriteLine("Hello world!");\n'
             '    }\n'
             '}\n')

        lines = self._get_lines(a, b, 'helloworld.cs')

        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0],
            [
                (0, 'public class HelloWorld {\n'),
                (1, '    public static void Main() {\n'),
            ])
        self.assertEqual(
            lines[1],
            [
                (3, 'public class HelloWorld\n'),
                (8, '    public static void Main()\n'),
            ])

    def test_java(self):
        """Testing interesting lines scanner with a Java file"""
        a = ('class HelloWorld {\n'
             '    public static void main(String[] args) {\n'
             '        System.out.println("Hello world!");\n'
             '    }\n'
             '}\n')

        b = ('/*\n'
             ' * The Hello World class.\n'
             ' */\n'
             'class HelloWorld\n'
             '{\n'
             '    /*\n'
             '     * The main function in this class.\n'
             '     */\n'
             '    public static void main(String[] args)\n'
             '    {\n'
             '        /*\n'
             '         * Print "Hello world!" to the screen.\n'
             '         */\n'
             '        System.out.println("Hello world!");\n'
             '    }\n'
             '}\n')

        lines = self._get_lines(a, b, 'helloworld.java')

        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0],
            [
                (0, 'class HelloWorld {\n'),
                (1, '    public static void main(String[] args) {\n'),
            ])
        self.assertEqual(
            lines[1],
            [
                (3, 'class HelloWorld\n'),
                (8, '    public static void main(String[] args)\n'),
            ])

    def test_javascript(self):
        """Testing interesting lines scanner with a JavaScript file"""
        a = ('function helloWorld() {\n'
             '    alert("Hello world!");\n'
             '}\n'
             '\n'
             'var data = {\n'
             '    helloWorld2: function() {\n'
             '        alert("Hello world!");\n'
             '    }\n'
             '}\n'
             '\n'
             'var helloWorld3 = function() {\n'
             '    alert("Hello world!");\n'
             '}\n')

        b = ('/*\n'
             ' * Prints "Hello world!"\n'
             ' */\n'
             'function helloWorld()\n'
             '{\n'
             '    alert("Hello world!");\n'
             '}\n'
             '\n'
             'var data = {\n'
             '    /*\n'
             '     * Prints "Hello world!"\n'
             '     */\n'
             '    helloWorld2: function()\n'
             '    {\n'
             '        alert("Hello world!");\n'
             '    }\n'
             '}\n'
             '\n'
             'var helloWorld3 = function()\n'
             '{\n'
             '    alert("Hello world!");\n'
             '}\n')

        lines = self._get_lines(a, b, 'helloworld.js')

        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0],
            [
                (0, 'function helloWorld() {\n'),
                (5, '    helloWorld2: function() {\n'),
                (10, 'var helloWorld3 = function() {\n'),
            ])
        self.assertEqual(
            lines[1],
            [
                (3, 'function helloWorld()\n'),
                (12, '    helloWorld2: function()\n'),
                (18, 'var helloWorld3 = function()\n'),
            ])

    def test_objective_c(self):
        """Testing interesting lines scanner with an Objective C file"""
        a = ('@interface MyClass : Object\n'
             '- (void) sayHello;\n'
             '@end\n'
             '\n'
             '@implementation MyClass\n'
             '- (void) sayHello {\n'
             '    printf("Hello world!");\n'
             '}\n'
             '@end\n')

        b = ('@interface MyClass : Object\n'
             '- (void) sayHello;\n'
             '@end\n'
             '\n'
             '@implementation MyClass\n'
             '/*\n'
             ' * Prints Hello world!\n'
             ' */\n'
             '- (void) sayHello\n'
             '{\n'
             '    printf("Hello world!");\n'
             '}\n'
             '@end\n')

        lines = self._get_lines(a, b, 'helloworld.m')

        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0],
            [
                (0, '@interface MyClass : Object\n'),
                (4, '@implementation MyClass\n'),
                (5, '- (void) sayHello {\n'),
            ])
        self.assertEqual(
            lines[1],
            [
                (0, '@interface MyClass : Object\n'),
                (4, '@implementation MyClass\n'),
                (8, '- (void) sayHello\n'),
            ])

    def test_perl(self):
        """Testing interesting lines scanner with a Perl file"""
        a = ('sub helloWorld {\n'
             '    print "Hello world!"\n'
             '}\n')

        b = ('# Prints Hello World\n'
             'sub helloWorld\n'
             '{\n'
             '    print "Hello world!"\n'
             '}\n')

        lines = self._get_lines(a, b, 'helloworld.pl')

        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], [(0, 'sub helloWorld {\n')])
        self.assertEqual(lines[1], [(1, 'sub helloWorld\n')])

    def test_php(self):
        """Testing interesting lines scanner with a PHP file"""
        a = ('<?php\n'
             'class HelloWorld {\n'
             '    function helloWorld() {\n'
             '        print "Hello world!";\n'
             '    }\n'
             '}\n'
             '?>\n')

        b = ('<?php\n'
             '/*\n'
             ' * Hello World class\n'
             ' */\n'
             'class HelloWorld\n'
             '{\n'
             '    /*\n'
             '     * Prints Hello World\n'
             '     */\n'
             '    function helloWorld()\n'
             '    {\n'
             '        print "Hello world!";\n'
             '    }\n'
             '\n'
             '    public function foo() {\n'
             '        print "Hello world!";\n'
             '    }\n'
             '}\n'
             '?>\n')

        lines = self._get_lines(a, b, 'helloworld.php')

        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0],
            [
                (1, 'class HelloWorld {\n'),
                (2, '    function helloWorld() {\n'),
            ])
        self.assertEqual(
            lines[1],
            [
                (4, 'class HelloWorld\n'),
                (9, '    function helloWorld()\n'),
                (14, '    public function foo() {\n'),
            ])

    def test_python(self):
        """Testing interesting lines scanner with a Python file"""
        a = ('class HelloWorld:\n'
             '    def main(self):\n'
             '        print "Hello World"\n')

        b = ('class HelloWorld:\n'
             '    """The Hello World class"""\n'
             '\n'
             '    def main(self):\n'
             '        """The main function in this class."""\n'
             '\n'
             '        # Prints "Hello world!" to the screen.\n'
             '        print "Hello world!"\n')

        lines = self._get_lines(a, b, 'helloworld.py')

        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0],
            [
                (0, 'class HelloWorld:\n'),
                (1, '    def main(self):\n'),
            ])
        self.assertEqual(
            lines[1],
            [
                (0, 'class HelloWorld:\n'),
                (3, '    def main(self):\n'),
            ])

    def test_ruby(self):
        """Testing interesting lines scanner with a Ruby file"""
        a = ('class HelloWorld\n'
             '    def helloWorld\n'
             '        puts "Hello world!"\n'
             '    end\n'
             'end\n')

        b = ('# Hello World class\n'
             'class HelloWorld\n'
             '    # Prints Hello World\n'
             '    def helloWorld()\n'
             '        puts "Hello world!"\n'
             '    end\n'
             'end\n')

        lines = self._get_lines(a, b, 'helloworld.rb')

        self.assertEqual(len(lines), 2)
        self.assertEqual(
            lines[0],
            [
                (0, 'class HelloWorld\n'),
                (1, '    def helloWorld\n'),
            ])
        self.assertEqual(
            lines[1],
            [
                (1, 'class HelloWorld\n'),
                (3, '    def helloWorld()\n'),
            ])

    def _get_lines(self, a, b, filename):
        differ = MyersDiffer(a.splitlines(True), b.splitlines(True))
        differ.add_interesting_lines_for_headers(filename)

        # Begin the scan.
        list(differ.get_opcodes())

        return (differ.get_interesting_lines('header', False),
                differ.get_interesting_lines('header', True))
