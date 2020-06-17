"""Administration UI customization for models."""

from __future__ import unicode_literals

from django.contrib.admin import ModelAdmin as DjangoModelAdmin


class ModelAdmin(DjangoModelAdmin):
    """Base class for administration UI representations of models.

    This should be used instead of :py:class:`django.contrib.admin.ModelAdmin`
    for any new model registrations. It provides additional options for
    Review Board's administration UI.

    Version Added:
        4.0
    """

    #: The template used for any fieldsets on the model's Change Form.
    #:
    #: If not explicitly overridden, ``admin/includes/fieldset.html`` will
    #: be used.
    fieldset_template_name = None
