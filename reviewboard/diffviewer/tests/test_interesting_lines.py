from __future__ import annotations

import logging
import re
from textwrap import dedent
from typing import TYPE_CHECKING

import kgb
import pytest

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
from reviewboard.diffviewer import interesting_lines
from reviewboard.diffviewer.myersdiff import MyersDiffer
from reviewboard.diffviewer.interesting_lines import (
    InterestingLine,
    _get_interesting_lines_via_regex,
    _get_interesting_lines_via_ts,
    get_interesting_lines,
)
from reviewboard.treesitter.core import get_parser

if TYPE_CHECKING:
    from collections.abc import Sequence

    from reviewboard.treesitter.language import SupportedLanguage


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


TS_TEST_CASES = [
    pytest.param(
        'python',
        """
            class HelloWorld:
                def main(self):
                    pass
        """,
        [
            (0, 'class HelloWorld:'),
            (1, '    def main(self):'),
        ],
        id='python',
    ),
    pytest.param(
        'python',
        """
            @decorator
            class HelloWorld:
                @property
                def value(self):
                    return 42
        """,
        [
            (1, 'class HelloWorld:'),
            (3, '    def value(self):'),
        ],
        id='python-decorated',
    ),
    pytest.param(
        'python',
        """
            async def fetch():
                pass
        """,
        [
            (0, 'async def fetch():'),
        ],
        id='python-async',
    ),
    pytest.param(
        'python',
        """
            def outer():
                def inner():
                    pass

                return inner
        """,
        [
            (0, 'def outer():'),
            (1, '    def inner():'),
        ],
        id='python-nested',
    ),
    pytest.param(
        'javascript',
        """
            function helloWorld() {
                alert('Hello world!');
            }

            class Greeter {
                greet() {
                    return () => 42;
                }
            }

            const data = {
                helloWorld2: function() {},
            };

            const helloWorld3 = (x) => x * 2;
        """,
        [
            (0, 'function helloWorld() {'),
            (4, 'class Greeter {'),
            (5, '    greet() {'),
            (6, '        return () => 42;'),
            (11, '    helloWorld2: function() {},'),
            (14, 'const helloWorld3 = (x) => x * 2;'),
        ],
        id='javascript',
    ),
    pytest.param(
        'typescript',
        """
            interface Greeter {
                name: string;
            }

            type Alias = string;

            enum Color {
                Red,
            }

            function greet(name: string): string {
                return name;
            }

            class Foo {
                greet(): void {}
            }
        """,
        [
            (0, 'interface Greeter {'),
            (4, 'type Alias = string;'),
            (6, 'enum Color {'),
            (10, 'function greet(name: string): string {'),
            (14, 'class Foo {'),
            (15, '    greet(): void {}'),
        ],
        id='typescript',
    ),
    pytest.param(
        'c',
        """
            struct point {
                int x;
            };

            enum color {
                RED,
            };

            int add(int a, int b);

            int add(int a, int b)
            {
                return a + b;
            }
        """,
        [
            (0, 'struct point {'),
            (4, 'enum color {'),
            (8, 'int add(int a, int b);'),
            (10, 'int add(int a, int b)'),
        ],
        id='c',
    ),
    pytest.param(
        'cpp',
        """
            class Greeter {
            public:
                void greet();
            };

            void Greeter::greet()
            {
            }

            template <typename T>
            T add(T a, T b)
            {
                return a + b;
            }
        """,
        [
            # Note that the in-class declaration of greet() is not
            # captured. It is a field_declaration in the C++ grammar, and
            # the upstream queries only capture out-of-class declarations.
            (0, 'class Greeter {'),
            (5, 'void Greeter::greet()'),
            (9, 'template <typename T>'),
            (10, 'T add(T a, T b)'),
        ],
        id='cpp',
    ),
    pytest.param(
        'java',
        """
            class HelloWorld {
                HelloWorld() {
                }

                public static void main(String[] args) {
                    System.out.println("Hello world!");
                }
            }
        """,
        [
            (0, 'class HelloWorld {'),
            (1, '    HelloWorld() {'),
            (4, '    public static void main(String[] args) {'),
        ],
        id='java',
    ),
    pytest.param(
        'csharp',
        """
            public class HelloWorld
            {
                public HelloWorld()
                {
                }

                public static void Main()
                {
                    System.Console.WriteLine("Hello world!");
                }
            }
        """,
        [
            (0, 'public class HelloWorld'),
            (2, '    public HelloWorld()'),
            (6, '    public static void Main()'),
        ],
        id='csharp',
    ),
    pytest.param(
        'ruby',
        """
            module Greetings
                class HelloWorld
                    def hello_world
                        puts "Hello world!"
                    end

                    def self.create
                        new
                    end
                end
            end
        """,
        [
            (0, 'module Greetings'),
            (1, '    class HelloWorld'),
            (2, '        def hello_world'),
            (6, '        def self.create'),
        ],
        id='ruby',
    ),
    pytest.param(
        'go',
        """
            type Point struct {
                X int
            }

            type Shape interface {
                Area() int
            }

            func Add(a, b int) int {
                return a + b
            }

            func (p Point) Area() int {
                return 0
            }
        """,
        [
            (0, 'type Point struct {'),
            (4, 'type Shape interface {'),
            (8, 'func Add(a, b int) int {'),
            (12, 'func (p Point) Area() int {'),
        ],
        id='go',
    ),
    pytest.param(
        'rust',
        """
            struct Point {
                x: i32,
            }

            enum Color {
                Red,
            }

            trait Shape {
                fn area(&self) -> i32;
            }

            impl Shape for Point {
                fn area(&self) -> i32 {
                    self.x
                }
            }
        """,
        [
            (0, 'struct Point {'),
            (4, 'enum Color {'),
            (8, 'trait Shape {'),
            (9, '    fn area(&self) -> i32;'),
            (12, 'impl Shape for Point {'),
            (13, '    fn area(&self) -> i32 {'),
        ],
        id='rust',
    ),
    pytest.param(
        'fish',
        """
            function hello_world
                echo hello
            end

            function greet -a name
                echo $name
            end
        """,
        [
            # The fish queries use the offset! directive, exercising the
            # directive handlers.
            (0, 'function hello_world'),
            (4, 'function greet -a name'),
        ],
        id='fish',
    ),
    pytest.param(
        'zig',
        """
            const Point = struct {
                x: i32,
            };

            fn add(a: i32, b: i32) i32 {
                return a + b;
            }
        """,
        [
            # The zig queries use the make-range! directive, exercising the
            # directive handlers.
            (0, 'const Point = struct {'),
            (4, 'fn add(a: i32, b: i32) i32 {'),
        ],
        id='zig',
    ),
    pytest.param(
        'php',
        """
            <?php
            class HelloWorld {
                public function helloWorld() {
                    print "Hello world!";
                }
            }

            interface Greeter {
            }

            function standalone() {
            }
        """,
        [
            (1, 'class HelloWorld {'),
            (2, '    public function helloWorld() {'),
            (7, 'interface Greeter {'),
            (10, 'function standalone() {'),
        ],
        id='php',
    ),
]


@pytest.mark.parametrize(('language_name', 'file_content', 'expected_lines'),
                         TS_TEST_CASES)
def test_get_lines_by_ts(
    language_name: SupportedLanguage,
    file_content: str,
    expected_lines: Sequence[InterestingLine],
) -> None:
    """Test _get_interesting_lines_via_ts.

    Args:
        language_name (str):
            The tree-sitter language name.

        file_content (str):
            The content of the file.

        expected_lines (list of tuple):
            The expected result.
    """
    source = dedent(file_content.strip('\n'))
    file_lines = source.splitlines()

    parser = get_parser(language_name)
    tree = parser.parse(source.encode())

    result = _get_interesting_lines_via_ts(language_name, file_lines, tree)

    assert result == expected_lines


def test_get_lines_by_ts_no_queries() -> None:
    """Test _get_interesting_lines_via_ts with no queries for a language."""
    source = 'SELECT 1;\n'
    tree = get_parser('sql').parse(source.encode())

    assert _get_interesting_lines_via_ts('sql', source.splitlines(),
                                         tree) is None


def test_get_interesting_lines_ts_path() -> None:
    """Test get_interesting_lines using the tree-sitter path."""
    source = 'def main():\n    pass\n'
    file_lines = source.splitlines()
    tree = get_parser('python').parse(source.encode())

    with kgb.spy_on(interesting_lines._get_interesting_lines_via_regex) \
            as spy:
        result = get_interesting_lines(filename='test.py',
                                       language_name='python',
                                       file_content=file_lines,
                                       tree=tree)

        assert result == [(0, 'def main():')]
        assert not spy.called


def test_get_interesting_lines_ts_empty_is_authoritative() -> None:
    """Test get_interesting_lines with an empty tree-sitter result.

    A file with no definitions must return an empty result, without
    falling back to the regexes (which for C would match nearly every
    top-level line).
    """
    source = 'int x = 42;\n'
    file_lines = source.splitlines()
    tree = get_parser('c').parse(source.encode())

    with kgb.spy_on(interesting_lines._get_interesting_lines_via_regex) \
            as spy:
        result = get_interesting_lines(filename='test.c',
                                       language_name='c',
                                       file_content=file_lines,
                                       tree=tree)

        assert result == []
        assert not spy.called


def test_get_interesting_lines_parse_error_falls_back() -> None:
    """Test get_interesting_lines with an unparseable file.

    When the tree-sitter parse has errors and no definitions were found,
    the regex scanner gets a shot at the file.
    """
    source = 'class HelloWorld(TestCase, EmailTestHelper);\n    pass\n'
    file_lines = source.splitlines()
    tree = get_parser('python').parse(source.encode())

    with kgb.spy_on(interesting_lines._get_interesting_lines_via_regex) \
            as spy:
        result = get_interesting_lines(filename='test.py',
                                       language_name='python',
                                       file_content=file_lines,
                                       tree=tree)

        assert result == [
            (0, 'class HelloWorld(TestCase, EmailTestHelper);'),
        ]
        assert spy.called


def test_get_interesting_lines_no_language() -> None:
    """Test get_interesting_lines with no detected language."""
    file_lines = ['def main():', '    pass']

    with kgb.spy_on(interesting_lines._get_interesting_lines_via_regex) \
            as spy:
        result = get_interesting_lines(filename='test.py',
                                       language_name=None,
                                       file_content=file_lines,
                                       tree=None)

        assert result == [(0, 'def main():')]
        assert spy.called


def test_get_interesting_lines_no_queries_for_language() -> None:
    """Test get_interesting_lines with a language without queries."""
    source = 'sub helloWorld {\n    print "Hello world!"\n}\n'
    file_lines = source.splitlines()
    tree = get_parser('perl').parse(source.encode())

    with kgb.spy_on(interesting_lines._get_interesting_lines_via_regex) \
            as spy:
        result = get_interesting_lines(filename='test.pl',
                                       language_name='perl',
                                       file_content=file_lines,
                                       tree=tree)

        assert result == [(0, 'sub helloWorld {')]
        assert spy.called


def test_get_interesting_lines_compile_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test get_interesting_lines with queries that fail to compile."""
    source = 'def main():\n    pass\n'
    file_lines = source.splitlines()
    tree = get_parser('python').parse(source.encode())

    # get_queries() is wrapped in lru_cache, so the spy goes on the
    # underlying function, and both caches need clearing so the call
    # reaches it.
    interesting_lines._get_interesting_lines_query.cache_clear()
    interesting_lines.get_queries.cache_clear()

    try:
        with (kgb.spy_on(interesting_lines.get_queries.__wrapped__,
                         op=kgb.ops.SpyOpReturn('(((broken')),
              caplog.at_level(logging.WARNING)):
            result = get_interesting_lines(filename='test.py',
                                           language_name='python',
                                           file_content=file_lines,
                                           tree=tree)

        assert result == [(0, 'def main():')]
        assert 'Failed to compile interesting lines queries' in caplog.text
    finally:
        interesting_lines._get_interesting_lines_query.cache_clear()
        interesting_lines.get_queries.cache_clear()


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


def test_legacy_differ_add_interesting_line_regex() -> None:
    """Test third-party regexes via Differ.add_interesting_line_regex."""
    file_lines = [
        '# TODO: fix this',
        'x = 1',
    ]

    differ = MyersDiffer([], file_lines)

    with pytest.warns(RemovedInReviewBoard11_0Warning):
        differ.add_interesting_line_regex(
            'todos', re.compile(r'\s*#\s*TODO'))

    # Begin the scan.
    list(differ.get_opcodes())

    assert differ.get_interesting_lines('todos', True) == [
        (0, '# TODO: fix this'),
    ]
