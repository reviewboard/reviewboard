"""Unit tests for reviewboard.diffviewer.parser.DiffXParser."""

from djblets.testing.decorators import add_fixtures

from reviewboard.diffviewer.errors import DiffParserError
from reviewboard.diffviewer.parser import DiffXParser
from reviewboard.diffviewer.testing.mixins import DiffParserTestingMixin
from reviewboard.scmtools.core import HEAD, PRE_CREATION, UNKNOWN
from reviewboard.testing import TestCase


class DiffXParserTests(DiffParserTestingMixin, TestCase):
    """Unit tests for reviewboard.diffviewer.parser.DiffXParser."""

    def test_parse_diff_with_basic_diff(self):
        """Testing DiffXParser.parse_diff with a basic DiffX file"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=156\n'
            b'{\n'
            b'    "path": {\n'
            b'        "new": "message2.py",\n'
            b'        "old": "message.py"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "new": "def456",\n'
            b'        "old": "abc123"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=693, line_endings=unix\n'
            b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
            b'+++ message2.py\t2021-07-02 13:21:31.428383873 -0700\n'
            b'@@ -164,10 +164,10 @@\n'
            b'             not isinstance(headers, MultiValueDict)):\n'
            b'             # Instantiating a MultiValueDict from a dict does '
            b'not ensure that\n'
            b'             # values are lists, so we have to ensure that '
            b'ourselves.\n'
            b'-            headers = MultiValueDict(dict(\n'
            b'-                (key, [value])\n'
            b'-                for key, value in six.iteritems(headers)\n'
            b'-            ))\n'
            b'+            headers = MultiValueDict({\n'
            b'+                key: [value]\n'
            b'+                for key, value in headers.items()\n'
            b'+            })\n'
            b' \n'
            b'         if in_reply_to:\n'
            b'             headers["In-Reply-To"] = in_reply_to\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'message.py',
            orig_file_details=b'abc123',
            modified_filename=b'message2.py',
            modified_file_details=b'def456',
            insert_count=4,
            delete_count=4,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'path': {
                            'old': 'message.py',
                            'new': 'message2.py',
                        },
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
                b'+++ message2.py\t2021-07-02 13:21:31.428383873 -0700\n'
                b'@@ -164,10 +164,10 @@\n'
                b'             not isinstance(headers, MultiValueDict)):\n'
                b'             # Instantiating a MultiValueDict from a dict '
                b'does not ensure that\n'
                b'             # values are lists, so we have to ensure that '
                b'ourselves.\n'
                b'-            headers = MultiValueDict(dict(\n'
                b'-                (key, [value])\n'
                b'-                for key, value in six.iteritems(headers)\n'
                b'-            ))\n'
                b'+            headers = MultiValueDict({\n'
                b'+                key: [value]\n'
                b'+                for key, value in headers.items()\n'
                b'+            })\n'
                b' \n'
                b'         if in_reply_to:\n'
                b'             headers["In-Reply-To"] = in_reply_to\n'
            ))

    def test_parse_diff_with_complex_diff(self):
        """Testing DiffXParser.parse_diff with a complex DiffX file"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-16, version=1.0\n'
            b'#.preamble: encoding=ascii, indent=2, length=36,'
            b' line_endings=dos, mimetype=text/plain\n'
            b'  This is the file-level preamble.\r\n'
            b'#.meta: encoding=utf-32, format=json, length=96\n'
            b'\xff\xfe\x00\x00{\x00\x00\x00\n\x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00"'
            b'\x00\x00\x00k\x00\x00\x00e\x00\x00\x00y\x00\x00\x00"'
            b'\x00\x00\x00:\x00\x00\x00 \x00\x00\x00"\x00\x00\x00v'
            b'\x00\x00\x00a\x00\x00\x00l\x00\x00\x00u\x00\x00\x00e'
            b'\x00\x00\x00"\x00\x00\x00\n\x00\x00\x00}\x00\x00\x00'
            b'\n\x00\x00\x00'
            b'#.change:\n'
            b'#..preamble: indent=2, length=14, line_endings=unix, '
            b'mimetype=text/markdown\n'
            b'  \xff\xfet\x00e\x00s\x00t\x00\n\x00'
            b'#..meta: encoding=utf-8, format=json, length=302\n'
            b'{\n'
            b'    "author": "Test User <test@example.com>",\n'
            b'    "author date": "2021-06-01T13:12:06-07:00",\n'
            b'    "committer": "Test User <test@example.com>",\n'
            b'    "date": "2021-06-02T19:26:31-07:00",\n'
            b'    "id": "a25e7b28af5e3184946068f432122c68c1a30b23",\n'
            b'    "parent id": "b892d5f833474c59d7851ff46a4b0bd919017e97"\n'
            b'}\n'
            b'#..file:\n'
            b'#...meta: encoding=latin1, format=json, length=166\n'
            b'{\n'
            b'    "path": "file1",\n'
            b'    "revision": {\n'
            b'        "new": "eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef",\n'
            b'        "old": "c8839177d1a5605aa60abe69db95c84183f0eebe"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=60, line_endings=unix\n'
            b'--- /file1\n'
            b'+++ /file1\n'
            b'@@ -498,7 +498,7 @@\n'
            b' ... diff content\n'
            b'#.change:\n'
            b'#..preamble: encoding=utf-8, indent=4, length=56, '
            b'line_endings=unix\n'
            b'    Summary of commit #2\n'
            b'    \n'
            b'    Here\'s a description.\n'
            b'#..meta: encoding=utf-8, format=json, length=302\n'
            b'{\n'
            b'    "author": "Test User <test@example.com>",\n'
            b'    "author date": "2021-06-01T19:46:22-07:00",\n'
            b'    "committer": "Test User <test@example.com>",\n'
            b'    "date": "2021-06-02T19:46:25-07:00",\n'
            b'    "id": "91127b687f583184144161f432222748c1a30b23",\n'
            b'    "parent id": "a25e7b28af5e3184946068f432122c68c1a30b23"\n'
            b'}\n'
            b'#..file:\n'
            b'#...meta: encoding=utf-32, format=json, length=668\n'
            b'\xff\xfe\x00\x00{\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00"\x00\x00\x00'
            b'p\x00\x00\x00a\x00\x00\x00t\x00\x00\x00h\x00\x00\x00'
            b'"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00"\x00\x00\x00'
            b'f\x00\x00\x00i\x00\x00\x00l\x00\x00\x00e\x00\x00\x00'
            b'2\x00\x00\x00"\x00\x00\x00,\x00\x00\x00\n\x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b'"\x00\x00\x00r\x00\x00\x00e\x00\x00\x00v\x00\x00\x00'
            b'i\x00\x00\x00s\x00\x00\x00i\x00\x00\x00o\x00\x00\x00'
            b'n\x00\x00\x00"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00'
            b'{\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00"\x00\x00\x00n\x00\x00\x00'
            b'e\x00\x00\x00w\x00\x00\x00"\x00\x00\x00:\x00\x00\x00'
            b' \x00\x00\x00"\x00\x00\x003\x00\x00\x008\x00\x00\x00'
            b'9\x00\x00\x00c\x00\x00\x00c\x00\x00\x006\x00\x00\x00'
            b'b\x00\x00\x007\x00\x00\x00a\x00\x00\x00e\x00\x00\x00'
            b'5\x00\x00\x00a\x00\x00\x006\x00\x00\x005\x00\x00\x00'
            b'9\x00\x00\x003\x00\x00\x008\x00\x00\x003\x00\x00\x00'
            b'e\x00\x00\x00a\x00\x00\x00b\x00\x00\x005\x00\x00\x00'
            b'd\x00\x00\x00f\x00\x00\x00c\x00\x00\x002\x00\x00\x00'
            b'5\x00\x00\x003\x00\x00\x007\x00\x00\x006\x00\x00\x00'
            b'4\x00\x00\x00e\x00\x00\x00c\x00\x00\x00c\x00\x00\x00'
            b'f\x00\x00\x008\x00\x00\x004\x00\x00\x007\x00\x00\x00'
            b'3\x00\x00\x002\x00\x00\x00"\x00\x00\x00,\x00\x00\x00'
            b'\n\x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00"\x00\x00\x00o\x00\x00\x00l\x00\x00\x00'
            b'd\x00\x00\x00"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00'
            b'"\x00\x00\x002\x00\x00\x008\x00\x00\x001\x00\x00\x00'
            b'b\x00\x00\x00a\x00\x00\x00c\x00\x00\x002\x00\x00\x00'
            b'b\x00\x00\x007\x00\x00\x000\x00\x00\x004\x00\x00\x00'
            b'6\x00\x00\x001\x00\x00\x007\x00\x00\x00e\x00\x00\x00'
            b'8\x00\x00\x000\x00\x00\x007\x00\x00\x008\x00\x00\x00'
            b'5\x00\x00\x000\x00\x00\x00e\x00\x00\x000\x00\x00\x00'
            b'7\x00\x00\x00e\x00\x00\x005\x00\x00\x004\x00\x00\x00'
            b'b\x00\x00\x00a\x00\x00\x00e\x00\x00\x003\x00\x00\x00'
            b'4\x00\x00\x006\x00\x00\x009\x00\x00\x00f\x00\x00\x00'
            b'6\x00\x00\x00a\x00\x00\x002\x00\x00\x00e\x00\x00\x00'
            b'7\x00\x00\x00"\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00}\x00\x00\x00'
            b'\n\x00\x00\x00}\x00\x00\x00\n\x00\x00\x00'
            b'#...diff: encoding=utf-16, length=22, line_endings=unix\n'
            b'\xff\xfe \x00.\x00.\x00.\x00 \x00d\x00i\x00f\x00f\x00\n\x00'
            b'#..file:\n'
            b'#...meta: encoding=utf-8, format=json, length=166\n'
            b'{\n'
            b'    "path": "file3",\n'
            b'    "revision": {\n'
            b'        "new": "0d4a0fb8d62b762a26e13591d06d93d79d61102f",\n'
            b'        "old": "be089b7197974703c83682088a068bef3422c6c2"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=87, line_endings=dos\n'
            b'--- a/file3\r\n'
            b'+++ b/file3\r\n'
            b'@@ -258,1 +258,2 @@\r\n'
            b'- old line\r\n'
            b'+ new line 1\r\n'
            b'+ new line 2\r\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=2,
            extra_data={
                'diffx': {
                    'metadata': {
                        'key': 'value',
                    },
                    'metadata_options': {
                        'encoding': 'utf-32',
                        'format': 'json',
                    },
                    'options': {
                        'encoding': 'utf-16',
                        'version': '1.0',
                    },
                    'preamble': 'This is the file-level preamble.\r\n',
                    'preamble_options': {
                        'encoding': 'ascii',
                        'indent': 2,
                        'line_endings': 'dos',
                        'mimetype': 'text/plain',
                    },
                },
            })

        # Inspect change #1.
        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(
            parsed_change,
            commit_id=b'a25e7b28af5e3184946068f432122c68c1a30b23',
            num_files=1,
            extra_data={
                'diffx': {
                    'metadata': {
                        'author': 'Test User <test@example.com>',
                        'author date': '2021-06-01T13:12:06-07:00',
                        'committer': 'Test User <test@example.com>',
                        'date': '2021-06-02T19:26:31-07:00',
                        'id': 'a25e7b28af5e3184946068f432122c68c1a30b23',
                        'parent id': 'b892d5f833474c59d7851ff46a4b0bd919017e97',
                    },
                    'metadata_options': {
                        'encoding': 'utf-8',
                        'format': 'json',
                    },
                    'preamble': 'test\n',
                    'preamble_options': {
                        'indent': 2,
                        'line_endings': 'unix',
                        'mimetype': 'text/markdown',
                    },
                },
            })

        # Inspect change #1, file #1
        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'file1',
            orig_file_details=b'c8839177d1a5605aa60abe69db95c84183f0eebe',
            modified_filename=b'file1',
            modified_file_details=b'eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef',
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'path': 'file1',
                        'revision': {
                            'old': 'c8839177d1a5605aa60abe69db95c84183f0eebe',
                            'new': 'eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef',
                        },
                    },
                    'metadata_options': {
                        'encoding': 'latin1',
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- /file1\n'
                b'+++ /file1\n'
                b'@@ -498,7 +498,7 @@\n'
                b' ... diff content\n'
            ))

        # Inspect change #2.
        parsed_change = parsed_diff.changes[1]
        self.assert_parsed_diff_change(
            parsed_change,
            commit_id=b'91127b687f583184144161f432222748c1a30b23',
            num_files=2,
            extra_data={
                'diffx': {
                    'metadata': {
                        'author': 'Test User <test@example.com>',
                        'author date': '2021-06-01T19:46:22-07:00',
                        'committer': 'Test User <test@example.com>',
                        'date': '2021-06-02T19:46:25-07:00',
                        'id': '91127b687f583184144161f432222748c1a30b23',
                        'parent id': 'a25e7b28af5e3184946068f432122c68c1a30b23',
                    },
                    'metadata_options': {
                        'encoding': 'utf-8',
                        'format': 'json',
                    },
                    'preamble': (
                        "Summary of commit #2\n"
                        "\n"
                        "Here's a description.\n"
                    ),
                    'preamble_options': {
                        'encoding': 'utf-8',
                        'indent': 4,
                        'line_endings': 'unix',
                    },
                },
            })

        # Inspect change #2, file #1
        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'file2',
            orig_file_details=b'281bac2b704617e807850e07e54bae3469f6a2e7',
            modified_filename=b'file2',
            modified_file_details=b'389cc6b7ae5a659383eab5dfc253764eccf84732',
            extra_data={
                'diffx': {
                    'diff_options': {
                        'encoding': 'utf-16',
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'path': 'file2',
                        'revision': {
                            'old': '281bac2b704617e807850e07e54bae3469f6a2e7',
                            'new': '389cc6b7ae5a659383eab5dfc253764eccf84732',
                        },
                    },
                    'metadata_options': {
                        'encoding': 'utf-32',
                        'format': 'json',
                    },
                },
                'encoding': 'utf-16',
            },
            data=(
                b'\xff\xfe \x00.\x00.\x00.\x00 \x00d\x00i\x00f\x00f\x00\n\x00'
            ))

        # Inspect change #2, file #2
        self.assert_parsed_diff_file(
            parsed_change.files[1],
            orig_filename=b'file3',
            orig_file_details=b'be089b7197974703c83682088a068bef3422c6c2',
            modified_filename=b'file3',
            modified_file_details=b'0d4a0fb8d62b762a26e13591d06d93d79d61102f',
            insert_count=2,
            delete_count=1,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'dos',
                    },
                    'metadata': {
                        'path': 'file3',
                        'revision': {
                            'old': 'be089b7197974703c83682088a068bef3422c6c2',
                            'new': '0d4a0fb8d62b762a26e13591d06d93d79d61102f',
                        },
                    },
                    'metadata_options': {
                        'encoding': 'utf-8',
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- a/file3\r\n'
                b'+++ b/file3\r\n'
                b'@@ -258,1 +258,2 @@\r\n'
                b'- old line\r\n'
                b'+ new line 1\r\n'
                b'+ new line 2\r\n'
            ))

    def test_parse_diff_with_path_string(self):
        """Testing DiffXParser.parse_diff with file's meta.path as single
        string
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=103\n'
            b'{\n'
            b'    "path": "message.py",\n'
            b'    "revision": {\n'
            b'        "new": "def456",\n'
            b'        "old": "abc123"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=692, line_endings=unix\n'
            b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
            b'+++ message.py\t2021-07-02 13:21:31.428383873 -0700\n'
            b'@@ -164,10 +164,10 @@\n'
            b'             not isinstance(headers, MultiValueDict)):\n'
            b'             # Instantiating a MultiValueDict from a dict does '
            b'not ensure that\n'
            b'             # values are lists, so we have to ensure that '
            b'ourselves.\n'
            b'-            headers = MultiValueDict(dict(\n'
            b'-                (key, [value])\n'
            b'-                for key, value in six.iteritems(headers)\n'
            b'-            ))\n'
            b'+            headers = MultiValueDict({\n'
            b'+                key: [value]\n'
            b'+                for key, value in headers.items()\n'
            b'+            })\n'
            b' \n'
            b'         if in_reply_to:\n'
            b'             headers["In-Reply-To"] = in_reply_to\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'message.py',
            orig_file_details=b'abc123',
            modified_filename=b'message.py',
            modified_file_details=b'def456',
            insert_count=4,
            delete_count=4,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'path': 'message.py',
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
                b'+++ message.py\t2021-07-02 13:21:31.428383873 -0700\n'
                b'@@ -164,10 +164,10 @@\n'
                b'             not isinstance(headers, MultiValueDict)):\n'
                b'             # Instantiating a MultiValueDict from a dict '
                b'does not ensure that\n'
                b'             # values are lists, so we have to ensure that '
                b'ourselves.\n'
                b'-            headers = MultiValueDict(dict(\n'
                b'-                (key, [value])\n'
                b'-                for key, value in six.iteritems(headers)\n'
                b'-            ))\n'
                b'+            headers = MultiValueDict({\n'
                b'+                key: [value]\n'
                b'+                for key, value in headers.items()\n'
                b'+            })\n'
                b' \n'
                b'         if in_reply_to:\n'
                b'             headers["In-Reply-To"] = in_reply_to\n'
            ))

    def test_parse_diff_with_revision_old_only(self):
        """Testing DiffXParser.parse_diff with file's revision.old and no
        revision.new
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=78\n'
            b'{\n'
            b'    "path": "message.py",\n'
            b'    "revision": {\n'
            b'        "old": "abc123"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=692, line_endings=unix\n'
            b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
            b'+++ message.py\t2021-07-02 13:21:31.428383873 -0700\n'
            b'@@ -164,10 +164,10 @@\n'
            b'             not isinstance(headers, MultiValueDict)):\n'
            b'             # Instantiating a MultiValueDict from a dict does '
            b'not ensure that\n'
            b'             # values are lists, so we have to ensure that '
            b'ourselves.\n'
            b'-            headers = MultiValueDict(dict(\n'
            b'-                (key, [value])\n'
            b'-                for key, value in six.iteritems(headers)\n'
            b'-            ))\n'
            b'+            headers = MultiValueDict({\n'
            b'+                key: [value]\n'
            b'+                for key, value in headers.items()\n'
            b'+            })\n'
            b' \n'
            b'         if in_reply_to:\n'
            b'             headers["In-Reply-To"] = in_reply_to\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'message.py',
            orig_file_details=b'abc123',
            modified_filename=b'message.py',
            modified_file_details=HEAD,
            insert_count=4,
            delete_count=4,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'path': 'message.py',
                        'revision': {
                            'old': 'abc123',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
                b'+++ message.py\t2021-07-02 13:21:31.428383873 -0700\n'
                b'@@ -164,10 +164,10 @@\n'
                b'             not isinstance(headers, MultiValueDict)):\n'
                b'             # Instantiating a MultiValueDict from a dict '
                b'does not ensure that\n'
                b'             # values are lists, so we have to ensure that '
                b'ourselves.\n'
                b'-            headers = MultiValueDict(dict(\n'
                b'-                (key, [value])\n'
                b'-                for key, value in six.iteritems(headers)\n'
                b'-            ))\n'
                b'+            headers = MultiValueDict({\n'
                b'+                key: [value]\n'
                b'+                for key, value in headers.items()\n'
                b'+            })\n'
                b' \n'
                b'         if in_reply_to:\n'
                b'             headers["In-Reply-To"] = in_reply_to\n'
            ))

    def test_parse_diff_with_revision_new_only(self):
        """Testing DiffXParser.parse_diff with file's revision.new and no
        revision.old
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=78\n'
            b'{\n'
            b'    "path": "message.py",\n'
            b'    "revision": {\n'
            b'        "new": "def456"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=692, line_endings=unix\n'
            b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
            b'+++ message.py\t2021-07-02 13:21:31.428383873 -0700\n'
            b'@@ -164,10 +164,10 @@\n'
            b'             not isinstance(headers, MultiValueDict)):\n'
            b'             # Instantiating a MultiValueDict from a dict does '
            b'not ensure that\n'
            b'             # values are lists, so we have to ensure that '
            b'ourselves.\n'
            b'-            headers = MultiValueDict(dict(\n'
            b'-                (key, [value])\n'
            b'-                for key, value in six.iteritems(headers)\n'
            b'-            ))\n'
            b'+            headers = MultiValueDict({\n'
            b'+                key: [value]\n'
            b'+                for key, value in headers.items()\n'
            b'+            })\n'
            b' \n'
            b'         if in_reply_to:\n'
            b'             headers["In-Reply-To"] = in_reply_to\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'message.py',
            orig_file_details=UNKNOWN,
            modified_filename=b'message.py',
            modified_file_details=b'def456',
            insert_count=4,
            delete_count=4,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'path': 'message.py',
                        'revision': {
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
                b'+++ message.py\t2021-07-02 13:21:31.428383873 -0700\n'
                b'@@ -164,10 +164,10 @@\n'
                b'             not isinstance(headers, MultiValueDict)):\n'
                b'             # Instantiating a MultiValueDict from a dict '
                b'does not ensure that\n'
                b'             # values are lists, so we have to ensure that '
                b'ourselves.\n'
                b'-            headers = MultiValueDict(dict(\n'
                b'-                (key, [value])\n'
                b'-                for key, value in six.iteritems(headers)\n'
                b'-            ))\n'
                b'+            headers = MultiValueDict({\n'
                b'+                key: [value]\n'
                b'+                for key, value in headers.items()\n'
                b'+            })\n'
                b' \n'
                b'         if in_reply_to:\n'
                b'             headers["In-Reply-To"] = in_reply_to\n'
            ))

    def test_parse_diff_with_revision_new_only_op_create(self):
        """Testing DiffXParser.parse_diff with file's revision.new and no
        revision.old and op=create
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=98\n'
            b'{\n'
            b'    "op": "create",\n'
            b'    "path": "message.py",\n'
            b'    "revision": {\n'
            b'        "new": "def456"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=692, line_endings=unix\n'
            b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
            b'+++ message.py\t2021-07-02 13:21:31.428383873 -0700\n'
            b'@@ -164,10 +164,10 @@\n'
            b'             not isinstance(headers, MultiValueDict)):\n'
            b'             # Instantiating a MultiValueDict from a dict does '
            b'not ensure that\n'
            b'             # values are lists, so we have to ensure that '
            b'ourselves.\n'
            b'-            headers = MultiValueDict(dict(\n'
            b'-                (key, [value])\n'
            b'-                for key, value in six.iteritems(headers)\n'
            b'-            ))\n'
            b'+            headers = MultiValueDict({\n'
            b'+                key: [value]\n'
            b'+                for key, value in headers.items()\n'
            b'+            })\n'
            b' \n'
            b'         if in_reply_to:\n'
            b'             headers["In-Reply-To"] = in_reply_to\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'message.py',
            orig_file_details=PRE_CREATION,
            modified_filename=b'message.py',
            modified_file_details=b'def456',
            insert_count=4,
            delete_count=4,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'op': 'create',
                        'path': 'message.py',
                        'revision': {
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
                b'+++ message.py\t2021-07-02 13:21:31.428383873 -0700\n'
                b'@@ -164,10 +164,10 @@\n'
                b'             not isinstance(headers, MultiValueDict)):\n'
                b'             # Instantiating a MultiValueDict from a dict '
                b'does not ensure that\n'
                b'             # values are lists, so we have to ensure that '
                b'ourselves.\n'
                b'-            headers = MultiValueDict(dict(\n'
                b'-                (key, [value])\n'
                b'-                for key, value in six.iteritems(headers)\n'
                b'-            ))\n'
                b'+            headers = MultiValueDict({\n'
                b'+                key: [value]\n'
                b'+                for key, value in headers.items()\n'
                b'+            })\n'
                b' \n'
                b'         if in_reply_to:\n'
                b'             headers["In-Reply-To"] = in_reply_to\n'
            ))

    def test_parse_diff_with_binary_file(self):
        """Testing DiffXParser.parse_diff with binary file"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=104\n'
            b'{\n'
            b'    "path": "message.bin",\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=23, type=binary, line_endings=unix\n'
            b'This is a binary file.\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'message.bin',
            orig_file_details=b'abc123',
            modified_filename=b'message.bin',
            modified_file_details=b'def456',
            binary=True,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                        'type': 'binary',
                    },
                    'metadata': {
                        'path': 'message.bin',
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=b'This is a binary file.\n')

    def test_parse_diff_with_file_op_delete(self):
        """Testing DiffXParser.parse_diff with file op=delete"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=123\n'
            b'{\n'
            b'    "op": "delete",\n'
            b'    "path": "message.py",\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=29, line_endings=unix\n'
            b'@@ -1 +0,0 @@\n'
            b'-Goodbye, file\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'message.py',
            orig_file_details=b'abc123',
            modified_filename=b'message.py',
            modified_file_details=b'def456',
            deleted=True,
            delete_count=1,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'op': 'delete',
                        'path': 'message.py',
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'@@ -1 +0,0 @@\n'
                b'-Goodbye, file\n'
            ))

    def test_parse_diff_with_op_move(self):
        """Testing DiffXParser.parse_diff with file op=move"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=169\n'
            b'{\n'
            b'    "op": "move",\n'
            b'    "path": {\n'
            b'        "old": "old-name",\n'
            b'        "new": "new-name"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    }\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'old-name',
            orig_file_details=b'abc123',
            modified_filename=b'new-name',
            modified_file_details=b'def456',
            moved=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'move',
                        'path': {
                            'old': 'old-name',
                            'new': 'new-name',
                        },
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_op_move_modify(self):
        """Testing DiffXParser.parse_diff with file op=move-modify"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=176\n'
            b'{\n'
            b'    "op": "move-modify",\n'
            b'    "path": {\n'
            b'        "old": "old-name",\n'
            b'        "new": "new-name"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=58, line_endings=unix\n'
            b'--- old-name\n'
            b'+++ new-name\n'
            b'@@ -1 +1 @@\n'
            b'-old line\n'
            b'+new line\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'old-name',
            orig_file_details=b'abc123',
            modified_filename=b'new-name',
            modified_file_details=b'def456',
            moved=True,
            insert_count=1,
            delete_count=1,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'op': 'move-modify',
                        'path': {
                            'old': 'old-name',
                            'new': 'new-name',
                        },
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- old-name\n'
                b'+++ new-name\n'
                b'@@ -1 +1 @@\n'
                b'-old line\n'
                b'+new line\n'
            ))

    def test_parse_diff_with_op_copy(self):
        """Testing DiffXParser.parse_diff with file op=copy"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=169\n'
            b'{\n'
            b'    "op": "copy",\n'
            b'    "path": {\n'
            b'        "old": "old-name",\n'
            b'        "new": "new-name"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    }\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'old-name',
            orig_file_details=b'abc123',
            modified_filename=b'new-name',
            modified_file_details=b'def456',
            copied=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'copy',
                        'path': {
                            'old': 'old-name',
                            'new': 'new-name',
                        },
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_op_copy_modify(self):
        """Testing DiffXParser.parse_diff with file op=copy-modify"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=176\n'
            b'{\n'
            b'    "op": "copy-modify",\n'
            b'    "path": {\n'
            b'        "old": "old-name",\n'
            b'        "new": "new-name"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=58, line_endings=unix\n'
            b'--- old-name\n'
            b'+++ new-name\n'
            b'@@ -1 +1 @@\n'
            b'-old line\n'
            b'+new line\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'old-name',
            orig_file_details=b'abc123',
            modified_filename=b'new-name',
            modified_file_details=b'def456',
            copied=True,
            insert_count=1,
            delete_count=1,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'op': 'copy-modify',
                        'path': {
                            'old': 'old-name',
                            'new': 'new-name',
                        },
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- old-name\n'
                b'+++ new-name\n'
                b'@@ -1 +1 @@\n'
                b'-old line\n'
                b'+new line\n'
            ))

    def test_parse_diff_with_existing_stats(self):
        """Testing DiffXParser.parse_diff with existing file stats"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=225\n'
            b'{\n'
            b'    "path": {\n'
            b'        "old": "old-name",\n'
            b'        "new": "new-name"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "stats": {\n'
            b'        "deletions": 100,\n'
            b'        "insertions": 200\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=58, line_endings=unix\n'
            b'--- old-name\n'
            b'+++ new-name\n'
            b'@@ -1 +1 @@\n'
            b'-old line\n'
            b'+new line\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'old-name',
            orig_file_details=b'abc123',
            modified_filename=b'new-name',
            modified_file_details=b'def456',
            insert_count=200,
            delete_count=100,
            extra_data={
                'diffx': {
                    'diff_options': {
                        'line_endings': 'unix',
                    },
                    'metadata': {
                        'path': {
                            'old': 'old-name',
                            'new': 'new-name',
                        },
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                        'stats': {
                            'deletions': 100,
                            'insertions': 200,
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            },
            data=(
                b'--- old-name\n'
                b'+++ new-name\n'
                b'@@ -1 +1 @@\n'
                b'-old line\n'
                b'+new line\n'
            ))

    def test_parse_diff_with_type_symlink_op_create_target_str(self):
        """Testing DiffXParser.parse_diff with file type=symlink, op=create,
        symlink target=string
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=153\n'
            b'{\n'
            b'    "op": "create",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "type": "symlink",\n'
            b'    "symlink target": "target/path/"\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=PRE_CREATION,
            modified_filename=b'name',
            modified_file_details=b'def456',
            new_symlink_target=b'target/path/',
            is_symlink=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'create',
                        'path': 'name',
                        'revision': {
                            'new': 'def456',
                        },
                        'symlink target': 'target/path/',
                        'type': 'symlink',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_type_symlink_op_create_target_dict(self):
        """Testing DiffXParser.parse_diff with file type=symlink, op=create,
        symlink target=dict
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=177\n'
            b'{\n'
            b'    "op": "create",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "type": "symlink",\n'
            b'    "symlink target": {\n'
            b'         "new": "target/path/"\n'
            b'    }\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=PRE_CREATION,
            modified_filename=b'name',
            modified_file_details=b'def456',
            new_symlink_target=b'target/path/',
            is_symlink=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'create',
                        'path': 'name',
                        'revision': {
                            'new': 'def456',
                        },
                        'symlink target': {
                            'new': 'target/path/',
                        },
                        'type': 'symlink',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_type_symlink_op_modify_target_str(self):
        """Testing DiffXParser.parse_diff with file type=symlink, op=modify,
        symlink target=string
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=212\n'
            b'{\n'
            b'    "op": "modify",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "symlink target": "target/path/",\n'
            b'    "type": "symlink"\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=b'abc123',
            modified_filename=b'name',
            modified_file_details=b'def456',
            old_symlink_target=b'target/path/',
            new_symlink_target=b'target/path/',
            is_symlink=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'modify',
                        'path': 'name',
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                        'symlink target': 'target/path/',
                        'type': 'symlink',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_type_symlink_op_modify_target_dict(self):
        """Testing DiffXParser.parse_diff with file type=symlink, op=modify,
        symlink target=dict
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=230\n'
            b'{\n'
            b'    "op": "modify",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "symlink target": {\n'
            b'        "old": "old/target/",\n'
            b'        "new": "new/target/"\n'
            b'    },\n'
            b'    "type": "symlink"\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details='abc123',
            modified_filename=b'name',
            modified_file_details=b'def456',
            old_symlink_target=b'old/target/',
            new_symlink_target=b'new/target/',
            is_symlink=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'modify',
                        'path': 'name',
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                        'symlink target': {
                            'old': 'old/target/',
                            'new': 'new/target/',
                        },
                        'type': 'symlink',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_type_symlink_op_delete_target_str(self):
        """Testing DiffXParser.parse_diff with file type=symlink, op=delete,
        symlink target=str
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=153\n'
            b'{\n'
            b'    "op": "delete",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "old": "abc123"\n'
            b'    },\n'
            b'    "symlink target": "target/path/",\n'
            b'    "type": "symlink"\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details='abc123',
            modified_filename=b'name',
            modified_file_details=HEAD,
            old_symlink_target=b'target/path/',
            is_symlink=True,
            deleted=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'delete',
                        'path': 'name',
                        'revision': {
                            'old': 'abc123',
                        },
                        'symlink target': 'target/path/',
                        'type': 'symlink',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_type_symlink_op_delete_target_dict(self):
        """Testing DiffXParser.parse_diff with file type=symlink, op=delete,
        symlink target=dict
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=176\n'
            b'{\n'
            b'    "op": "delete",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "old": "abc123"\n'
            b'    },\n'
            b'    "symlink target": {\n'
            b'        "old": "target/path/"\n'
            b'    },\n'
            b'    "type": "symlink"\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details='abc123',
            modified_filename=b'name',
            modified_file_details=HEAD,
            old_symlink_target=b'target/path/',
            is_symlink=True,
            deleted=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'delete',
                        'path': 'name',
                        'revision': {
                            'old': 'abc123',
                        },
                        'symlink target': {
                            'old': 'target/path/',
                        },
                        'type': 'symlink',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_unix_file_mode_op_create_target_str(self):
        """Testing DiffXParser.parse_diff with op=create, unix file
        mode=string
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=125\n'
            b'{\n'
            b'    "op": "create",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "unix file mode": "0100644"\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=PRE_CREATION,
            modified_filename=b'name',
            modified_file_details=b'def456',
            new_unix_mode='0100644',
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'create',
                        'path': 'name',
                        'revision': {
                            'new': 'def456',
                        },
                        'unix file mode': '0100644',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_unix_file_mode_op_create_target_dict(self):
        """Testing DiffXParser.parse_diff with op=create, unix file
        mode=dict
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=148\n'
            b'{\n'
            b'    "op": "create",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "unix file mode": {\n'
            b'        "new": "0100644"\n'
            b'    }\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=PRE_CREATION,
            modified_filename=b'name',
            modified_file_details=b'def456',
            new_unix_mode='0100644',
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'create',
                        'path': 'name',
                        'revision': {
                            'new': 'def456',
                        },
                        'unix file mode': {
                            'new': '0100644',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_unix_file_mode_op_modify_target_str(self):
        """Testing DiffXParser.parse_diff with op=modify, unix file
        mode=string
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=150\n'
            b'{\n'
            b'    "op": "modify",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "unix file mode": "0100644"\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=b'abc123',
            modified_filename=b'name',
            modified_file_details=b'def456',
            old_unix_mode='0100644',
            new_unix_mode='0100644',
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'modify',
                        'path': 'name',
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                        'unix file mode': '0100644',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_unix_file_mode_op_modify_target_dict(self):
        """Testing DiffXParser.parse_diff with op=modify, unix file
        mode=dict
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=199\n'
            b'{\n'
            b'    "op": "modify",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "old": "abc123",\n'
            b'        "new": "def456"\n'
            b'    },\n'
            b'    "unix file mode": {\n'
            b'        "old": "0100644",\n'
            b'        "new": "0100755"\n'
            b'    }\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=b'abc123',
            modified_filename=b'name',
            modified_file_details=b'def456',
            old_unix_mode='0100644',
            new_unix_mode='0100755',
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'modify',
                        'path': 'name',
                        'revision': {
                            'old': 'abc123',
                            'new': 'def456',
                        },
                        'unix file mode': {
                            'old': '0100644',
                            'new': '0100755',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_unix_file_mode_op_delete_target_str(self):
        """Testing DiffXParser.parse_diff with op=delete, unix file
        mode=string
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=125\n'
            b'{\n'
            b'    "op": "delete",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "old": "abc123"\n'
            b'    },\n'
            b'    "unix file mode": "0100644"\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=b'abc123',
            modified_filename=b'name',
            modified_file_details=HEAD,
            old_unix_mode='0100644',
            deleted=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'delete',
                        'path': 'name',
                        'revision': {
                            'old': 'abc123',
                        },
                        'unix file mode': '0100644',
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_unix_file_mode_op_delete_target_dict(self):
        """Testing DiffXParser.parse_diff with op=delete, unix file
        mode=dict
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=148\n'
            b'{\n'
            b'    "op": "delete",\n'
            b'    "path": "name",\n'
            b'    "revision": {\n'
            b'        "old": "abc123"\n'
            b'    },\n'
            b'    "unix file mode": {\n'
            b'        "old": "0100644"\n'
            b'    }\n'
            b'}\n'
        )

        parsed_diff = parser.parse_diff()
        self.assert_parsed_diff(
            parsed_diff,
            parser=parser,
            num_changes=1,
            extra_data={
                'diffx': {
                    'options': {
                        'encoding': 'utf-8',
                        'version': '1.0',
                    },
                },
            })

        parsed_change = parsed_diff.changes[0]
        self.assert_parsed_diff_change(parsed_change,
                                       num_files=1)

        self.assert_parsed_diff_file(
            parsed_change.files[0],
            orig_filename=b'name',
            orig_file_details=b'abc123',
            modified_filename=b'name',
            modified_file_details=HEAD,
            old_unix_mode='0100644',
            deleted=True,
            extra_data={
                'diffx': {
                    'metadata': {
                        'op': 'delete',
                        'path': 'name',
                        'revision': {
                            'old': 'abc123',
                        },
                        'unix file mode': {
                            'old': '0100644',
                        },
                    },
                    'metadata_options': {
                        'format': 'json',
                    },
                },
            })

    def test_parse_diff_with_invalid_diffx(self):
        """Testing DiffXParser.parse_diff with invalid DiffX file contents"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'BLARGH\n'
        )

        message = (
            "Error on line 2: Unexpected or improperly formatted header: %r"
            % b'BLARGH'
        )

        with self.assertRaisesMessage(DiffParserError, message):
            parser.parse_diff()

    def test_parse_diff_with_path_invalid_type(self):
        """Testing DiffXParser.parse_diff with invalid file path type"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=94\n'
            b'{\n'
            b'    "path": 123,\n'
            b'    "revision": {\n'
            b'        "new": "def456",\n'
            b'        "old": "abc123"\n'
            b'    }\n'
            b'}\n'
        )

        message = (
            'Unexpected type %s for "path" key in change 1, file 1'
            % int
        )

        with self.assertRaisesMessage(DiffParserError, message):
            parser.parse_diff()

    def test_parse_diff_with_path_dict_missing_old(self):
        """Testing DiffXParser.parse_diff with file path as dictionary with
        missing "old" key
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=120\n'
            b'{\n'
            b'    "path": {\n'
            b'        "new": "file"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "new": "def456",\n'
            b'        "old": "abc123"\n'
            b'    }\n'
            b'}\n'
        )

        message = 'Missing the "path.old" key in change 1, file 1'

        with self.assertRaisesMessage(DiffParserError, message):
            parser.parse_diff()

    def test_parse_diff_with_path_dict_missing_new(self):
        """Testing DiffXParser.parse_diff with file path as dictionary with
        missing "new" key
        """
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=120\n'
            b'{\n'
            b'    "path": {\n'
            b'        "old": "file"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "new": "def456",\n'
            b'        "old": "abc123"\n'
            b'    }\n'
            b'}\n'
        )

        message = 'Missing the "path.new" key in change 1, file 1'

        with self.assertRaisesMessage(DiffParserError, message):
            parser.parse_diff()

    def test_parse_diff_with_revision_invalid_type(self):
        """Testing DiffXParser.parse_diff with invalid file revision type"""
        parser = DiffXParser(
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=44\n'
            b'{\n'
            b'    "path": "file",\n'
            b'    "revision": 123\n'
            b'}\n'
        )

        message = (
            'Unexpected type %s for "revision" key in change 1, file 1'
            % int
        )

        with self.assertRaisesMessage(DiffParserError, message):
            parser.parse_diff()

    @add_fixtures(['test_scmtools'])
    def test_raw_diff_with_diffset_simple(self):
        """Testing DiffXParser.raw_diff with DiffSet and simple diff"""
        repository = self.create_repository(tool_name='Test')
        diffset = self.create_diffset(repository=repository)
        diffset.extra_data = {
            'diffx': {
                'options': {
                    'encoding': 'utf-8',
                    'version': '1.0',
                },
            },
        }
        diffset.save(update_fields=('extra_data',))

        diffcommit = self.create_diffcommit(diffset=diffset,
                                            with_diff=False)

        filediff = self.create_filediff(
            diffset=diffset,
            commit=diffcommit,
            save=False,
            diff=(
                b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
                b'+++ message2.py\t2021-07-02 13:21:31.428383873 -0700\n'
                b'@@ -164,10 +164,10 @@\n'
                b'             not isinstance(headers, MultiValueDict)):\n'
                b'             # Instantiating a MultiValueDict from a dict '
                b'does not ensure that\n'
                b'             # values are lists, so we have to ensure that '
                b'ourselves.\n'
                b'-            headers = MultiValueDict(dict(\n'
                b'-                (key, [value])\n'
                b'-                for key, value in six.iteritems(headers)\n'
                b'-            ))\n'
                b'+            headers = MultiValueDict({\n'
                b'+                key: [value]\n'
                b'+                for key, value in headers.items()\n'
                b'+            })\n'
                b' \n'
                b'         if in_reply_to:\n'
                b'             headers["In-Reply-To"] = in_reply_to\n'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'line_endings': 'unix',
                },
                'metadata': {
                    'path': {
                        'old': 'message.py',
                        'new': 'message2.py',
                    },
                    'revision': {
                        'old': 'abc123',
                        'new': 'def456',
                    },
                },
                'metadata_options': {
                    'format': 'json',
                },
            },
        }
        filediff.save()

        parser = DiffXParser(b'')
        self.assertEqual(
            parser.raw_diff(diffset),
            b'#diffx: encoding=utf-8, version=1.0\n'
            b'#.change:\n'
            b'#..file:\n'
            b'#...meta: format=json, length=156\n'
            b'{\n'
            b'    "path": {\n'
            b'        "new": "message2.py",\n'
            b'        "old": "message.py"\n'
            b'    },\n'
            b'    "revision": {\n'
            b'        "new": "def456",\n'
            b'        "old": "abc123"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=693, line_endings=unix\n'
            b'--- message.py\t2021-07-02 13:20:12.285875444 -0700\n'
            b'+++ message2.py\t2021-07-02 13:21:31.428383873 -0700\n'
            b'@@ -164,10 +164,10 @@\n'
            b'             not isinstance(headers, MultiValueDict)):\n'
            b'             # Instantiating a MultiValueDict from a dict does '
            b'not ensure that\n'
            b'             # values are lists, so we have to ensure that '
            b'ourselves.\n'
            b'-            headers = MultiValueDict(dict(\n'
            b'-                (key, [value])\n'
            b'-                for key, value in six.iteritems(headers)\n'
            b'-            ))\n'
            b'+            headers = MultiValueDict({\n'
            b'+                key: [value]\n'
            b'+                for key, value in headers.items()\n'
            b'+            })\n'
            b' \n'
            b'         if in_reply_to:\n'
            b'             headers["In-Reply-To"] = in_reply_to\n')

    @add_fixtures(['test_scmtools'])
    def test_raw_diff_with_diffset_complex(self):
        """Testing DiffXParser.raw_diff with DiffSet and complex diff"""
        repository = self.create_repository(tool_name='Test')
        diffset = self.create_diffset(repository=repository)
        diffset.extra_data = {
            'diffx': {
                'metadata': {
                    'key': 'value',
                },
                'metadata_options': {
                    'encoding': 'utf-32',
                    'format': 'json',
                },
                'options': {
                    'encoding': 'utf-16',
                    'version': '1.0',
                },
                'preamble': 'This is the file-level preamble.\r\n',
                'preamble_options': {
                    'encoding': 'ascii',
                    'indent': 2,
                    'line_endings': 'dos',
                    'mimetype': 'text/plain',
                },
            },
        }
        diffset.save(update_fields=('extra_data',))

        # Create DiffCommit #1.
        diffcommit = self.create_diffcommit(
            diffset=diffset,
            commit_id='a25e7b28af5e3184946068f432122c68c1a30b23',
            with_diff=False)
        diffcommit.extra_data = {
            'diffx': {
                'metadata': {
                    'author': 'Test User <test@example.com>',
                    'author date': '2021-06-01T13:12:06-07:00',
                    'committer': 'Test User <test@example.com>',
                    'date': '2021-06-02T19:26:31-07:00',
                    'id': 'a25e7b28af5e3184946068f432122c68c1a30b23',
                    'parent id': 'b892d5f833474c59d7851ff46a4b0bd919017e97',
                },
                'metadata_options': {
                    'encoding': 'utf-8',
                    'format': 'json',
                },
                'preamble': 'test\n',
                'preamble_options': {
                    'indent': 2,
                    'line_endings': 'unix',
                    'mimetype': 'text/markdown',
                },
            },
        }
        diffcommit.save(update_fields=('extra_data',))

        filediff = self.create_filediff(
            diffset=diffset,
            commit=diffcommit,
            source_file='file1',
            source_revision='c8839177d1a5605aa60abe69db95c84183f0eebe',
            dest_file='file1',
            dest_detail='eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef',
            save=False,
            diff=(
                b'--- /file1\n'
                b'+++ /file1\n'
                b'@@ -498,7 +498,7 @@\n'
                b' ... diff content\n'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'line_endings': 'unix',
                },
                'metadata': {
                    'path': 'file1',
                    'revision': {
                        'old': 'c8839177d1a5605aa60abe69db95c84183f0eebe',
                        'new': 'eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef',
                    },
                },
                'metadata_options': {
                    'encoding': 'latin1',
                    'format': 'json',
                },
            },
        }
        filediff.save()

        # Create DiffCommit #2.
        diffcommit = self.create_diffcommit(
            diffset=diffset,
            commit_id='91127b687f583184144161f432222748c1a30b23',
            with_diff=False)
        diffcommit.extra_data = {
            'diffx': {
                'metadata': {
                    'author': 'Test User <test@example.com>',
                    'author date': '2021-06-01T19:46:22-07:00',
                    'committer': 'Test User <test@example.com>',
                    'date': '2021-06-02T19:46:25-07:00',
                    'id': '91127b687f583184144161f432222748c1a30b23',
                    'parent id': 'a25e7b28af5e3184946068f432122c68c1a30b23',
                },
                'metadata_options': {
                    'encoding': 'utf-8',
                    'format': 'json',
                },
                'preamble': (
                    "Summary of commit #2\n"
                    "\n"
                    "Here's a description.\n"
                ),
                'preamble_options': {
                    'encoding': 'utf-8',
                    'indent': 4,
                    'line_endings': 'unix',
                },
            },
        }
        diffcommit.save(update_fields=('extra_data',))

        filediff = self.create_filediff(
            diffset=diffset,
            commit=diffcommit,
            source_file='file2',
            source_revision='281bac2b704617e807850e07e54bae3469f6a2e7',
            dest_file='file2',
            dest_detail='389cc6b7ae5a659383eab5dfc253764eccf84732',
            save=False,
            diff=(
                b'\xff\xfe \x00.\x00.\x00.\x00 \x00d\x00i\x00f\x00f\x00\n\x00'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'encoding': 'utf-16',
                    'line_endings': 'unix',
                },
                'metadata': {
                    'path': 'file2',
                    'revision': {
                        'old': '281bac2b704617e807850e07e54bae3469f6a2e7',
                        'new': '389cc6b7ae5a659383eab5dfc253764eccf84732',
                    },
                },
                'metadata_options': {
                    'encoding': 'utf-32',
                    'format': 'json',
                },
            },
            'encoding': 'utf-16',
        }
        filediff.save()

        filediff = self.create_filediff(
            diffset=diffset,
            commit=diffcommit,
            source_file='file3',
            source_revision='be089b7197974703c83682088a068bef3422c6c2',
            dest_file='file3',
            dest_detail='0d4a0fb8d62b762a26e13591d06d93d79d61102f',
            save=False,
            diff=(
                b'--- a/file3\r\n'
                b'+++ b/file3\r\n'
                b'@@ -258,1 +258,2 @@\r\n'
                b'- old line\r\n'
                b'+ new line 1\r\n'
                b'+ new line 2\r\n'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'line_endings': 'dos',
                },
                'metadata': {
                    'path': 'file3',
                    'revision': {
                        'old': 'be089b7197974703c83682088a068bef3422c6c2',
                        'new': '0d4a0fb8d62b762a26e13591d06d93d79d61102f',
                    },
                },
                'metadata_options': {
                    'encoding': 'utf-8',
                    'format': 'json',
                },
            },
        }
        filediff.save()

        parser = DiffXParser(b'')
        self.assertEqual(
            parser.raw_diff(diffset),
            b'#diffx: encoding=utf-16, version=1.0\n'
            b'#.preamble: encoding=ascii, indent=2, length=36,'
            b' line_endings=dos, mimetype=text/plain\n'
            b'  This is the file-level preamble.\r\n'
            b'#.meta: encoding=utf-32, format=json, length=96\n'
            b'\xff\xfe\x00\x00{\x00\x00\x00\n\x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00"'
            b'\x00\x00\x00k\x00\x00\x00e\x00\x00\x00y\x00\x00\x00"'
            b'\x00\x00\x00:\x00\x00\x00 \x00\x00\x00"\x00\x00\x00v'
            b'\x00\x00\x00a\x00\x00\x00l\x00\x00\x00u\x00\x00\x00e'
            b'\x00\x00\x00"\x00\x00\x00\n\x00\x00\x00}\x00\x00\x00'
            b'\n\x00\x00\x00'
            b'#.change:\n'
            b'#..preamble: indent=2, length=14, line_endings=unix, '
            b'mimetype=text/markdown\n'
            b'  \xff\xfet\x00e\x00s\x00t\x00\n\x00'
            b'#..meta: encoding=utf-8, format=json, length=302\n'
            b'{\n'
            b'    "author": "Test User <test@example.com>",\n'
            b'    "author date": "2021-06-01T13:12:06-07:00",\n'
            b'    "committer": "Test User <test@example.com>",\n'
            b'    "date": "2021-06-02T19:26:31-07:00",\n'
            b'    "id": "a25e7b28af5e3184946068f432122c68c1a30b23",\n'
            b'    "parent id": "b892d5f833474c59d7851ff46a4b0bd919017e97"\n'
            b'}\n'
            b'#..file:\n'
            b'#...meta: encoding=latin1, format=json, length=166\n'
            b'{\n'
            b'    "path": "file1",\n'
            b'    "revision": {\n'
            b'        "new": "eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef",\n'
            b'        "old": "c8839177d1a5605aa60abe69db95c84183f0eebe"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=60, line_endings=unix\n'
            b'--- /file1\n'
            b'+++ /file1\n'
            b'@@ -498,7 +498,7 @@\n'
            b' ... diff content\n'
            b'#.change:\n'
            b'#..preamble: encoding=utf-8, indent=4, length=56, '
            b'line_endings=unix\n'
            b'    Summary of commit #2\n'
            b'    \n'
            b'    Here\'s a description.\n'
            b'#..meta: encoding=utf-8, format=json, length=302\n'
            b'{\n'
            b'    "author": "Test User <test@example.com>",\n'
            b'    "author date": "2021-06-01T19:46:22-07:00",\n'
            b'    "committer": "Test User <test@example.com>",\n'
            b'    "date": "2021-06-02T19:46:25-07:00",\n'
            b'    "id": "91127b687f583184144161f432222748c1a30b23",\n'
            b'    "parent id": "a25e7b28af5e3184946068f432122c68c1a30b23"\n'
            b'}\n'
            b'#..file:\n'
            b'#...meta: encoding=utf-32, format=json, length=668\n'
            b'\xff\xfe\x00\x00{\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00"\x00\x00\x00'
            b'p\x00\x00\x00a\x00\x00\x00t\x00\x00\x00h\x00\x00\x00'
            b'"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00"\x00\x00\x00'
            b'f\x00\x00\x00i\x00\x00\x00l\x00\x00\x00e\x00\x00\x00'
            b'2\x00\x00\x00"\x00\x00\x00,\x00\x00\x00\n\x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b'"\x00\x00\x00r\x00\x00\x00e\x00\x00\x00v\x00\x00\x00'
            b'i\x00\x00\x00s\x00\x00\x00i\x00\x00\x00o\x00\x00\x00'
            b'n\x00\x00\x00"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00'
            b'{\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00"\x00\x00\x00n\x00\x00\x00'
            b'e\x00\x00\x00w\x00\x00\x00"\x00\x00\x00:\x00\x00\x00'
            b' \x00\x00\x00"\x00\x00\x003\x00\x00\x008\x00\x00\x00'
            b'9\x00\x00\x00c\x00\x00\x00c\x00\x00\x006\x00\x00\x00'
            b'b\x00\x00\x007\x00\x00\x00a\x00\x00\x00e\x00\x00\x00'
            b'5\x00\x00\x00a\x00\x00\x006\x00\x00\x005\x00\x00\x00'
            b'9\x00\x00\x003\x00\x00\x008\x00\x00\x003\x00\x00\x00'
            b'e\x00\x00\x00a\x00\x00\x00b\x00\x00\x005\x00\x00\x00'
            b'd\x00\x00\x00f\x00\x00\x00c\x00\x00\x002\x00\x00\x00'
            b'5\x00\x00\x003\x00\x00\x007\x00\x00\x006\x00\x00\x00'
            b'4\x00\x00\x00e\x00\x00\x00c\x00\x00\x00c\x00\x00\x00'
            b'f\x00\x00\x008\x00\x00\x004\x00\x00\x007\x00\x00\x00'
            b'3\x00\x00\x002\x00\x00\x00"\x00\x00\x00,\x00\x00\x00'
            b'\n\x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00"\x00\x00\x00o\x00\x00\x00l\x00\x00\x00'
            b'd\x00\x00\x00"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00'
            b'"\x00\x00\x002\x00\x00\x008\x00\x00\x001\x00\x00\x00'
            b'b\x00\x00\x00a\x00\x00\x00c\x00\x00\x002\x00\x00\x00'
            b'b\x00\x00\x007\x00\x00\x000\x00\x00\x004\x00\x00\x00'
            b'6\x00\x00\x001\x00\x00\x007\x00\x00\x00e\x00\x00\x00'
            b'8\x00\x00\x000\x00\x00\x007\x00\x00\x008\x00\x00\x00'
            b'5\x00\x00\x000\x00\x00\x00e\x00\x00\x000\x00\x00\x00'
            b'7\x00\x00\x00e\x00\x00\x005\x00\x00\x004\x00\x00\x00'
            b'b\x00\x00\x00a\x00\x00\x00e\x00\x00\x003\x00\x00\x00'
            b'4\x00\x00\x006\x00\x00\x009\x00\x00\x00f\x00\x00\x00'
            b'6\x00\x00\x00a\x00\x00\x002\x00\x00\x00e\x00\x00\x00'
            b'7\x00\x00\x00"\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00}\x00\x00\x00'
            b'\n\x00\x00\x00}\x00\x00\x00\n\x00\x00\x00'
            b'#...diff: encoding=utf-16, length=22, line_endings=unix\n'
            b'\xff\xfe \x00.\x00.\x00.\x00 \x00d\x00i\x00f\x00f\x00\n\x00'
            b'#..file:\n'
            b'#...meta: encoding=utf-8, format=json, length=166\n'
            b'{\n'
            b'    "path": "file3",\n'
            b'    "revision": {\n'
            b'        "new": "0d4a0fb8d62b762a26e13591d06d93d79d61102f",\n'
            b'        "old": "be089b7197974703c83682088a068bef3422c6c2"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=87, line_endings=dos\n'
            b'--- a/file3\r\n'
            b'+++ b/file3\r\n'
            b'@@ -258,1 +258,2 @@\r\n'
            b'- old line\r\n'
            b'+ new line 1\r\n'
            b'+ new line 2\r\n')

    @add_fixtures(['test_scmtools'])
    def test_raw_diff_with_diffset_no_diffcommits(self):
        """Testing DiffXParser.raw_diff with DiffSet and no DiffCommits"""
        repository = self.create_repository(tool_name='Test')
        diffset = self.create_diffset(repository=repository)
        diffset.extra_data = {
            'diffx': {
                'metadata': {
                    'key': 'value',
                },
                'metadata_options': {
                    'encoding': 'utf-32',
                    'format': 'json',
                },
                'options': {
                    'encoding': 'utf-16',
                    'version': '1.0',
                },
                'preamble': 'This is the file-level preamble.\r\n',
                'preamble_options': {
                    'encoding': 'ascii',
                    'indent': 2,
                    'line_endings': 'dos',
                    'mimetype': 'text/plain',
                },
            },
            'change_extra_data': {
                'diffx': {
                    'metadata': {
                        'author': 'Test User <test@example.com>',
                        'author date': '2021-06-01T13:12:06-07:00',
                        'committer': 'Test User <test@example.com>',
                        'date': '2021-06-02T19:26:31-07:00',
                        'id': 'a25e7b28af5e3184946068f432122c68c1a30b23',
                        'parent id':
                            'b892d5f833474c59d7851ff46a4b0bd919017e97',
                    },
                    'metadata_options': {
                        'encoding': 'utf-8',
                        'format': 'json',
                    },
                    'preamble': 'test\n',
                    'preamble_options': {
                        'indent': 2,
                        'line_endings': 'unix',
                        'mimetype': 'text/markdown',
                    },
                },
            },
        }
        diffset.save(update_fields=('extra_data',))

        filediff = self.create_filediff(
            diffset=diffset,
            source_file='file1',
            source_revision='c8839177d1a5605aa60abe69db95c84183f0eebe',
            dest_file='file1',
            dest_detail='eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef',
            save=False,
            diff=(
                b'--- /file1\n'
                b'+++ /file1\n'
                b'@@ -498,7 +498,7 @@\n'
                b' ... diff content\n'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'line_endings': 'unix',
                },
                'metadata': {
                    'path': 'file1',
                    'revision': {
                        'old': 'c8839177d1a5605aa60abe69db95c84183f0eebe',
                        'new': 'eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef',
                    },
                },
                'metadata_options': {
                    'encoding': 'latin1',
                    'format': 'json',
                },
            },
        }
        filediff.save()

        filediff = self.create_filediff(
            diffset=diffset,
            source_file='file2',
            source_revision='281bac2b704617e807850e07e54bae3469f6a2e7',
            dest_file='file2',
            dest_detail='389cc6b7ae5a659383eab5dfc253764eccf84732',
            save=False,
            diff=(
                b'\xff\xfe \x00.\x00.\x00.\x00 \x00d\x00i\x00f\x00f\x00\n\x00'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'encoding': 'utf-16',
                    'line_endings': 'unix',
                },
                'metadata': {
                    'path': 'file2',
                    'revision': {
                        'old': '281bac2b704617e807850e07e54bae3469f6a2e7',
                        'new': '389cc6b7ae5a659383eab5dfc253764eccf84732',
                    },
                },
                'metadata_options': {
                    'encoding': 'utf-32',
                    'format': 'json',
                },
            },
            'encoding': 'utf-16',
        }
        filediff.save()

        parser = DiffXParser(b'')
        self.assertEqual(
            parser.raw_diff(diffset),
            b'#diffx: encoding=utf-16, version=1.0\n'
            b'#.preamble: encoding=ascii, indent=2, length=36,'
            b' line_endings=dos, mimetype=text/plain\n'
            b'  This is the file-level preamble.\r\n'
            b'#.meta: encoding=utf-32, format=json, length=96\n'
            b'\xff\xfe\x00\x00{\x00\x00\x00\n\x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00"'
            b'\x00\x00\x00k\x00\x00\x00e\x00\x00\x00y\x00\x00\x00"'
            b'\x00\x00\x00:\x00\x00\x00 \x00\x00\x00"\x00\x00\x00v'
            b'\x00\x00\x00a\x00\x00\x00l\x00\x00\x00u\x00\x00\x00e'
            b'\x00\x00\x00"\x00\x00\x00\n\x00\x00\x00}\x00\x00\x00'
            b'\n\x00\x00\x00'
            b'#.change:\n'
            b'#..preamble: indent=2, length=14, line_endings=unix, '
            b'mimetype=text/markdown\n'
            b'  \xff\xfet\x00e\x00s\x00t\x00\n\x00'
            b'#..meta: encoding=utf-8, format=json, length=302\n'
            b'{\n'
            b'    "author": "Test User <test@example.com>",\n'
            b'    "author date": "2021-06-01T13:12:06-07:00",\n'
            b'    "committer": "Test User <test@example.com>",\n'
            b'    "date": "2021-06-02T19:26:31-07:00",\n'
            b'    "id": "a25e7b28af5e3184946068f432122c68c1a30b23",\n'
            b'    "parent id": "b892d5f833474c59d7851ff46a4b0bd919017e97"\n'
            b'}\n'
            b'#..file:\n'
            b'#...meta: encoding=latin1, format=json, length=166\n'
            b'{\n'
            b'    "path": "file1",\n'
            b'    "revision": {\n'
            b'        "new": "eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef",\n'
            b'        "old": "c8839177d1a5605aa60abe69db95c84183f0eebe"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=60, line_endings=unix\n'
            b'--- /file1\n'
            b'+++ /file1\n'
            b'@@ -498,7 +498,7 @@\n'
            b' ... diff content\n'
            b'#..file:\n'
            b'#...meta: encoding=utf-32, format=json, length=668\n'
            b'\xff\xfe\x00\x00{\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00"\x00\x00\x00'
            b'p\x00\x00\x00a\x00\x00\x00t\x00\x00\x00h\x00\x00\x00'
            b'"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00"\x00\x00\x00'
            b'f\x00\x00\x00i\x00\x00\x00l\x00\x00\x00e\x00\x00\x00'
            b'2\x00\x00\x00"\x00\x00\x00,\x00\x00\x00\n\x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b'"\x00\x00\x00r\x00\x00\x00e\x00\x00\x00v\x00\x00\x00'
            b'i\x00\x00\x00s\x00\x00\x00i\x00\x00\x00o\x00\x00\x00'
            b'n\x00\x00\x00"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00'
            b'{\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00"\x00\x00\x00n\x00\x00\x00'
            b'e\x00\x00\x00w\x00\x00\x00"\x00\x00\x00:\x00\x00\x00'
            b' \x00\x00\x00"\x00\x00\x003\x00\x00\x008\x00\x00\x00'
            b'9\x00\x00\x00c\x00\x00\x00c\x00\x00\x006\x00\x00\x00'
            b'b\x00\x00\x007\x00\x00\x00a\x00\x00\x00e\x00\x00\x00'
            b'5\x00\x00\x00a\x00\x00\x006\x00\x00\x005\x00\x00\x00'
            b'9\x00\x00\x003\x00\x00\x008\x00\x00\x003\x00\x00\x00'
            b'e\x00\x00\x00a\x00\x00\x00b\x00\x00\x005\x00\x00\x00'
            b'd\x00\x00\x00f\x00\x00\x00c\x00\x00\x002\x00\x00\x00'
            b'5\x00\x00\x003\x00\x00\x007\x00\x00\x006\x00\x00\x00'
            b'4\x00\x00\x00e\x00\x00\x00c\x00\x00\x00c\x00\x00\x00'
            b'f\x00\x00\x008\x00\x00\x004\x00\x00\x007\x00\x00\x00'
            b'3\x00\x00\x002\x00\x00\x00"\x00\x00\x00,\x00\x00\x00'
            b'\n\x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00"\x00\x00\x00o\x00\x00\x00l\x00\x00\x00'
            b'd\x00\x00\x00"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00'
            b'"\x00\x00\x002\x00\x00\x008\x00\x00\x001\x00\x00\x00'
            b'b\x00\x00\x00a\x00\x00\x00c\x00\x00\x002\x00\x00\x00'
            b'b\x00\x00\x007\x00\x00\x000\x00\x00\x004\x00\x00\x00'
            b'6\x00\x00\x001\x00\x00\x007\x00\x00\x00e\x00\x00\x00'
            b'8\x00\x00\x000\x00\x00\x007\x00\x00\x008\x00\x00\x00'
            b'5\x00\x00\x000\x00\x00\x00e\x00\x00\x000\x00\x00\x00'
            b'7\x00\x00\x00e\x00\x00\x005\x00\x00\x004\x00\x00\x00'
            b'b\x00\x00\x00a\x00\x00\x00e\x00\x00\x003\x00\x00\x00'
            b'4\x00\x00\x006\x00\x00\x009\x00\x00\x00f\x00\x00\x00'
            b'6\x00\x00\x00a\x00\x00\x002\x00\x00\x00e\x00\x00\x00'
            b'7\x00\x00\x00"\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00}\x00\x00\x00'
            b'\n\x00\x00\x00}\x00\x00\x00\n\x00\x00\x00'
            b'#...diff: encoding=utf-16, length=22, line_endings=unix\n'
            b'\xff\xfe \x00.\x00.\x00.\x00 \x00d\x00i\x00f\x00f\x00\n\x00')

    @add_fixtures(['test_scmtools'])
    def test_raw_diff_with_diffcommit(self):
        """Testing DiffXParser.raw_diff with DiffCommit"""
        repository = self.create_repository(tool_name='Test')
        diffset = self.create_diffset(repository=repository)
        diffset.extra_data = {
            'diffx': {
                'metadata': {
                    'key': 'value',
                },
                'metadata_options': {
                    'encoding': 'utf-32',
                    'format': 'json',
                },
                'options': {
                    'encoding': 'utf-16',
                    'version': '1.0',
                },
                'preamble': 'This is the file-level preamble.\r\n',
                'preamble_options': {
                    'encoding': 'ascii',
                    'indent': 2,
                    'line_endings': 'dos',
                    'mimetype': 'text/plain',
                },
            },
        }
        diffset.save(update_fields=('extra_data',))

        # Create DiffCommit #1.
        diffcommit1 = self.create_diffcommit(
            diffset=diffset,
            commit_id='a25e7b28af5e3184946068f432122c68c1a30b23',
            with_diff=False)
        diffcommit1.extra_data = {
            'diffx': {
                'metadata': {
                    'author': 'Test User <test@example.com>',
                    'author date': '2021-06-01T13:12:06-07:00',
                    'committer': 'Test User <test@example.com>',
                    'date': '2021-06-02T19:26:31-07:00',
                    'id': 'a25e7b28af5e3184946068f432122c68c1a30b23',
                    'parent id': 'b892d5f833474c59d7851ff46a4b0bd919017e97',
                },
                'metadata_options': {
                    'encoding': 'utf-8',
                    'format': 'json',
                },
                'preamble': 'test\n',
                'preamble_options': {
                    'indent': 2,
                    'line_endings': 'unix',
                    'mimetype': 'text/markdown',
                },
            },
        }
        diffcommit1.save(update_fields=('extra_data',))

        filediff = self.create_filediff(
            diffset=diffset,
            commit=diffcommit1,
            source_file='file1',
            source_revision='c8839177d1a5605aa60abe69db95c84183f0eebe',
            dest_file='file1',
            dest_detail='eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef',
            save=False,
            diff=(
                b'--- /file1\n'
                b'+++ /file1\n'
                b'@@ -498,7 +498,7 @@\n'
                b' ... diff content\n'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'line_endings': 'unix',
                },
                'metadata': {
                    'path': 'file1',
                    'revision': {
                        'old': 'c8839177d1a5605aa60abe69db95c84183f0eebe',
                        'new': 'eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef',
                    },
                },
                'metadata_options': {
                    'encoding': 'latin1',
                    'format': 'json',
                },
            },
        }
        filediff.save()

        # Create DiffCommit #2. This one won't be used.
        diffcommit2 = self.create_diffcommit(
            diffset=diffset,
            commit_id='91127b687f583184144161f432222748c1a30b23',
            with_diff=False)
        diffcommit2.extra_data = {
            'diffx': {
                'metadata': {
                    'author': 'Test User <test@example.com>',
                    'author date': '2021-06-01T19:46:22-07:00',
                    'committer': 'Test User <test@example.com>',
                    'date': '2021-06-02T19:46:25-07:00',
                    'id': '91127b687f583184144161f432222748c1a30b23',
                    'parent id': 'a25e7b28af5e3184946068f432122c68c1a30b23',
                },
                'metadata_options': {
                    'encoding': 'utf-8',
                    'format': 'json',
                },
                'preamble': (
                    "Summary of commit #2\n"
                    "\n"
                    "Here's a description.\n"
                ),
                'preamble_options': {
                    'encoding': 'utf-8',
                    'indent': 4,
                    'line_endings': 'unix',
                },
            },
        }
        diffcommit2.save(update_fields=('extra_data',))

        filediff = self.create_filediff(
            diffset=diffset,
            commit=diffcommit2,
            source_file='file2',
            source_revision='281bac2b704617e807850e07e54bae3469f6a2e7',
            dest_file='file2',
            dest_detail='389cc6b7ae5a659383eab5dfc253764eccf84732',
            save=False,
            diff=(
                b'\xff\xfe \x00.\x00.\x00.\x00 \x00d\x00i\x00f\x00f\x00\n\x00'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'encoding': 'utf-16',
                    'line_endings': 'unix',
                },
                'metadata': {
                    'path': 'file2',
                    'revision': {
                        'old': '281bac2b704617e807850e07e54bae3469f6a2e7',
                        'new': '389cc6b7ae5a659383eab5dfc253764eccf84732',
                    },
                },
                'metadata_options': {
                    'encoding': 'utf-32',
                    'format': 'json',
                },
            },
            'encoding': 'utf-16',
        }
        filediff.save()

        filediff = self.create_filediff(
            diffset=diffset,
            commit=diffcommit2,
            source_file='file3',
            source_revision='be089b7197974703c83682088a068bef3422c6c2',
            dest_file='file3',
            dest_detail='0d4a0fb8d62b762a26e13591d06d93d79d61102f',
            save=False,
            diff=(
                b'--- a/file3\r\n'
                b'+++ b/file3\r\n'
                b'@@ -258,1 +258,2 @@\r\n'
                b'- old line\r\n'
                b'+ new line 1\r\n'
                b'+ new line 2\r\n'
            ))
        filediff.extra_data = {
            'diffx': {
                'diff_options': {
                    'line_endings': 'dos',
                },
                'metadata': {
                    'path': 'file3',
                    'revision': {
                        'old': 'be089b7197974703c83682088a068bef3422c6c2',
                        'new': '0d4a0fb8d62b762a26e13591d06d93d79d61102f',
                    },
                },
                'metadata_options': {
                    'encoding': 'utf-8',
                    'format': 'json',
                },
            },
        }
        filediff.save()

        parser = DiffXParser(b'')
        self.assertEqual(
            parser.raw_diff(diffcommit1),
            b'#diffx: encoding=utf-16, version=1.0\n'
            b'#.change:\n'
            b'#..preamble: indent=2, length=14, line_endings=unix, '
            b'mimetype=text/markdown\n'
            b'  \xff\xfet\x00e\x00s\x00t\x00\n\x00'
            b'#..meta: encoding=utf-8, format=json, length=302\n'
            b'{\n'
            b'    "author": "Test User <test@example.com>",\n'
            b'    "author date": "2021-06-01T13:12:06-07:00",\n'
            b'    "committer": "Test User <test@example.com>",\n'
            b'    "date": "2021-06-02T19:26:31-07:00",\n'
            b'    "id": "a25e7b28af5e3184946068f432122c68c1a30b23",\n'
            b'    "parent id": "b892d5f833474c59d7851ff46a4b0bd919017e97"\n'
            b'}\n'
            b'#..file:\n'
            b'#...meta: encoding=latin1, format=json, length=166\n'
            b'{\n'
            b'    "path": "file1",\n'
            b'    "revision": {\n'
            b'        "new": "eed8df7f1400a95cdf5a87ddb947e7d9c5a19cef",\n'
            b'        "old": "c8839177d1a5605aa60abe69db95c84183f0eebe"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=60, line_endings=unix\n'
            b'--- /file1\n'
            b'+++ /file1\n'
            b'@@ -498,7 +498,7 @@\n'
            b' ... diff content\n')

        self.assertEqual(
            parser.raw_diff(diffcommit2),
            b'#diffx: encoding=utf-16, version=1.0\n'
            b'#.change:\n'
            b'#..preamble: encoding=utf-8, indent=4, length=56, '
            b'line_endings=unix\n'
            b'    Summary of commit #2\n'
            b'    \n'
            b'    Here\'s a description.\n'
            b'#..meta: encoding=utf-8, format=json, length=302\n'
            b'{\n'
            b'    "author": "Test User <test@example.com>",\n'
            b'    "author date": "2021-06-01T19:46:22-07:00",\n'
            b'    "committer": "Test User <test@example.com>",\n'
            b'    "date": "2021-06-02T19:46:25-07:00",\n'
            b'    "id": "91127b687f583184144161f432222748c1a30b23",\n'
            b'    "parent id": "a25e7b28af5e3184946068f432122c68c1a30b23"\n'
            b'}\n'
            b'#..file:\n'
            b'#...meta: encoding=utf-32, format=json, length=668\n'
            b'\xff\xfe\x00\x00{\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00"\x00\x00\x00'
            b'p\x00\x00\x00a\x00\x00\x00t\x00\x00\x00h\x00\x00\x00'
            b'"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00"\x00\x00\x00'
            b'f\x00\x00\x00i\x00\x00\x00l\x00\x00\x00e\x00\x00\x00'
            b'2\x00\x00\x00"\x00\x00\x00,\x00\x00\x00\n\x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b'"\x00\x00\x00r\x00\x00\x00e\x00\x00\x00v\x00\x00\x00'
            b'i\x00\x00\x00s\x00\x00\x00i\x00\x00\x00o\x00\x00\x00'
            b'n\x00\x00\x00"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00'
            b'{\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00"\x00\x00\x00n\x00\x00\x00'
            b'e\x00\x00\x00w\x00\x00\x00"\x00\x00\x00:\x00\x00\x00'
            b' \x00\x00\x00"\x00\x00\x003\x00\x00\x008\x00\x00\x00'
            b'9\x00\x00\x00c\x00\x00\x00c\x00\x00\x006\x00\x00\x00'
            b'b\x00\x00\x007\x00\x00\x00a\x00\x00\x00e\x00\x00\x00'
            b'5\x00\x00\x00a\x00\x00\x006\x00\x00\x005\x00\x00\x00'
            b'9\x00\x00\x003\x00\x00\x008\x00\x00\x003\x00\x00\x00'
            b'e\x00\x00\x00a\x00\x00\x00b\x00\x00\x005\x00\x00\x00'
            b'd\x00\x00\x00f\x00\x00\x00c\x00\x00\x002\x00\x00\x00'
            b'5\x00\x00\x003\x00\x00\x007\x00\x00\x006\x00\x00\x00'
            b'4\x00\x00\x00e\x00\x00\x00c\x00\x00\x00c\x00\x00\x00'
            b'f\x00\x00\x008\x00\x00\x004\x00\x00\x007\x00\x00\x00'
            b'3\x00\x00\x002\x00\x00\x00"\x00\x00\x00,\x00\x00\x00'
            b'\n\x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00"\x00\x00\x00o\x00\x00\x00l\x00\x00\x00'
            b'd\x00\x00\x00"\x00\x00\x00:\x00\x00\x00 \x00\x00\x00'
            b'"\x00\x00\x002\x00\x00\x008\x00\x00\x001\x00\x00\x00'
            b'b\x00\x00\x00a\x00\x00\x00c\x00\x00\x002\x00\x00\x00'
            b'b\x00\x00\x007\x00\x00\x000\x00\x00\x004\x00\x00\x00'
            b'6\x00\x00\x001\x00\x00\x007\x00\x00\x00e\x00\x00\x00'
            b'8\x00\x00\x000\x00\x00\x007\x00\x00\x008\x00\x00\x00'
            b'5\x00\x00\x000\x00\x00\x00e\x00\x00\x000\x00\x00\x00'
            b'7\x00\x00\x00e\x00\x00\x005\x00\x00\x004\x00\x00\x00'
            b'b\x00\x00\x00a\x00\x00\x00e\x00\x00\x003\x00\x00\x00'
            b'4\x00\x00\x006\x00\x00\x009\x00\x00\x00f\x00\x00\x00'
            b'6\x00\x00\x00a\x00\x00\x002\x00\x00\x00e\x00\x00\x00'
            b'7\x00\x00\x00"\x00\x00\x00\n\x00\x00\x00 \x00\x00\x00'
            b' \x00\x00\x00 \x00\x00\x00 \x00\x00\x00}\x00\x00\x00'
            b'\n\x00\x00\x00}\x00\x00\x00\n\x00\x00\x00'
            b'#...diff: encoding=utf-16, length=22, line_endings=unix\n'
            b'\xff\xfe \x00.\x00.\x00.\x00 \x00d\x00i\x00f\x00f\x00\n\x00'
            b'#..file:\n'
            b'#...meta: encoding=utf-8, format=json, length=166\n'
            b'{\n'
            b'    "path": "file3",\n'
            b'    "revision": {\n'
            b'        "new": "0d4a0fb8d62b762a26e13591d06d93d79d61102f",\n'
            b'        "old": "be089b7197974703c83682088a068bef3422c6c2"\n'
            b'    }\n'
            b'}\n'
            b'#...diff: length=87, line_endings=dos\n'
            b'--- a/file3\r\n'
            b'+++ b/file3\r\n'
            b'@@ -258,1 +258,2 @@\r\n'
            b'- old line\r\n'
            b'+ new line 1\r\n'
            b'+ new line 2\r\n')
