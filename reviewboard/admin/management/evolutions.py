from __future__ import unicode_literals

from django.core.management import call_command
from django_evolution import models as django_evolution

from reviewboard.diffviewer.models import FileDiff


def init_evolutions(app, created_models, **kwargs):
    """Attempt to initialize the Django Evolution schema signatures.

    This attempts to initialize the evolution signatures to sane values. This
    works around the issue where a first syncdb with Django Evolution (even on
    existing databases) will cause Django Evolution to assume the database is
    the most up to date, even if it's not. This will break the database. Our
    workarounds prevent this by starting off with sane values and doing some
    smart checks.
    """
    if FileDiff in created_models:
        # This is a new install. Let it continue through. The database will
        # be created with an up-to-date schema.
        return

    try:
        latest_version = django_evolution.Version.objects.latest('when')
    except django_evolution.Version.DoesNotExist:
        # This install didn't previously have Django Evolution. We might need
        # to prefill it with the schema from before the first db mutation.
        # However, we only want to do this if this is an existing database,
        # or users will have to evolve after the first install, which is
        # bad.
        latest_version = None

    if latest_version:
        # There's an existing Django Evolution install. Check to see if it's
        # broken, as it may be from the time just after the addition of
        # Django Evolution where it wouldn't migrate databases and instead
        # marked the schemas as being up to date in the stored signature.
        try:
            # If this succeeds, we're good.
            FileDiff.objects.filter(parent_diff64="")

            return
        except:
            # If that failed, then most likely it's due to the
            # parent_diff_base64 column not existing in the database, which
            # means that Django Evolution's view of the database and the
            # database itself are out of match from an early install during
            # the breakage period.
            #
            # We can feel free to nuke the Django Evolution tables so that
            # we can apply our own schema in order to kickstart a proper
            # evolution.
            django_evolution.Version.objects.all().delete()
            django_evolution.Evolution.objects.all().delete()

    # Load the Django Evolution fixture describing the database at the time
    # of the Django Evolution addition.
    call_command('loaddata', 'admin/fixtures/initial_evolution_schema.json',
                 verbosity=0)
