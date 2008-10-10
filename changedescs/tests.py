from django.test import TestCase

from reviewboard.changedescs.models import ChangeDescription


class ChangeDescTests(TestCase):
    """Tests the ChangeDescription model."""
    def testRecordString(self):
        """Testing record_field_change with a string value"""
        old_value = "abc"
        new_value = "def"

        changedesc = ChangeDescription()
        changedesc.record_field_change("test", old_value, new_value)

        self.assert_("test" in changedesc.fields_changed)
        self.assert_("old" in changedesc.fields_changed["test"])
        self.assert_("new" in changedesc.fields_changed["test"])
        self.assert_("added" not in changedesc.fields_changed["test"])
        self.assert_("removed" not in changedesc.fields_changed["test"])
        self.assertEqual(changedesc.fields_changed["test"]["old"], (old_value,))
        self.assertEqual(changedesc.fields_changed["test"]["new"], (new_value,))

    def testRecordList(self):
        """Testing record_field_change with a list value"""
        old_value = [1, 2, 3]
        new_value = [2, 3, 4]

        changedesc = ChangeDescription()
        changedesc.record_field_change("test", old_value, new_value)

        self.assert_("test" in changedesc.fields_changed)
        self.assert_("old" in changedesc.fields_changed["test"])
        self.assert_("new" in changedesc.fields_changed["test"])
        self.assert_("added" in changedesc.fields_changed["test"])
        self.assert_("removed" in changedesc.fields_changed["test"])
        self.assertEqual(changedesc.fields_changed["test"]["old"],
                         [(i,) for i in old_value])
        self.assertEqual(changedesc.fields_changed["test"]["new"],
                         [(i,) for i in new_value])
        self.assertEqual(changedesc.fields_changed["test"]["added"], [(4,)])
        self.assertEqual(changedesc.fields_changed["test"]["removed"], [(1,)])

    def testRecordObjectListNameField(self):
        """Testing record_field_change with an object list (using name_field)"""
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

        self.assert_("test" in changedesc.fields_changed)
        self.assert_("old" in changedesc.fields_changed["test"])
        self.assert_("new" in changedesc.fields_changed["test"])
        self.assert_("added" in changedesc.fields_changed["test"])
        self.assert_("removed" in changedesc.fields_changed["test"])
        self.assertEqual(changedesc.fields_changed["test"]["old"],
                         [(obj.text, obj.get_absolute_url(), obj.id)
                          for obj in old_value])
        self.assertEqual(changedesc.fields_changed["test"]["new"],
                         [(obj.text, obj.get_absolute_url(), obj.id)
                          for obj in new_value])
        self.assertEqual(changedesc.fields_changed["test"]["added"],
                         [(new_value[2].text, new_value[2].get_absolute_url(),
                           new_value[2].id)])
        self.assertEqual(changedesc.fields_changed["test"]["removed"],
                         [(old_value[0].text, old_value[0].get_absolute_url(),
                           old_value[0].id)])

    def testRecordListMismatchType(self):
        """Testing record_field_change with mismatched types"""
        changedesc = ChangeDescription()
        self.assertRaises(ValueError,
                          changedesc.record_field_change,
                          "test", 123, True)
