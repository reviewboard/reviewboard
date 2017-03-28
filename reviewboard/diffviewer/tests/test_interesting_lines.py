from __future__ import unicode_literals

from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.testing import TestCase


class InterestingLinesTest(TestCase):
    """Unit tests for interesting lines scanner in differ."""

    def test_csharp(self):
        """Testing interesting lines scanner with a C# file"""
        a = (b'public class HelloWorld {\n'
             b'    public static void Main() {\n'
             b'        System.Console.WriteLine("Hello world!");\n'
             b'    }\n'
             b'}\n')

        b = (b'/*\n'
             b' * The Hello World class.\n'
             b' */\n'
             b'public class HelloWorld\n'
             b'{\n'
             b'    /*\n'
             b'     * The main function in this class.\n'
             b'     */\n'
             b'    public static void Main()\n'
             b'    {\n'
             b'        /*\n'
             b'         * Print "Hello world!" to the screen.\n'
             b'         */\n'
             b'        System.Console.WriteLine("Hello world!");\n'
             b'    }\n'
             b'}\n')

        lines = self._get_lines(a, b, 'helloworld.cs')

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (0, 'public class HelloWorld {\n'))
        self.assertEqual(lines[0][1], (1, '    public static void Main() {\n'))

        self.assertEqual(lines[1][0], (3, 'public class HelloWorld\n'))
        self.assertEqual(lines[1][1], (8, '    public static void Main()\n'))

    def test_java(self):
        """Testing interesting lines scanner with a Java file"""
        a = (b'class HelloWorld {\n'
             b'    public static void main(String[] args) {\n'
             b'        System.out.println("Hello world!");\n'
             b'    }\n'
             b'}\n')

        b = (b'/*\n'
             b' * The Hello World class.\n'
             b' */\n'
             b'class HelloWorld\n'
             b'{\n'
             b'    /*\n'
             b'     * The main function in this class.\n'
             b'     */\n'
             b'    public static void main(String[] args)\n'
             b'    {\n'
             b'        /*\n'
             b'         * Print "Hello world!" to the screen.\n'
             b'         */\n'
             b'        System.out.println("Hello world!");\n'
             b'    }\n'
             b'}\n')

        lines = self._get_lines(a, b, 'helloworld.java')

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (0, 'class HelloWorld {\n'))
        self.assertEqual(lines[0][1],
                         (1, '    public static void main(String[] args) {\n'))

        self.assertEqual(len(lines[1]), 2)
        self.assertEqual(lines[1][0], (3, 'class HelloWorld\n'))
        self.assertEqual(lines[1][1],
                         (8, '    public static void main(String[] args)\n'))

    def test_javascript(self):
        """Testing interesting lines scanner with a JavaScript file"""
        a = (b'function helloWorld() {\n'
             b'    alert("Hello world!");\n'
             b'}\n'
             b'\n'
             b'var data = {\n'
             b'    helloWorld2: function() {\n'
             b'        alert("Hello world!");\n'
             b'    }\n'
             b'}\n'
             b'\n'
             b'var helloWorld3 = function() {\n'
             b'    alert("Hello world!");\n'
             b'}\n')

        b = (b'/*\n'
             b' * Prints "Hello world!"\n'
             b' */\n'
             b'function helloWorld()\n'
             b'{\n'
             b'    alert("Hello world!");\n'
             b'}\n'
             b'\n'
             b'var data = {\n'
             b'    /*\n'
             b'     * Prints "Hello world!"\n'
             b'     */\n'
             b'    helloWorld2: function()\n'
             b'    {\n'
             b'        alert("Hello world!");\n'
             b'    }\n'
             b'}\n'
             b'\n'
             b'var helloWorld3 = function()\n'
             b'{\n'
             b'    alert("Hello world!");\n'
             b'}\n')

        lines = self._get_lines(a, b, 'helloworld.js')

        self.assertEqual(len(lines[0]), 3)
        self.assertEqual(lines[0][0], (0, 'function helloWorld() {\n'))
        self.assertEqual(lines[0][1], (5, '    helloWorld2: function() {\n'))
        self.assertEqual(lines[0][2], (10, 'var helloWorld3 = function() {\n'))

        self.assertEqual(len(lines[1]), 3)
        self.assertEqual(lines[1][0], (3, 'function helloWorld()\n'))
        self.assertEqual(lines[1][1], (12, '    helloWorld2: function()\n'))
        self.assertEqual(lines[1][2], (18, 'var helloWorld3 = function()\n'))

    def test_objective_c(self):
        """Testing interesting lines scanner with an Objective C file"""
        a = (b'@interface MyClass : Object\n'
             b'- (void) sayHello;\n'
             b'@end\n'
             b'\n'
             b'@implementation MyClass\n'
             b'- (void) sayHello {\n'
             b'    printf("Hello world!");\n'
             b'}\n'
             b'@end\n')

        b = (b'@interface MyClass : Object\n'
             b'- (void) sayHello;\n'
             b'@end\n'
             b'\n'
             b'@implementation MyClass\n'
             b'/*\n'
             b' * Prints Hello world!\n'
             b' */\n'
             b'- (void) sayHello\n'
             b'{\n'
             b'    printf("Hello world!");\n'
             b'}\n'
             b'@end\n')

        lines = self._get_lines(a, b, 'helloworld.m')

        self.assertEqual(len(lines[0]), 3)
        self.assertEqual(lines[0][0], (0, '@interface MyClass : Object\n'))
        self.assertEqual(lines[0][1], (4, '@implementation MyClass\n'))
        self.assertEqual(lines[0][2], (5, '- (void) sayHello {\n'))

        self.assertEqual(len(lines[1]), 3)
        self.assertEqual(lines[1][0], (0, '@interface MyClass : Object\n'))
        self.assertEqual(lines[1][1], (4, '@implementation MyClass\n'))
        self.assertEqual(lines[1][2], (8, '- (void) sayHello\n'))

    def test_perl(self):
        """Testing interesting lines scanner with a Perl file"""
        a = (b'sub helloWorld {\n'
             b'    print "Hello world!"\n'
             b'}\n')

        b = (b'# Prints Hello World\n'
             b'sub helloWorld\n'
             b'{\n'
             b'    print "Hello world!"\n'
             b'}\n')

        lines = self._get_lines(a, b, 'helloworld.pl')

        self.assertEqual(len(lines[0]), 1)
        self.assertEqual(lines[0][0], (0, 'sub helloWorld {\n'))

        self.assertEqual(len(lines[1]), 1)
        self.assertEqual(lines[1][0], (1, 'sub helloWorld\n'))

    def test_php(self):
        """Testing interesting lines scanner with a PHP file"""
        a = (b'<?php\n'
             b'class HelloWorld {\n'
             b'    function helloWorld() {\n'
             b'        print "Hello world!";\n'
             b'    }\n'
             b'}\n'
             b'?>\n')

        b = (b'<?php\n'
             b'/*\n'
             b' * Hello World class\n'
             b' */\n'
             b'class HelloWorld\n'
             b'{\n'
             b'    /*\n'
             b'     * Prints Hello World\n'
             b'     */\n'
             b'    function helloWorld()\n'
             b'    {\n'
             b'        print "Hello world!";\n'
             b'    }\n'
             b'\n'
             b'    public function foo() {\n'
             b'        print "Hello world!";\n'
             b'    }\n'
             b'}\n'
             b'?>\n')

        lines = self._get_lines(a, b, 'helloworld.php')

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (1, 'class HelloWorld {\n'))
        self.assertEqual(lines[0][1], (2, '    function helloWorld() {\n'))

        self.assertEqual(len(lines[1]), 3)
        self.assertEqual(lines[1][0], (4, 'class HelloWorld\n'))
        self.assertEqual(lines[1][1], (9, '    function helloWorld()\n'))
        self.assertEqual(lines[1][2], (14, '    public function foo() {\n'))

    def test_python(self):
        """Testing interesting lines scanner with a Python file"""
        a = (b'class HelloWorld:\n'
             b'    def main(self):\n'
             b'        print "Hello World"\n')

        b = (b'class HelloWorld:\n'
             b'    """The Hello World class"""\n'
             b'\n'
             b'    def main(self):\n'
             b'        """The main function in this class."""\n'
             b'\n'
             b'        # Prints "Hello world!" to the screen.\n'
             b'        print "Hello world!"\n')

        lines = self._get_lines(a, b, 'helloworld.py')

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (0, 'class HelloWorld:\n'))
        self.assertEqual(lines[0][1], (1, '    def main(self):\n'))

        self.assertEqual(len(lines[1]), 2)
        self.assertEqual(lines[1][0], (0, 'class HelloWorld:\n'))
        self.assertEqual(lines[1][1], (3, '    def main(self):\n'))

    def test_ruby(self):
        """Testing interesting lines scanner with a Ruby file"""
        a = (b'class HelloWorld\n'
             b'    def helloWorld\n'
             b'        puts "Hello world!"\n'
             b'    end\n'
             b'end\n')

        b = (b'# Hello World class\n'
             b'class HelloWorld\n'
             b'    # Prints Hello World\n'
             b'    def helloWorld()\n'
             b'        puts "Hello world!"\n'
             b'    end\n'
             b'end\n')

        lines = self._get_lines(a, b, 'helloworld.rb')

        self.assertEqual(len(lines[0]), 2)
        self.assertEqual(lines[0][0], (0, 'class HelloWorld\n'))
        self.assertEqual(lines[0][1], (1, '    def helloWorld\n'))

        self.assertEqual(len(lines[1]), 2)
        self.assertEqual(lines[1][0], (1, 'class HelloWorld\n'))
        self.assertEqual(lines[1][1], (3, '    def helloWorld()\n'))

    def _get_lines(self, a, b, filename):
        differ = MyersDiffer(a.splitlines(True), b.splitlines(True))
        differ.add_interesting_lines_for_headers(filename)

        # Begin the scan.
        list(differ.get_opcodes())

        return (differ.get_interesting_lines('header', False),
                differ.get_interesting_lines('header', True))
