from datetime import datetime

from django.contrib.auth.models import User

from reviewboard.changedescs.models import ChangeDescription
from reviewboard.testing.testcase import TestCase


class ChangeDescTests(TestCase):
    """Tests for the ChangeDescription model."""

    def test_record_string(self):
        """Testing ChangeDescription.record_field_change with a string value"""
        old_value = "abc"
        new_value = "def"

        changedesc = ChangeDescription()
        changedesc.record_field_change("test", old_value, new_value)

        self.assertIn("test", changedesc.fields_changed)
        self.assertIn("old", changedesc.fields_changed["test"])
        self.assertIn("new", changedesc.fields_changed["test"])
        self.assertNotIn("added", changedesc.fields_changed["test"])
        self.assertNotIn("removed", changedesc.fields_changed["test"])
        self.assertEqual(changedesc.fields_changed["test"]["old"],
                         (old_value,))
        self.assertEqual(changedesc.fields_changed["test"]["new"],
                         (new_value,))

    def test_record_list(self):
        """Testing ChangeDescription.record_field_change with a list value"""
        old_value = [1, 2, 3]
        new_value = [2, 3, 4]

        changedesc = ChangeDescription()
        changedesc.record_field_change("test", old_value, new_value)

        self.assertIn("test", changedesc.fields_changed)
        self.assertIn("old", changedesc.fields_changed["test"])
        self.assertIn("new", changedesc.fields_changed["test"])
        self.assertIn("added", changedesc.fields_changed["test"])
        self.assertIn("removed", changedesc.fields_changed["test"])
        self.assertEqual(changedesc.fields_changed["test"]["old"],
                         [(i,) for i in old_value])
        self.assertEqual(changedesc.fields_changed["test"]["new"],
                         [(i,) for i in new_value])
        self.assertEqual(changedesc.fields_changed["test"]["added"], [(4,)])
        self.assertEqual(changedesc.fields_changed["test"]["removed"], [(1,)])

    def test_record_object_list_name_field(self):
        """Testing ChangeDescription.record_field_change with an object list
        (using name_field)
        """
        class DummyObject(object):
            def __init__(self, id):
                self.id = id
                self.text = "Object %s" % id

            def get_absolute_url(self):
                return "http://localhost/%s" % self.id

        objs = [DummyObject(i) for i in range(4)]
        old_value = [objs[0], objs[1], objs[2]]
        new_value = [objs[1], objs[2], objs[3]]

        changedesc = ChangeDescription()
        changedesc.record_field_change("test", old_value, new_value, "text")

        self.assertIn("test", changedesc.fields_changed)
        self.assertIn("old", changedesc.fields_changed["test"])
        self.assertIn("new", changedesc.fields_changed["test"])
        self.assertIn("added", changedesc.fields_changed["test"])
        self.assertIn("removed", changedesc.fields_changed["test"])
        self.assertEqual(set(changedesc.fields_changed["test"]["old"]),
                         set([(obj.text, obj.get_absolute_url(), obj.id)
                             for obj in old_value]))
        self.assertEqual(set(changedesc.fields_changed["test"]["new"]),
                         set([(obj.text, obj.get_absolute_url(), obj.id)
                             for obj in new_value]))
        self.assertEqual(set(changedesc.fields_changed["test"]["added"]),
                         set([(new_value[2].text,
                              new_value[2].get_absolute_url(),
                              new_value[2].id)]))
        self.assertEqual(set(changedesc.fields_changed["test"]["removed"]),
                         set([(old_value[0].text,
                               old_value[0].get_absolute_url(),
                               old_value[0].id)]))

    def test_record_field_change_with_build_url_fuc(self) -> None:
        """Testing ChangeDescription.record_field_change with build_url_func"""
        class DummyObject:
            def __init__(self, id):
                self.id = id
                self.text = "Object %s" % id

        objs = [DummyObject(i) for i in range(4)]
        old_value = [objs[0], objs[1], objs[2]]
        new_value = [objs[1], objs[2], objs[3]]

        changedesc = ChangeDescription()
        changedesc.record_field_change(
            field="test",
            old_value=old_value,
            new_value=new_value,
            name_field='text',
            build_url_func=lambda obj: f'/path/to/{obj.id}')

        self.assertEqual(
            changedesc.fields_changed,
            {
                'test': {
                    'added': [
                        ('Object 3', '/path/to/3', 3)
                    ],
                    'new': [
                        ('Object 1', '/path/to/1', 1),
                        ('Object 2', '/path/to/2', 2),
                        ('Object 3', '/path/to/3', 3),
                    ],
                    'old': [
                        ('Object 0', '/path/to/0', 0),
                        ('Object 1', '/path/to/1', 1),
                        ('Object 2', '/path/to/2', 2),
                    ],
                    'removed': [
                        ('Object 0', '/path/to/0', 0),
                    ],
                },
            })

    def test_record_list_mismatch_type(self):
        """Testing ChangeDescription.record_field_change with
        mismatched types
        """
        changedesc = ChangeDescription()
        self.assertRaises(ValueError,
                          changedesc.record_field_change,
                          "test", 123, True)

    def test_is_new_for_user_with_non_owner(self):
        """Testing ChangeDescription.is_new_for_user with non-owner"""
        user1 = User.objects.create_user(username='test-user-1',
                                         email='user1@example.com')
        user2 = User.objects.create_user(username='test-user-2',
                                         email='user2@example.com')

        changedesc = ChangeDescription(
            user=user1,
            timestamp=datetime(2017, 9, 7, 15, 27, 0))
        self.assertTrue(changedesc.is_new_for_user(
            user=user2,
            last_visited=datetime(2017, 9, 7, 10, 0, 0)))
        self.assertFalse(changedesc.is_new_for_user(
            user=user2,
            last_visited=datetime(2017, 9, 7, 16, 0, 0)))
        self.assertFalse(changedesc.is_new_for_user(
            user=user2,
            last_visited=datetime(2017, 9, 7, 15, 27, 0)))

    def test_is_new_for_user_with_owner(self):
        """Testing ChangeDescription.is_new_for_user with owner"""
        user = User.objects.create_user(username='test-user',
                                        email='test@example.com')

        changedesc = ChangeDescription(
            user=user,
            timestamp=datetime(2017, 9, 7, 15, 27, 0))
        self.assertFalse(changedesc.is_new_for_user(
            user=user,
            last_visited=datetime(2017, 9, 7, 16, 0, 0)))
