from datetime import datetime

from django.db import models
from django.utils.translation import ugettext_lazy as _
from djblets.util.fields import JSONField


class ChangeDescription(models.Model):
    """
    The recorded set of changes, containing optional description text
    and fields that have changed.

    This is a general model that can be used in applications for recording
    changes how they see fit. A helper function, 'record_field_changed',
    can be used to record information in a standard way for most value types,
    but the 'fields_changed' dictionary can be manipulated however the caller
    chooses.

    A ChangeDescription is not bound to a particular model. It is up to models
    to establish relationships with a ChangeDescription.

    Each field in 'fields_changed' represents a changed field.

    For string fields, the following fields will be available:

       * 'old': The old value of the field
       * 'new': The new value of the field

    For list and set fields, the following fields will be available:

       * 'removed': The fields that were removed, if any.
       * 'added': The fields that were added, if any.
    """
    timestamp = models.DateTimeField(_('timestamp'), default=datetime.now)
    public = models.BooleanField(_("public"), default=False)
    text = models.TextField(_("change text"), blank=True)
    fields_changed = JSONField(_("fields changed"))

    def record_field_change(self, field, old_value, new_value,
                            name_field=None):
        """
        Records a field change.

        This will encode field changes following the rules in the overlying
        'ChangeDescription' documentation.

        'name_field' can be specified for lists or other iterables. When
        specified, each list item will be a tuple in the form of
        (object_name, object_url, object_id). Otherwise, it will be a
        tuple in the form of (item,).

        It is generally expected that fields with lists of model objects will
        have 'name_field' set, whereas lists of numbers or some other
        value type will not. Specifying a 'name_field' for non-objects will
        cause an AttributeError.
        """
        def serialize_changed_obj_list(items, name_field):
            if name_field:
                return [(getattr(item, name_field),
                         item.get_absolute_url(),
                         item.id)
                        for item in list(items)]
            else:
                return [(item,) for item in list(items)]

        if (type(old_value) != type(new_value) and
            not (isinstance(old_value, basestring) and
                 isinstance(new_value, basestring))):
            raise ValueError("%s (%s) and %s (%s) are of two different value "
                             "types." % (old_value, type(old_value),
                                         new_value, type(new_value)))

        if hasattr(old_value, "__iter__"):
            old_set = set(old_value)
            new_set = set(new_value)

            self.fields_changed[field] = {
                'old': serialize_changed_obj_list(old_value, name_field),
                'new': serialize_changed_obj_list(new_value, name_field),
                'added': serialize_changed_obj_list(new_set - old_set,
                                                    name_field),
                'removed': serialize_changed_obj_list(old_set - new_set,
                                                      name_field),
            }
        else:
            self.fields_changed[field] = {
                'old': (old_value,),
                'new': (new_value,),
            }

    def truncate_text(self):
        if len(self.text) > 60:
            return self.text[0:57] + "..."
        else:
            return self.text

    def __unicode__(self):
        return self.text

    class Meta:
        ordering = ['-timestamp']
