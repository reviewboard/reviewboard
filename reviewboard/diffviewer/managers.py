from django.db import models
from djblets.util.fields import Base64DecodedValue


class FileDiffDataManager(models.Manager):
    """
    A custom manager for FileDiffData

    Sets the binary data to a Base64DecodedValue, so that Base64Field is
    forced to encode the data. This is a workaround to Base64Field checking
    if the object has been saved into the database using the pk.
    """
    def get_or_create(self, *args, **kwargs):
        defaults = kwargs.get('defaults', {})

        if defaults and defaults['binary']:
            defaults['binary'] = \
                Base64DecodedValue(kwargs['defaults']['binary'])

        return super(FileDiffDataManager, self).get_or_create(*args, **kwargs)
