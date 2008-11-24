def fix_django_evolution_issues(settings):
    # XXX Django r8244 moves django.db.models.fields.files.ImageField and
    # FileField into django.db.models.files, causing existing
    # signatures to fail. For the purpose of loading, temporarily
    # place these back into fields. The next time the signature is
    # generated in Django Evolution, the correct, new location will be
    # written.
    #
    # TODO: Remove this when Django Evolution works again.
    from django.core.management import setup_environ
    project_directory = setup_environ(settings)

    import django.db.models.fields as model_fields
    import django.db.models.fields.files as model_files
    model_fields.ImageField = model_files.ImageField
    model_fields.FileField = model_files.FileField
