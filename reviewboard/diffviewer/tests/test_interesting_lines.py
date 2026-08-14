from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.interesting_lines import (
    InterestingLine,
    _get_interesting_lines_via_regex,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@pytest.fixture(autouse=True, scope='session')
def django_db_setup() -> None:
    """Perform django database setup.

    These tests don't use the django database at all, and because of
    parameterize(), that ends up being a pretty big performance hit. This
    overrides db setup to be a no-op.
    """
    pass


@pytest.fixture
def _django_db_helper() -> None:  # pyright:ignore[reportUnusedFunction]
    """Perform internal django database work.

    These tests don't use the django database at all, and because of
    parameterize(), that ends up being a pretty big performance hit. This
    overrides db setup to be a no-op.
    """
    pass


REGEX_TEST_CASES = [
    pytest.param(
        'a.cs',
        """
            public class HelloWorld {
                public static void Main() {
                    System.Console.WriteLine("Hello world!");
                }
            }
        """,
        [
            (0, 'public class HelloWorld {'),
            (1, '    public static void Main() {'),
        ],
        id='csharp',
    ),
    pytest.param(
        'b.cs',
        """
            /*
             * The Hello World class.
             */
            public class HelloWorld
            {
                /*
                 * The main function in this class.
                 */
                public static void Main()
                {
                    /*
                     * Print "Hello world!" to the screen.
                     */
                    System.Console.WriteLine("Hello world!");
                }
            }
        """,
        [
            (3, 'public class HelloWorld'),
            (8, '    public static void Main()'),
        ],
        id='csharp',
    ),
    pytest.param(
        'a.java',
        """
            class HelloWorld {
                public static void main(String[] args) {
                    System.out.println("Hello world!");
                }
            }
        """,
        [
            (0, 'class HelloWorld {'),
            (1, '    public static void main(String[] args) {'),
        ],
        id='java',
    ),
    pytest.param(
        'b.java',
        """
            /*
             * The Hello World class.
             */
            class HelloWorld
            {
                /*
                 * The main function in this class.
                 */
                public static void main(String[] args)
                {
                    /*
                     * Print "Hello world!" to the screen.
                     */
                    System.out.println("Hello world!");
                }
            }
        """,
        [
            (3, 'class HelloWorld'),
            (8, '    public static void main(String[] args)'),
        ],
        id='java',
    ),
    pytest.param(
        'a.js',
        """
            function helloWorld() {
                alert("Hello world!");
            }

            var data = {
                helloWorld2: function() {
                    alert("Hello world!");
                }
            }

            var helloWorld3 = function() {
                alert("Hello world!");
            }
        """,
        [
            (0, 'function helloWorld() {'),
            (5, '    helloWorld2: function() {'),
            (10, 'var helloWorld3 = function() {'),
        ],
        id='javascript',
    ),
    pytest.param(
        'b.js',
        """
            /*
             * Prints "Hello world!"
             */
            function helloWorld()
            {
                alert("Hello world!");
            }

            var data = {
                /*
                 * Prints "Hello world!"
                 */
                helloWorld2: function()
                {
                    alert("Hello world!");
                }
            }

            var helloWorld3 = function()
            {
                alert("Hello world!");
            }
        """,
        [
            (3, 'function helloWorld()'),
            (12, '    helloWorld2: function()'),
            (18, 'var helloWorld3 = function()'),
        ],
        id='javascript',
    ),
    pytest.param(
        'a.m',
        """
            @interface MyClass : Object
            - (void) sayHello;
            @end

            @implementation MyClass
            - (void) sayHello {
                printf("Hello world!");
            }
            @end
        """,
        [
            (0, '@interface MyClass : Object'),
            (4, '@implementation MyClass'),
            (5, '- (void) sayHello {'),
        ],
        id='objc',
    ),
    pytest.param(
        'b.m',
        """
            @interface MyClass : Object
            - (void) sayHello;
            @end

            @implementation MyClass
            /*
             * Prints Hello world!
             */
            - (void) sayHello
            {
                printf("Hello world!");
            }
            @end
        """,
        [
            (0, '@interface MyClass : Object'),
            (4, '@implementation MyClass'),
            (8, '- (void) sayHello'),
        ],
        id='objc',
    ),
    pytest.param(
        'a.pl',
        """
            sub helloWorld {
                print "Hello world!"
            }
        """,
        [
            (0, 'sub helloWorld {'),
        ],
        id='perl',
    ),
    pytest.param(
        'b.pl',
        """
            # Prints Hello World
            sub helloWorld
            {
                print "Hello world!"
            }
        """,
        [
            (1, 'sub helloWorld'),
        ],
        id='perl',
    ),
    pytest.param(
        'a.php',
        """
            <?php
            class HelloWorld {
                function helloWorld() {
                    print "Hello world!";
                }
            }
            ?>
        """,
        [
            (1, 'class HelloWorld {'),
            (2, '    function helloWorld() {'),
        ],
        id='php',
    ),
    pytest.param(
        'b.php',
        """
            <?php
            /*
             * Hello World class
             */
            class HelloWorld
            {
                /*
                 * Prints Hello World
                 */
                function helloWorld()
                {
                    print "Hello world!";
                }

                public function foo() {
                    print "Hello world!";
                }
            }
            ?>
        """,
        [
            (4, 'class HelloWorld'),
            (9, '    function helloWorld()'),
            (14, '    public function foo() {'),
        ],
        id='php',
    ),
    pytest.param(
        'a.py',
        """
            class HelloWorld:
                def main(self):
                    print "Hello World"
        """,
        [
            (0, 'class HelloWorld:'),
            (1, '    def main(self):'),
        ],
        id='python',
    ),
    pytest.param(
        'b.py',
        '''
            class HelloWorld:
                """The Hello World class"""

                def main(self):
                    """The main function in this class."""

                    # Prints "Hello world!" to the screen.
                    print "Hello world!"
        ''',
        [
            (0, 'class HelloWorld:'),
            (3, '    def main(self):'),
        ],
        id='python',
    ),
    pytest.param(
        'a.rb',
        """
            class HelloWorld
                def helloWorld
                    puts "Hello world!"
                end
            end
        """,
        [
            (0, 'class HelloWorld'),
            (1, '    def helloWorld'),
        ],
        id='ruby',
    ),
    pytest.param(
        'b.rb',
        """
            # Hello World class
            class HelloWorld
                # Prints Hello World
                def helloWorld()
                    puts "Hello world!"
                end
            end
        """,
        [
            (1, 'class HelloWorld'),
            (3, '    def helloWorld()'),
        ],
        id='ruby',
    ),
]


@pytest.mark.parametrize(('filename', 'file_content', 'expected_lines'),
                         REGEX_TEST_CASES)
def test_get_lines_by_regex(
    filename: str,
    file_content: str,
    expected_lines: Sequence[InterestingLine],
) -> None:
    """Test get_interesting_lines_via_regex.

    Args:
        filename (str):
            The filename of the file.

        file_content (list of str):
            The content of the file, split into lines.

        expected_lines (list of tuple):
            The expected result.
    """
    file_lines = dedent(file_content.strip('\n')).splitlines()
    result = _get_interesting_lines_via_regex(filename, file_lines)

    assert result == expected_lines


@pytest.mark.parametrize(('filename', 'file_content', 'expected_lines'),
                         REGEX_TEST_CASES)
def test_legacy_differ_api(
    filename: str,
    file_content: str,
    expected_lines: Sequence[InterestingLine],
) -> None:
    """Test the legacy Differ.get_interesting_lines API.

    Args:
        filename (str):
            The filename of the file.

        file_content (list of str):
            The content of the file, split into lines.

        expected_lines (list of tuple):
            The expected result.
    """
    file_lines = dedent(file_content.strip('\n')).splitlines()

    # Since we've now moved each test case into its own parametrized case, just
    # do a diff from an empty file to the file content.
    differ = MyersDiffer([], file_lines)
    differ.add_interesting_lines_for_headers(filename)

    # Begin the scan.
    list(differ.get_opcodes())

    result = differ.get_interesting_lines('header', True)

    assert result == expected_lines
