"""Testing utilities for diff parsers.

Version Added:
    4.0.6
"""


class DiffParserTestingMixin(object):
    """Testing utilities for diff parsers.

    This must be mixed into a class using
    :py:class:`djblets.testing.testcases.TestCase`.

    Version Added:
        4.0.6
    """

    def assert_parsed_diff(self, parsed_diff, num_changes=0, **attrs):
        """Assert that a ParsedDiff has the expected attributes.

        Args:
            parsed_diff (reviewboard.diffviewer.parser.ParsedDiff):
                The parsed diff to check.

            num_changed (int, optional):
                The expected number of changes in the parsed diff.

            **attrs (dict, optional):
                A dictionary of explicit non-default attribute values to check.

        Raises:
            AssertionError:
                One or more attributes do not match.
        """
        self._assert_parsed_diff_obj(
            parsed_diff,
            attrs=attrs,
            default_attrs={
                'uses_commit_ids_as_revisions': False,
            })
        self.assertEqual(len(parsed_diff.changes), num_changes)

    def assert_parsed_diff_change(self, parsed_diff_change, num_files=0,
                                  **attrs):
        """Assert that a ParsedDiffChange has the expected attributes.

        Args:
            parsed_diff (reviewboard.diffviewer.parser.ParsedDiffChange):
                The parsed diff change to check.

            num_files (int, optional):
                The expected number of files in the parsed change.

            **attrs (dict, optional):
                A dictionary of explicit non-default attribute values to check.

        Raises:
            AssertionError:
                One or more attributes do not match.
        """
        self._assert_parsed_diff_obj(
            parsed_diff_change,
            attrs=attrs,
            default_attrs={
                'commit_id': None,
                'parent_commit_id': None,
            })
        self.assertEqual(len(parsed_diff_change.files), num_files)

    def assert_parsed_diff_file(self, parsed_diff_file, **attrs):
        """Assert that a ParsedDiffFile has the expected attributes.

        Args:
            parsed_diff_file (reviewboard.diffviewer.parser.ParsedDiffFile):
                The parsed diff file to check.

            **attrs (dict, optional):
                A dictionary of explicit non-default attribute values to check.

        Raises:
            AssertionError:
                One or more attributes do not match.
        """
        data = attrs.pop('data', b'')

        self._assert_parsed_diff_obj(
            parsed_diff_file,
            attrs=attrs,
            default_attrs={
                'binary': False,
                'copied': False,
                'delete_count': 0,
                'deleted': False,
                'index_header_value': None,
                'insert_count': 0,
                'is_symlink': False,
                'moved': False,
                'new_symlink_target': None,
                'new_unix_mode': None,
                'old_symlink_target': None,
                'old_unix_mode': None,
            })

        self.assertEqual(parsed_diff_file.data.splitlines(),
                         data.splitlines())

    def _assert_parsed_diff_obj(self, parsed_diff_obj, attrs, default_attrs):
        """Utility to assert that a parsed object has the expected attributes.

        Args:
            parsed_diff_obj (object):
                The parsed diff object to check.

            attrs (dict):
                A dictionary of explicit attribute values to check.

            default_attrs (dict):
                Default attribute values to check, if not explicitly provided.

        Raises:
            AssertionError:
                One or more attributes do not match.
        """
        # We'll test this separately in order to get a better error when
        # assertions fail on this.
        extra_data = attrs.pop('extra_data', {})

        self.assertAttrsEqual(parsed_diff_obj, dict(default_attrs, **attrs))
        self.assertEqual(parsed_diff_obj.extra_data, extra_data)
