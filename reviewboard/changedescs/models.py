from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.db.models.query import QuerySet
from django.utils import six, timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import JSONField


@python_2_unicode_compatible
class ChangeDescription(models.Model):
    """The recorded set of changes, with a description and the changed fields.

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

    user = models.ForeignKey(User, null=True, blank=True)
    timestamp = models.DateTimeField(_('timestamp'), default=timezone.now)
    public = models.BooleanField(_("public"), default=False)
    text = models.TextField(_("change text"), blank=True)
    rich_text = models.BooleanField(_("rich text"), default=False)
    fields_changed = JSONField(_("fields changed"))

    def get_user(self, model=None):
        """Return the user associated with the change description.

        This function delegates to the model it is associated with (if
        provided) to determine the user if it has not been previously
        determined. Once the user has been determined, it will be saved to the
        database.

        Args:
            model (django.db.models.Model, optional):
                The model instance this change description is associated with.

        Returns:
            django.contrib.auth.models.User:
            The user associated with the change description, or
            :py:data:`None` if it could not be determined.
        """
        if (self.user is None and
            model and
            hasattr(model, 'determine_user_for_changedesc')):
            self.user = model.determine_user_for_changedesc(self)
            self.save(update_fields=('user',))

        return self.user

    def is_new_for_user(self, user, last_visited, model=None):
        """Return whether this change description is new for a user.

        The change description is considered new if their last visited
        time is older than the change description's timestamp and the
        user is not the one who created the change description.

        Args:
            user (django.contrib.auth.models.User):
                The user accessing the change description.

            last_visited (datetime.datetime):
                The last time the user accessed a page where the change
                description would be shown.

            model (django.db.models.Model, optional):
                The model instance this change description is associated with.
                This is needed for calculating a user, if one is not
                associated, and should generally be provided.

        Returns:
            bool:
            ``True`` if the change description is new to this user. ``False``
            if it's older than the last visited time or the user created it.
        """
        owner = self.get_user(model)

        return owner and user != owner and last_visited < self.timestamp

    def record_field_change(self, field, old_value, new_value,
                            name_field=None):
        """Record a field change.

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
        def serialize_changed_obj(item, name_field):
            return (getattr(item, name_field),
                    item.get_absolute_url(),
                    item.id)

        def serialize_changed_obj_list(items, name_field):
            if name_field:
                return [
                    serialize_changed_obj(item, name_field)
                    for item in items
                ]
            else:
                return [
                    (item,)
                    for item in items
                ]

        if (type(old_value) != type(new_value) and
            not (isinstance(old_value, six.string_types) and
                 isinstance(new_value, six.string_types)) and
            old_value is not None and new_value is not None):
            raise ValueError("%s (%s) and %s (%s) are of two different value "
                             "types." % (old_value, type(old_value),
                                         new_value, type(new_value)))

        if isinstance(old_value, (dict, list, set, tuple, QuerySet)):
            old_set = set(old_value)
            new_set = set(new_value)

            self.fields_changed[field] = {
                'old': serialize_changed_obj_list(old_value, name_field),
                'new': serialize_changed_obj_list(new_value, name_field),
                'added': serialize_changed_obj_list(new_set - old_set,
                                                    name_field),
                'removed': serialize_changed_obj_list(old_set - new_set,
                                                      name_field)
            }
        elif field == 'submitter':
            self.fields_changed[field] = {
                'old': [serialize_changed_obj(old_value, name_field)],
                'new': [serialize_changed_obj(new_value, name_field)],
            }
        else:
            self.fields_changed[field] = {
                'old': (old_value,),
                'new': (new_value,),
            }

    def __str__(self):
        """Return a string representation of the object."""
        return self.text

    def has_modified_fields(self):
        """Determine if the 'fields_changed' variable is non-empty.

        Uses the 'fields_changed' variable to determine if there are any
        current modifications being tracked to this ChangedDescription object.
        """
        return bool(self.fields_changed)

    class Meta:
        db_table = 'changedescs_changedescription'
        ordering = ['-timestamp']
        get_latest_by = "timestamp"
        verbose_name = _('Change Description')
        verbose_name_plural = _('Change Descriptions')
