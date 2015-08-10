from django.db.models.options import Options


_options = Options({})


# Index names changed in Django 1.5, with the introduction of index_together.
supports_index_together = hasattr(_options, 'index_together')
